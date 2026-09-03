"""
core/rutas.py
Resolución de rutas compatible con ejecución normal y con PyInstaller.
"""

import json
import os
import sys
from pathlib import Path

from core.version import VERSION


def _base_recursos() -> Path:
    """
    Carpeta donde viven los archivos de solo lectura (plantilla, assets, catálogos).
    - Normal:      <raíz del proyecto>/recursos
    - PyInstaller: sys._MEIPASS/recursos  (carpeta temporal donde se extraen los recursos)
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "recursos"
    return Path(__file__).parent.parent / "recursos"


def _base_docs() -> Path:
    """
    Carpeta con documentación de solo lectura (manual de usuario, etc.),
    mismo criterio que _base_recursos().
    - Normal:      <raíz del proyecto>/docs
    - PyInstaller: sys._MEIPASS/docs (agregada al build con --add-data,
      ver build_windows.ps1 / .github/workflows/release.yml)
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "docs"
    return Path(__file__).parent.parent / "docs"


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


def _es_dev() -> bool:
    """True cuando se corre desde el checkout de código fuente, sin
    versión de release (ver core.version.VERSION) — el workflow de
    release (.github/workflows/release.yml) siempre sobreescribe VERSION
    con el tag de git antes de empaquetar con PyInstaller, así que una
    instalación descargada de un release de GitHub nunca cae acá."""
    return VERSION == "0.0.0-dev"


def _carpeta_dropbox_dev() -> Path:
    """Carpeta que emula la raíz de Dropbox (con la misma estructura
    SGTD/... que arman los callers de _detectar_dropbox()) para la
    versión de desarrollador (ver _es_dev). Así, corriendo desde el
    código fuente, la app nunca lee ni escribe la Dropbox real de la
    empresa — sirve para pruebas y como fuente de archivos de ejemplo.
    Vive junto a los datos locales de esta máquina (ver _base_datos()),
    separada de DATOS/ mismo (ese es el fallback de "no hay Dropbox
    instalado", con su propia estructura sin SGTD/ — ver
    core/repositorio_ops.py::_ruta_base y análogos)."""
    p = _base_datos() / "DropboxDev"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _detectar_dropbox() -> Path | None:
    """Devuelve la carpeta raíz de Dropbox leyendo su info.json, o None si
    Dropbox Desktop no está instalado en esta máquina.

    En la versión de desarrollador (ver _es_dev) devuelve en cambio
    _carpeta_dropbox_dev(), una carpeta local separada que emula la
    Dropbox real — para que corriendo desde el código fuente nunca se
    toque la Dropbox real de la empresa, ni siquiera si esta máquina la
    tiene instalada y sincronizada."""
    if _es_dev():
        return _carpeta_dropbox_dev()

    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        info = Path(local) / "Dropbox" / "info.json"
    else:
        info = Path.home() / ".dropbox" / "info.json"

    if info.exists():
        try:
            data = json.loads(info.read_text(encoding="utf-8"))
            # info.json solo trae la clave de las cuentas vinculadas en esta
            # máquina: "personal", "business", o ambas si hay dos cuentas
            # enlazadas. Antes se asumía siempre "personal" y una cuenta de
            # equipo (Dropbox Business, típico en una empresa) quedaba sin
            # detectar, cayendo en silencio a la carpeta local.
            for cuenta in ("personal", "business"):
                if cuenta in data:
                    return Path(data[cuenta]["path"])
        except Exception:
            pass

    if sys.platform == "darwin":
        # Fallback si no hay info.json (o no se pudo leer): las versiones
        # recientes de Dropbox Desktop montan la carpeta sincronizada bajo
        # ~/Library/CloudStorage/ vía el File Provider de macOS en vez de
        # (o además de) ~/Dropbox directo.
        cloud = Path.home() / "Library" / "CloudStorage"
        if cloud.is_dir():
            candidatas = sorted(p for p in cloud.glob("Dropbox*") if p.is_dir())
            if candidatas:
                return candidatas[0]

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


RECURSOS  = _base_recursos()   # recursos/: catálogos de referencia (solo lectura), plantilla xlsx, assets/
DOCS      = _base_docs()       # docs/: manual de usuario y otra documentación de solo lectura
DATOS     = _base_datos()      # datos locales por máquina (fallback sin Dropbox)
CONF      = _base_conf()       # clientes.json, contactos.json (datos que el operador va agregando)
