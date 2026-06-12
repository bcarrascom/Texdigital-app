"""
core/rutas.py
Resolución de rutas compatible con ejecución normal y con PyInstaller.
"""

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
    Carpeta donde viven los archivos que el usuario edita (clientes.txt, contactos.txt).
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


RECURSOS  = _base_recursos()   # recursos/: plantilla xlsx, assets/, catálogos, seeds
DATOS     = _base_datos()      # clientes.txt, contactos.txt
