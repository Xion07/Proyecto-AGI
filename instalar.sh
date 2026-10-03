#!/usr/bin/env bash
# Instalador del proyecto AGI de autenticación.
# Detecto las rutas de Asterisk en vez de asumirlas, porque cambian entre distribuciones
# (Debian/Ubuntu usan /usr/share/asterisk; una instalación desde fuente usa /var/lib/asterisk).
# Si la detección falla, se pueden forzar: sudo AGI_DIR=... DATA_DIR=... CONF_DIR=... ./instalar.sh
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ok()    { printf '\033[32m[ok]\033[0m    %s\n' "$*"; }
info()  { printf '\033[34m[info]\033[0m  %s\n' "$*"; }
fallo() { printf '\033[31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

# ---------- 1. Revisiones previas ----------
[ "$(id -u)" -eq 0 ] || fallo "Corre el script con sudo: sudo ./instalar.sh"
command -v asterisk >/dev/null || fallo "No encuentro el comando 'asterisk'. ¿Está instalado?"
# Necesito Asterisk corriendo porque le pregunto sus rutas y al final recargo el dialplan
asterisk -rx "core show version" >/dev/null 2>&1 \
    || fallo "Asterisk no responde. Arráncalo con: sudo systemctl start asterisk"
ok "Asterisk está corriendo"

# ---------- 2. Detectar rutas ----------
valor_config() {
    # La ruta es la última columna de la línea, sin importar cómo se llame la etiqueta
    asterisk -rx "core show settings" | grep -i "$1" | head -n1 | awk '{print $NF}' || true
}
AGI_DIR="${AGI_DIR:-$(valor_config 'AGI')}"
DATA_DIR="${DATA_DIR:-$(valor_config 'Data directory')}"
CONF_DIR="${CONF_DIR:-$(valor_config 'Config directory')}"
: "${AGI_DIR:=/var/lib/asterisk/agi-bin}"
: "${DATA_DIR:=/var/lib/asterisk}"
: "${CONF_DIR:=/etc/asterisk}"
SONIDOS_DIR="${SONIDOS_DIR:-$DATA_DIR/sounds/agi_auth}"

# Usuario que corre Asterisk (normalmente 'asterisk'; si corre como root, uso root)
AST_USER="${AST_USER:-$(ps -o user= -C asterisk 2>/dev/null | head -n1 | tr -d ' ' || true)}"
: "${AST_USER:=asterisk}"
id "$AST_USER" >/dev/null 2>&1 || { info "No existe el usuario '$AST_USER', uso root"; AST_USER=root; }
AST_GRUPO="$(id -gn "$AST_USER")"

info "AGI:      $AGI_DIR"
info "Sonidos:  $SONIDOS_DIR"
info "Config:   $CONF_DIR"
info "Usuario:  $AST_USER:$AST_GRUPO"

# ---------- 3. Dependencias ----------
faltan=()
command -v python3   >/dev/null || faltan+=(python3)
command -v espeak-ng >/dev/null || faltan+=(espeak-ng)
command -v sox       >/dev/null || faltan+=(sox)
if [ ${#faltan[@]} -gt 0 ]; then
    info "Instalando dependencias: ${faltan[*]}"
    if   command -v apt-get >/dev/null; then apt-get update -qq && apt-get install -y "${faltan[@]}"
    elif command -v dnf     >/dev/null; then dnf install -y "${faltan[@]}"
    elif command -v yum     >/dev/null; then yum install -y "${faltan[@]}"
    else fallo "No sé instalar paquetes en este sistema. Instala a mano: ${faltan[*]}"
    fi
fi
ok "Dependencias listas"

# ---------- 4. Copiar scripts ----------
mkdir -p "$AGI_DIR"
install -m 755 -o "$AST_USER" -g "$AST_GRUPO" "$AQUI/auth.py" "$AGI_DIR/auth.py"
for f in prompts.py init_db.py generar_prompts.py; do
    install -m 644 -o "$AST_USER" -g "$AST_GRUPO" "$AQUI/$f" "$AGI_DIR/$f"
done
ok "Scripts copiados a $AGI_DIR"

# ---------- 5. Audios en español ----------
python3 "$AGI_DIR/generar_prompts.py" "$SONIDOS_DIR" >/dev/null
chown -R "$AST_USER:$AST_GRUPO" "$SONIDOS_DIR"
ok "Audios generados en $SONIDOS_DIR"

# ---------- 6. Base de datos ----------
AGI_AUTH_USER="$AST_USER" python3 "$AGI_DIR/init_db.py"
ok "Base de datos lista"

# ---------- 7. Dialplan ----------
mkdir -p "$CONF_DIR"
install -m 640 -o "$AST_USER" -g "$AST_GRUPO" "$AQUI/extensions_agi.conf" "$CONF_DIR/extensions_agi.conf"
touch "$CONF_DIR/extensions.conf"
if ! grep -q 'extensions_agi.conf' "$CONF_DIR/extensions.conf"; then
    cp "$CONF_DIR/extensions.conf" "$CONF_DIR/extensions.conf.bak_agi"   # respaldo por si algo sale mal
    printf '\n#include extensions_agi.conf\n' >> "$CONF_DIR/extensions.conf"
fi
ok "Dialplan instalado (respaldo en extensions.conf.bak_agi)"

# ---------- 8. SELinux (Fedora/RHEL) ----------
if command -v restorecon >/dev/null 2>&1; then
    restorecon -R "$AGI_DIR" "$SONIDOS_DIR" "$(dirname "$SONIDOS_DIR")" /var/lib/asterisk/agi_auth 2>/dev/null || true
fi

# ---------- 9. Recargar y verificar ----------
asterisk -rx "dialplan reload" >/dev/null
asterisk -rx "dialplan show agi-auth" | grep -q '700' \
    || fallo "El contexto [agi-auth] no aparece en el dialplan. Revisa $CONF_DIR/extensions.conf"
ok "Dialplan cargado: la extensión 700 existe"

# Autoprueba: ejecuto el AGI como el usuario de Asterisk y le simulo una llamada que cuelga.
# Si llega a pedir el usuario, es porque Python, permisos, BD y audios están bien.
salida="$(printf 'agi_request: auth.py\n\n200 result=1\n' \
    | runuser -u "$AST_USER" -- python3 "$AGI_DIR/auth.py" 2>&1 || true)"
if printf '%s' "$salida" | grep -q 'pedir_usuario'; then
    ok "Autoprueba superada"
else
    printf '%s\n' "$salida"
    fallo "La autoprueba falló. Mira la sección 'Solución de problemas' de la documentación."
fi

echo
echo "Instalación terminada. Registra un softphone y llama a la extensión 700."
echo "Admin: 9999 / 482913   |   Usuario: 1001 / 135792"
