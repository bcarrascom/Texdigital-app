"""
core/repositorio_ops.py
Persistencia de Órdenes de Producción (OP) como JSON en la carpeta Dropbox
compartida. Una OP nace de una cotización aprobada; ya no se generan Excel/PDF
para las OPs, solo JSON (lo leen los paneles de TV de producción).

Ciclo de vida de una OP activa:
  JSON/ (activa) -> Completadas/ (recién completada) -> Historial/ (>14 días)
  JSON/ (activa) <-> Pendiente/ (esperando fecha de entrega definitiva)

Dentro de cada una de esas 4 carpetas, los JSON viven en subcarpetas
AAAA/MM/{numero}.json según la Fecha_ingreso de la OP (NO la Fecha_entrega
— la fecha de ingreso no cambia en la vida de la OP, así que el mes queda
fijo aunque la OP se mueva de JSON/ a Completadas/ a Historial/). Esto es
lo que permite a ui/historial_ops.py listar un mes puntual sin tener que
abrir los miles de archivos que va a ir acumulando Historial/ con los
años — elegir un año/mes es solo listar una subcarpeta, sin tocar el
resto. Ver `listar_meses_disponibles`/`listar_ops_del_mes`. La mecánica
de AAAA/MM en sí (migración, mover preservando mes, etc.) vive en
core/carpetas_mensuales.py, compartida con core/repositorio_cotizaciones.py.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox
from core import carpetas_mensuales as cm

DIAS_ENVEJECIMIENTO = 14
_CAMPO_FECHA = "Fecha_ingreso"

_CARPETAS_BASE = ("JSON", "Completadas", "Pendiente", "Historial")


def _ruta_base() -> Path:
    dropbox = _detectar_dropbox()
    if dropbox:
        return dropbox / "SGTD" / "OPs"
    return DATOS / "OPs"


_migradas: set[str] = set()


def _carpeta(nombre: str) -> Path:
    """Carpeta base (JSON/Completadas/Pendiente/Historial), migrada a la
    estructura AAAA/MM la primera vez que se pide en esta sesión. La clave
    de "ya migrada" es la ruta completa, no solo `nombre` — _ruta_base()
    es estable durante toda la sesión de la app real, pero mantenerlo así
    de todos modos evita que un test con otra carpeta temporal (mismo
    nombre "JSON", otra base) se salte la migración por error."""
    p = _ruta_base() / nombre
    p.mkdir(parents=True, exist_ok=True)
    clave = str(p)
    if clave not in _migradas:
        cm.migrar_archivos_planos(p, _CAMPO_FECHA)
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
    de verdad de una OP, así que se deja plana (sin AAAA/MM)."""
    p = _ruta_base() / "HTML"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cargar_op(numero: int) -> dict | None:
    """Busca el JSON de una OP por número en las 4 carpetas (activa,
    completada, pendiente, historial) y lo devuelve, o None si no existe
    en ninguna. Mismo orden de búsqueda que
    ui.panel_produccion._ApiPanelProduccion.obtener_op_por_numero."""
    for carpeta in (carpeta_json(), carpeta_completadas(), carpeta_pendiente(), carpeta_historial()):
        ruta = cm.buscar(carpeta, numero)
        if ruta is not None:
            try:
                return json.loads(ruta.read_text(encoding="utf-8"))
            except Exception:
                return None
    return None


def guardar_op(datos: dict) -> Path:
    """Guarda datos como JSON de OP, en la subcarpeta AAAA/MM de
    JSON/ que corresponde a su Fecha_ingreso. Sobreescribe si ya existe el
    número (mismo mes — una OP recién promovida no puede ya existir en
    otro mes)."""
    numero = datos["Cotizacion"]
    anio, mes = cm.anio_mes(datos, _CAMPO_FECHA)
    destino = cm.subcarpeta_mes(carpeta_json(), anio, mes) / f"{numero}.json"
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def mover_a_completadas(numero: int) -> None:
    """Mueve el JSON de la OP completada de JSON/ a Completadas/."""
    cm.mover_preservando_mes(carpeta_json(), carpeta_completadas(), numero)


