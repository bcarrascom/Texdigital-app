"""
core/precios.py
Cálculo de precios de una cotización (no-backlight y backlight), a partir de
los catálogos con precio: textiles.json (valor por ML/M² impreso, ver más
abajo), estructuras.json (valorML o valorUNIT) y terminaciones.json (valor
por ML impreso).

Modelo (confirmado con el usuario y verificado contra una cotización real —
Excel "Cubre alarma", ver test_precios.py — no hay precio "manual" por
producto):
  - No-backlight: valor = impresión     (ML impresión × valor de la tela)
                        + terminaciones (Σ valor de cada agregada, por ML o
                                          por unidad según el ítem)
                        + estructuras   (ídem, por ML o por unidad)
    Las Estructuras/Terminaciones son ADITIVAS: una lista de nombres por
    producto, no una selección única.
    "Cantidad efectiva" = Cantidad × 2 si Tiro y retiro, si no Cantidad tal
    cual. Tiro y retiro (imprimir las dos caras) implica coser/rematar cada
    cara por separado, así que duplica cuánta terminación/estructura-unitaria
    se aplica — igual que duplica el ML impreso.
    Las terminaciones/estructuras del catálogo legado (recursos/
    estructuras_legado.json, terminaciones_legado.json) son por UNIDAD
    (valorUNIT × Cantidad efectiva) — confirmado con una cotización real:
    "Cubre alarma" con Cantidad 80, Tiro y retiro, terminación "Cubre
    alarmas" — el Excel cobra valor × 160 (Cantidad efectiva), NO valor ×
    ML (ver test_precios_legado.py); y con el usuario para "Basta"/
    "Bolsillos" ($3.500 por producto cada una). El catálogo también admite
    ítems por ML impreso (valorML × ml_facturable en vez de valorUNIT) —
    mismo mecanismo que ya usa el modelo aditivo para estructuras.json (ver
    core.repositorio.cargar_estructuras / cargar_estructuras_legado: cada
    ítem del catálogo trae "valor" (→ valorUNIT) o "valorML", nunca los
    dos) — por si algún ítem futuro lo necesita, aunque hoy ninguno del
    catálogo legado lo usa.
  - Backlight: valor = M² impreso × valor de la tela (Alto × Ancho × Cantidad)
                      + valor de la caja, si el producto lleva caja (ver
                        core.valor_cajas.valor_caja_desde_guardado — perfil,
                        luces, traseras, armado, fuente de poder y pintura,
                        con los precios de recursos/precios_cajas.json).
    Backlight es el único tipo de producto que mide su tela en M² en vez de
    ML. Si datos["caja"] es "Sin caja" (o no viene), el producto no lleva
    caja y el valor es solo la tela impresa.

Piso mínimo de facturación (ML_MINIMO_POR_PRODUCTO / M2_MINIMO_POR_PRODUCTO):
  el mínimo (2 ML no-backlight, 2 M² Backlight) existe porque cortar un
  rollo de tela requiere ~1 m de tensión antes y después del corte — un
  costo que se paga UNA VEZ POR ROLLO, no una vez por cada producto que
  sale de ese mismo rollo. Por eso el piso se aplica POR GRUPO DE TEXTIL/
  TELA (d["textil"] en no-backlight, d["tela"] en backlight — ver
  ml_o_area_facturable_por_producto), no por línea de producto individual:
  si dos productos del mismo textil no llegan a 2 ML cada uno pero suman
  más de 2 ML entre ambos, no se aplica ningún piso — ya están usando tela
  de sobra para cubrir esa tensión. Si el grupo entero queda bajo el
  mínimo, el mínimo se reparte proporcional al ML/M² real de cada producto
  dentro del grupo (no en partes iguales, ver _distribuir_piso) — cada uno
  mantiene su peso relativo. Un textil con un solo producto se comporta
  exactamente igual que antes (el "grupo" es ese único producto).
  Tampoco se aplica el piso a cada unidad y después se multiplica por
  Cantidad (eso sobrestimaría el producto con Cantidad > 1: 2 unidades de
  0.5 ML cada una no son "2 × 2 ML = 4 ML", son "1 ML real, que como está
  bajo el piso, se cobra como 2 ML").
  Este piso SOLO afecta el costo de impresión (y, en el modelo "aditivo",
  las estructuras valorML — ambas se calculan a partir del mismo ML) — el
  ML real (sin piso) se sigue usando tal cual para todo lo que no es plata:
  calcular_ml() en core/presentar_op.py (orden de producción — ahí importa
  cuánta tela se corta de verdad, no cuánto se cobra) y las columnas
  informativas "ML imp."/"M² imp." de la ventana de resumen (ui/cotizacion.py,
  ui/cotizador_backlight.py) NO pasan por este piso.
  costo_producto() por sí sola NO conoce a los demás productos de la
  cotización, así que no puede aplicar el piso grupal por su cuenta — quien
  llama con la lista completa (costo_cotizacion(), descuento_textil(),
  core/presentar_cotizacion.py, ui/cotizacion.py) debe calcular primero
  ml_o_area_facturable_por_producto(productos) y pasarle a costo_producto()
  el valor ya-con-piso-de-grupo-aplicado vía el parámetro
  ml_o_area_facturable. Si se omite (default None, como en todos los tests
  de un producto suelto), costo_producto() aplica el piso a esa única línea
  como si fuera su propio grupo — mismo resultado que antes de este cambio.

Descuento-textil (ver descuento_textil/costo_cotizacion, confirmado con el
  usuario): descuento adicional por volumen de tela impresa, aparte del %
  manual "Descuento" del contacto — se calcula siempre, pero de los dos
  descuentos SOLO se aplica el que dé más ahorro en $ para toda la
  cotización, nunca los dos juntos. Backlight usa un solo tramo (5/10/20%
  sobre 10/20/50 m²) para el total de m² impresos de la cotización entera;
  no-backlight usa un tramo por cada textil individual (agrupando por
  d["textil"]), aplicado solo al costo de impresión de esos productos.
"""

