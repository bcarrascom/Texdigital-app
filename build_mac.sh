#!/bin/bash
# build_mac.sh — Empaqueta la app en un .app de macOS con PyInstaller.
# Ejecutar desde la carpeta empresa_app:  bash build_mac.sh

set -e

APP_NAME="Sistema de Gestion"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Verificando Python 3 ==="
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 no está instalado."
    echo "Descárgalo desde https://www.python.org/downloads/"
    exit 1
fi
python3 --version

echo ""
echo "=== Instalando dependencias ==="
python3 -m pip install --upgrade pip --quiet
python3 -m pip install pyinstaller -r "$SCRIPT_DIR/requirements.txt" --quiet

echo ""
echo "=== Limpiando builds anteriores ==="
rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR/dist" "$SCRIPT_DIR/${APP_NAME}.spec"

echo ""
echo "=== Empaquetando... ==="
cd "$SCRIPT_DIR"

python3 -m PyInstaller \
    --name "$APP_NAME" \
    --windowed \
    --onedir \
    --collect-all openpyxl \
    --add-data "recursos:recursos" \
    --hidden-import "PIL._tkinter_finder" \
    main.py

echo ""
echo "=== Creando acceso directo en el Escritorio ==="
DESKTOP="$HOME/Desktop"
ALIAS_NAME="${APP_NAME}.app"
APP_PATH="$SCRIPT_DIR/dist/${APP_NAME}.app"

# Eliminar alias anterior si existe
rm -rf "$DESKTOP/$ALIAS_NAME"

# Crear alias (acceso directo) al .app completo — no al binario interno
osascript - "$APP_PATH" "$DESKTOP/$ALIAS_NAME" << 'EOF'
on run argv
    set appPath to item 1 of argv
    set aliasPath to item 2 of argv
    tell application "Finder"
        make alias file to POSIX file appPath at POSIX file (do shell script "dirname " & quoted form of aliasPath)
        set name of result to (do shell script "basename " & quoted form of aliasPath)
    end tell
end run
EOF

echo "Acceso directo creado en el Escritorio: $ALIAS_NAME"

echo ""
echo "=== Listo ==="
echo "El archivo está en:  dist/${APP_NAME}.app"
echo ""
echo "Tu mamá puede abrir la app desde el acceso directo del Escritorio."
echo "IMPORTANTE: el acceso directo apunta al .app completo, no al binario interno."
