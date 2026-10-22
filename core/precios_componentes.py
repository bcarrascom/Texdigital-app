"""
core/precios_componentes.py
Cuánto se cobra por cada estructura, cada terminación y cada pieza de una
caja de Backlight — ajustes GLOBALES (ver core.ajustes_globales), editables
en Configuración. Pedido de Bruno (2026-10-22): nada de precios fijos
dentro de la app.

Los nombres (qué estructuras y terminaciones existen, qué piezas lleva una
caja) siguen siendo los del catálogo de la app (recursos/); acá se cambia
solo cuánto vale cada uno. Mientras no se guarde nada, valen los de ahí.

  Conf/precios_estructuras.json    {"version": 1, "valores": {nombre: {"valorUNIT": x} | {"valorML": x}}}
  Conf/precios_terminaciones.json  (igual)
  Conf/precios_cajas.json          {"version": 1, "cajas": {mismo formato que recursos/precios_cajas.json}}

Una estructura con materiales de Inventario asociados se sigue cobrando por
esos materiales (ver core.repositorio_materiales.kwargs_precios): el valor
de acá es el que vale cuando no.
"""

import copy

from core import ajustes_globales

VERSION = 1

LISTAS = ("estructuras", "terminaciones")
_ARCHIVO = {"estructuras": "precios_estructuras", "terminaciones": "precios_terminaciones"}
_ARCHIVO_CAJAS = "precios_cajas"

# Las secciones de una caja con un precio por clave ("fp": por watts).
SECCIONES_CAJA = ("luces", "traseras", "armado", "fp", "perfiles")


def _numero(v) -> float | None:
    if v is None or isinstance(v, bool) or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n == n and abs(n) != float("inf") else None


def _catalogo(tipo: str) -> dict[str, dict]:
    """{nombre: {"valorUNIT"|"valorML": x}} de recursos/, en su orden."""
    from core import repositorio
    if tipo == "estructuras":
        return repositorio.ESTRUCTURAS_LEGADO_VALORES
    if tipo == "terminaciones":
        return repositorio.TERMINACIONES_LEGADO_VALORES
    raise ValueError(tipo)


# ── Estructuras y terminaciones ─────────────────────────────────────────────

def valores(tipo: str) -> dict[str, dict]:
    """{nombre: {"valorUNIT": x} | {"valorML": x}} vigentes — el formato que
    recibe core.precios.costo_producto. La unidad es la del catálogo."""
    base = _catalogo(tipo)
    guardado = ajustes_globales.leer(_ARCHIVO[tipo]).get("valores")
    guardado = guardado if isinstance(guardado, dict) else {}
    vigentes = {}
    for nombre in base:
        clave = next(iter(base[nombre]))
        g = guardado.get(nombre)
        n = _numero(g.get(clave)) if isinstance(g, dict) else None
        vigentes[nombre] = {clave: base[nombre][clave] if n is None or n <= 0 else n}
    return vigentes


def cargar_lista(tipo: str) -> list[dict]:
    """[{"nombre", "valor", "unidad": "un." | "ML"}] en el orden del catálogo."""
    filas = []
    for nombre, v in valores(tipo).items():
        clave, valor = next(iter(v.items()))
        filas.append({"nombre": nombre, "valor": valor, "unidad": "ML" if clave == "valorML" else "un."})
    return filas


def _validar_valor(v) -> str | None:
    if v in (None, ""):
        return "Falta el valor."
    n = _numero(v)
    if n is None or n <= 0:
        return "El valor tiene que ser un monto mayor que 0."
    return None


def guardar_lista(tipo: str, filas: list[dict]) -> dict:
    """Guarda [{"nombre", "valor"}] (solo los del catálogo). {"ok": True} o
    {"ok": False, "errores": [{"nombre", "mensaje"}]}."""
    base = _catalogo(tipo)
    filas = [f for f in filas or [] if f.get("nombre") in base]
    errores = [{"nombre": f["nombre"], "mensaje": m} for f in filas if (m := _validar_valor(f.get("valor")))]
    if errores:
        return {"ok": False, "errores": errores}
    guardado = ajustes_globales.leer(_ARCHIVO[tipo]).get("valores")
    por_nombre = dict(guardado) if isinstance(guardado, dict) else {}
    for f in filas:
        por_nombre[f["nombre"]] = {next(iter(base[f["nombre"]])): _numero(f["valor"])}
    return _guardar(_ARCHIVO[tipo], {"valores": por_nombre})


