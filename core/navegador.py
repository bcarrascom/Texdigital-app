"""
core/navegador.py
Abre en el navegador los HTML que arma la app para imprimir (cotización,
OP, guía de despacho).

En Windows basta `webbrowser.open`: Edge y Chrome abren una pestaña en la
ventana que ya está abierta.

En el Mac no (reporte de un usuario, 2026-11-20): `webbrowser.open` le pasa
el archivo al navegador por LaunchServices, y el navegador decide dónde
abrirlo. Safari abre los archivos en una ventana nueva, y Chrome también
cuando su última ventana está en otro escritorio (Spaces) que la app, p.
ej. si la app está en pantalla completa. Por eso, en el Mac, se le pide
por AppleScript al navegador por defecto que abra una pestaña nueva en su
ventana de adelante. macOS pide permiso una vez por navegador ("…quiere
controlar Google Chrome"); si se niega, o el navegador no es Safari ni uno
de los basados en Chromium, o algo falla, se abre como antes.

Se abre en un hilo aparte: mientras macOS espera la respuesta al permiso,
la pantalla de la app no queda esperando.
"""

import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

_SAFARI = {"com.apple.Safari", "com.apple.SafariTechnologyPreview"}

# Los basados en Chromium tienen el mismo diccionario de AppleScript que
# Chrome (window, tab, active tab index).
_CHROMIUM = {
    "com.google.Chrome",
    "com.google.Chrome.beta",
    "com.google.Chrome.dev",
    "com.google.Chrome.canary",
    "org.chromium.Chromium",
    "com.brave.Browser",
    "com.microsoft.edgemac",
    "com.vivaldi.Vivaldi",
}

# El navegador por defecto es el que abre los enlaces https (no el que
# abre los .html, que puede ser un editor).
_SCRIPT_POR_DEFECTO = '''
use AppleScript version "2.4"
use framework "AppKit"
use scripting additions
set enlace to current application's NSURL's URLWithString:"https://example.com"
set app_url to (current application's NSWorkspace's sharedWorkspace())'s URLForApplicationToOpenURL:enlace
if app_url is missing value then return ""
return ((current application's NSBundle's bundleWithURL:app_url)'s bundleIdentifier()) as text
'''

# Cada script recibe la URL como argumento (nunca se escribe dentro del
# script) y devuelve "ok" si abrió la pestaña. Con el navegador cerrado
# devuelve "cerrado": al abrirlo, el navegador abre su propia ventana, y
# una pestaña nuestra quedaría al lado de una vacía; ahí basta abrirlo
# como siempre, con la URL.
_SCRIPT_SAFARI = '''
on run argv
    set u to item 1 of argv
    if application id "{id}" is not running then return "cerrado"
    tell application id "{id}"
        if (count of windows) is 0 then
            make new document with properties {{URL:u}}
        else
            tell front window
                set current tab to (make new tab at end of tabs with properties {{URL:u}})
            end tell
        end if
        activate
    end tell
    return "ok"
end run
'''

_SCRIPT_CHROMIUM = '''
on run argv
    set u to item 1 of argv
    if application id "{id}" is not running then return "cerrado"
    tell application id "{id}"
        if (count of windows) is 0 then
            make new window
            set URL of active tab of front window to u
        else
            tell front window
                make new tab at end of tabs with properties {{URL:u}}
                set active tab index to (count of tabs)
            end tell
        end if
        activate
    end tell
    return "ok"
end run
'''


def _osascript(script: str, *args: str) -> str | None:
    """Corre un AppleScript y devuelve lo que imprime, o None si falló
    (p. ej. el permiso negado: error -1743)."""
    try:
        r = subprocess.run(["osascript", "-", *args], input=script,
                           capture_output=True, text=True)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def _navegador_por_defecto() -> str:
    return _osascript(_SCRIPT_POR_DEFECTO) or ""


def _script_pestana(bundle_id: str) -> str | None:
    if bundle_id in _SAFARI:
        return _SCRIPT_SAFARI.format(id=bundle_id)
    if bundle_id in _CHROMIUM:
        return _SCRIPT_CHROMIUM.format(id=bundle_id)
    return None


def _abrir_en_pestana_mac(url: str) -> bool:
    script = _script_pestana(_navegador_por_defecto())
    if script is None:
        return False
    return _osascript(script, url) == "ok"


def _abrir(url: str) -> None:
    if sys.platform == "darwin" and _abrir_en_pestana_mac(url):
        return
    webbrowser.open(url)


def abrir_html(ruta: Path) -> None:
    """Abre `ruta` (un HTML local) en el navegador por defecto, en una
    pestaña de la ventana que ya está abierta."""
    url = Path(ruta).resolve().as_uri()
    threading.Thread(target=_abrir, args=(url,), daemon=True).start()
