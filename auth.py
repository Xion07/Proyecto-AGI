#!/usr/bin/env python3
# AGI de autenticación por teclado (DTMF).
# Cada frase se la pasa al AGI de Google ya instalado en Issabel
# (por defecto googletts.agi). Ese script baja el audio, lo guarda
# en caché y lo reproduce en el canal.
import hashlib
import hmac
import logging
import os
import re
import secrets
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompts import NOMBRES_DIGITO, PROMPTS  # noqa: E402

# ---------- Configuración ----------
DB_PATH = os.environ.get("AGI_AUTH_DB", "/var/lib/asterisk/agi_auth/usuarios.db")
TTS_CONF = os.path.join(os.path.dirname(DB_PATH), "google_tts.conf")
LOG_PATH = "/var/log/asterisk/agi_auth.log"
MAX_INTENTOS = 3
TIMEOUT_MS = 10000
INTERDIGIT_MS = 4000
ITERACIONES = 100_000
CLAVE_MIN, CLAVE_MAX = 6, 8
USUARIO_MIN, USUARIO_MAX = 3, 8
SCRIPT_TTS_DEFECTO = "googletts.agi"
IDIOMA_DEFECTO = "es"


class Colgado(Exception):
    """El llamante colgó o Asterisk cerró el canal."""


class ErrorTTS(Exception):
    """El AGI de Google no pudo reproducir la frase."""


# ---------- Voz ----------
def sanear_tts(texto):
    """Deja la frase en una sola pieza para el comando EXEC.

    EXEC entrega a la aplicación AGI una cadena separada por comas:
    script,texto,idioma. Una coma, comillas o un salto de línea dentro
    del texto romperían ese parseo o el protocolo AGI.
    """
    texto = str(texto or "")
    texto = texto.replace(",", ".")
    texto = texto.replace(";", ".")
    texto = texto.replace('"', "")
    texto = texto.replace("'", "")
    texto = re.sub(r"[\\|*~<>^()\[\]{}]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def comando_tts(texto, script, lang, speed=""):
    """Arma el EXEC que llama al AGI de Google ya instalado en Issabel.

    Las comillas envuelven todo el tercer argumento. El parser de AGI
    parte por espacios, y solo respeta comillas si abren el argumento.
    Por eso no sirve googletts.agi,"texto con espacios",es.
    """
    texto = sanear_tts(texto)
    script = str(script or "").strip()
    lang = str(lang or "").strip() or IDIOMA_DEFECTO
    speed = str(speed or "").strip()
    if not texto:
        raise ValueError("texto vacío")
    if not script or "," in script or '"' in script:
        raise ValueError("nombre de AGI inválido")
    if not re.fullmatch(r"[A-Za-z]{2}(-[A-Za-z0-9]+)?", lang):
        raise ValueError("idioma inválido")
    if speed and not re.fullmatch(r"[0-9]+(\.[0-9]+)?", speed):
        raise ValueError("velocidad inválida")
    datos = f"{script},{texto},{lang}"
    if speed:
        datos = f"{datos},{speed}"
    return f'EXEC AGI "{datos}"'


def leer_config_tts():
    script, lang, speed = SCRIPT_TTS_DEFECTO, IDIOMA_DEFECTO, ""
    try:
        with open(TTS_CONF, encoding="utf-8") as archivo:
            for linea in archivo:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                clave, valor = clave.strip(), valor.strip()
                if clave == "script" and valor:
                    script = valor
                elif clave == "lang" and valor:
                    lang = valor
                elif clave == "speed":
                    speed = valor
    except OSError:
        pass
    return script, lang, speed


# ---------- Seguridad ----------
def hashear(clave, salt=None):
    # PBKDF2 con sal por usuario: nunca se guarda la clave en texto plano.
    if salt is None:
        salt = secrets.token_bytes(16)
    resumen = hashlib.pbkdf2_hmac("sha256", clave.encode(), salt, ITERACIONES)
    return salt.hex(), resumen.hex()


def verificar(clave, salt_hex, hash_hex):
    _, resumen = hashear(clave, bytes.fromhex(salt_hex))
    return hmac.compare_digest(resumen, hash_hex)


def validar_clave(clave, usuario, actual=None):
    """Devuelve None si la clave cumple la política, o el nombre del aviso."""
    if not clave.isdigit() or not CLAVE_MIN <= len(clave) <= CLAVE_MAX:
        return "clave_longitud"
    if len(set(clave)) == 1:
        return "clave_iguales"
    diferencias = {int(b) - int(a) for a, b in zip(clave, clave[1:])}
    if diferencias in ({1}, {-1}):
        return "clave_secuencia"
    if clave == usuario:
        return "clave_igual_usuario"
    if actual is not None and clave == actual:
        return "clave_igual_actual"
    return None


# ---------- Base de datos ----------
def abrir_db():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"No existe la base de datos {DB_PATH}. Corre init_db.py")
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def buscar_usuario(conexion, usuario):
    return conexion.execute(
        "SELECT usuario, rol, salt, hash FROM usuarios WHERE usuario = ?", (usuario,)
    ).fetchone()