def fijar(tipo: str, nombre: str, valor: float) -> None:
    """El valor de UNA estructura o terminación (la que se acaba de agregar,
    ver core.catalogo.agregar_componente), sin tocar las demás."""
    base = _catalogo(tipo)
    guardado = ajustes_globales.leer(_ARCHIVO[tipo]).get("valores")
    por_nombre = dict(guardado) if isinstance(guardado, dict) else {}
    por_nombre[nombre] = {next(iter(base.get(nombre) or {"valorUNIT": 0})): float(valor)}
    _guardar(_ARCHIVO[tipo], {"valores": por_nombre})


# ── Cajas de Backlight ──────────────────────────────────────────────────────

def cajas() -> dict:
    """Los precios de cajas vigentes, con la forma de core.repositorio.PRECIOS_CAJAS
    ("fp" con los watts como int)."""
    from core.repositorio import PRECIOS_CAJAS

    vigentes = copy.deepcopy(PRECIOS_CAJAS)
    guardado = ajustes_globales.leer(_ARCHIVO_CAJAS).get("cajas")
    guardado = guardado if isinstance(guardado, dict) else {}
    for seccion in SECCIONES_CAJA:
        g = guardado.get(seccion) if isinstance(guardado.get(seccion), dict) else {}
        for clave in vigentes[seccion]:
            n = _numero(g.get(str(clave)))
            if n is not None and n > 0:
                vigentes[seccion][clave] = n
    n = _numero(guardado.get("pintura_por_ml"))
    if n is not None and n > 0:
        vigentes["pintura_por_ml"] = n
    return vigentes


def guardar_cajas(datos: dict) -> dict:
    """Guarda {sección: {clave: valor}, "pintura_por_ml": valor} con las
    claves del catálogo. {"ok": True} o {"ok": False, "errores": [{"seccion",
    "clave", "mensaje"}]}."""
    from core.repositorio import PRECIOS_CAJAS

    errores, cajas_nuevas = [], {}
    for seccion in SECCIONES_CAJA:
        enviados = datos.get(seccion) if isinstance(datos.get(seccion), dict) else {}
        cajas_nuevas[seccion] = {}
        for clave in PRECIOS_CAJAS[seccion]:
            v = enviados.get(str(clave))
            if (m := _validar_valor(v)):
                errores.append({"seccion": seccion, "clave": str(clave), "mensaje": m})
            else:
                cajas_nuevas[seccion][str(clave)] = _numero(v)
    if (m := _validar_valor(datos.get("pintura_por_ml"))):
        errores.append({"seccion": "pintura_por_ml", "clave": None, "mensaje": m})
    if errores:
        return {"ok": False, "errores": errores}
    cajas_nuevas["pintura_por_ml"] = _numero(datos["pintura_por_ml"])
    return _guardar(_ARCHIVO_CAJAS, {"cajas": cajas_nuevas})


# ── Comunes ─────────────────────────────────────────────────────────────────

def _guardar(nombre: str, cambios: dict) -> dict:
    try:
        ajustes_globales.guardar(nombre, cambios, VERSION)
    except ajustes_globales.AjusteMasNuevo:
        return {"ok": False, "errores": [{"mensaje":
                "Estos precios los guardó una versión más nueva de la app. Actualiza esta instalación para poder cambiarlos."}]}
    return {"ok": True}


def solo_lectura(tipo: str) -> bool:
    """tipo: "estructuras", "terminaciones" o "cajas"."""
    return ajustes_globales.es_mas_nuevo(_ARCHIVO.get(tipo, _ARCHIVO_CAJAS), VERSION)
