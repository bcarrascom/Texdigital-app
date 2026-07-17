"""
core/calculo_cajas.py
Cálculos de materiales para productos backlight con caja. Implementa
exactamente logica_cajas_backlight.md (§3 a §8, más el plan de tiras
de §5.4). Funciones puras: no leen archivos ni tocan la UI — reciben los
catálogos (luces, fuentes de poder) ya cargados desde core.repositorio.

Nomenclatura de las funciones y variables intermedias sigue la del MD para
poder auditar el código línea a línea contra la especificación.
"""

import math

# ══════════════════════════════════════════════════════════════════════════════
# Helpers de catálogo / clasificación
# ══════════════════════════════════════════════════════════════════════════════

def _buscar_luz(catalogo_luces: list[dict], nombre_corto: str) -> dict | None:
    return next((l for l in catalogo_luces if l.get("corto") == nombre_corto), None)


def _es_malla(nombre_corto: str) -> bool:
    """"Malla 150" y "Malla 12v" son mallas; el resto (M12, Basic 5, ...,
    sin luces) no lo son."""
    return (nombre_corto or "").strip().lower().startswith("malla")


def _es_malla_150(nombre_corto: str) -> bool:
    return (nombre_corto or "").strip().lower() == "malla 150"


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
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# §5.3 — Grilla de mallas
# ══════════════════════════════════════════════════════════════════════════════

def _n_lado_cm(l_cm: float) -> int:
    """n(L) de §5.3: cantidad mínima de luces a lo largo de un lado de L cm
    tal que ninguna quede a más de 5 cm de un borde, con paso de 5 cm."""
    # redondear antes de operar: convertir metros a cm (ancho*100) puede
    # dejar ruido de punto flotante (0.55*100 == 55.00000000000001), que
    # ceil() convertiría en un resultado incorrecto.
    l_cm = round(l_cm, 6)
    if l_cm <= 10:
        return 1
    return math.ceil(round((l_cm - 10) / 5, 6)) + 1


def luces_x_caja_grilla(ancho: float, alto: float) -> int:
    """Cantidad de luces de la grilla de una malla (Ancho y Alto en metros)."""
    return _n_lado_cm(ancho * 100) * _n_lado_cm(alto * 100)


# ══════════════════════════════════════════════════════════════════════════════
# §5.4 — Plan de tiras (plano de instalación de mallas)
# No participa del conteo de la tabla de materiales (eso es §5.3); es solo
# para poder dibujar un plano a escala más adelante.
# ══════════════════════════════════════════════════════════════════════════════

def _posiciones_centradas(l_cm: float, n: int) -> list[float]:
    """Posiciones (cm desde el borde 0) de n luces con paso de 5 cm,
    centradas en l_cm de forma que ningún margen a un borde supere 5 cm."""
    if n <= 1:
        return [l_cm / 2]
    span = 5 * (n - 1)
    offset = (l_cm - span) / 2
    return [offset + 5 * i for i in range(n)]


def _agrupar_en_tiras(n: int) -> list[int]:
    """Reparte n luces consecutivas en tiras de hasta 10 luces; la última
    del grupo puede quedar recortada (< 10)."""
    grupos = []
    restante = n
    while restante > 0:
        grupos.append(min(10, restante))
        restante -= 10
    return grupos


def _tiras_horizontales(n_ancho: int, n_alto: int, pos_x: list[float], pos_y: list[float]) -> list[dict]:
    tiras = []
    for fila in range(n_alto):
        y = pos_y[fila]
        idx = 0
        for k in _agrupar_en_tiras(n_ancho):
            xs = pos_x[idx:idx + k]
            tiras.append({"orientacion": "h", "y": y, "x0": xs[0], "x1": xs[-1],
                          "n_luces": k, "recortada": k < 10})
            idx += k
    return tiras


def _tiras_verticales(n_ancho: int, n_alto: int, pos_x: list[float], pos_y: list[float]) -> list[dict]:
    tiras = []
    for col in range(n_ancho):
        x = pos_x[col]
        idx = 0
        for k in _agrupar_en_tiras(n_alto):
            ys = pos_y[idx:idx + k]
            tiras.append({"orientacion": "v", "x": x, "y0": ys[0], "y1": ys[-1],
                          "n_luces": k, "recortada": k < 10})
            idx += k
    return tiras


