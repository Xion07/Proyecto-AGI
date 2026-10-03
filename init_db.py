#!/usr/bin/env python3
# Crea la base de datos y siembra un administrador y un usuario de prueba.
# Correrlo con sudo para poder dejar la carpeta y el archivo a nombre de asterisk.
import os
import pwd
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import DB_PATH, hashear, validar_clave  # noqa: E402

# Usuario del sistema que corre Asterisk (el instalador lo detecta y lo pasa por variable)
USUARIO_SISTEMA = os.environ.get("AGI_AUTH_USER", "asterisk")

# Cuentas iniciales: (usuario, rol, clave). Cámbialas después de la primera prueba.
SEMILLA = [
    ("9999", "admin", "482913"),
    ("1001", "usuario", "135792"),
]


def main():
    carpeta = os.path.dirname(DB_PATH)
    os.makedirs(carpeta, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    con.execute(
        """CREATE TABLE IF NOT EXISTS usuarios (
               usuario TEXT PRIMARY KEY,
               rol     TEXT NOT NULL CHECK (rol IN ('usuario', 'admin')),
               salt    TEXT NOT NULL,
               hash    TEXT NOT NULL,
               creado  TEXT DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    for usuario, rol, clave in SEMILLA:
        # Valido la semilla con la misma política para no meter claves que la política rechazaría
        assert validar_clave(clave, usuario) is None, f"clave semilla inválida: {usuario}"
        salt, h = hashear(clave)
        con.execute(
            "INSERT OR IGNORE INTO usuarios (usuario, rol, salt, hash) VALUES (?, ?, ?, ?)",
            (usuario, rol, salt, h),
        )
        print(f"{rol:8} {usuario} / {clave}")
    con.commit()
    con.close()

    # Dejo carpeta y archivo a nombre de asterisk; sin esto el AGI no puede escribir
    try:
        pw = pwd.getpwnam(USUARIO_SISTEMA)
        for ruta in (carpeta, DB_PATH):
            os.chown(ruta, pw.pw_uid, pw.pw_gid)
        os.chmod(carpeta, 0o750)
        os.chmod(DB_PATH, 0o640)
    except (KeyError, PermissionError):
        print(f"Ojo: no pude dejar la BD a nombre de '{USUARIO_SISTEMA}'. Hazlo a mano con chown.")
    print(f"Base lista en {DB_PATH}")


if __name__ == "__main__":
    main()