from core.repositorio import (
    TEXTILES_ANCHOS,
    TEXTILES_VALORES,
    ESTRUCTURAS_VALORES,
    TERMINACIONES_VALORES,
    ESTRUCTURAS_LEGADO_VALORES,
    TERMINACIONES_LEGADO_VALORES,
    PRECIOS_CAJAS,
)
from core.valor_cajas import valor_caja_desde_guardado

IVA_PORCENTAJE = 19

# Ver docstring del módulo ("Piso mínimo de facturación") — mínimo de ML/M²
# facturado por línea de producto (ya con Cantidad aplicada), no por unidad.
ML_MINIMO_POR_PRODUCTO = 2.0
M2_MINIMO_POR_PRODUCTO = 2.0


def _con_piso(valor: float, piso: float) -> float:
    """Sube `valor` a `piso` si queda por debajo — pero solo si `valor` ya
    es positivo (0 = todavía no hay medidas completas o el textil no está
    en el catálogo, no es un caso de "monto chico" que corresponda subir)."""
    return piso if 0 < valor < piso else valor


def formatear_clp(valor: float) -> str:
    """$1.234.567 — formato chileno, sin decimales."""
    return "$" + f"{round(valor):,}".replace(",", ".")


def calcular_ml(d: dict, ancho_tela: float | None) -> tuple[float | None, float | None]:
    """
    Calcula Ratio y ML impresos para un producto no-backlight.
        UxA   = ancho_tela / ancho_producto, SIN truncar, si el truncado
                da menos de 1 (para no terminar dividiendo por 0 más abajo —
                ese caso, además, habilita el checkbox "Forzar")
              = TRUNCADO hacia abajo al entero en cualquier otro caso: UxA
                son las unidades que caben físicamente a lo ancho del rollo
                de tela, y una unidad "y tanto" no cabe — 1,5 m de tela con
                recortes de 0,8 m de ancho da 1 unidad por pasada (no 2):
                3.9 -> 3, 4.1 -> 4.
        ratio = cantidad / UxA
        ml = ratio * alto
        si Tiro y retiro: ml *= 2 (se imprimen las dos caras, mismo cálculo
        que Cara única pero el doble de tela)
    Devuelve (None, None) si no hay ancho de tela registrado.

    OJO: a diferencia de UxA, `ml` NO se redondea acá. En el Excel, la celda
    de "ml impresos" se ve con 2 decimales pero conserva el valor completo
    por dentro — las fórmulas de plata (Valor Impresión total, etc.) usan
    ese valor sin redondear. Redondear `ml` antes de multiplicarlo por el
    valor de la tela introducía un error de hasta $0,005 × valor/ML en el
    costo de impresión (caso real: 4.266666.. ML de Stretch a $12.000/ML
    redondeaba a 4.27, dando $51.240 en vez de los $51.200 exactos — un
    error de $40 solo por el redondeo intermedio). Quien necesite mostrar
    "ml impresos" en pantalla debe redondear ahí, para mostrar, no acá.
    """
    if ancho_tela is None:
        return None, None
    cruda = ancho_tela / d["ancho"]
    # +1e-9 antes de truncar: sin esto, un caso que matemáticamente debería
    # dar un entero exacto (ej. 1.2/0.4=3) puede llegar como 2.9999999999999996
    # por el punto flotante, y truncar de más (UxA=2 en vez de 3). El
    # epsilon es muchísimo más chico que cualquier medida real (metros con
    # 2-3 decimales), así que no afecta casos genuinos cerca de un entero.
    uxa = cruda if int(cruda) < 1 else int(cruda + 1e-9)
    ratio = d["cantidad"] / uxa
    ml = ratio * d["alto"]
    if d.get("impresion") == "Tiro y retiro":
        ml *= 2
    return ratio, ml


