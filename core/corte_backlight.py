"""
core/corte_backlight.py
Los márgenes de costura que se le suman a las medidas de un backlight para
cortar la tela — un ajuste GLOBAL (ver core.ajustes_globales), editable en
Configuración › Backlight. Pedido de Bruno (2026-10-25); hasta entonces eran
fijos en core/presentar_op.py (1,5 y 2,5 cm desde 2026-10-01).

  caja_terminada  si lo que se midió es la caja terminada (o la caja es nuestra)
  area_visual     si lo que se midió es el área visual: hay que envolver más perfil

En Conf/corte_backlight.json, en metros: {"version": 1, "caja_terminada": 0.015,
"area_visual": 0.025}. Lo que falte vale lo de siempre.

No cambian precios (el corte no entra en el cálculo de la cotización), así que
no se congela por cotización: la OP y el panel de producción muestran siempre
los márgenes de hoy, que son con los que se va a cortar.
"""

from core import ajustes_globales

NOMBRE = "corte_backlight"
VERSION = 1

POR_DEFECTO = {"caja_terminada": 0.015, "area_visual": 0.025}

# Un margen de más de 20 cm es casi seguro un error de tipeo (metros por cm).
MAXIMO = 0.20


def _numero(v) -> float | None:
    if v is None or isinstance(v, bool) or v == "":
        return None
    try:
        n = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return n if n == n and abs(n) != float("inf") else None


def cargar() -> dict:
    """{"caja_terminada": m, "area_visual": m}, con su valor por defecto si
    falta o no se puede leer."""
    guardado = ajustes_globales.leer(NOMBRE)
    margenes = {}
    for clave, defecto in POR_DEFECTO.items():
        n = _numero(guardado.get(clave))
        margenes[clave] = defecto if n is None or not 0 <= n <= MAXIMO else n
    return margenes


def margen(terminaciones_caja: str, margenes: dict | None = None) -> float:
    """El margen que corresponde: el de caja terminada si es "CAJA TERMINADA";
    cualquier otro valor, el de área visual (el más grande: ante la duda, sobra
    tela en vez de faltar)."""
    margenes = margenes or cargar()
    return margenes["caja_terminada"] if terminaciones_caja == "CAJA TERMINADA" else margenes["area_visual"]


def guardar(datos: dict) -> dict:
    """datos en metros. {"ok": True} o {"ok": False, "errores": {campo: mensaje}}."""
    errores, margenes = {}, {}
    for clave in POR_DEFECTO:
        n = _numero(datos.get(clave))
        if n is None or not 0 <= n <= MAXIMO:
            errores[clave] = f"Tiene que ser un margen entre 0 y {MAXIMO * 100:g} cm."
        else:
            margenes[clave] = round(n, 4)
    if errores:
        return {"ok": False, "errores": errores}
    try:
        ajustes_globales.guardar(NOMBRE, margenes, VERSION)
    except ajustes_globales.AjusteMasNuevo:
        return {"ok": False, "errores": {"general":
                "Estos márgenes los guardó una versión más nueva de la app. Actualiza esta instalación para poder cambiarlos."}}
    return {"ok": True}


def solo_lectura() -> bool:
    return ajustes_globales.es_mas_nuevo(NOMBRE, VERSION)
