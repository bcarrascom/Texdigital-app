"""
core/repositorio_inventario.py
Persistencia del módulo Inventario: rollos de tela — el único tipo de
material que se gestiona por ahora (ver core/config.py y el módulo
Inventario en menu.html; "Materiales" generales queda para más adelante).

Vive en rollos_tela.json, en Dropbox/SGTD/Conf (core.rutas.CONF) — mismo
lugar que direcciones.json (core/repositorio.py): dato que el operador va
agregando en el día a día, compartido entre todas las instalaciones (más
de una persona puede estar mirando el mismo stock). Los rollos
decomisionados (ver decomisionar_rollo) se sacan de ahí y quedan en
rollos_tela_historial.json, mismo directorio — un registro aparte, no se
borran sin dejar rastro.
"""

import json
import uuid
from datetime import datetime

from core.rutas import CONF as _CONF_DIR

ROLLOS_PATH = _CONF_DIR / "rollos_tela.json"
HISTORIAL_PATH = _CONF_DIR / "rollos_tela_historial.json"


def _hoy_dma() -> str:
    return datetime.now().strftime("%d/%m/%Y")


def _leer_json(ruta) -> list[dict]:
    if not ruta.exists():
        return []
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return []


def _escribir_json(ruta, datos: list[dict]) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def _leer() -> list[dict]:
    rollos = _leer_json(ROLLOS_PATH)
    # Backfill de "fecha" para rollos guardados antes de que existiera el
    # campo (mismo criterio que core.repositorio.cargar_direcciones con
    # "id"): se completa la primera vez que se leen y se guarda, no hace
    # falta una migración aparte. Hoy es la mejor fecha disponible para un
    # rollo que nunca la tuvo.
    faltan_fechas = False
    for r in rollos:
        if not r.get("fecha"):
            r["fecha"] = _hoy_dma()
            faltan_fechas = True
    if faltan_fechas:
        _escribir(rollos)
    return rollos


def _escribir(rollos: list[dict]) -> None:
    _escribir_json(ROLLOS_PATH, rollos)


def listar_rollos() -> list[dict]:
    """Todos los rollos, el más nuevo primero (mismo criterio que
    cotizaciones/OPs en el menú: ordenar por ID descendente)."""
    return sorted(_leer(), key=lambda r: r.get("id", ""), reverse=True)


def obtener_rollo(id_: str) -> dict | None:
    for r in _leer():
        if r.get("id") == id_:
            return r
    return None


def _siguiente_id(rollos: list[dict]) -> str:
    """4 dígitos, con ceros a la izquierda, siguiente al mayor ID existente
    — se deriva de los datos en vez de llevar un contador aparte (mismo
    espíritu que core.repositorio_despachos.siguiente_numero_guia).
    Empieza en "0001"."""
    maximo = 0
    for r in rollos:
        try:
            maximo = max(maximo, int(r.get("id", 0)))
        except (TypeError, ValueError):
            continue
    return f"{maximo + 1:04d}"


def crear_rollo(
    nombre_textil: str, ancho: float, metros_restantes: float,
    metros_iniciales: float | None = None,
) -> dict:
    """`metros_iniciales` es opcional: el inventario arranca con rollos que
    ya vienen usados de antes, así que lo único que se sabe con certeza es
    cuánto queda AHORA (`metros_restantes`) — no necesariamente cuánto
    medía el rollo antes de que se le sacara nada. Si no se informa, se
    asume que el rollo entra al sistema completo (iniciales = restantes,
    o sea 100% de stock)."""
    rollos = _leer()
    metros_restantes = float(metros_restantes)
    metros_iniciales = float(metros_iniciales) if metros_iniciales else metros_restantes
    nuevo = {
        "id":               _siguiente_id(rollos),
        "nombre_textil":    nombre_textil.strip(),
        "ancho":            float(ancho),
        "metros_iniciales": metros_iniciales,
        "metros_restantes": metros_restantes,
        "fecha":            _hoy_dma(),
        "usos":             [],
    }
    rollos.append(nuevo)
    _escribir(rollos)
    return nuevo