def cantidad_efectiva(d: dict) -> float:
    """Cantidad × 2 si Tiro y retiro (imprimir ambas caras duplica cuánta
    terminación/estructura-unitaria se aplica), si no la Cantidad tal cual."""
    cantidad = d.get("cantidad", 0) or 0
    return cantidad * 2 if d.get("impresion") == "Tiro y retiro" else cantidad


def parsear_valor_manual(texto: str) -> float | None:
    """
    Detecta si un ítem de la lista de Estructuras/Terminaciones es en
    realidad un monto en pesos escrito directo por el usuario (ajuste
    manual) en vez del nombre de un ítem del catálogo — formatos típicos:
    "10000", "10.000", "$10.000" (también admite "$ 10.000" con espacio y
    "10,000" con coma). Devuelve el monto, o None si no matchea ninguno de
    esos formatos (es un nombre de catálogo normal).

    Este ajuste se suma DIRECTO al total de esa categoría (Estructuras o
    Terminaciones) — no se multiplica por Cantidad efectiva ni se busca en
    ningún catálogo: el número que el usuario escribió YA es el monto final
    para ese producto. Sirve para parchar diferencias puntuales entre el
    precio del Excel viejo y el que da el programa, sin tener que ajustar
    el catálogo entero por un solo caso.
    """
    texto = texto.strip()
    if texto.startswith("$"):
        texto = texto[1:].strip()
    limpio = texto.replace(".", "").replace(",", "")
    if limpio and limpio.isdigit():
        return float(limpio)
    return None


