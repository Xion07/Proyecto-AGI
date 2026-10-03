#!/usr/bin/env python3
# Genera los audios en español con espeak-ng y los convierte a wav 8 kHz mono 16 bit,
# que es el formato que Asterisk reproduce sin transcodificar.
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompts import PROMPTS  # noqa: E402

DESTINO = sys.argv[1] if len(sys.argv) > 1 else "/var/lib/asterisk/sounds/agi_auth"
VOZ = "es-419"  # español latino; si tu espeak-ng no la trae, cambia a "es"


def main():
    for programa in ("espeak-ng", "sox"):
        if not shutil.which(programa):
            sys.exit(f"Falta {programa}. Instala con: sudo dnf install espeak-ng sox")

    os.makedirs(DESTINO, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for nombre, texto in PROMPTS.items():
            crudo = os.path.join(tmp, nombre + ".wav")
            final = os.path.join(DESTINO, nombre + ".wav")
            subprocess.run(["espeak-ng", "-v", VOZ, "-s", "150", "-w", crudo, texto], check=True)
            subprocess.run(["sox", "-V1", "-G", crudo, "-r", "8000", "-c", "1", "-b", "16", final], check=True)
            print("ok", nombre)

    # Ojo: el dueño de los audios debe ser el usuario de Asterisk; el instalador (o el paso
    # manual del documento) hace el chown, no lo hago aquí para no asumir el nombre del usuario.
    print(f"{len(PROMPTS)} audios en {DESTINO}")


if __name__ == "__main__":
    main()
