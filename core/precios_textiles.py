"""
core/precios_textiles.py
Cuánto se cobra por metro de cada textil — un ajuste GLOBAL (ver
core.ajustes_globales), editable en Configuración › Textiles. Pedido de
Bruno (2026-10-22): nada de precios fijos dentro de la app.

Cada textil se cobra de una de dos formas:
  "fijo"   un valor por metro (ML, o M² en Backlight) que el usuario define
           en Configuración.
  "rollo"  el valor de venta del rollo de Inventario del que va a salir la
           tela (cada rollo tiene el suyo, ver core.repositorio_inventario).

Y un interruptor general decide cuál vale:
  modo "fijo"        todos los textiles por su valor fijo
  modo "rollo"       todos por el valor del rollo
  modo "por_textil"  cada textil según su propio interruptor ("cobro")

El rollo "del que va a salir la tela" es el mismo que elegiría Inventario al
aprobar (el más chico que alcanza solo, ver _asignar_rollos_por_producto),
mirado producto por producto con el stock de hoy. Si ningún rollo alcanza
—o el que alcanza no tiene valor—, se cobra el valor fijo del textil y el
cotizador lo avisa (decisión de Bruno, 2026-10-26). Por eso el valor fijo
es OBLIGATORIO en todos los textiles, también en los que se cobran por
rollo: es el respaldo. Un textil sin valor (datos de antes de esa regla)
sale sin precio (0), igual que uno que no está en el catálogo.

En Conf/precios_textiles.json:
    {"version": 1, "modo": "fijo" | "rollo" | "por_textil",
     "textiles": {nombre: {"cobro": "fijo" | "rollo", "valor": número | null}}}

Mientras el archivo no exista (o no traiga un textil), se parte de lo que
viene en recursos/textiles.json: cobro fijo con el valor de ahí.
"""

from core import ajustes_globales
from core import config as _config

NOMBRE = "precios_textiles"
VERSION = 1

MODOS = ("fijo", "rollo", "por_textil")
COBROS = ("fijo", "rollo")


def _inventario_habilitado() -> bool:
    return _config.MODULOS_HABILITADOS.get("inventario", True)


def _numero(v) -> float | None:
    """Un valor de precio como número, o None si no hay (vacío, texto, no
    finito). El 0 y los negativos sí vuelven: los rechaza `validar`."""
    if v is None or isinstance(v, bool):
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n == n and n not in (float("inf"), float("-inf")) else None


# ── Leer ─────────────────────────────────────────────────────────────────────

def cargar() -> dict:
    """Los ajustes vigentes, con un renglón por textil del catálogo:

        {"modo": ..., "textiles": [{"nombre", "ancho", "cobro", "valor"}, ...]}
    """
    from core.repositorio import TEXTILES, TEXTILES_ANCHOS, TEXTILES_VALORES

    guardado = ajustes_globales.leer(NOMBRE)
    modo = guardado.get("modo") if guardado.get("modo") in MODOS else "fijo"
    por_nombre = guardado.get("textiles") if isinstance(guardado.get("textiles"), dict) else {}
    textiles = []
    for nombre in TEXTILES:
        g = por_nombre.get(nombre) if isinstance(por_nombre.get(nombre), dict) else {}
        textiles.append({
            "nombre": nombre,
            "ancho":  TEXTILES_ANCHOS.get(nombre),
            "cobro":  g.get("cobro") if g.get("cobro") in COBROS else "fijo",
            # "valor" guardado en null es "sin valor", a propósito: no vuelve al del catálogo.
            "valor":  _numero(g["valor"]) if "valor" in g else TEXTILES_VALORES.get(nombre),
        })
    return {"modo": modo, "textiles": textiles}


def cobro_efectivo(modo: str, cobro: str) -> str:
    """Cómo se cobra de verdad un textil con este `cobro`, bajo este `modo`.
    Con Inventario apagado no hay rollos: todo es fijo."""
    if not _inventario_habilitado():
        return "fijo"
    if modo == "por_textil":
        return cobro if cobro in COBROS else "fijo"
    return "rollo" if modo == "rollo" else "fijo"


