"""
core/calculo_cajas.py
Cálculos de materiales para productos backlight con caja. Funciones puras:
no leen archivos ni tocan la UI — reciben los catálogos (luces, fuentes de
poder) ya cargados desde core.repositorio.

Malla 150 y Malla 12v (§5.3/§5.4 de logica_cajas_backlight.md, versión
anterior): la especificación original las trataba distinto a las luces
laterales — como una grilla de LEDs individuales repartida por todo el
fondo de la caja (luces_x_caja_grilla/plan_tiras, ya eliminados de este
archivo). Esa interpretación se probó CONTRA el Excel original con dos
ejemplos reales del usuario y no daba resultados compatibles ni ajustando
el precio proporcionalmente (ver conversación — con una caja de 1.5x0.45m,
"Malla 12v" da literalmente 1 sola unidad usada, algo que una grilla que
cubre toda el área nunca podría dar por chica que fuera la caja).

Lo que sí reproduce el Excel exacto (confirmado a la peseta con esos mismos
dos ejemplos): Malla 150 y Malla 12v se cuentan EXACTAMENTE igual que
cualquier luz lateral (M12, M6, M9, M3, Basic...) — usando su propio ancho
físico ("medida" en luces.json: 0.3 m y 1.0 m respectivamente) en la misma
fórmula de "cuántas unidades entran a lo largo del lado más largo"
(led_x_lado). La única diferencia real de las mallas es que la cantidad
usada NO se multiplica por lados_a_cubrir — a diferencia de un led lateral,
que se repite simétricamente en los lados que corresponda, una malla no
"se aplica por lado": la cantidad final es directamente led_x_lado.
"""

import math

# ══════════════════════════════════════════════════════════════════════════════
# Helpers de catálogo / clasificación
# ══════════════════════════════════════════════════════════════════════════════

def _buscar_luz(catalogo_luces: list[dict], nombre_corto: str) -> dict | None:
    return next((l for l in catalogo_luces if l.get("corto") == nombre_corto), None)


def _es_malla(nombre_corto: str) -> bool:
    """"Malla 150" y "Malla 12v" son mallas; el resto (M12, Basic 5, ...,
    sin luces) no lo son. Se cuentan igual que cualquier luz lateral (ver
    docstring del módulo) — esto solo importa para decidir si la cantidad
    final se multiplica por lados_a_cubrir o no."""
    return (nombre_corto or "").strip().lower().startswith("malla")


def _es_sin_luces(nombre_corto: str) -> bool:
    return (nombre_corto or "").strip().lower() == "sin luces"


def _es_perfil_doble(nombre_perfil: str) -> bool:
    return "doble" in (nombre_perfil or "").lower()


def es_perfil_60(nombre_perfil: str) -> bool:
    return (nombre_perfil or "").strip().upper() == "PERFIL 60 MM"


def _watts_de(nombre_corto: str, catalogo_luces: list[dict]) -> float:
    if _es_sin_luces(nombre_corto):
        return 0.0
    luz = _buscar_luz(catalogo_luces, nombre_corto)
    return float(luz["watts"]) if luz else 0.0


# ══════════════════════════════════════════════════════════════════════════════
# §3 — Variables geométricas base
# ══════════════════════════════════════════════════════════════════════════════

def lado_corto(ancho: float, alto: float) -> float:
    return min(ancho, alto)


def lado_largo(ancho: float, alto: float) -> float:
    return max(ancho, alto)


def mts_lineales_x_caja(ancho: float, alto: float) -> float:
    return (ancho * 2) + (alto * 2)


# ══════════════════════════════════════════════════════════════════════════════
# §4 — Selección de luces por defecto
# ══════════════════════════════════════════════════════════════════════════════

def luces1_default(perfil: str, ancho: float, alto: float) -> str:
    """Nombre corto (de luces.json) que corresponde por defecto a Luces 1.
    Umbral de 1.5 m de lado corto inclusive → malla."""
    if es_perfil_60(perfil) or lado_corto(ancho, alto) >= 1.5:
        return "Malla 150"
    return "M12"


# ══════════════════════════════════════════════════════════════════════════════
# §5.1 — Lados a cubrir
# ══════════════════════════════════════════════════════════════════════════════

