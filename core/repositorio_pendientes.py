"""
core/repositorio_pendientes.py
Persistencia de cotizaciones pendientes (progreso guardado a medio hacer,
desde cualquier pantalla de producto de ui/cotizacion.py o
ui/cotizador_backlight.py — ver "Guardar progreso" / Ctrl+S).

Carpeta plana única (sin la estructura AAAA/MM que usa
core/repositorio_cotizaciones.py): esa estructura se basa en el campo
"Fecha", que una cotización pendiente todavía no tiene — se define recién
en el formulario de cliente, al final del flujo, que es también donde recién
existe un N° de cotización. Mientras tanto, cada pendiente se identifica por
un id (ver nuevo_id) — no por número ni cliente, que todavía no existen.
"""

import json
import uuid
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox


def carpeta_pendientes() -> Path:
    """Carpeta dedicada a cotizaciones pendientes, dentro de la misma raíz
    que usa core/repositorio_cotizaciones.py (Dropbox/SGTD/Cotizaciones si
    Dropbox está instalado, si no la carpeta local de datos)."""
    dropbox = _detectar_dropbox()
    base = (
        (dropbox / "SGTD" / "Cotizaciones" / "Pendientes") if dropbox
        else (DATOS / "Cotizaciones" / "Pendientes")
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


def nuevo_id() -> str:
    """Identificador de una cotización pendiente (no hay N° de cotización
    todavía) — se genera una sola vez, al primer "Guardar progreso" de una
    cotización nueva, y se reutiliza en los guardados siguientes para
    sobreescribir el mismo archivo en vez de duplicarlo."""
    return uuid.uuid4().hex[:12]


def guardar_pendiente(datos: dict) -> Path:
    """Guarda (o sobreescribe, si `datos["id"]` ya existía) una cotización
    pendiente como <id>.json en carpeta_pendientes()."""
    destino = carpeta_pendientes() / f"{datos['id']}.json"
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def listar_pendientes() -> list[dict]:
    """Todas las cotizaciones pendientes guardadas. Sin orden particular —
    quien llama decide cómo ordenarlas (ver ui/pendientes_cotizaciones.py)."""
    resultado = []
    for archivo in carpeta_pendientes().glob("*.json"):
        try:
            resultado.append(json.loads(archivo.read_text(encoding="utf-8")))
        except Exception:
            pass
    return resultado


def cargar_pendiente(id_: str) -> dict | None:
    """Lee una cotización pendiente por id, o None si no existe (o el
    archivo quedó corrupto)."""
    ruta = carpeta_pendientes() / f"{id_}.json"
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return None


def eliminar_pendiente(id_: str) -> bool:
    """Elimina una cotización pendiente por id — se llama tanto al
    terminarla de verdad (ui/formulario_cliente.py, pasa a ser una
    cotización guardada normal) como al descartarla a mano desde la lista
    de pendientes. Devuelve True si encontró y borró algo."""
    ruta = carpeta_pendientes() / f"{id_}.json"
    if ruta.exists():
        ruta.unlink()
        return True
    return False