# ---------- Protocolo AGI ----------
class AGI:
    def __init__(self):
        self.env = {}
        while True:
            linea = self._recibir()
            if not linea:
                break
            if ":" in linea:
                clave, valor = linea.split(":", 1)
                self.env[clave.strip()] = valor.strip()
        script, lang, speed = leer_config_tts()
        # Los argumentos del dialplan pisan el archivo de configuración.
        self.tts_script = self.env.get("agi_arg_1") or script
        self.tts_lang = self.env.get("agi_arg_2") or lang
        self.tts_speed = self.env.get("agi_arg_3") or speed

    def _enviar(self, comando):
        sys.stdout.buffer.write((comando + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()

    def _recibir(self):
        linea = sys.stdin.buffer.readline()
        if not linea:
            return ""
        return linea.decode("utf-8", errors="replace").strip()

    def _cmd(self, comando, exigente=True):
        self._enviar(comando)
        respuesta = self._recibir()
        logging.debug("%s -> %s", comando, respuesta)
        if not respuesta:
            if exigente:
                raise Colgado()
            return None
        hallado = re.match(r"200 result=(\S*)", respuesta)
        if not hallado:
            if exigente:
                raise Colgado()
            return None
        valor = hallado.group(1)
        if valor == "-1":
            if exigente:
                raise Colgado()
            return None
        return valor

    def canal_activo(self):
        # 0 = colgado. 6 = establecida. Con 2 o más el canal sigue vivo.
        estado = self._cmd("CHANNEL STATUS", exigente=False)
        try:
            return estado is not None and int(estado) >= 2
        except ValueError:
            return False

    def decir(self, texto):
        texto = sanear_tts(texto)
        if not texto:
            return
        try:
            comando = comando_tts(texto, self.tts_script, self.tts_lang, self.tts_speed)
        except ValueError as exc:
            logging.error("no armo el TTS: %s", exc)
            raise ErrorTTS(str(exc))
        logging.info("google tts: %s", texto)
        aviso = texto if len(texto) <= 80 else texto[:77] + "..."
        self._cmd(f'VERBOSE "Google TTS: {aviso}" 3', exigente=False)
        resultado = self._cmd(comando, exigente=False)
        if resultado is None:
            if not self.canal_activo():
                raise Colgado()
            logging.error("falló %s", comando)
            raise ErrorTTS(texto)

    def decir_prompt(self, nombre):
        self.decir(PROMPTS[nombre])

    def beep(self):
        # El bip avisa que la frase terminó y ya se pueden marcar los dígitos.
        if self._cmd('STREAM FILE en/beep ""', exigente=False) is None:
            self._cmd('STREAM FILE beep ""', exigente=False)

    def leer_digitos(self, max_digitos):
        """Lee DTMF hasta #, el máximo o un silencio.

        Google ya reprodujo la frase. GET DATA no sirve aquí porque exige
        un archivo de sounds/. Con un solo dígito (menús) regresa en cuanto
        llega esa tecla.
        """
        teclas = []
        espera = TIMEOUT_MS
        while len(teclas) < max_digitos:
            codigo = self._cmd(f"WAIT FOR DIGIT {espera}")
            if codigo in ("0", "", None):
                break
            try:
                tecla = chr(int(codigo))
            except ValueError:
                break
            if tecla == "#":
                break
            if not tecla.isdigit():
                break
            teclas.append(tecla)
            espera = INTERDIGIT_MS
        return "".join(teclas)

    def preguntar(self, nombre, max_digitos):
        self.decir_prompt(nombre)
        self.beep()
        return self.leer_digitos(max_digitos)

    def decir_con_digitos(self, frase, digitos):
        if not str(digitos).isdigit():
            return
        palabras = " ".join(NOMBRES_DIGITO[int(d)] for d in str(digitos))
        self.decir(f"{frase} {palabras}.")


# ---------- Flujos ----------
def elegir_rol(agi):
    for _ in range(MAX_INTENTOS):
        opcion = agi.preguntar("bienvenida", 1)
        if opcion == "1":
            return "usuario"
        if opcion == "2":
            return "admin"
        agi.decir_prompt("opcion_invalida")
    return None


def autenticar(agi, conexion, rol_esperado):
    for _ in range(MAX_INTENTOS):
        usuario = agi.preguntar("pedir_usuario", USUARIO_MAX + 1)
        clave = agi.preguntar("pedir_clave", CLAVE_MAX + 1)
        fila = buscar_usuario(conexion, usuario) if usuario else None
        if not fila or not verificar(clave, fila["salt"], fila["hash"]):
            logging.info("login fallido usuario=%s opcion=%s", usuario, rol_esperado)
            agi.decir_prompt("login_fail")
            continue
        if fila["rol"] != rol_esperado:
            logging.info("rol incorrecto usuario=%s opcion=%s", usuario, rol_esperado)
            agi.decir_prompt("sin_permiso")
            continue
        logging.info("login ok usuario=%s rol=%s", usuario, rol_esperado)
        agi.decir_prompt("login_ok")
        return fila["usuario"]
    agi.decir_prompt("intentos_agotados")
    return None


def cambiar_clave(agi, conexion, usuario):
    fila = buscar_usuario(conexion, usuario)
    actual = agi.preguntar("pedir_clave_actual", CLAVE_MAX + 1)
    if not verificar(actual, fila["salt"], fila["hash"]):
        logging.info("cambio de clave rechazado usuario=%s", usuario)
        agi.decir_prompt("clave_actual_incorrecta")
        return

    nueva = agi.preguntar("pedir_clave_nueva", CLAVE_MAX + 1)
    error = validar_clave(nueva, usuario, actual)
    if error:
        agi.decir_prompt(error)
        agi.decir_prompt("politica_clave")
        return

    if agi.preguntar("confirmar_clave_nueva", CLAVE_MAX + 1) != nueva:
        agi.decir_prompt("claves_no_coinciden")
        return

    salt, resumen = hashear(nueva)
    conexion.execute(
        "UPDATE usuarios SET salt = ?, hash = ? WHERE usuario = ?",
        (salt, resumen, usuario),
    )
    conexion.commit()
    logging.info("clave cambiada usuario=%s", usuario)
    agi.decir_prompt("clave_cambiada")


def crear_cuenta(agi, conexion, admin):
    nuevo = agi.preguntar("pedir_nuevo_usuario", USUARIO_MAX + 1)
    if not (nuevo.isdigit() and USUARIO_MIN <= len(nuevo) <= USUARIO_MAX):
        agi.decir_prompt("usuario_invalido")
        return
    if buscar_usuario(conexion, nuevo):
        agi.decir_prompt("usuario_existe")
        return

    clave = agi.preguntar("pedir_clave_inicial", CLAVE_MAX + 1)
    error = validar_clave(clave, nuevo)
    if error:
        agi.decir_prompt(error)
        agi.decir_prompt("politica_clave")
        return

    agi.decir_con_digitos(PROMPTS["va_a_crear"], nuevo)
    if agi.preguntar("confirmar_cancelar", 1) != "1":
        agi.decir_prompt("accion_cancelada")
        return

    salt, resumen = hashear(clave)
    conexion.execute(
        "INSERT INTO usuarios (usuario, rol, salt, hash) VALUES (?, 'usuario', ?, ?)",
        (nuevo, salt, resumen),
    )
    conexion.commit()
    logging.info("cuenta creada usuario=%s por admin=%s", nuevo, admin)
    agi.decir_prompt("cuenta_creada")


def menu(agi, conexion, usuario, rol):
    nombre_menu = "menu_admin" if rol == "admin" else "menu_usuario"
    fallos = 0
    while fallos < MAX_INTENTOS:
        opcion = agi.preguntar(nombre_menu, 1)
        if opcion == "9":
            return
        if rol == "admin" and opcion == "1":
            fallos = 0
            crear_cuenta(agi, conexion, usuario)
        elif (rol == "admin" and opcion == "2") or (rol == "usuario" and opcion == "1"):
            fallos = 0
            cambiar_clave(agi, conexion, usuario)
        else:
            fallos += 1
            agi.decir_prompt("opcion_invalida")


def configurar_log():
    formato = logging.Formatter("%(asctime)s %(message)s")
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    try:
        archivo = logging.FileHandler(LOG_PATH)
        archivo.setFormatter(formato)
        raiz.addHandler(archivo)
    except OSError:
        pass
    consola = logging.StreamHandler(sys.stderr)
    consola.setFormatter(formato)
    raiz.addHandler(consola)


def main():
    configurar_log()
    agi = AGI()
    conexion = None
    try:
        logging.info(
            "llamada google script=%s lang=%s", agi.tts_script, agi.tts_lang
        )
        conexion = abrir_db()
        rol = elegir_rol(agi)
        if rol:
            usuario = autenticar(agi, conexion, rol)
            if usuario:
                menu(agi, conexion, usuario, rol)
        agi.decir_prompt("despedida")
    except Colgado:
        logging.info("el llamante colgó")
    except ErrorTTS:
        logging.error(
            "Google TTS no habló. Prueba la extensión 702. "
            "Revisa internet, sox, mpg123 y %s",
            agi.tts_script,
        )
        try:
            agi.beep()
        except Colgado:
            pass
    except Exception:
        logging.exception("error inesperado")
        try:
            agi.decir_prompt("error_sistema")
        except (Colgado, ErrorTTS):
            pass
    finally:
        if conexion:
            conexion.close()


if __name__ == "__main__":
    main()
