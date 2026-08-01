"""
core/repositorio_ops.py
Persistencia de Órdenes de Producción (OP) como JSON en la carpeta Dropbox
compartida. Una OP nace de una cotización aprobada; ya no se generan Excel/PDF
para las OPs, solo JSON (lo leen los paneles de TV de producción).

Ciclo de vida de una OP activa:
  JSON/ (activa) -> Completadas/ (recién completada) -> Historial/ (>14 días)
  JSON/ (activa) <-> Pendiente/ (esperando fecha de entrega definitiva)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox

DIAS_ENVEJECIMIENTO = 14


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


def carpeta_completadas() -> Path:
    p = _ruta_base() / "Completadas"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_pendiente() -> Path:
    p = _ruta_base() / "Pendiente"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_html() -> Path:
    p = _ruta_base() / "HTML"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cargar_op(numero: int) -> dict | None:
    """Busca el JSON de una OP por número en las 4 carpetas (activa,
    completada, pendiente, historial) y lo devuelve, o None si no existe
    en ninguna. Mismo orden de búsqueda que
    ui.panel_produccion._ApiPanelProduccion.obtener_op_por_numero."""
    for carpeta in (carpeta_json(), carpeta_completadas(), carpeta_pendiente(), carpeta_historial()):
        ruta = carpeta / f"{numero}.json"
        if ruta.exists():
            try:
                return json.loads(ruta.read_text(encoding="utf-8"))
            except Exception:
                return None
    return None


def guardar_op(datos: dict) -> Path:
    """Guarda datos como JSON de OP. Sobreescribe si ya existe el número."""
    numero = datos["Cotizacion"]
    destino = carpeta_json() / f"{numero}.json"
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def _mover(origen_carpeta: Path, destino_carpeta: Path, numero: int) -> None:
    origen = origen_carpeta / f"{numero}.json"
    if origen.exists():
        origen.replace(destino_carpeta / origen.name)


def mover_a_completadas(numero: int) -> None:
    """Mueve el JSON de la OP completada de JSON/ a Completadas/."""
    _mover(carpeta_json(), carpeta_completadas(), numero)


def mover_a_pendiente(numero: int) -> None:
    """Mueve el JSON de la OP de JSON/ a Pendiente/ (a la espera de que el
    cliente confirme una fecha de entrega definitiva)."""
    _mover(carpeta_json(), carpeta_pendiente(), numero)


def reactivar_desde_pendiente(numero: int, fecha_entrega: str) -> None:
    """Mueve el JSON de Pendiente/ a JSON/ con la nueva Fecha_entrega."""
    origen = carpeta_pendiente() / f"{numero}.json"
    if not origen.exists():
        return
    datos = json.loads(origen.read_text(encoding="utf-8"))
    datos["Fecha_entrega"] = fecha_entrega
    (carpeta_json() / origen.name).write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    origen.unlink()


def actualizar_fecha_entrega(numero: int, fecha_entrega: str) -> None:
    """Actualiza la Fecha_entrega de una OP activa, sin moverla de carpeta."""
    ruta = carpeta_json() / f"{numero}.json"
    if not ruta.exists():
        return
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["Fecha_entrega"] = fecha_entrega
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def envejecer_completadas(dias: int = DIAS_ENVEJECIMIENTO) -> None:
    """Mueve a Historial/ las OPs de Completadas/ cuya Fecha_entrega tenga
    más de `dias` días de antigüedad. Mantiene liviano el set que lee el
    calendario del panel de listado."""
    limite = datetime.now() - timedelta(days=dias)
    for archivo in carpeta_completadas().glob("*.json"):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
            fecha = datetime.strptime(datos["Fecha_entrega"], "%d/%m/%Y")
        except Exception:
            continue
        if fecha < limite:
            archivo.replace(carpeta_historial() / archivo.name)


def actualizar_listos(numero: int, indices: list[int]) -> None:
    """Guarda en el JSON de la OP qué productos (por índice) están marcados
    como listos en el panel de TV, para que sobreviva a un reinicio."""
    ruta = carpeta_json() / f"{numero}.json"
    if not ruta.exists():
        return
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["ProductosListos"] = indices
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
