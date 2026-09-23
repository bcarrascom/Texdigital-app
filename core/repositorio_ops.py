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

# ── Estado de una OP (activa/entregada/entregada_atrasada/cancelada) ────────
# No es lo mismo que "en qué carpeta vive" (JSON/Completadas/Pendiente/
# Historial — eso sigue existiendo tal cual, es la mecánica de archivos).
# "Estado" es un campo dentro del JSON: se escribe recién al completar o
# cancelar una OP (ver mover_a_completadas/cancelar_op), comparando la
# fecha real contra Fecha_entrega para decidir entre "entregada" y
# "entregada_atrasada" — no es algo que el operador elija a mano.
ESTADO_ACTIVA              = "activa"
ESTADO_ENTREGADA           = "entregada"
ESTADO_ENTREGADA_ATRASADA  = "entregada_atrasada"
ESTADO_CANCELADA           = "cancelada"


def _hoy_dma() -> str:
    return datetime.now().strftime("%d/%m/%Y")


def estado_op(datos: dict, origen: str | None = None) -> str:
    """Estado de una OP para mostrar (ver docstring de la sección arriba).

    - Si el JSON ya trae "Estado" (OP completada/cancelada con este
      mecanismo), se usa tal cual.
    - Si no, pero trae "Fecha_completada" (no debería pasar salvo un JSON
      tocado a mano), se deriva comparando esa fecha contra Fecha_entrega.
    - Si no hay ninguno de los dos (OP vieja, de antes de este campo):
      "activa" si `origen` es "JSON"/"Pendiente" (sigue en una carpeta
      activa) o no se indica `origen`; "entregada" como resultado neutro
      si `origen` es "Completadas"/"Historial" (ya se sabe que se
      completó, solo no se sabe si fue a tiempo)."""
    estado = datos.get("Estado")
    if estado:
        return estado

    fecha_completada = datos.get("Fecha_completada")
    if fecha_completada:
        try:
            completada = datetime.strptime(fecha_completada, "%d/%m/%Y")
            entrega = datetime.strptime(datos.get("Fecha_entrega", ""), "%d/%m/%Y")
            return ESTADO_ENTREGADA if completada <= entrega else ESTADO_ENTREGADA_ATRASADA
        except Exception:
            pass

    if origen in ("Completadas", "Historial"):
        return ESTADO_ENTREGADA
    return ESTADO_ACTIVA


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
    """Mueve el JSON de la OP completada de JSON/ a Completadas/, grabando
    Fecha_completada (hoy) y Estado (entregada/entregada_atrasada, según
    Fecha_completada vs Fecha_entrega — ver estado_op)."""
    origen = carpeta_json() / f"{numero}.json"
    if not origen.exists():
        return
    datos = json.loads(origen.read_text(encoding="utf-8"))
    datos["Fecha_completada"] = _hoy_dma()
    datos["Estado"] = estado_op(datos)
    destino = carpeta_completadas() / origen.name
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    origen.unlink()


def mover_a_despachos(numero: int) -> None:
    """Mueve el JSON de la OP completada de JSON/ a Despachos/OPs/ (módulo
    Despachos, ver core/repositorio_despachos.py) en vez de a Completadas/
    — para OPs que tienen Despacho y/o Instalacion (ver
    ui/panel_produccion.py::completar_op, que decide cuál de las dos
    llamar). Graba Fecha_completada/Estado igual que mover_a_completadas
    (mismo criterio: entregada/entregada_atrasada según Fecha_completada
    vs Fecha_entrega), pero el destino y el resto del ciclo de vida
    (EstadoDespacho, guías) los maneja core.repositorio_despachos —
    importado acá adentro (no arriba del archivo) para que este módulo
    "base" no dependa en el import-time de uno más específico que vive
    encima suyo."""
    from core import repositorio_despachos

    origen = carpeta_json() / f"{numero}.json"
    if not origen.exists():
        return
    datos = json.loads(origen.read_text(encoding="utf-8"))
    datos["Fecha_completada"] = _hoy_dma()
    datos["Estado"] = estado_op(datos)
    repositorio_despachos.recibir_op(datos)
    origen.unlink()