def editar_rollo(id_: str, nombre_textil: str, ancho: float) -> dict | None:
    """Solo nombre_textil/ancho son editables después de creado —
    metros_iniciales/restantes se manejan aparte (ver ajustar_restante),
    para que no se pueda pisar a mano el historial de stock del rollo."""
    rollos = _leer()
    for r in rollos:
        if r.get("id") == id_:
            r["nombre_textil"] = nombre_textil.strip()
            r["ancho"] = float(ancho)
            _escribir(rollos)
            return r
    return None


def decomisionar_rollo(id_: str) -> bool:
    """"Decomisionar" (botón 🗑 de la tabla de rollos, panel de Inventario
    en menu.html) — un rollo agotado o demasiado flaco para que alguien lo
    elija a mano no se borra sin dejar rastro: sale de rollos_tela.json y
    su registro completo (con todo su historial de usos) queda archivado
    en HISTORIAL_PATH, con la fecha del decomiso. Devuelve True si
    encontró y movió algo."""
    rollos = _leer()
    objetivo = next((r for r in rollos if r.get("id") == id_), None)
    if objetivo is None:
        return False
    nuevos = [r for r in rollos if r.get("id") != id_]
    _escribir(nuevos)

    objetivo["fecha_decomiso"] = _hoy_dma()
    historial = _leer_json(HISTORIAL_PATH)
    historial.append(objetivo)
    _escribir_json(HISTORIAL_PATH, historial)
    return True


def _agregar_registro(r: dict, *, tipo: str, anterior: float, nuevo: float, descripcion: str) -> None:
    """Un solo formato de entrada para TODO lo que le pasa al stock de un
    rollo — ajuste manual o consumo automático (ver ajustar_restante/
    consumir_para_op): guarda el valor de ANTES y DESPUÉS (no un delta),
    para poder revisarlo más tarde sin ambigüedad y para poder deshacer
    la entrada más reciente (ver eliminar_ajuste)."""
    r.setdefault("usos", []).append({
        "id":                        uuid.uuid4().hex,
        "fecha":                     _hoy_dma(),
        "tipo":                      tipo,  # "ajuste" (manual) | "consumo" (aprobar cotización)
        "metros_restantes_anterior": anterior,
        "metros_restantes_nuevo":    nuevo,
        "descripcion":               descripcion.strip(),
    })


def ajustar_restante(id_: str, nuevo_restante: float, descripcion: str = "") -> dict | None:
    """Corrección manual del stock de un rollo (diálogo 'Ajustar cantidad'
    del panel de Inventario, menu.html) — a diferencia del consumo
    automático (ver consumir_para_op), acá el usuario pone DIRECTO la
    cantidad que corresponde, no un delta a descontar: sirve tanto para
    corregir un error de carga como cualquier ajuste que no venga de
    aprobar una cotización. Si el nuevo valor supera metros_iniciales, ese
    también sube — así la barra de stock nunca muestra más de 100%;
    "iniciales" pasa a ser, de hecho, lo más grande que
    se supo que tuvo este rollo. Queda registrado en 'usos' SIEMPRE (no
    solo si baja), para poder revisarlo después. Devuelve el rollo
    actualizado, o None si no existe."""
    rollos = _leer()
    for r in rollos:
        if r.get("id") == id_:
            anterior = r.get("metros_restantes", 0.0)
            nuevo_restante = round(float(nuevo_restante), 3)
            r["metros_restantes"] = nuevo_restante
            if nuevo_restante > r.get("metros_iniciales", 0.0):
                r["metros_iniciales"] = nuevo_restante
            _agregar_registro(r, tipo="ajuste", anterior=anterior, nuevo=nuevo_restante, descripcion=descripcion)
            _escribir(rollos)
            return r
    return None


