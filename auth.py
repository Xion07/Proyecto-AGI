#!/usr/bin/env python3
# AGI de autenticación: ingreso como usuario o administrador por teclado (DTMF).
import hashlib
import hmac
import logging
import os
import re
import secrets
import sqlite3
import sys

# ---------- Configuración ----------
# La BD vive en su propia carpeta porque SQLite crea archivos temporales (journal)
# junto a la base y el usuario asterisk necesita permiso de escritura en esa carpeta.
DB_PATH = os.environ.get("AGI_AUTH_DB", "/var/lib/asterisk/agi_auth/usuarios.db")
CARPETA_SONIDOS = "agi_auth"   # relativa a /var/lib/asterisk/sounds
LOG_PATH = "/var/log/asterisk/agi_auth.log"
MAX_INTENTOS = 3
TIMEOUT_MS = 8000
ITERACIONES = 100_000
CLAVE_MIN, CLAVE_MAX = 6, 8
USUARIO_MIN, USUARIO_MAX = 3, 8


# ---------- Seguridad ----------
def hashear(clave, salt=None):
    # Uso PBKDF2 con sal por usuario: así dos usuarios con la misma clave
    # no tienen el mismo hash y nunca guardo la clave en texto plano.
    if salt is None:
        salt = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", clave.encode(), salt, ITERACIONES)
    return salt.hex(), h.hex()


def verificar(clave, salt_hex, hash_hex):
    _, h = hashear(clave, bytes.fromhex(salt_hex))
    # compare_digest para no filtrar información por tiempo de respuesta
    return hmac.compare_digest(h, hash_hex)


def validar_clave(clave, usuario, actual=None):
    """Devuelve None si la clave cumple la política, o el nombre del audio con el error."""
    # Por teléfono solo se pueden digitar números, por eso la política es numérica
    if not clave.isdigit() or not CLAVE_MIN <= len(clave) <= CLAVE_MAX:
        return "clave_longitud"
    if len(set(clave)) == 1:
        return "clave_iguales"
    difs = {int(b) - int(a) for a, b in zip(clave, clave[1:])}
    if difs in ({1}, {-1}):  # 123456 o 654321
        return "clave_secuencia"
    if clave == usuario:
        return "clave_igual_usuario"
    if actual is not None and clave == actual:
        return "clave_igual_actual"
    return None


# ---------- Base de datos ----------
def abrir_db():
    # Reviso que exista porque sqlite3.connect crea un archivo vacío sin avisar
    # y después el error sale raro ("no such table").
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"No existe la base de datos {DB_PATH}. Corre init_db.py")
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def buscar_usuario(con, usuario):
    return con.execute(
        "SELECT usuario, rol, salt, hash FROM usuarios WHERE usuario = ?", (usuario,)
    ).fetchone()


# ---------- Protocolo AGI ----------
class Colgado(Exception):
    """El llamante colgó (o Asterisk cerró el canal)."""


class AGI:
    def __init__(self):
        # Asterisk manda las variables del canal y termina con una línea vacía
        self.env = {}
        while True:
            linea = sys.stdin.readline().strip()
            if not linea:
                break
            if ":" in linea:
                k, v = linea.split(":", 1)
                self.env[k.strip()] = v.strip()

    def _cmd(self, comando):
        sys.stdout.write(comando + "\n")
        sys.stdout.flush()
        resp = sys.stdin.readline()
        logging.debug("%s -> %s", comando, resp.strip())
        m = re.match(r"200 result=(\S*)", resp)
        # Cualquier cosa distinta de "200" (510, 511 canal muerto...) o result=-1
        # la trato como colgada para cortar el script limpio.
        if not m or m.group(1) == "-1":
            raise Colgado()
        return m.group(1)

    def decir(self, nombre):
        self._cmd(f'STREAM FILE {CARPETA_SONIDOS}/{nombre} ""')

    def preguntar(self, nombre, max_digitos):
        # GET DATA reproduce el audio y recoge dígitos; termina con # o al llegar al máximo
        return self._cmd(f"GET DATA {CARPETA_SONIDOS}/{nombre} {TIMEOUT_MS} {max_digitos}")

    def decir_digitos(self, digitos):
        for d in digitos:
            self.decir(f"d_{d}")


# ---------- Flujos ----------
def elegir_rol(agi):
    for _ in range(MAX_INTENTOS):
        op = agi.preguntar("bienvenida", 1)
        if op == "1":
            return "usuario"
        if op == "2":
            return "admin"
        agi.decir("opcion_invalida")
    return None


