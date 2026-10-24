"""
core/ajustes_globales.py
Los ajustes GLOBALES de la empresa (los que valen igual en todas las
instalaciones: precios, reglas de cobro...) — un JSON por tema en
Dropbox/SGTD/Conf (ver core.rutas.CONF), junto a clientes/contactos/
proveedores. Pedido de Bruno (2026-10-22): sobreviven a una actualización
porque viven fuera de la carpeta de la app (que se borra entera al bajar
una versión nueva), y valen para cualquiera que cotice.

Los ajustes LOCALES (de cada instalación: tamaño del texto...) no van acá:
son core.repositorio.cargar_preferencias, en %APPDATA%.

Cada archivo lleva "version". Las reglas, para que una instalación vieja y
una nueva puedan convivir mientras no todas se actualizan:
  - Al leer, lo que no se conoce se ignora (no se borra).
  - Al guardar, se conserva lo que había y esta versión no conoce: solo se
    pisan las claves que se guardan.
  - Una instalación vieja NO guarda sobre un archivo de una versión más
    nueva que la suya (AjusteMasNuevo): podría escribir algo que la nueva
    ya no entiende igual. Se puede leer igual.

Lo que viene con la app (recursos/*.json) es solo el punto de partida: si
el archivo todavía no existe, cada módulo arma sus valores por defecto con
eso (ver core.precios_textiles).
"""

import json
import os
from pathlib import Path

from core.rutas import CONF as _CONF_DIR


class AjusteMasNuevo(Exception):
    """El archivo lo guardó una versión de la app más nueva que esta."""


def _ruta(nombre: str) -> Path:
    return _CONF_DIR / f"{nombre}.json"


def leer(nombre: str) -> dict:
    """El contenido de Conf/<nombre>.json. {} si no existe o está corrupto
    (cada módulo cae a sus valores por defecto)."""
    ruta = _ruta(nombre)
    if not ruta.exists():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return datos if isinstance(datos, dict) else {}


def es_mas_nuevo(nombre: str, version: int) -> bool:
    """Si el archivo es de una versión de formato mayor que `version`."""
    try:
        return int(leer(nombre).get("version", 0)) > version
    except (TypeError, ValueError):
        return False


def guardar(nombre: str, cambios: dict, version: int) -> None:
    """Escribe `cambios` en Conf/<nombre>.json con formato `version`,
    conservando las claves que ya estaban y no se tocan. Se escribe a un
    temporal y se reemplaza: un corte a mitad nunca deja el archivo a medias."""
    if es_mas_nuevo(nombre, version):
        raise AjusteMasNuevo(nombre)
    datos = {**leer(nombre), **cambios, "version": version}
    ruta = _ruta(nombre)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporal, ruta)