def _plan_hibrida_h(n_ancho, n_alto, pos_x, pos_y) -> list[dict]:
    bloque = 10 * (n_ancho // 10)
    tiras = []
    if bloque > 0:
        tiras += _tiras_horizontales(bloque, n_alto, pos_x[:bloque], pos_y)
    resto = n_ancho - bloque
    if resto > 0:
        tiras += _tiras_verticales(resto, n_alto, pos_x[bloque:], pos_y)
    return tiras


def _plan_hibrida_v(n_ancho, n_alto, pos_x, pos_y) -> list[dict]:
    bloque = 10 * (n_alto // 10)
    tiras = []
    if bloque > 0:
        tiras += _tiras_verticales(n_ancho, bloque, pos_x, pos_y[:bloque])
    resto = n_alto - bloque
    if resto > 0:
        tiras += _tiras_horizontales(n_ancho, resto, pos_x, pos_y[bloque:])
    return tiras


def plan_tiras(ancho: float, alto: float) -> dict:
    """
    Evalúa las 4 estrategias de §5.4 (pura horizontal, pura vertical,
    híbrida H, híbrida V) y elige la de menos tiras colocadas, desempatando
    por menos tiras recortadas. Devuelve la estrategia elegida con las
    coordenadas (en cm, relativas a la esquina inferior-izquierda de la
    caja) de cada tira y cada luz.
    """
    ancho_cm, alto_cm = ancho * 100, alto * 100
    n_ancho, n_alto = _n_lado_cm(ancho_cm), _n_lado_cm(alto_cm)
    pos_x = _posiciones_centradas(ancho_cm, n_ancho)
    pos_y = _posiciones_centradas(alto_cm, n_alto)

    estrategias = {
        "pura_horizontal": _tiras_horizontales(n_ancho, n_alto, pos_x, pos_y),
        "pura_vertical":   _tiras_verticales(n_ancho, n_alto, pos_x, pos_y),
        "hibrida_h":       _plan_hibrida_h(n_ancho, n_alto, pos_x, pos_y),
        "hibrida_v":       _plan_hibrida_v(n_ancho, n_alto, pos_x, pos_y),
    }

    def _costo(tiras):
        return (len(tiras), sum(1 for t in tiras if t["recortada"]))

    mejor_nombre = min(estrategias, key=lambda k: _costo(estrategias[k]))
    tiras = estrategias[mejor_nombre]

    luces = [{"x": x, "y": y} for x in pos_x for y in pos_y]

    return {
        "estrategia": mejor_nombre,
        "n_tiras": len(tiras),
        "n_recortadas": sum(1 for t in tiras if t["recortada"]),
        "tiras": tiras,
        "luces": luces,
        "n_ancho": n_ancho, "n_alto": n_alto,
        "ancho_cm": ancho_cm, "alto_cm": alto_cm,
    }


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

def calcular_caja(ancho: float, alto: float, cantidad: int, perfil: str,
                   luces1: str, luces2: str,
                   catalogo_luces: list[dict], catalogo_fp: list[dict],
                   cantidad_malla12v_1: float | None = None,
                   cantidad_malla12v_2: float | None = None) -> dict:
    """
    Calcula la tabla de materiales (§8) de una caja de backlight.
    `cantidad` es el n° de cajas del producto (Cantidad ingresada por el
    usuario). `cantidad_malla12v_N` es la cantidad x caja ingresada a mano
    cuando Luces N == "Malla 12v" (§5.3, pendiente de especificaciones de
    tira); se ignora para cualquier otra luz.

    Devuelve {"filas": [...], "watts": float, "fp": dict|None, ...intermedios}.
    Cada fila: {"material", "tipo", "cantidad_x_caja", "cantidad_total",
    "pendiente_manual"} (pendiente_manual solo aplica a filas de Luces con
    Malla 12v sin cantidad ingresada).
    """
    lc = lado_corto(ancho, alto)
    ll = lado_largo(ancho, alto)
    mts_lineales = mts_lineales_x_caja(ancho, alto)
    lac = lados_a_cubrir(perfil, luces1, ancho, alto)

    # "Led 1 x lado" (§5.2): solo aplica si Luces 1 es un led lateral. Una
    # malla no ocupa el borde (cubre el fondo, §5.3), así que no le resta
    # espacio a Luces 2 en el borde.
    if _es_malla(luces1) or _es_sin_luces(luces1):
        led1_x_lado, ancho_led1 = 0, 0.0
    else:
        luz1 = _buscar_luz(catalogo_luces, luces1)
        ancho_led1 = luz1["medida"] if luz1 else 0.0
        led1_x_lado = 0 if ancho_led1 == 0 else math.floor(round((ll - 0.03) / ancho_led1, 6))

    def _cantidad_luz(nombre, cantidad_manual, es_luces1):
        """Cantidad x caja de una fila de luz, y si quedó pendiente de
        ingreso manual (Malla 12v sin cantidad todavía)."""
        if _es_sin_luces(nombre):
            return 0.0, False
        if _es_malla(nombre):
            if _es_malla_150(nombre):
                return luces_x_caja_grilla(ancho, alto) / 10, False
            # Malla 12v: pendiente de especificaciones de tira (§5.3 / MD §1.1)
            if cantidad_manual is None:
                return 0.0, True
            return float(cantidad_manual), False
        if es_luces1:
            return float(lac * led1_x_lado), False
        luz = _buscar_luz(catalogo_luces, nombre)
        ancho_led2 = luz["medida"] if luz else 0.0
        ml_x_cubrir = ll - (led1_x_lado * ancho_led1)
        led2_x_lado = 0 if ancho_led2 == 0 else math.floor(round(ml_x_cubrir / ancho_led2, 6))
        return float(lac * led2_x_lado), False

    cant1_x_caja, luces1_pendiente = _cantidad_luz(luces1, cantidad_malla12v_1, True)
    cant2_x_caja, luces2_pendiente = _cantidad_luz(luces2, cantidad_malla12v_2, False)

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
         "pendiente_manual": luces1_pendiente},
        {"material": "Luces 2", "tipo": luces2,
         "cantidad_x_caja": cant2_x_caja, "cantidad_total": cant2_x_caja * cantidad,
         "pendiente_manual": luces2_pendiente},
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
    }
