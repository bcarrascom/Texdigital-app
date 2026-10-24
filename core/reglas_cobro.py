"""
core/reglas_cobro.py
Las reglas con que se cobra una cotización, más allá del precio de cada
componente — un ajuste GLOBAL (ver core.ajustes_globales), editable en
Configuración › Reglas de cobro. Pedido de Bruno (2026-10-22): editables,
partiendo de las que la app traía fijas (core.precios):

  iva               % de IVA sobre el neto total
  ml_minimo         mínimo de ML que se cobra por grupo de textil
  m2_minimo         lo mismo en Backlight, en M²
  tramos_descuento  descuento por volumen: [[desde m², %], ...]

En Conf/reglas_cobro.json: {"version": 1, "iva": ..., "ml_minimo": ...,
"m2_minimo": ..., "tramos_descuento": [[m², %], ...]}. Lo que falte (o no se
pueda leer) vale lo de core.precios.

Cada cotización congela las reglas con que se calculó (ver
core.lista_precios): cambiarlas no cambia el total de las ya guardadas.
"""

from core import ajustes_globales
from core import precios as _precios

NOMBRE = "reglas_cobro"
VERSION = 1

# Lo que la app traía fijo (y vale mientras no se guarde nada).
POR_DEFECTO = {
    "iva":              float(_precios.IVA_PORCENTAJE),
    "ml_minimo":        float(_precios.ML_MINIMO_POR_PRODUCTO),
    "m2_minimo":        float(_precios.M2_MINIMO_POR_PRODUCTO),
    "tramos_descuento": [[float(m2), float(pct)] for m2, pct in _precios.TRAMOS_DESCUENTO_TEXTIL],
}

MAX_TRAMOS = 10


def _numero(v) -> float | None:
    if v is None or isinstance(v, bool) or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n == n and abs(n) != float("inf") else None


def _tramos(v) -> list[list[float]] | None:
    """Los tramos como [[m², %], ...] de mayor a menor, o None si no se pueden leer."""
    if not isinstance(v, list):
        return None
    tramos = []
    for t in v:
        if not isinstance(t, (list, tuple)) or len(t) != 2:
            return None
        m2, pct = _numero(t[0]), _numero(t[1])
        if m2 is None or pct is None:
            return None
        tramos.append([m2, pct])
    return sorted(tramos, key=lambda t: t[0], reverse=True)


def validar(datos: dict) -> list[dict]:
    """Lo que impide guardar: [{"campo": ..., "mensaje": ...}] ("campo" es
    "iva", "ml_minimo", "m2_minimo" o "tramo:<i>" con el índice tal como
    vino). Vacía si todo está bien."""
    errores = []
    iva = _numero(datos.get("iva"))
    if iva is None or not 0 <= iva < 100:
        errores.append({"campo": "iva", "mensaje": "El IVA tiene que ser un % entre 0 y 100."})
    for campo, unidad in (("ml_minimo", "ML"), ("m2_minimo", "M²")):
        n = _numero(datos.get(campo))
        if n is None or n < 0:
            errores.append({"campo": campo, "mensaje": f"El mínimo tiene que ser 0 {unidad} o más."})
    tramos = datos.get("tramos_descuento")
    if not isinstance(tramos, list):
        return errores + [{"campo": "tramos", "mensaje": "Faltan los tramos de descuento."}]
    if len(tramos) > MAX_TRAMOS:
        errores.append({"campo": "tramos", "mensaje": f"Como máximo {MAX_TRAMOS} tramos."})
    vistos = set()
    for i, t in enumerate(tramos):
        m2 = _numero(t[0]) if isinstance(t, (list, tuple)) and len(t) == 2 else None
        pct = _numero(t[1]) if isinstance(t, (list, tuple)) and len(t) == 2 else None
        if m2 is None or m2 <= 0:
            errores.append({"campo": f"tramo:{i}", "mensaje": "Los m² del tramo tienen que ser más que 0."})
        elif m2 in vistos:
            errores.append({"campo": f"tramo:{i}", "mensaje": "Hay dos tramos desde los mismos m²."})
        elif pct is None or not 0 < pct < 100:
            errores.append({"campo": f"tramo:{i}", "mensaje": "El descuento tiene que ser un % entre 0 y 100."})
        if m2 is not None:
            vistos.add(m2)
    return errores


def cargar() -> dict:
    """Las reglas vigentes, cada una con su valor por defecto si falta o no
    se puede leer."""
    guardado = ajustes_globales.leer(NOMBRE)
    reglas = {}
    for campo in ("iva", "ml_minimo", "m2_minimo"):
        n = _numero(guardado.get(campo))
        reglas[campo] = POR_DEFECTO[campo] if n is None or n < 0 else n
    tramos = _tramos(guardado.get("tramos_descuento"))
    reglas["tramos_descuento"] = [list(t) for t in POR_DEFECTO["tramos_descuento"]] if tramos is None else tramos
    return reglas


def guardar(datos: dict) -> dict:
    """{"ok": True} o {"ok": False, "errores": [...]} (ver `validar`)."""
    errores = validar(datos)
    if errores:
        return {"ok": False, "errores": errores}
    reglas = {campo: _numero(datos[campo]) for campo in ("iva", "ml_minimo", "m2_minimo")}
    reglas["tramos_descuento"] = _tramos(datos["tramos_descuento"])
    try:
        ajustes_globales.guardar(NOMBRE, reglas, VERSION)
    except ajustes_globales.AjusteMasNuevo:
        return {"ok": False, "errores": [{"campo": None, "mensaje":
                "Estas reglas las guardó una versión más nueva de la app. Actualiza esta instalación para poder cambiarlas."}]}
    return {"ok": True}


def solo_lectura() -> bool:
    return ajustes_globales.es_mas_nuevo(NOMBRE, VERSION)
