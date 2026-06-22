"""
core/repositorio_ops.py
Persistencia de Órdenes de Producción (OP) como JSON en la carpeta Dropbox
compartida. Una OP nace de una cotización aprobada; ya no se generan Excel/PDF
para las OPs, solo JSON (lo lee el panel de TV de producción).
"""

import json
from pathlib import Path

from core.repositorio_cotizaciones import _detectar_dropbox
from core.rutas import DATOS


def _ruta_base() -> Path:
    dropbox = _detectar_dropbox()
    if dropbox:
        return dropbox / "SGTD" / "OPs"
    return DATOS / "OPs"


def carpeta_json() -> Path:
    p = _ruta_base() / "JSON"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_historial() -> Path:
    p = _ruta_base() / "Historial"
    p.mkdir(parents=True, exist_ok=True)
    return p


def guardar_op(datos: dict) -> Path:
    """Guarda datos como JSON de OP. Sobreescribe si ya existe el número."""
    numero = datos["Cotizacion"]
    destino = carpeta_json() / f"{numero}.json"
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino
