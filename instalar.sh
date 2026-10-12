#!/usr/bin/env bash
# Instala el AGI de autenticación usando el TTS de Google que ya está en Issabel.
# La extensión 700 es el sistema. La 702 dice una frase suelta para probar la voz.
# Si quedó una prueba anterior en la 701, la quita.
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ok()    { printf '\033[32m[ok]\033[0m    %s\n' "$*"; }
info()  { printf '\033[34m[info]\033[0m  %s\n' "$*"; }
fallo() { printf '\033[31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || fallo "Corre el script con sudo: sudo bash instalar.sh"
command -v asterisk >/dev/null || fallo "No encuentro el comando asterisk."
asterisk -rx "core show version" >/dev/null 2>&1 \
    || fallo "Asterisk no responde. Arráncalo con: sudo systemctl start asterisk"
ok "Asterisk está corriendo"

valor_config() {
    local salida
    salida="$(asterisk -rx "core show settings" 2>/dev/null || true)"
    printf '%s\n' "$salida" | awk -v k="$1" 'BEGIN{IGNORECASE=1} index(tolower($0), tolower(k)){print $NF; exit}' || true
}
AGI_DIR="${AGI_DIR:-$(valor_config 'AGI')}"
DATA_DIR="${DATA_DIR:-$(valor_config 'Data directory')}"
CONF_DIR="${CONF_DIR:-$(valor_config 'Config directory')}"
: "${AGI_DIR:=/var/lib/asterisk/agi-bin}"
: "${DATA_DIR:=/var/lib/asterisk}"
: "${CONF_DIR:=/etc/asterisk}"

AST_USER="${AST_USER:-$(ps -o user= -C asterisk 2>/dev/null | head -n1 | tr -d ' ' || true)}"
: "${AST_USER:=asterisk}"
id "$AST_USER" >/dev/null 2>&1 || { info "No existe el usuario '$AST_USER', uso root"; AST_USER=root; }
AST_GRUPO="$(id -gn "$AST_USER")"

info "AGI:    $AGI_DIR"
info "Config: $CONF_DIR"
info "Usuario: $AST_USER:$AST_GRUPO"

buscar_google() {
    local dir="$1"
    local nombre hallado
    [ -d "$dir" ] || return 1
    for nombre in googletts.agi google_tts.agi GoogleTTS.agi ttsgoogle.agi; do
        if [ -f "$dir/$nombre" ]; then
            printf '%s\n' "$dir/$nombre"
            return 0
        fi
        if [ -f "$dir/googletts/$nombre" ]; then
            printf '%s\n' "$dir/googletts/$nombre"
            return 0
        fi
    done
    hallado="$(find "$dir" -maxdepth 2 -type f \( -iname 'googletts.agi' -o -iname '*google*tts*.agi' -o -iname '*tts*google*.agi' \) -print -quit 2>/dev/null || true)"
    if [ -n "$hallado" ]; then
        printf '%s\n' "$hallado"
        return 0
    fi
    return 1
}

RUTA_GOOGLE=""
if [ -n "${GOOGLE_AGI:-}" ]; then
    if [ -f "$GOOGLE_AGI" ]; then
        RUTA_GOOGLE="$GOOGLE_AGI"
    elif [ -f "$AGI_DIR/$GOOGLE_AGI" ]; then
        RUTA_GOOGLE="$AGI_DIR/$GOOGLE_AGI"
    else
        fallo "No existe GOOGLE_AGI=$GOOGLE_AGI"
    fi
else
    for dir in "$AGI_DIR" /var/lib/asterisk/agi-bin /usr/share/asterisk/agi-bin; do
        if RUTA_GOOGLE="$(buscar_google "$dir")"; then
            break
        fi
        RUTA_GOOGLE=""
    done
fi

if [ -z "$RUTA_GOOGLE" ]; then
    info "Busqué googletts.agi en $AGI_DIR y no está."
    find "$AGI_DIR" -maxdepth 2 -type f \( -iname '*google*' -o -iname '*tts*' \) 2>/dev/null || true
    fallo "Indica la ruta con: sudo GOOGLE_AGI=/ruta/googletts.agi bash instalar.sh"
fi

case "$RUTA_GOOGLE" in
    "$AGI_DIR"/*) NOMBRE_GOOGLE="${RUTA_GOOGLE#"$AGI_DIR"/}" ;;
    *)            NOMBRE_GOOGLE="$RUTA_GOOGLE" ;;
esac
ok "AGI de Google: $RUTA_GOOGLE"
chmod 755 "$RUTA_GOOGLE" 2>/dev/null || true

instalar_paquetes() {
    if command -v apt-get >/dev/null; then
        apt-get update -qq && apt-get install -y "$@"
    elif command -v dnf >/dev/null; then
        dnf install -y "$@"
    elif command -v yum >/dev/null; then
        yum install -y "$@"
    else
        return 1
    fi
}

faltan=()
command -v python3 >/dev/null || faltan+=(python3)
command -v perl    >/dev/null || faltan+=(perl)
command -v sox     >/dev/null || faltan+=(sox)
command -v mpg123  >/dev/null || faltan+=(mpg123)
if [ ${#faltan[@]} -gt 0 ]; then
    info "Instalando: ${faltan[*]}"
    instalar_paquetes "${faltan[@]}" || fallo "Instala a mano: ${faltan[*]}"
fi
ok "python3, perl, sox y mpg123 están instalados"

if ! perl -MLWP::UserAgent -MURI::Escape -MDigest::MD5 -e 'exit 0' >/dev/null 2>&1; then
    info "Instalando módulos Perl que usa el AGI de Google"
    if command -v apt-get >/dev/null; then
        instalar_paquetes libwww-perl liblwp-protocol-https-perl || true
    else
        instalar_paquetes perl-libwww-perl perl-LWP-Protocol-https perl-URI perl-Digest-MD5 || true
    fi
fi
if command -v timeout >/dev/null; then
    perl_cmd=(timeout 20 perl -c "$RUTA_GOOGLE")
else
    perl_cmd=(perl -c "$RUTA_GOOGLE")
fi
if "${perl_cmd[@]}" >/dev/null 2>/tmp/googletts_perl_check.txt; then
    ok "El AGI de Google compila"
else
    info "perl -c reportó esto (la 702 lo confirma al llamar):"
    cat /tmp/googletts_perl_check.txt || true
fi
rm -f /tmp/googletts_perl_check.txt

if command -v curl >/dev/null; then
    codigo="$(curl -sS -o /dev/null -m 12 -w '%{http_code}' https://translate.google.com || true)"
    case "$codigo" in
        200|204|301|302|303|307|308) ok "La máquina llega a Google" ;;
        *) info "No confirmé salida a translate.google.com (respuesta: ${codigo:-ninguna}). Sin internet la voz no suena." ;;
    esac
fi

# Quitar la prueba paralela (701 / espeak) si todavía está en el servidor.
rm -f "$AGI_DIR/auth_google.py" "$AGI_DIR/prompts_google.py" "$AGI_DIR/init_db_google.py" "$AGI_DIR/generar_prompts.py"
if [ -f "$CONF_DIR/extensions_agi_google.conf" ]; then
    rm -f "$CONF_DIR/extensions_agi_google.conf"
    ok "Quité el dialplan de la extensión 701"
fi
if [ -f "$CONF_DIR/extensions.conf" ] && grep -q 'extensions_agi_google.conf' "$CONF_DIR/extensions.conf"; then
    sed -i '/extensions_agi_google.conf/d' "$CONF_DIR/extensions.conf"
fi
if [ -d "$DATA_DIR/sounds/agi_auth" ]; then
    rm -rf "$DATA_DIR/sounds/agi_auth"
    ok "Quité los audios de espeak"
fi

mkdir -p "$AGI_DIR"
install -m 755 -o "$AST_USER" -g "$AST_GRUPO" "$AQUI/auth.py" "$AGI_DIR/auth.py"
install -m 644 -o "$AST_USER" -g "$AST_GRUPO" "$AQUI/prompts.py" "$AGI_DIR/prompts.py"
install -m 644 -o "$AST_USER" -g "$AST_GRUPO" "$AQUI/init_db.py" "$AGI_DIR/init_db.py"
ok "Scripts copiados a $AGI_DIR"

AGI_AUTH_USER="$AST_USER" python3 "$AGI_DIR/init_db.py"
ok "Base de datos lista (si ya existía, las claves se conservan)"

CONF_TTS="/var/lib/asterisk/agi_auth/google_tts.conf"
if [ -n "${AGI_AUTH_DB:-}" ]; then
    CONF_TTS="$(dirname "$AGI_AUTH_DB")/google_tts.conf"
fi
cat > "$CONF_TTS" << EOF
# Lo lee auth.py en cada llamada.
script=$NOMBRE_GOOGLE
lang=es
speed=
EOF
chown "$AST_USER:$AST_GRUPO" "$CONF_TTS"
chmod 640 "$CONF_TTS"
ok "Voz configurada en $CONF_TTS"

TMP_CONF="$(mktemp)"
python3 - "$AQUI/extensions_agi.conf" "$TMP_CONF" "$NOMBRE_GOOGLE" << 'PY'
import sys
src, dst, nombre = sys.argv[1:]
texto = open(src, encoding="utf-8").read().replace("\r\n", "\n").replace("\r", "\n")
texto = texto.replace("AGI(googletts.agi,", "AGI(%s," % nombre)
open(dst, "w", encoding="utf-8", newline="\n").write(texto)
PY
install -m 640 -o "$AST_USER" -g "$AST_GRUPO" "$TMP_CONF" "$CONF_DIR/extensions_agi.conf"
rm -f "$TMP_CONF"

touch "$CONF_DIR/extensions.conf"
if ! grep -q 'extensions_agi.conf' "$CONF_DIR/extensions.conf"; then
    cp -a "$CONF_DIR/extensions.conf" "$CONF_DIR/extensions.conf.bak_agi"
    printf '\n#include extensions_agi.conf\n' >> "$CONF_DIR/extensions.conf"
fi
ok "Dialplan instalado"

if command -v restorecon >/dev/null 2>&1; then
    restorecon -R "$AGI_DIR" /var/lib/asterisk/agi_auth 2>/dev/null || true
fi

touch /var/log/asterisk/agi_auth.log 2>/dev/null || true
chown "$AST_USER:$AST_GRUPO" /var/log/asterisk/agi_auth.log 2>/dev/null || true
chmod 640 /var/log/asterisk/agi_auth.log 2>/dev/null || true

asterisk -rx "dialplan reload" >/dev/null
salida700="$(asterisk -rx "dialplan show 700@agi-auth" 2>/dev/null || true)"
if ! printf '%s\n' "$salida700" | grep -F 'auth.py' >/dev/null; then
    fallo "La extensión 700 no quedó en el dialplan. Revisa $CONF_DIR/extensions.conf"
fi
if printf '%s\n' "$salida700" | grep -F 'auth_google.py' >/dev/null; then
    fallo "La 700 todavía apunta a auth_google.py."
fi
ok "Dialplan cargado: la extensión 700 usa auth.py"

salida702="$(asterisk -rx "dialplan show 702@agi-auth" 2>/dev/null || true)"
if ! printf '%s\n' "$salida702" | grep -F "$NOMBRE_GOOGLE" >/dev/null; then
    fallo "La extensión 702 no quedó en el dialplan."
fi
ok "La extensión 702 prueba el AGI de Google"

python3 - "$AGI_DIR" << 'PY'
import sys
sys.path.insert(0, sys.argv[1])
import auth

def partes(cmd):
    assert cmd.startswith('EXEC AGI "') and cmd.endswith('"'), cmd
    return cmd[len('EXEC AGI "'):-1].split(",")

for texto in auth.PROMPTS.values():
    trozos = partes(auth.comando_tts(texto, "googletts.agi", "es"))
    assert len(trozos) == 3, (texto, trozos)
    assert trozos[0] == "googletts.agi"
    assert trozos[2] == "es"
    assert "," not in trozos[1]

trozos = partes(auth.comando_tts("Hola, mundo.", "googletts.agi", "es", "1"))
assert trozos == ["googletts.agi", "Hola. mundo.", "es", "1"], trozos
assert auth.validar_clave("482913", "9999") is None
assert auth.validar_clave("111111", "9999") == "clave_iguales"
sal, resumen = auth.hashear("135792")
assert auth.verificar("135792", sal, resumen)
assert not auth.verificar("000000", sal, resumen)
print("autoprueba python ok")
PY
ok "Autoprueba del script superada"

echo
echo "Listo. Una sola versión, con voz de Google."
echo "  702  prueba solo la voz"
echo "  700  el sistema completo"
echo
echo "Admin: 9999 / 482913   |   Usuario: 1001 / 135792"
echo "Si esas cuentas ya existían, siguen con la contraseña que tenían."
echo "Marca después del bip. En usuario y clave cierra con la tecla numeral."
