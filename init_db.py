#!/usr/bin/env python3
# Crea la base y siembra un administrador y un usuario de prueba.
# Si esas cuentas ya existen, conserva su contraseña.
import os
import pwd
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import DB_PATH, hashear, validar_clave  # noqa: E402

USUARIO_SISTEMA = os.environ.get("AGI_AUTH_USER", "asterisk")

SEMILLA = [
    ("9999", "admin", "482913"),
    ("1001", "usuario", "135792"),
]


def main():
    carpeta = os.path.dirname(DB_PATH)
    os.makedirs(carpeta, exist_ok=True)

    conexion = sqlite3.connect(DB_PATH)
    conexion.execute(
        """CREATE TABLE IF NOT EXISTS usuarios (
               usuario TEXT PRIMARY KEY,
               rol     TEXT NOT NULL CHECK (rol IN ('usuario', 'admin')),
               salt    TEXT NOT NULL,
               hash    TEXT NOT NULL,
               creado  TEXT DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    for usuario, rol, clave in SEMILLA:
        assert validar_clave(clave, usuario) is None, f"clave semilla inválida: {usuario}"
        existe = conexion.execute(
            "SELECT 1 FROM usuarios WHERE usuario = ?", (usuario,)
        ).fetchone()
        if existe:
            print(f"{rol:8} {usuario} ya existía: se conserva su contraseña")
            continue
        salt, resumen = hashear(clave)
        conexion.execute(
            "INSERT INTO usuarios (usuario, rol, salt, hash) VALUES (?, ?, ?, ?)",
            (usuario, rol, salt, resumen),
        )
        print(f"{rol:8} {usuario} / {clave}")
    conexion.commit()
    conexion.close()

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