def lados_a_cubrir(perfil: str, luces1_nombre: str, ancho: float, alto: float) -> int:
    if es_perfil_60(perfil):
        return 1
    if _es_sin_luces(luces1_nombre):
        return 0
    if _es_malla(luces1_nombre):
        return 1
    lc = lado_corto(ancho, alto)
    if lc < 0.8:
        return 1
    if lc < 1.5:
        return 2
    # lc >= 1.5: por defecto correspondería malla (ver luces1_default), pero
    # si el usuario igual eligió un led lateral (M12, etc.) acá, la caja
    # sigue necesitando cubrir 1 lado — no 0. Confirmado contra una
    # cotización real (Excel original): caja de 2.68×2.785 con M12 dio
    # lados_a_cubrir=1 (4 luces x lado), nunca 0.
    return 1


# ══════════════════════════════════════════════════════════════════════════════
# §6 — Watts y Fuente de poder
# ══════════════════════════════════════════════════════════════════════════════

def seleccionar_fp(watts: float, catalogo_fp: list[dict]) -> dict | None:
    """Devuelve {"nombre", "watts_unidad", "cantidad"} o None si Watts == 0
    (sin fuente de poder). catalogo_fp: lista de {watts, nombre}."""
    def _buscar(w):
        return next((f for f in catalogo_fp if f.get("watts") == w), None)

    if watts <= 0:
        return None
    if watts < 35:
        f = _buscar(35)
    elif watts < 50:
        f = _buscar(50)
    elif watts < 75:
        f = _buscar(75)
    elif watts < 100:
        f = _buscar(100)
    elif watts < 150:
        f = _buscar(150)
    elif watts < 200:
        f = _buscar(200)
    elif watts < 350:
        f = _buscar(350)
    elif watts <= 450:
        f = _buscar(450)
    else:
        f = _buscar(350)
        return {"nombre": f["nombre"] if f else "FP 350",
                "watts_unidad": 350, "cantidad": math.ceil(round(watts / 350, 6))}
    return {"nombre": f["nombre"] if f else None,
            "watts_unidad": f["watts"] if f else None, "cantidad": 1}


# ══════════════════════════════════════════════════════════════════════════════
# §7 — Traseras
# ══════════════════════════════════════════════════════════════════════════════

def traseras_tipo(perfil: str, luces1_nombre: str) -> str:
    """Trasera a usar detrás de la caja. Las mallas (Malla 150 o Malla 12v)
    NUNCA llevan traseras — la luz misma cubre el fondo — así que van con
    el perfil doble en "Sin traseras" (corrige la versión original del MD,
    que proponía Alucobond 122x244 para mallas: en la práctica no se usa)."""
    if _es_perfil_doble(perfil) or _es_malla(luces1_nombre):
        return "Sin traseras"
    return "Trovicel 122"


# ══════════════════════════════════════════════════════════════════════════════
# §8 — Tabla de materiales completa
# ══════════════════════════════════════════════════════════════════════════════

def _ancho_y_conteo(nombre: str, disponible: float, catalogo_luces: list[dict]) -> tuple[float, int]:
    """Ancho físico ("medida") de una luz y cuántas unidades enteras entran
    en `disponible` metros — misma fórmula para CUALQUIER luz, mallas
    incluidas (ver docstring del módulo): Malla 150/Malla 12v no son un
    caso especial, solo tienen su propio ancho (0.3 m / 1.0 m)."""
    if _es_sin_luces(nombre):
        return 0.0, 0
    luz = _buscar_luz(catalogo_luces, nombre)
    ancho_luz = luz["medida"] if luz else 0.0
    conteo = 0 if ancho_luz == 0 else math.floor(round(disponible / ancho_luz, 6))
    return ancho_luz, conteo