def valores_fijos(ajustes: dict | None = None) -> dict[str, float]:
    """{textil: valor fijo por metro} de los que tienen uno. Un nombre que
    no es del catálogo (no se puede configurar) conserva su valor de
    recursos/, si tiene."""
    from core.repositorio import TEXTILES_VALORES

    from core.catalogo import alias_textiles

    ajustes = ajustes or cargar()
    configurables = {t["nombre"] for t in ajustes["textiles"]}
    fijos = {n: v for n, v in TEXTILES_VALORES.items() if n not in configurables}
    fijos.update({t["nombre"]: t["valor"] for t in ajustes["textiles"] if t["valor"] is not None})
    # Los nombres anteriores de un textil renombrado valen lo mismo que él
    # (las cotizaciones ya hechas los usan, ver core.catalogo).
    fijos.update({viejo: fijos[nuevo] for viejo, nuevo in alias_textiles().items() if nuevo in fijos})
    return fijos


def valor_fijo(nombre: str) -> float | None:
    return valores_fijos().get(nombre)


# ── Validar y guardar ───────────────────────────────────────────────────────

def validar(modo, textiles: list[dict]) -> list[dict]:
    """Lo que impide guardar: [{"textil": nombre | None, "mensaje": ...}].
    Vacía si todo está bien. La misma regla que aplica Configuración antes
    de dejar apretar Guardar, repetida acá para que no dependa de la pantalla."""
    errores = []
    if modo not in MODOS:
        return [{"textil": None, "mensaje": "Elige cómo se cobran los textiles."}]
    if modo != "fijo" and not _inventario_habilitado():
        errores.append({"textil": None, "mensaje": "El módulo Inventario está apagado: los textiles solo se pueden cobrar por valor fijo."})
    for t in textiles:
        nombre = t.get("nombre")
        if modo == "por_textil" and t.get("cobro") not in COBROS:
            errores.append({"textil": nombre, "mensaje": "Elige si se cobra por valor fijo o por rollo."})
            continue
        valor = t.get("valor")
        if valor in (None, ""):
            # Obligatorio también por rollo: es lo que se cobra si ningún rollo alcanza.
            errores.append({"textil": nombre, "mensaje": "Falta el valor por metro."})
            continue
        n = _numero(valor)
        if n is None or n <= 0:
            errores.append({"textil": nombre, "mensaje": "El valor tiene que ser un monto mayor que 0."})
    return errores


def guardar(datos: dict) -> dict:
    """Guarda lo que manda Configuración: {"modo", "textiles": [{nombre,
    cobro, valor}]}. Solo cuentan los textiles del catálogo. Devuelve
    {"ok": True} o {"ok": False, "errores": [...]} (ver `validar`)."""
    from core.repositorio import TEXTILES

    modo = datos.get("modo")
    catalogo = set(TEXTILES)
    textiles = [t for t in datos.get("textiles") or [] if t.get("nombre") in catalogo]
    errores = validar(modo, textiles)
    if errores:
        return {"ok": False, "errores": errores}

    guardado = ajustes_globales.leer(NOMBRE).get("textiles")
    por_nombre = dict(guardado) if isinstance(guardado, dict) else {}
    for t in textiles:
        valor = t.get("valor")
        por_nombre[t["nombre"]] = {
            "cobro": t.get("cobro") if t.get("cobro") in COBROS else "fijo",
            "valor": None if valor in (None, "") else _numero(valor),
        }
    try:
        ajustes_globales.guardar(NOMBRE, {"modo": modo, "textiles": por_nombre}, VERSION)
    except ajustes_globales.AjusteMasNuevo:
        return {"ok": False, "errores": [{"textil": None, "mensaje":
                "Estos precios los guardó una versión más nueva de la app. Actualiza esta instalación para poder cambiarlos."}]}
    return {"ok": True}


def solo_lectura() -> bool:
    """Si el archivo es de una versión más nueva: se ve, pero no se guarda."""
    return ajustes_globales.es_mas_nuevo(NOMBRE, VERSION)


def _por_nombre() -> dict:
    guardado = ajustes_globales.leer(NOMBRE).get("textiles")
    return dict(guardado) if isinstance(guardado, dict) else {}


def fijar(nombre: str, cobro: str = "fijo", valor: float | None = None) -> None:
    """Cómo se cobra UN textil (el que se acaba de agregar, ver
    core.catalogo.agregar_textil), sin tocar los demás."""
    por_nombre = _por_nombre()
    por_nombre[nombre] = {"cobro": cobro if cobro in COBROS else "fijo", "valor": valor}
    ajustes_globales.guardar(NOMBRE, {"textiles": por_nombre}, VERSION)