def completar_op(numero: int) -> None:
    """Completa una OP activa — decide sola entre mover_a_completadas y
    mover_a_despachos según si tiene Despacho y/o Instalacion (ver
    docstring de mover_a_despachos). Punto único de esta decisión: la usan
    tanto el panel de producción (ui/panel_produccion.py, el único lugar
    donde esto se podía hacer hasta ahora) como el botón "Completar" de
    ver-op.html, en la ventana principal.

    Con el módulo Despachos apagado (core.config.MODULOS_HABILITADOS,
    pedido de Bruno 2026-09-17 pensando en sacar un release con el módulo
    todavía pausado) SIEMPRE va a mover_a_completadas, aunque la OP tenga
    Despacho/Instalacion cargado — nueva-cotizacion.html deja marcar esos
    checkboxes sin importar si el módulo está habilitado (son solo un
    monto más del total, no dependen de Despachos para calcularse), así
    que sin este chequeo una OP así completada quedaría archivada en
    Despachos/OPs/, un módulo sin pantalla accesible: nadie podría verla,
    marcarla entregada, ni generar su guía."""
    from core import config as _config

    numero = int(numero)
    datos = cargar_op(numero)
    despachos_habilitado = _config.MODULOS_HABILITADOS.get("despachos", True)
    if despachos_habilitado and datos and (datos.get("Despacho") is not None or datos.get("Instalacion") is not None):
        mover_a_despachos(numero)
    else:
        mover_a_completadas(numero)


def retirar_activa(numero: int) -> dict | None:
    """Saca una OP de JSON/ (activa) de circulación y devuelve su JSON
    crudo, o None sin tocar nada si `numero` no está ahí. Para "Recotizar"
    (ui/dialogo_recotizar.py, inversa de ui/dialogo_aprobar.py::
    promover_a_op): solo actúa sobre OPs activas a propósito — una OP ya
    completada/pendiente/en historial no se puede recotizar."""
    origen = carpeta_json() / f"{numero}.json"
    if not origen.exists():
        return None
    datos = json.loads(origen.read_text(encoding="utf-8"))
    origen.unlink()
    return datos


def cancelar_op(numero: int) -> None:
    """Marca una OP como cancelada y la saca de circulación activa — busca
    el JSON en JSON/ o Pendiente/ (las dos carpetas "activas"), le graba
    Estado="cancelada" y Fecha_completada (hoy, aunque acá no se use para
    derivar nada — es solo registro de cuándo se cerró), y lo mueve a
    Completadas/ (mismo destino que una entrega real; lo distingue el
    campo Estado, no la carpeta — envejecer_completadas la va a mover a
    Historial/ igual que cualquier otra, sin importar cuál sea)."""
    for carpeta in (carpeta_json(), carpeta_pendiente()):
        origen = carpeta / f"{numero}.json"
        if origen.exists():
            datos = json.loads(origen.read_text(encoding="utf-8"))
            datos["Fecha_completada"] = _hoy_dma()
            datos["Estado"] = ESTADO_CANCELADA
            destino = carpeta_completadas() / origen.name
            destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
            origen.unlink()
            return


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