def costo_producto(
    d: dict,
    *,
    modelo: str = "legado",
    textiles_valores: dict[str, float] | None = None,
    textiles_anchos: dict[str, float] | None = None,
    estructuras_valores: dict[str, dict] | None = None,
    terminaciones_valores: dict[str, float] | None = None,
    estructuras_legado_valores: dict[str, float] | None = None,
    terminaciones_legado_valores: dict[str, float] | None = None,
    precios_cajas: dict | None = None,
    ml_o_area_facturable: float | None = None,
) -> dict:
    """
    Devuelve el desglose de costo de un producto (dict interno del
    cotizador, mismo esquema que usa ui/cotizacion.py y
    ui/cotizador_backlight.py). Distingue backlight de no-backlight igual
    que `mapear_producto` (core/repositorio_cotizaciones.py): backlight
    trae la clave "tela".

    Los catálogos son parámetros opcionales (default: los reales de
    Dropbox/SGTD/Conf, vía core.repositorio) para poder testear con
    catálogos fijos, igual que core/calculo_cajas.py.

    `modelo` (solo afecta productos no-backlight — "Neo" vs "Demo", ver
    core.repositorio.*_LEGADO). En AMBOS modelos, d["estructuras"]/
    d["terminaciones"] son las mismas listas de nombres (aditivas) — lo que
    cambia es en qué catálogo se buscan y cómo se valorizan:
      - "legado" (DEFAULT, modelo "Demo" — adoptado como modelo principal):
        los nombres se buscan en estructuras_legado_valores/
        terminaciones_legado_valores (recursos/estructuras_legado.json,
        terminaciones_legado.json — precios derivados de "Lista vieja.pdf").
        Igual que "aditivo": cada ítem puede traer "valorML" (× ML impreso)
        o "valorUNIT" (× Cantidad efectiva) — la mayoría son valorUNIT, pero
        no todos (ver docstring del módulo).
      - "aditivo" (modelo "Neo" — código de la versión anterior, dejado
        andando para una eventual vuelta atrás, ya no es el default): los
        nombres se buscan en estructuras_valores/terminaciones_valores
        (recursos/estructuras.json, terminaciones.json). Estructuras puede
        traer "valorML" (× ML impreso) o "valorUNIT" (× Cantidad efectiva);
        terminaciones siempre es por Cantidad efectiva.

    En cualquiera de los dos modelos, si un "nombre" de la lista en
    realidad es un monto en pesos escrito por el usuario (ver
    parsear_valor_manual — ej. "$10.000"), ese monto se suma DIRECTO al
    total de esa categoría, sin pasar por el catálogo ni multiplicarse por
    Cantidad efectiva — es un ajuste manual puntual para ese producto, no
    un ítem reusable.

    `ml_o_area_facturable`: ver docstring del módulo ("Piso mínimo de
    facturación"). Si se pasa, se usa DIRECTO como el ML/M² ya-con-piso-de-
    grupo-aplicado (se ignora el piso de un solo producto). Si es None
    (default), se calcula el piso como si este producto fuera su propio
    grupo — mismo comportamiento que antes de que existiera el piso grupal.
    En ningún caso afecta "ml_o_area" del resultado, que sigue siendo
    siempre el valor real sin piso.
    """
    textiles_valores       = TEXTILES_VALORES if textiles_valores is None else textiles_valores
    textiles_anchos        = TEXTILES_ANCHOS if textiles_anchos is None else textiles_anchos
    estructuras_valores    = ESTRUCTURAS_VALORES if estructuras_valores is None else estructuras_valores
    terminaciones_valores  = TERMINACIONES_VALORES if terminaciones_valores is None else terminaciones_valores
    estructuras_legado_valores   = ESTRUCTURAS_LEGADO_VALORES if estructuras_legado_valores is None else estructuras_legado_valores
    terminaciones_legado_valores = TERMINACIONES_LEGADO_VALORES if terminaciones_legado_valores is None else terminaciones_legado_valores
    precios_cajas           = PRECIOS_CAJAS if precios_cajas is None else precios_cajas

    cantidad = d.get("cantidad", 0) or 0

    if "tela" in d:
        area = d.get("alto", 0.0) * d.get("ancho", 0.0) * cantidad
        area_facturable = (
            _con_piso(area, M2_MINIMO_POR_PRODUCTO)
            if ml_o_area_facturable is None else ml_o_area_facturable
        )
        valor_tela = textiles_valores.get(d.get("tela", ""), 0.0)
        costo_impresion = area_facturable * valor_tela

        detalle_caja = None
        costo_caja = 0.0
        if isinstance(d.get("caja"), dict):
            detalle_caja = valor_caja_desde_guardado(
                d["caja"], precios_cajas, cantidad=cantidad,
                ancho=d.get("ancho"), alto=d.get("alto"),
            )
            costo_caja = detalle_caja["valor_total"]

        resultado = {
            "ml_o_area":          area,
            "costo_impresion":    costo_impresion,
            "costo_terminaciones": 0.0,
            "costo_estructuras":   0.0,
            "costo_caja":         costo_caja,
            "detalle_estructuras":  {},
            "detalle_terminaciones": {},
            "detalle_caja":       detalle_caja,
            "total":               costo_impresion + costo_caja,
        }
    else:
        ancho_tela = textiles_anchos.get(d.get("textil", ""))
        _, ml = calcular_ml(d, ancho_tela)
        ml = ml or 0.0
        ml_facturable = (
            _con_piso(ml, ML_MINIMO_POR_PRODUCTO)
            if ml_o_area_facturable is None else ml_o_area_facturable
        )

        valor_tela = textiles_valores.get(d.get("textil", ""), 0.0)
        costo_impresion = ml_facturable * valor_tela

        cant_efectiva = cantidad_efectiva(d)

        terminaciones = d.get("terminaciones") or []
        estructuras = d.get("estructuras") or []

        if modelo == "legado":
            def _valorizar_legado(nombre, catalogo):
                valor_manual = parsear_valor_manual(nombre)
                if valor_manual is not None:
                    return valor_manual
                valores = catalogo.get(nombre)
                if not valores:
                    return 0.0
                if "valorML" in valores:
                    return ml_facturable * valores["valorML"]
                if "valorUNIT" in valores:
                    return cant_efectiva * valores["valorUNIT"]
                return 0.0

            detalle_terminaciones = {
                t: _valorizar_legado(t, terminaciones_legado_valores) for t in terminaciones
            }
            costo_terminaciones = sum(detalle_terminaciones.values())

            detalle_estructuras = {
                e: _valorizar_legado(e, estructuras_legado_valores) for e in estructuras
            }
            costo_estructuras = sum(detalle_estructuras.values())
        else:
            detalle_terminaciones = {}
            for t in terminaciones:
                valor_manual = parsear_valor_manual(t)
                detalle_terminaciones[t] = (
                    valor_manual if valor_manual is not None
                    else terminaciones_valores.get(t, 0.0) * cant_efectiva
                )
            costo_terminaciones = sum(detalle_terminaciones.values())

            detalle_estructuras = {}
            for nombre in estructuras:
                valor_manual = parsear_valor_manual(nombre)
                if valor_manual is not None:
                    detalle_estructuras[nombre] = valor_manual
                    continue
                valores = estructuras_valores.get(nombre)
                if not valores:
                    detalle_estructuras[nombre] = 0.0
                elif "valorML" in valores:
                    detalle_estructuras[nombre] = ml_facturable * valores["valorML"]
                elif "valorUNIT" in valores:
                    detalle_estructuras[nombre] = cant_efectiva * valores["valorUNIT"]
                else:
                    detalle_estructuras[nombre] = 0.0
            costo_estructuras = sum(detalle_estructuras.values())

        total = costo_impresion + costo_terminaciones + costo_estructuras
        resultado = {
            "ml_o_area":            ml,
            "costo_impresion":      costo_impresion,
            "costo_terminaciones":  costo_terminaciones,
            "costo_estructuras":    costo_estructuras,
            "detalle_estructuras":  detalle_estructuras,
            "detalle_terminaciones": detalle_terminaciones,
            "total":                total,
        }

    resultado["valor_unitario"] = resultado["total"] / cantidad if cantidad else 0.0
    return resultado