def renombrar(viejo: str, nuevo: str) -> None:
    """Lo guardado de `viejo` pasa a `nuevo` (ver core.catalogo.editar_textil)."""
    por_nombre = _por_nombre()
    if viejo in por_nombre:
        por_nombre[nuevo] = por_nombre.pop(viejo)
        ajustes_globales.guardar(NOMBRE, {"textiles": por_nombre}, VERSION)


# ── Valorizar ────────────────────────────────────────────────────────────────

def _nombre_textil(d: dict) -> str:
    """El nombre ACTUAL del textil de `d` (una cotización vieja puede traer
    uno anterior, ver core.catalogo)."""
    from core.catalogo import nombre_textil
    return nombre_textil((d.get("tela") if "tela" in d else d.get("textil")) or "")


def _por_rollo(d: dict, rollos: list[dict]) -> tuple[float | None, str, str | None]:
    """(valor, motivo, id del rollo) del rollo del que saldría este producto,
    ver docstring del módulo. motivo: "rollo" (el más chico que alcanza, con
    su valor), "sin_rollo" (ninguno alcanza) o "rollo_sin_valor" (el que
    alcanza no tiene valor). Sin valor en los dos últimos: vale el fijo."""
    from core.repositorio_inventario import rollo_para_producto

    rollo = rollo_para_producto(d, rollos)
    if rollo is None:
        return None, "sin_rollo", None
    if rollo.get("valor") is None:
        return None, "rollo_sin_valor", rollo.get("id")
    return float(rollo["valor"]), "rollo", rollo.get("id")


def valorizador(ajustes: dict | None = None):
    """Una función producto → valor por metro de su textil (o None si no
    tiene), para core.precios.costo_producto(valor_textil=...). Lee los
    ajustes al crearla y los rollos recién la primera vez que un producto
    se cobra por rollo, una sola vez: crear una por cálculo, no guardarla.

    La función trae además `.detalle(producto)`: de dónde sale ese valor, para
    que el cotizador avise cuando un textil se cotiza sin precio o sin un rollo
    que alcance (pedido de Bruno, 2026-10-26):

        {"textil", "cobro": "fijo" | "rollo", "valor": número | None,
         "origen": "fijo" | "rollo" | "sin_rollo" | "rollo_sin_valor",
         "rollo": id | None}

    "sin_rollo" / "rollo_sin_valor": se cobra por rollo, pero ningún rollo
    alcanza (o el que alcanza no tiene valor), así que vale el fijo. "valor"
    None: el textil no tiene valor fijo (se cotiza en $0)."""
    from core.repositorio_inventario import listar_rollos

    ajustes = ajustes or cargar()
    fijos = valores_fijos(ajustes)
    por_rollo = {t["nombre"] for t in ajustes["textiles"] if cobro_efectivo(ajustes["modo"], t["cobro"]) == "rollo"}
    rollos = None

    def detalle(d: dict) -> dict:
        nonlocal rollos
        nombre = _nombre_textil(d)
        if nombre in por_rollo:
            if rollos is None:
                rollos = listar_rollos()
            v, motivo, rollo = _por_rollo(d, rollos)
            if v is not None:
                return {"textil": nombre, "cobro": "rollo", "valor": v, "origen": motivo, "rollo": rollo}
            return {"textil": nombre, "cobro": "rollo", "valor": fijos.get(nombre), "origen": motivo, "rollo": rollo}
        return {"textil": nombre, "cobro": "fijo", "valor": fijos.get(nombre), "origen": "fijo", "rollo": None}

    def valor(d: dict) -> float | None:
        return detalle(d)["valor"]

    valor.detalle = detalle
    return valor


def textiles_sin_precio(ajustes: dict | None = None) -> list[str]:
    """Los textiles sin valor fijo. Desde 2026-10-26 el valor fijo es
    obligatorio (ver `validar`), así que solo pasa con datos de antes: el
    cotizador avisa apenas se elige uno, porque podría cotizarse en $0."""
    ajustes = ajustes or cargar()
    fijos = valores_fijos(ajustes)
    return [t["nombre"] for t in ajustes["textiles"] if t["nombre"] not in fijos]