def calcular_caja(ancho: float, alto: float, cantidad: int, perfil: str,
                   luces1: str, luces2: str,
                   catalogo_luces: list[dict], catalogo_fp: list[dict]) -> dict:
    """
    Calcula la tabla de materiales (§8) de una caja de backlight.
    `cantidad` es el n° de cajas del producto (Cantidad ingresada por el
    usuario).

    Devuelve {"filas": [...], "watts": float, "fp": dict|None, "ml_x_cubrir":
    float, ...intermedios}. Cada fila: {"material", "tipo",
    "cantidad_x_caja", "cantidad_total", "pendiente_manual"}
    ("pendiente_manual" queda siempre False — ya no hay ninguna luz que
    requiera un ingreso manual, ver docstring del módulo).

    "ml_x_cubrir" = lado_largo − (ancho_led1 × led1_x_lado): metros
    lineales que le quedan al lado más largo después de acomodar Luces 1,
    disponibles para Luces 2 (§7 del Excel original, "Metros lineales por
    cubrir" — se muestra en pantalla igual que el resto de la tabla).
    """
    lc = lado_corto(ancho, alto)
    ll = lado_largo(ancho, alto)
    mts_lineales = mts_lineales_x_caja(ancho, alto)
    lac = lados_a_cubrir(perfil, luces1, ancho, alto)

    # "Led 1 x lado": cuántas unidades de Luces 1 (con su ancho físico
    # propio, sea led lateral o malla) entran a lo largo del lado más largo
    # (con 0.03 m de margen de borde).
    ancho_led1, led1_x_lado = _ancho_y_conteo(luces1, ll - 0.03, catalogo_luces)
    ml_x_cubrir = ll - (ancho_led1 * led1_x_lado)
    ancho_led2, led2_x_lado = _ancho_y_conteo(luces2, ml_x_cubrir, catalogo_luces)

    def _cantidad_luz(nombre, led_x_lado):
        """Cantidad x caja de una fila de luz. Las mallas NO se aplican
        "por lado" (a diferencia de un led lateral, que se repite
        simétricamente en los lados que corresponda) — su cantidad final es
        directamente led_x_lado, sin multiplicar por lados_a_cubrir."""
        if _es_sin_luces(nombre):
            return 0.0
        if _es_malla(nombre):
            return float(led_x_lado)
        return float(lac * led_x_lado)

    cant1_x_caja = _cantidad_luz(luces1, led1_x_lado)
    cant2_x_caja = _cantidad_luz(luces2, led2_x_lado)

    watts = (_watts_de(luces1, catalogo_luces) * cant1_x_caja
             + _watts_de(luces2, catalogo_luces) * cant2_x_caja)
    fp = seleccionar_fp(watts, catalogo_fp)

    traseras_nombre = traseras_tipo(perfil, luces1)
    perfil_x_caja = mts_lineales / 6
    # Las traseras se cortan de planchas enteras — no existe "0.36
    # planchas" — así que se redondea hacia arriba POR CAJA y de ahí se
    # saca el total (no al revés: redondear el total ya sumado daría un
    # número distinto y menor al real, ej. 2 cajas x 0.4 -> 1+1=2, no
    # TECHO(0.8)=1). Esto queda en el cálculo mismo (no es solo de
    # pantalla) porque el archivo guardado debe reflejar cuánto material
    # hace falta pedir de verdad.
    if traseras_nombre == "Sin traseras":
        traseras_x_caja = 0
    else:
        traseras_x_caja = math.ceil(round((ancho * alto) / (1.22 * 2.44), 6))

    filas = [
        {"material": "Perfil", "tipo": perfil,
         "cantidad_x_caja": perfil_x_caja, "cantidad_total": perfil_x_caja * cantidad,
         "pendiente_manual": False},
        {"material": "Traseras", "tipo": traseras_nombre,
         "cantidad_x_caja": traseras_x_caja, "cantidad_total": traseras_x_caja * cantidad,
         "pendiente_manual": False},
        {"material": "Luces 1", "tipo": luces1,
         "cantidad_x_caja": cant1_x_caja, "cantidad_total": cant1_x_caja * cantidad,
         "pendiente_manual": False},
        {"material": "Luces 2", "tipo": luces2,
         "cantidad_x_caja": cant2_x_caja, "cantidad_total": cant2_x_caja * cantidad,
         "pendiente_manual": False},
    ]
    if fp is None:
        filas.append({"material": "FP", "tipo": None,
                      "cantidad_x_caja": 0, "cantidad_total": 0, "pendiente_manual": False})
    else:
        filas.append({"material": "FP", "tipo": fp["nombre"],
                      "cantidad_x_caja": fp["cantidad"], "cantidad_total": fp["cantidad"] * cantidad,
                      "pendiente_manual": False})

    return {
        "filas": filas,
        "watts": watts,
        "fp": fp,
        "lados_a_cubrir": lac,
        "lado_corto": lc,
        "lado_largo": ll,
        "mts_lineales_x_caja": mts_lineales,
        "ml_x_cubrir": ml_x_cubrir,
    }