def mover_a_pendiente(numero: int) -> None:
    """Mueve el JSON de la OP de JSON/ a Pendiente/ (a la espera de que el
    cliente confirme una fecha de entrega definitiva)."""
    cm.mover_preservando_mes(carpeta_json(), carpeta_pendiente(), numero)


def reactivar_desde_pendiente(numero: int, fecha_entrega: str) -> None:
    """Mueve el JSON de Pendiente/ a JSON/ (misma subcarpeta AAAA/MM, la
    Fecha_ingreso no cambia) con la nueva Fecha_entrega."""
    origen = cm.buscar(carpeta_pendiente(), numero)
    if origen is None:
        return
    datos = json.loads(origen.read_text(encoding="utf-8"))
    datos["Fecha_entrega"] = fecha_entrega
    relativo = origen.relative_to(carpeta_pendiente())
    destino = carpeta_json() / relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    origen.unlink()


def actualizar_fecha_entrega(numero: int, fecha_entrega: str) -> None:
    """Actualiza la Fecha_entrega de una OP activa, sin moverla de carpeta."""
    ruta = cm.buscar(carpeta_json(), numero)
    if ruta is None:
        return
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["Fecha_entrega"] = fecha_entrega
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def envejecer_completadas(dias: int = DIAS_ENVEJECIMIENTO) -> None:
    """Mueve a Historial/ las OPs de Completadas/ cuya Fecha_entrega tenga
    más de `dias` días de antigüedad (misma subcarpeta AAAA/MM relativa,
    según su Fecha_ingreso). Mantiene liviano el set que lee el calendario
    del panel de listado."""
    limite = datetime.now() - timedelta(days=dias)
    for archivo in carpeta_completadas().rglob("*.json"):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
            fecha = datetime.strptime(datos["Fecha_entrega"], "%d/%m/%Y")
        except Exception:
            continue
        if fecha < limite:
            relativo = archivo.relative_to(carpeta_completadas())
            destino = carpeta_historial() / relativo
            destino.parent.mkdir(parents=True, exist_ok=True)
            archivo.replace(destino)


def actualizar_listos(numero: int, indices: list[int]) -> None:
    """Guarda en el JSON de la OP qué productos (por índice) están marcados
    como listos en el panel de TV, para que sobreviva a un reinicio."""
    ruta = cm.buscar(carpeta_json(), numero)
    if ruta is None:
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
    return cm.eliminar(
        [carpeta_json(), carpeta_completadas(), carpeta_pendiente(), carpeta_historial()],
        numero,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Historial por mes (ui/historial_ops.py) — la razón de ser de AAAA/MM: se
# puede saber qué meses tienen datos, y leer un mes puntual, sin abrir un
# solo archivo de los demás meses.
# ══════════════════════════════════════════════════════════════════════════════

def listar_meses_disponibles() -> list[tuple[int, int]]:
    """(año, mes) únicos con al menos una OP, en cualquiera de las 4
    carpetas — incluye las activas (JSON/Pendiente/Completadas), no solo
    Historial/. Solo lista nombres de subcarpeta, no abre ningún JSON."""
    return cm.listar_meses_disponibles([_carpeta(n) for n in _CARPETAS_BASE])


def listar_ops_del_mes(anio: int, mes: int) -> list[tuple[dict, str]]:
    """OPs de un año/mes puntual, juntando las 4 carpetas — incluye las
    activas. Devuelve [(datos, origen), ...] con `origen` en
    "JSON"/"Completadas"/"Pendiente"/"Historial" (para que la ventana de
    historial pueda mostrar el estado de cada una). Solo abre los archivos
    de ese mes — el resto del historial queda sin tocar."""
    carpetas_con_etiqueta = [(_carpeta(n), n) for n in _CARPETAS_BASE]
    return cm.listar_archivos_del_mes(carpetas_con_etiqueta, anio, mes)
