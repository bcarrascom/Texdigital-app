"""
core/rutas.py
Resolución de rutas compatible con ejecución normal y con PyInstaller.
"""

import json
import os
import sys
from pathlib import Path


def _base_recursos() -> Path:
    """
    Carpeta donde viven los archivos de solo lectura (plantilla, assets, catálogos).
    - Normal:      <raíz del proyecto>/recursos
    - PyInstaller: sys._MEIPASS/recursos  (carpeta temporal donde se extraen los recursos)
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "recursos"
    return Path(__file__).parent.parent / "recursos"


def _base_datos() -> Path:
    """
    Carpeta local (por máquina) para datos que no dependen de Dropbox.
    Siempre debe ser escribible y persistente entre ejecuciones.
    - Windows: %APPDATA%/SistemaGestion
    - macOS:   ~/Library/Application Support/SistemaGestion
    """
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "SistemaGestion"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "SistemaGestion"
    else:
        base = Path.home() / ".SistemaGestion"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _detectar_dropbox() -> Path | None:
    """Devuelve la carpeta raíz de Dropbox leyendo su info.json, o None si
    Dropbox Desktop no está instalado en esta máquina."""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        info = Path(local) / "Dropbox" / "info.json"
    else:
        info = Path.home() / ".dropbox" / "info.json"

    if not info.exists():
        return None
    try:
        data = json.loads(info.read_text(encoding="utf-8"))
        return Path(data["personal"]["path"])
    except Exception:
        return None


def _base_conf() -> Path:
    """
    Carpeta de configuración compartida entre todas las instalaciones:
    clientes, contactos y los catálogos de productos/textiles. Vive en
    Dropbox (Dropbox/SGTD/Conf) para que un cambio hecho en una máquina se
    vea en todas. Si Dropbox no está instalado, cae a la carpeta local de
    datos (queda por máquina, como antes).
    """
    dropbox = _detectar_dropbox()
    base = (dropbox / "SGTD" / "Conf") if dropbox else (DATOS / "Conf")
    base.mkdir(parents=True, exist_ok=True)
    return base


RECURSOS  = _base_recursos()   # recursos/: plantilla xlsx, assets/, seeds de fábrica
DATOS     = _base_datos()      # datos locales por máquina (fallback sin Dropbox)
CONF      = _base_conf()       # clientes.json, contactos.json, productos.json, textiles.json