# ── Descuento por textil (tramos según volumen de m² impresos) ──────────────
# Confirmado con el usuario: mismos tramos para Backlight y no-backlight,
# solo cambia qué se suma para ubicar el tramo (ver descuento_textil). Lista
# ordenada de mayor a menor piso para que tramo_descuento_textil() pueda
# recorrerla de arriba hacia abajo y quedarse con el primer piso que se
# cumple.
TRAMOS_DESCUENTO_TEXTIL = [
    (50.0, 20.0),
    (20.0, 10.0),
    (10.0, 5.0),
]


def tramo_descuento_textil(m2: float) -> float:
    """% de descuento-textil según m² impresos: 10-20 m² -> 5%, 20-50 m²
    -> 10%, 50 m² en adelante -> 20%. Bajo 10 m², 0% (no aplica)."""
    for piso, pct in TRAMOS_DESCUENTO_TEXTIL:
        if m2 >= piso:
            return pct
    return 0.0


def _area_producto(d: dict) -> float:
    """m² impresos de una línea para efectos del descuento-textil: Alto ×
    Ancho × Cantidad efectiva — mismo cálculo que ya usa Backlight para su
    total (ahí ES el total, no hay estructuras/terminaciones que sumar
    aparte), reutilizado acá también para no-backlight como métrica de
    volumen (no de costo de impresión, que sigue siendo ML × valor tela —
    ver calcular_ml)."""
    return d.get("alto", 0.0) * d.get("ancho", 0.0) * cantidad_efectiva(d)


def _clave_grupo_descuento_textil(d: dict) -> tuple[str, str | None]:
    """Clave de agrupamiento para el descuento-textil (ver descuento_textil)
    — DISTINTA de _clave_grupo_textil (esa es para el piso mínimo): acá
    TODO el backlight de la cotización es un solo grupo global
    ("backlight", None), sin importar la tela de cada producto — regla de
    negocio propia del descuento (confirmado con el usuario: "Backlight...
    un solo tramo para toda la cotización"). No-backlight sigue siendo por
    textil individual, igual que antes."""
    if "tela" in d:
        return ("backlight", None)
    return ("no_backlight", d.get("textil", ""))


