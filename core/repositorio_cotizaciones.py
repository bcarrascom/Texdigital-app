"""
core/repositorio_cotizaciones.py
Persistencia de cotizaciones como JSON en la carpeta Dropbox compartida.
Fallback a AppData si Dropbox Desktop no está instalado.
"""

import json
import os
import sys
from pathlib import Path

from core.rutas import DATOS


def _detectar_dropbox() -> Path | None:
    """Devuelve la carpeta raíz de Dropbox leyendo su info.json, o None."""
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


def _ruta_base() -> Path:
    dropbox = _detectar_dropbox()
    if dropbox:
        return dropbox / "SGTD" / "Cotizaciones"
    return DATOS / "Cotizaciones"


def carpeta_json() -> Path:
    p = _ruta_base() / "JSON"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_excel() -> Path:
    p = _ruta_base() / "Excel"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_historial() -> Path:
    p = _ruta_base() / "Historial"
    p.mkdir(parents=True, exist_ok=True)
    return p


def siguiente_numero() -> int:
    """Devuelve max(números existentes) + 1, o 1000 si no hay ninguno.

    Revisa cotizaciones Y OPs (activas e historial), porque una OP puede
    tener un número más alto que las cotizaciones activas (su cotización de
    origen ya pasó a Historial), y reusar ese número causaría un choque.
    """
    from core import repositorio_ops

    carpetas = [
        carpeta_json(),
        carpeta_historial(),
        repositorio_ops.carpeta_json(),
        repositorio_ops.carpeta_historial(),
    ]
    numeros = []
    for carpeta in carpetas:
        for archivo in carpeta.glob("*.json"):
            try:
                numeros.append(int(archivo.stem))
            except ValueError:
                pass
    return max(numeros) + 1 if numeros else 1000


def guardar_cotizacion(datos: dict) -> Path:
    """Guarda datos como JSON. Sobreescribe si ya existe el número."""
    numero = datos["Cotizacion"]
    destino = carpeta_json() / f"{numero}.json"
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def mover_a_historial(numero: int) -> None:
    """Mueve el JSON de la cotización aprobada de JSON/ a Historial/."""
    origen = carpeta_json() / f"{numero}.json"
    if origen.exists():
        origen.replace(carpeta_historial() / origen.name)


def eliminar_excel(numero: int) -> None:
    """Elimina el Excel de la cotización aprobada (ya no se necesita)."""
    for nombre in (f"Cotización {numero:04d}.xlsx", f"Cotización {numero}.xlsx"):
        p = carpeta_excel() / nombre
        if p.exists():
            p.unlink()
            break