def eliminar_ajuste(id_rollo: str, id_ajuste: str) -> dict | None:
    """Deshace un ajuste/consumo cargado por error — solo tiene sentido
    sobre la entrada MÁS RECIENTE (usos[-1]): cada entrada nueva guarda el
    restante de ANTES relativo a la que le sigue, así que deshacer una del
    medio dejaría el resto del historial apuntando a un valor que ya no es
    real. Si `id_ajuste` no es la más reciente, no hace nada y devuelve
    None (el diálogo solo ofrece deshacer en la fila de arriba)."""
    rollos = _leer()
    for r in rollos:
        if r.get("id") == id_rollo:
            usos = r.get("usos", [])
            if not usos or usos[-1].get("id") != id_ajuste:
                return None
            objetivo = usos.pop()
            r["metros_restantes"] = objetivo.get("metros_restantes_anterior", r.get("metros_restantes", 0.0))
            _escribir(rollos)
            return r
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Suficiencia de stock para una cotización y consumo automático al aprobarla
# — ver ui/api_cotizacion.py::verificar_materiales (aviso en nueva-cotizacion.
# html) y ui/dialogo_aprobar.py (bloquea/consume al aprobar). "Metros" acá
# siempre son metros LINEALES de rollo (lo que trackea un rollo), no área.
# ══════════════════════════════════════════════════════════════════════════════

def _metros_lineales(producto_interno: dict) -> tuple[str, float]:
    """(nombre_textil, metros lineales de rollo que consume) de un
    producto interno de cotización (ver ui/api_cotizacion.py::
    _producto_a_interno / core.repositorio_cotizaciones.producto_desde_json).
    Backlight factura en ÁREA (m², ver core/precios.py::costo_producto) —
    acá se convierte a metros lineales dividiendo por el ancho de catálogo
    del textil (recursos/textiles.json): un metro de rollo entero, a lo
    ancho. Sin ese ancho en el catálogo no hay forma de convertir —
    devuelve 0 en vez de reventar (no bloquea la aprobación por un textil
    que ni siquiera está en el catálogo)."""
    from core.precios import costo_producto
    from core.repositorio import TEXTILES_ANCHOS

    es_backlight = "tela" in producto_interno
    textil = (producto_interno.get("tela" if es_backlight else "textil") or "").strip()
    if not textil:
        return "", 0.0
    resultado = costo_producto(producto_interno)
    if es_backlight:
        ancho_tela = TEXTILES_ANCHOS.get(textil)
        metros = resultado["ml_o_area"] / ancho_tela if ancho_tela else 0.0
    else:
        metros = resultado["ml_o_area"]
    return textil, metros


def metros_necesarios(productos_internos: list[dict]) -> dict[str, float]:
    """{textil: metros lineales totales que necesita esta lista de
    productos} — agrupa por textil, sumando todos los productos que lo
    usan."""
    necesarios: dict[str, float] = {}
    for p in productos_internos:
        textil, metros = _metros_lineales(p)
        if textil and metros:
            necesarios[textil] = necesarios.get(textil, 0.0) + metros
    return necesarios


def stock_por_textil() -> dict[str, float]:
    """{textil: suma de metros_restantes de todos sus rollos}."""
    stock: dict[str, float] = {}
    for r in _leer():
        textil = r.get("nombre_textil", "")
        stock[textil] = stock.get(textil, 0.0) + r.get("metros_restantes", 0.0)
    return stock