def _clave_grupo_textil(d: dict) -> tuple[str, str]:
    """Clave de agrupamiento para el piso mínimo de facturación (ver
    ml_o_area_facturable_por_producto): separa backlight de no-backlight
    (para no mezclar ML con M² en la misma suma) y agrupa por el nombre del
    textil/tela dentro de cada tipo. Es un agrupamiento DISTINTO del que usa
    descuento_textil() para el descuento por volumen (ese agrupa TODO el
    backlight en un solo grupo global — regla de negocio aparte) — acá
    backlight también se agrupa por tela individual, igual que no-backlight
    por textil."""
    if "tela" in d:
        return ("backlight", d.get("tela", ""))
    return ("no_backlight", d.get("textil", ""))


def _distribuir_piso(valores_reales: list[float], piso: float) -> list[float]:
    """Dado el ML/M² real (sin piso) de cada producto de un mismo grupo de
    textil, devuelve el ML/M² facturable de cada uno (ver docstring del
    módulo, "Piso mínimo de facturación"): si la suma del grupo ya supera
    el piso, cada uno factura su valor real tal cual (ya se está usando
    tela de sobra para cubrir la tensión de corte); si no, el piso se
    reparte proporcional al peso real de cada producto — no en partes
    iguales, para no regalarle más ML al producto chico que al grande."""
    total_real = sum(valores_reales)
    if total_real <= 0:
        return [0.0 for _ in valores_reales]
    if total_real >= piso:
        return list(valores_reales)
    return [v / total_real * piso for v in valores_reales]


def ml_o_area_facturable_por_producto(productos: list[dict], **kwargs) -> list[float]:
    """ML/M² facturable de cada producto de la cotización, con el piso
    mínimo (ML_MINIMO_POR_PRODUCTO / M2_MINIMO_POR_PRODUCTO) aplicado POR
    GRUPO DE TEXTIL/TELA (ver _clave_grupo_textil y _distribuir_piso), no
    por línea individual. Devuelve una lista alineada 1:1 con `productos`
    (mismo orden). Pasarle el resultado a costo_producto(...,
    ml_o_area_facturable=...) elemento a elemento.

    kwargs se pasan tal cual a costo_producto (catálogos fijos para tests,
    ver ahí) — solo se usa para leer "ml_o_area" (siempre el valor real,
    sin piso, de cada producto individual)."""
    reales = [costo_producto(p, **kwargs)["ml_o_area"] for p in productos]

    grupos: dict[tuple[str, str], list[int]] = {}
    for i, p in enumerate(productos):
        grupos.setdefault(_clave_grupo_textil(p), []).append(i)

    facturables = [0.0] * len(productos)
    for (tipo, _textil), indices in grupos.items():
        piso = M2_MINIMO_POR_PRODUCTO if tipo == "backlight" else ML_MINIMO_POR_PRODUCTO
        valores_grupo = [reales[i] for i in indices]
        for i, valor in zip(indices, _distribuir_piso(valores_grupo, piso)):
            facturables[i] = valor
    return facturables