def actualizar_op_ingreso_inser(numero: int, valor: str) -> bool:
    """Graba (o borra, si `valor` viene vacío) el campo OpIngresoInser de
    una OP — dato de producción para backlight (N° de ingreso en el
    proveedor de impresión Inser) que el usuario carga a mano desde
    ver-op.html, en cualquier momento de la vida de la OP: no hay un paso
    del ciclo (completar, pasar a pendiente, etc.) que lo gatille, así que
    se busca en las 4 carpetas igual que cargar_op/eliminar_op. Devuelve
    False sin tocar nada si la OP no existe en ninguna."""
    numero = int(numero)
    valor = valor.strip()
    for carpeta in (carpeta_json(), carpeta_completadas(), carpeta_pendiente()):
        ruta = carpeta / f"{numero}.json"
        if ruta.exists():
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            if valor:
                datos["OpIngresoInser"] = valor
            else:
                datos.pop("OpIngresoInser", None)
            ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
    ruta = cm.buscar(carpeta_historial(), numero)
    if ruta is None:
        return False
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if valor:
        datos["OpIngresoInser"] = valor
    else:
        datos.pop("OpIngresoInser", None)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


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
    historial pueda mostrar el estado de cada una). Cada `datos` queda con
    su "Estado" normalizado (ver estado_op) antes de devolverse, incluso
    para OPs viejas que no lo traían guardado."""
    resultado = []
    for nombre in _CARPETAS_PLANAS:
        for archivo in _carpeta(nombre).glob("*.json"):
            datos = _leer_json(archivo)
            if datos is not None and cm.anio_mes(datos, _CAMPO_FECHA) == (anio, mes):
                datos["Estado"] = estado_op(datos, nombre)
                resultado.append((datos, nombre))
    carpeta_mes = carpeta_historial() / f"{anio:04d}" / f"{mes:02d}"
    if carpeta_mes.is_dir():
        for archivo in carpeta_mes.glob("*.json"):
            datos = _leer_json(archivo)
            if datos is not None:
                datos["Estado"] = estado_op(datos, "Historial")
                resultado.append((datos, "Historial"))
    return resultado


def listar_todas_las_ops() -> list[dict]:
    """Todas las OPs guardadas (activas + Pendiente + Completadas +
    Historial), de TODOS los meses, cada una con su Estado normalizado
    (ver estado_op) — para pantallas que necesitan cruzar todo sin filtrar
    por mes (ver ui.api_menu._ops_activas, ui.api_historial_ops).

    No hay una carpeta "todas juntas" para leer de una — listar_ops_del_mes
    exige un (año, mes) puntual incluso para JSON/Completadas/Pendiente
    (planas, pero igual filtradas por Fecha_ingreso ahí adentro). Se
    recorre listar_meses_disponibles() (de Historial/, más que nada) + el
    mes actual (por si una OP activa recién creada todavía no aparece en
    ningún mes de Historial/), sin abrir un mismo número dos veces."""
    meses = set(listar_meses_disponibles())
    hoy = datetime.now()
    meses.add((hoy.year, hoy.month))

    vistos: set = set()
    todas: list[dict] = []
    for anio, mes in meses:
        for datos, _origen in listar_ops_del_mes(anio, mes):
            numero = datos.get("Cotizacion")
            if numero in vistos:
                continue
            vistos.add(numero)
            todas.append(datos)
    return todas


def avisos_ops(ops: list[dict] | None = None) -> list[dict]:
    """Un aviso por cada OP activa cuya Fecha_entrega ya pasó — pedido de
    Bruno (2026-09-13), para el ícono de aviso del módulo de Producción/OPs
    en el menú principal (mismo mecanismo que
    core.repositorio_inventario.avisos_stock, pero con una sola gravedad:
    acá no hay amarilla/naranja, una OP atrasada siempre es roja).

    `ops` se puede pasar ya leído y filtrado a activas (ver
    ui.api_menu.ApiMenu.obtener_resumen, que ya arma esa lista — mismo
    shape {numero, empresa, fecha_entrega} que devuelve ui.api_menu.
    _ops_activas, con fecha_entrega en "%d/%m/%Y") para no releer todo el
    historial de OPs una segunda vez. Si no se pasa, arma esa misma lista
    acá desde listar_todas_las_ops(). Una OP sin Fecha_entrega válida (no
    debería pasar en una activa, pero por las dudas) se ignora en vez de
    reventar."""
    if ops is None:
        ops = [
            {
                "numero":        d.get("Cotizacion"),
                "empresa":       d.get("Empresa", "—"),
                "fecha_entrega": d.get("Fecha_entrega", ""),
            }
            for d in listar_todas_las_ops()
            if d.get("Estado") == ESTADO_ACTIVA
        ]
    hoy = datetime.now().date()
    avisos = []
    for o in ops:
        try:
            entrega = datetime.strptime(o.get("fecha_entrega", ""), "%d/%m/%Y").date()
        except ValueError:
            continue
        if entrega < hoy:
            avisos.append({
                "numero":        o["numero"],
                "empresa":       o["empresa"],
                "fecha_entrega": o["fecha_entrega"],
            })
    return avisos