def calcular_faltantes(productos_internos: list[dict]) -> list[dict]:
    """Textiles que NO alcanzan para cubrir `productos_internos`: lista de
    {textil, necesario, disponible, faltante} (metros lineales, 2
    decimales) — vacía si hay stock suficiente de todos. Usado tanto para
    el aviso de nueva-cotizacion.html como para bloquear la aprobación de
    una cotización (ver ui/dialogo_aprobar.py)."""
    necesarios = metros_necesarios(productos_internos)
    disponible = stock_por_textil()
    faltantes = []
    for textil, necesario in necesarios.items():
        stock = disponible.get(textil, 0.0)
        if stock + 1e-6 < necesario:
            faltantes.append({
                "textil":     textil,
                "necesario":  round(necesario, 2),
                "disponible": round(stock, 2),
                "faltante":   round(necesario - stock, 2),
            })
    return faltantes


def consumir_para_op(productos_internos: list[dict], numero_op, referencia: str = "") -> list[list[dict]]:
    """Descuenta de los rollos el material que gasta `productos_internos`
    — se llama SOLO al aprobar una cotización (ui/dialogo_aprobar.py),
    nunca antes: es el único momento en que el material se da por gastado
    de verdad (ver docstring del módulo).

    De qué rollo se descuenta cada producto NO lo elige el usuario: entre
    los rollos del textil que corresponda, siempre se prioriza el que
    tiene MENOS metros restantes (no el más viejo). Es a propósito —
    pedido directo de Bruno: en la oficina se acumulan rollos flacos (varios
    con menos de 50 m) que nadie elige a mano "por flojera", prefiriendo
    siempre un rollo nuevo y grande — resultado: millones de pesos en tela
    a medio usar, acumulándose. Consumir primero el rollo más chico que
    alcance fuerza a terminarlos antes de tocar uno grande, así los rollos
    nuevos se abren recién cuando de verdad hacen falta.

    Devuelve, en el MISMO ORDEN que `productos_internos`, qué rollo(s) le
    tocaron a cada producto: [[{"id", "metros"}, ...], ...] — un producto
    puede repartirse entre más de un rollo si el primero (el más chico) no
    alcanza solo. Esto es lo que ui/dialogo_aprobar.py graba en
    producto["RollosUsados"] de la OP, para que el panel de producción
    (recursos/panel_tv/display_op.html) le diga al operario qué rollo
    buscar — la asignación se decide UNA vez, acá, no se recalcula después.

    El reparto es GLOBAL a la OP, no por producto: se consume en el orden
    de aparición de los productos, así que si dos comparten textil, el
    segundo puede terminar en un rollo distinto al primero (el más chico
    ya quedó en 0). Asume que ya se validó con calcular_faltantes() que
    alcanza — si por alguna razón no alcanzara, un producto se queda sin
    cubrir del todo y sigue sin reventar: frenar la aprobación es
    responsabilidad de quien llama, no de esta función."""
    rollos = _leer()
    descripcion = f"OP {numero_op}" + (f" · {referencia}" if referencia else "")
    asignacion_por_producto: list[list[dict]] = []

    for producto in productos_internos:
        textil, necesario = _metros_lineales(producto)
        if not textil or necesario <= 0:
            asignacion_por_producto.append([])
            continue

        # Se re-ordena EN CADA producto, no una sola vez al principio: el
        # consumo de un producto anterior puede haber dejado a un rollo en
        # 0 (sale de la lista) o haber corrido a otro al primer lugar.
        candidatos = sorted(
            (r for r in rollos if r.get("nombre_textil") == textil and r.get("metros_restantes", 0.0) > 0),
            key=lambda r: r.get("metros_restantes", 0.0),
        )
        usados = []
        por_cubrir = necesario
        for r in candidatos:
            if por_cubrir <= 0:
                break
            anterior = r.get("metros_restantes", 0.0)
            usar = min(anterior, por_cubrir)
            nuevo = round(anterior - usar, 3)
            r["metros_restantes"] = nuevo
            _agregar_registro(r, tipo="consumo", anterior=anterior, nuevo=nuevo, descripcion=descripcion)
            usados.append({"id": r["id"], "metros": round(usar, 3)})
            por_cubrir -= usar
        asignacion_por_producto.append(usados)

    _escribir(rollos)
    return asignacion_por_producto