def autenticar(agi, con, rol_esperado):
    # Pido un dígito más del máximo para detectar entradas demasiado largas
    for _ in range(MAX_INTENTOS):
        usuario = agi.preguntar("pedir_usuario", USUARIO_MAX + 1)
        clave = agi.preguntar("pedir_clave", CLAVE_MAX + 1)
        fila = buscar_usuario(con, usuario) if usuario else None
        # Mismo mensaje si falla el usuario o la clave, para no revelar cuál existe
        if not fila or not verificar(clave, fila["salt"], fila["hash"]):
            logging.info("login fallido usuario=%s opcion=%s", usuario, rol_esperado)
            agi.decir("login_fail")
            continue
        if fila["rol"] != rol_esperado:
            logging.info("rol incorrecto usuario=%s opcion=%s", usuario, rol_esperado)
            agi.decir("sin_permiso")
            continue
        logging.info("login ok usuario=%s rol=%s", usuario, rol_esperado)
        agi.decir("login_ok")
        return fila["usuario"]
    agi.decir("intentos_agotados")
    return None


def cambiar_clave(agi, con, usuario):
    fila = buscar_usuario(con, usuario)
    actual = agi.preguntar("pedir_clave_actual", CLAVE_MAX + 1)
    if not verificar(actual, fila["salt"], fila["hash"]):
        logging.info("cambio de clave rechazado (clave actual mala) usuario=%s", usuario)
        agi.decir("clave_actual_incorrecta")
        return

    nueva = agi.preguntar("pedir_clave_nueva", CLAVE_MAX + 1)
    error = validar_clave(nueva, usuario, actual)
    if error:
        agi.decir(error)
        agi.decir("politica_clave")
        return

    if agi.preguntar("confirmar_clave_nueva", CLAVE_MAX + 1) != nueva:
        agi.decir("claves_no_coinciden")
        return

    salt, h = hashear(nueva)
    con.execute("UPDATE usuarios SET salt = ?, hash = ? WHERE usuario = ?", (salt, h, usuario))
    con.commit()
    logging.info("clave cambiada usuario=%s", usuario)
    agi.decir("clave_cambiada")


def crear_cuenta(agi, con, admin):
    nuevo = agi.preguntar("pedir_nuevo_usuario", USUARIO_MAX + 1)
    if not (nuevo.isdigit() and USUARIO_MIN <= len(nuevo) <= USUARIO_MAX):
        agi.decir("usuario_invalido")
        return
    if buscar_usuario(con, nuevo):
        agi.decir("usuario_existe")
        return

    clave = agi.preguntar("pedir_clave_inicial", CLAVE_MAX + 1)
    error = validar_clave(clave, nuevo)
    if error:
        agi.decir(error)
        agi.decir("politica_clave")
        return

    # Le leo el número de vuelta al admin para que confirme antes de guardar
    agi.decir("va_a_crear")
    agi.decir_digitos(nuevo)
    if agi.preguntar("confirmar_cancelar", 1) != "1":
        agi.decir("accion_cancelada")
        return

    salt, h = hashear(clave)
    con.execute(
        "INSERT INTO usuarios (usuario, rol, salt, hash) VALUES (?, 'usuario', ?, ?)",
        (nuevo, salt, h),
    )
    con.commit()
    logging.info("cuenta creada usuario=%s por admin=%s", nuevo, admin)
    agi.decir("cuenta_creada")


def menu(agi, con, usuario, rol):
    nombre_menu = "menu_admin" if rol == "admin" else "menu_usuario"
    fallos = 0
    while fallos < MAX_INTENTOS:
        op = agi.preguntar(nombre_menu, 1)
        if op == "9":
            return
        if rol == "admin" and op == "1":
            fallos = 0
            crear_cuenta(agi, con, usuario)
        elif (rol == "admin" and op == "2") or (rol == "usuario" and op == "1"):
            fallos = 0
            cambiar_clave(agi, con, usuario)
        else:
            fallos += 1
            agi.decir("opcion_invalida")


def configurar_log():
    try:
        logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                            format="%(asctime)s %(message)s")
    except OSError:
        # Si no puedo escribir el log, que al menos salga por stderr (se ve en la CLI de Asterisk)
        logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                            format="%(asctime)s %(message)s")


def main():
    configurar_log()
    agi = AGI()
    con = None
    try:
        con = abrir_db()
        rol = elegir_rol(agi)
        if rol:
            usuario = autenticar(agi, con, rol)
            if usuario:
                menu(agi, con, usuario, rol)
        agi.decir("despedida")
    except Colgado:
        logging.info("el llamante colgó")
    except Exception:
        logging.exception("error inesperado")
        try:
            agi.decir("error_sistema")
        except Colgado:
            pass
    finally:
        if con:
            con.close()


if __name__ == "__main__":
    main()