def descuento_textil(productos: list[dict], **kwargs) -> dict:
    """
    Descuento adicional por volumen de tela impresa — independiente del %
    manual "Descuento" del contacto (ver costo_cotizacion, que se queda
    solo con el que dé más ahorro entre los dos, nunca ambos a la vez).

    - Backlight: TODOS los productos backlight de la cotización son un solo
      grupo global (sin importar la tela de cada uno), con un solo tramo
      según la suma de sus m² impresos. El % se aplica SOLO al costo de
      impresión (igual que no-backlight) — NO a la caja (perfil/luces/
      armado/etc., ver core.valor_cajas): es un descuento por volumen de
      TELA impresa, la caja no es tela.
    - No-backlight: un tramo POR TEXTIL — se agrupan los productos por
      d["textil"], se suma el m² de cada grupo por separado (puede caer en
      tramos distintos entre sí dentro de la misma cotización), y el % de
      cada grupo se aplica SOLO al costo de impresión de esos productos, no
      a sus estructuras/terminaciones (que no dependen del textil).
    - Ambos grupos conviven en la misma cotización sin pisarse (ver
      _clave_grupo_descuento_textil) — una cotización MIXTA (backlight +
      no-backlight a la vez) calcula el grupo backlight global y cada grupo
      de textil no-backlight de forma completamente independiente.

    Devuelve {"monto": $ total descontado, "neto": $ neto de los productos
    (sin despacho/instalación — no son tela), "pct_visual": monto/neto×100}.
    `pct_visual` es un % derivado del $ ahorrado, pensado solo para mostrar
    en pantalla/impreso (ver docstring de costo_cotizacion) — el monto real
    ya viene armado tramo por tramo/textil, no se recalcula a partir de
    este %. kwargs se pasan tal cual a costo_producto (catálogos fijos para
    tests, ver ahí)."""
    if not productos:
        return {"monto": 0.0, "neto": 0.0, "pct_visual": 0.0}

    # Piso mínimo de facturación por grupo de textil/tela (ver docstring del
    # módulo) — el costo_impresion/total de cada línea debe reflejar el
    # piso YA repartido por grupo, no el piso de un solo producto.
    facturables = ml_o_area_facturable_por_producto(productos, **kwargs)

    def _costo(p, f):
        return costo_producto(p, ml_o_area_facturable=f, **kwargs)

    neto = sum(_costo(p, f)["total"] for p, f in zip(productos, facturables))

    grupos: dict[tuple[str, str | None], list[tuple[dict, float]]] = {}
    for p, f in zip(productos, facturables):
        grupos.setdefault(_clave_grupo_descuento_textil(p), []).append((p, f))

    monto = 0.0
    for grupo in grupos.values():
        pct_grupo = tramo_descuento_textil(sum(_area_producto(p) for p, _ in grupo))
        if not pct_grupo:
            continue
        costo_impresion_grupo = sum(_costo(p, f)["costo_impresion"] for p, f in grupo)
        monto += costo_impresion_grupo * pct_grupo / 100

    pct_visual = (monto / neto * 100) if neto else 0.0
    return {"monto": monto, "neto": neto, "pct_visual": pct_visual}


def costo_cotizacion(productos: list[dict], descuento_pct: float = 0.0,
                      despacho: float = 0.0, instalacion: float = 0.0,
                      **kwargs) -> dict:
    """
    Suma el costo de todos los productos y aplica descuento + IVA.
    `despacho` e `instalacion` (opcionales) son montos fijos que se suman
    directo al neto — no son productos (no tienen medidas, no se guardan
    en la lista `productos`), son cargos aparte que hoy se cobran a mano
    porque todavía no se generan guías de despacho ni se detalla la
    instalación. Quedan sujetos al mismo descuento % e IVA que el resto —
    son un ítem más de la cotización cada uno.

    Descuento-textil (ver descuento_textil): se calcula siempre, pero SOLO
    se aplica uno de los dos descuentos, el que dé más ahorro en $ — nunca
    los dos juntos. El despacho/instalación no entran en la comparación del
    descuento-textil (no son tela), pero si gana el % normal, sí quedan
    descontados igual que antes (comportamiento sin cambios).

    Devuelve {neto, descuento, descuento_textil_pct, fuente_descuento,
    neto_total, iva, total}. `descuento_textil_pct` es el % (derivado,
    "visual") del descuento-textil calculado para esta cotización, se
    devuelve siempre (haya ganado o no) para poder mostrarlo en pantalla.
    `fuente_descuento` es "normal" o "textil", según cuál se aplicó.
    kwargs se pasan tal cual a costo_producto (catálogos fijos para tests,
    ver ahí)."""
    # Piso mínimo de facturación por grupo de textil/tela (ver docstring
    # del módulo y ml_o_area_facturable_por_producto).
    facturables = ml_o_area_facturable_por_producto(productos, **kwargs)
    neto_productos = sum(
        costo_producto(p, ml_o_area_facturable=f, **kwargs)["total"]
        for p, f in zip(productos, facturables)
    )
    neto = neto_productos + (despacho or 0.0) + (instalacion or 0.0)

    monto_normal = neto * descuento_pct / 100
    dtextil = descuento_textil(productos, **kwargs)

    if dtextil["monto"] > monto_normal:
        descuento = dtextil["monto"]
        fuente_descuento = "textil"
    else:
        descuento = monto_normal
        fuente_descuento = "normal"

    neto_total = neto - descuento
    iva = neto_total * IVA_PORCENTAJE / 100
    total = neto_total + iva
    return {
        "neto":                 neto,
        "descuento":            descuento,
        "descuento_textil_pct": dtextil["pct_visual"],
        "fuente_descuento":     fuente_descuento,
        "neto_total":           neto_total,
        "iva":                  iva,
        "total":                total,
    }
