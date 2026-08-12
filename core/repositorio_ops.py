"""
core/repositorio_ops.py
Persistencia de Órdenes de Producción (OP) como JSON en la carpeta Dropbox
compartida. Una OP nace de una cotización aprobada; ya no se generan Excel/PDF
para las OPs, solo JSON (lo leen los paneles de TV de producción).

Ciclo de vida de una OP activa:
  JSON/ (activa) -> Completadas/ (recién completada) -> Historial/ (>14 días)
  JSON/ (activa) <-> Pendiente/ (esperando fecha de entrega definitiva)

JSON/, Completadas/ y Pendiente/ quedan PLANAS (sin subcarpetas) — el panel
de producción siempre las lee completas de una sola vez, sin importar el
mes, así que organizarlas por AAAA/MM no aporta nada y solo suma
complejidad; además son chicas (se auto-podan solas: Completadas/ vacía
hacia Historial/ a los 14 días). Solo Historial/ — la que de verdad puede
llegar a acumular miles de archivos con los años — se organiza en
subcarpetas AAAA/MM/{numero}.json según la Fecha_ingreso de la OP, para
que ui/historial_ops.py pueda listar un mes puntual sin tener que abrir
el resto. Ver `listar_meses_disponibles`/`listar_ops_del_mes`. La mecánica
de AAAA/MM en sí vive en core/carpetas_mensuales.py, compartida con
core/repositorio_cotizaciones.py.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox
from core import carpetas_mensuales as cm

DIAS_ENVEJECIMIENTO = 14
_CAMPO_FECHA = "Fecha_ingreso"

_CARPETAS_PLANAS = ("JSON", "Completadas", "Pendiente")


def _ruta_base() -> Path:
    dropbox = _detectar_dropbox()
    if dropbox:
        return dropbox / "SGTD" / "OPs"
    return DATOS / "OPs"


_migradas: set[str] = set()


def _carpeta(nombre: str) -> Path:
    """Carpeta de ciclo de vida, ajustada a su estructura (plana o AAAA/MM)
    la primera vez que se pide en esta sesión. La clave de "ya ajustada" es
    la ruta completa, no solo `nombre` — _ruta_base() es estable durante
    toda la sesión de la app real, pero mantenerlo así de todos modos evita
    que un test con otra carpeta temporal (mismo nombre, otra base) se
    salte el ajuste por error."""
    p = _ruta_base() / nombre
    p.mkdir(parents=True, exist_ok=True)
    clave = str(p)
    if clave not in _migradas:
        if nombre == "Historial":
            cm.migrar_archivos_planos(p, _CAMPO_FECHA)
        else:
            cm.aplanar_archivos(p)
        _migradas.add(clave)
    return p


def carpeta_json() -> Path:
    return _carpeta("JSON")


def carpeta_historial() -> Path:
    return _carpeta("Historial")


def carpeta_completadas() -> Path:
    return _carpeta("Completadas")


def carpeta_pendiente() -> Path:
    return _carpeta("Pendiente")


def carpeta_html() -> Path:
    """HTML impreso — se regenera cada vez que se imprime, no es la fuente
    de verdad de una OP, así que se deja plana."""
    p = _ruta_base() / "HTML"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cargar_op(numero: int) -> dict | None:
    """Busca el JSON de una OP por número en las 4 carpetas (activa,
    completada, pendiente, historial) y lo devuelve, o None si no existe
    en ninguna. Mismo orden de búsqueda que
    ui.panel_produccion._ApiPanelProduccion.obtener_op_por_numero."""
    for carpeta in (carpeta_json(), carpeta_completadas(), carpeta_pendiente()):
        ruta = carpeta / f"{numero}.json"
        if ruta.exists():
            try:
                return json.loads(ruta.read_text(encoding="utf-8"))
            except Exception:
                return None
    ruta = cm.buscar(carpeta_historial(), numero)
    if ruta is not None:
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def guardar_op(datos: dict) -> Path:
    """Guarda datos como JSON de OP en JSON/ (plana). Sobreescribe si ya
    existe el número."""
    numero = datos["Cotizacion"]
    destino = carpeta_json() / f"{numero}.json"
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def _mover_plano(origen_carpeta: Path, destino_carpeta: Path, numero: int) -> None:
    origen = origen_carpeta / f"{numero}.json"
    if origen.exists():
        origen.replace(destino_carpeta / origen.name)


def mover_a_completadas(numero: int) -> None:
    """Mueve el JSON de la OP completada de JSON/ a Completadas/."""
    _mover_plano(carpeta_json(), carpeta_completadas(), numero)


def mover_a_pendiente(numero: int) -> None:
    """Mueve el JSON de la OP de JSON/ a Pendiente/ (a la espera de que el
    cliente confirme una fecha de entrega definitiva)."""
    _mover_plano(carpeta_json(), carpeta_pendiente(), numero)


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
    """Mueve a Historial/ (a su subcarpeta AAAA/MM según Fecha_ingreso) las
    OPs de Completadas/ cuya Fecha_entrega tenga más de `dias` días de
    antigüedad. Mantiene liviano el set que lee el calendario del panel de
    listado."""
    limite = datetime.now() - timedelta(days=dias)
    for archivo in carpeta_completadas().glob("*.json"):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
            fecha = datetime.strptime(datos["Fecha_entrega"], "%d/%m/%Y")
        except Exception:
            continue
        if fecha < limite:
            anio, mes = cm.anio_mes(datos, _CAMPO_FECHA)
            destino = cm.subcarpeta_mes(carpeta_historial(), anio, mes) / archivo.name
            archivo.replace(destino)


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


def eliminar_op(numero: int) -> bool:
    """Elimina el JSON de una OP, sea cual sea la carpeta de ciclo de vida
    en la que esté (activa, completada, pendiente o historial). Devuelve
    True si encontró y borró algo."""
    for carpeta in (carpeta_json(), carpeta_completadas(), carpeta_pendiente()):
        ruta = carpeta / f"{numero}.json"
        if ruta.exists():
            ruta.unlink()
            return True
    return cm.eliminar([carpeta_historial()], numero)


# ══════════════════════════════════════════════════════════════════════════════
# Historial por mes (ui/historial_ops.py). JSON/Completadas/Pendiente son
# planas y chicas — se recorren completas cada vez que se pide un mes (sin
# costo real, se auto-podan solas). Historial/ es la única organizada por
# AAAA/MM, así que ahí sí se puede listar un mes puntual sin abrir el resto.
# ══════════════════════════════════════════════════════════════════════════════

def _leer_json(archivo: Path) -> dict | None:
    try:
        return json.loads(archivo.read_text(encoding="utf-8"))
    except Exception:
        return None


def listar_meses_disponibles() -> list[tuple[int, int]]:
    """(año, mes) únicos con al menos una OP, en cualquiera de las 4
    carpetas — incluye las activas (JSON/Pendiente/Completadas), no solo
    Historial/."""
    metas = set(cm.listar_meses_disponibles([carpeta_historial()]))
    for nombre in _CARPETAS_PLANAS:
        for archivo in _carpeta(nombre).glob("*.json"):
            datos = _leer_json(archivo)
            if datos is not None:
                metas.add(cm.anio_mes(datos, _CAMPO_FECHA))
    return sorted(metas)


def listar_ops_del_mes(anio: int, mes: int) -> list[tuple[dict, str]]:
    """OPs de un año/mes puntual, juntando las 4 carpetas — incluye las
    activas. Devuelve [(datos, origen), ...] con `origen` en
    "JSON"/"Completadas"/"Pendiente"/"Historial" (para que la ventana de
    historial pueda mostrar el estado de cada una)."""
    resultado = []
    for nombre in _CARPETAS_PLANAS:
        for archivo in _carpeta(nombre).glob("*.json"):
            datos = _leer_json(archivo)
            if datos is not None and cm.anio_mes(datos, _CAMPO_FECHA) == (anio, mes):
                resultado.append((datos, nombre))
    carpeta_mes = carpeta_historial() / f"{anio:04d}" / f"{mes:02d}"
    if carpeta_mes.is_dir():
        for archivo in carpeta_mes.glob("*.json"):
            datos = _leer_json(archivo)
            if datos is not None:
                resultado.append((datos, "Historial"))
    return resultado
