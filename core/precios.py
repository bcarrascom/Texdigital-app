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
                        + terminaciones (Σ valor de cada agregada × Cantidad efectiva)
                        + estructuras   (ML impresión × Σ valorML + Cantidad efectiva × Σ valorUNIT)
    Las Estructuras/Terminaciones son ADITIVAS: una lista de nombres por
    producto, no una selección única.
    "Cantidad efectiva" = Cantidad × 2 si Tiro y retiro, si no Cantidad tal
    cual. Tiro y retiro (imprimir las dos caras) implica coser/rematar cada
    cara por separado, así que duplica cuánta terminación/estructura-unitaria
    se aplica — igual que duplica el ML impreso.
    OJO: las terminaciones NO se calculan en base a ML ni a Alto — son un
    valor FIJO por catálogo (terminaciones.json solo guarda un número por
    ítem, sin distinguir valorML/valorUNIT como estructuras.json). Se
    verificó con una cotización real: "Cubre alarma" con Cantidad 80, Tiro y
    retiro, terminación "Cubre alarmas" ($3.500) — el Excel cobra
    3.500 × 160 (Cantidad efectiva) = $560.000, NO 3.500 × ML. Antes se
    intentó un modelo ML-based para terminaciones (multiplicar por Alto ×
    Cantidad); ese modelo sobrestimaba el costo porque además de duplicar la
    cantidad, multiplicaba por Alto — algo que el Excel real no hace.
  - Backlight: valor = M² impreso × valor de la tela (Alto × Ancho × Cantidad).
    Backlight es el único tipo de producto que mide su tela en M² en vez de
    ML. No incluye el costo de los materiales de la caja (perfiles/luces/
    fuentes de poder) — esos catálogos no tienen precio todavía; queda para
    una entrega futura.

Piso mínimo de facturación (ML_MINIMO_POR_PRODUCTO / M2_MINIMO_POR_PRODUCTO):
  cada producto (una línea del cotizador, ya con su Cantidad aplicada — no
  cada unidad por separado) se factura sobre un mínimo de 2 ML (no-backlight)
  o 2 M² (Backlight). Si el ML/M² real de esa línea completa da menos de 2,
  se factura como si fueran exactamente 2 — NO se aplica el piso a cada
  unidad y después se multiplica por Cantidad (eso sobrestimaría e
  producto con Cantidad > 1: 2 unidades de 0.5 ML cada una no son "2 × 2 ML
  = 4 ML", son "1 ML real, que como está bajo el piso, se cobra como 2 ML").
  Este piso SOLO afecta el costo de impresión (y, en el modelo "aditivo",
  las estructuras valorML — ambas se calculan a partir del mismo ML) — el
  ML real (sin piso) se sigue usando tal cual para todo lo que no es plata:
  calcular_ml() en core/presentar_op.py (orden de producción — ahí importa
  cuánta tela se corta de verdad, no cuánto se cobra) y las columnas
  informativas "ML imp."/"M² imp." de la ventana de resumen (ui/cotizacion.py,
  ui/cotizador_backlight.py) NO pasan por este piso.
"""

import math

from core.repositorio import (
    TEXTILES_ANCHOS,
    TEXTILES_VALORES,
    ESTRUCTURAS_VALORES,
    TERMINACIONES_VALORES,
    ESTRUCTURAS_LEGADO_VALORES,
    TERMINACIONES_LEGADO_VALORES,
)

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


def _redondear_excel(x: float) -> int:
    """Redondeo estilo Excel (mitad hacia arriba): 3.5 -> 4. El round()
    nativo de Python usa redondeo bancario (mitad al par más cercano:
    3.5 -> 4 pero 2.5 -> 2), que no calza con el Excel original."""
    return math.floor(x + 0.5)


def calcular_ml(d: dict, ancho_tela: float | None) -> tuple[float | None, float | None]:
    """
    Calcula Ratio y ML impresos para un producto no-backlight. Traducción
    literal de la fórmula del Excel original:
        =SI(ESNUMERO([@Ancho]),
            SI(REDONDEAR.MENOS([@[Ancho Tela]]/[@Ancho],0)<1,
                [@[Ancho Tela]]/[@Ancho],
                REDONDEAR([@[Ancho Tela]]/[@Ancho],0)),
            "")
    O sea:
        UxA   = ancho_tela / ancho_producto, SIN redondear, si el truncado
                da menos de 1 (para no terminar dividiendo por 0 más abajo)
              = REDONDEADO al entero más cercano en cualquier otro caso
                (NO truncado/floor — ahí estaba el bug: 1.58/0.45=3.511
                truncaba a 3, pero el Excel redondea a 4)
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
    uxa = cruda if int(cruda) < 1 else _redondear_excel(cruda)
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
        terminaciones_legado.json — precios por unidad derivados de "Lista
        vieja.pdf"). Todo es por unidad: valor × Cantidad efectiva (ver
        cantidad_efectiva), sin distinción ML/unidad.
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
    """
    textiles_valores       = TEXTILES_VALORES if textiles_valores is None else textiles_valores
    textiles_anchos        = TEXTILES_ANCHOS if textiles_anchos is None else textiles_anchos
    estructuras_valores    = ESTRUCTURAS_VALORES if estructuras_valores is None else estructuras_valores
    terminaciones_valores  = TERMINACIONES_VALORES if terminaciones_valores is None else terminaciones_valores
    estructuras_legado_valores   = ESTRUCTURAS_LEGADO_VALORES if estructuras_legado_valores is None else estructuras_legado_valores
    terminaciones_legado_valores = TERMINACIONES_LEGADO_VALORES if terminaciones_legado_valores is None else terminaciones_legado_valores

    cantidad = d.get("cantidad", 0) or 0

    if "tela" in d:
        area = d.get("alto", 0.0) * d.get("ancho", 0.0) * cantidad
        area_facturable = _con_piso(area, M2_MINIMO_POR_PRODUCTO)
        valor_tela = textiles_valores.get(d.get("tela", ""), 0.0)
        costo_impresion = area_facturable * valor_tela
        resultado = {
            "ml_o_area":          area,
            "costo_impresion":    costo_impresion,
            "costo_terminaciones": 0.0,
            "costo_estructuras":   0.0,
            "detalle_estructuras":  {},
            "detalle_terminaciones": {},
            "total":               costo_impresion,
        }
    else:
        ancho_tela = textiles_anchos.get(d.get("textil", ""))
        _, ml = calcular_ml(d, ancho_tela)
        ml = ml or 0.0
        ml_facturable = _con_piso(ml, ML_MINIMO_POR_PRODUCTO)

        valor_tela = textiles_valores.get(d.get("textil", ""), 0.0)
        costo_impresion = ml_facturable * valor_tela

        cant_efectiva = cantidad_efectiva(d)

        terminaciones = d.get("terminaciones") or []
        estructuras = d.get("estructuras") or []

        if modelo == "legado":
            detalle_terminaciones = {}
            for t in terminaciones:
                valor_manual = parsear_valor_manual(t)
                detalle_terminaciones[t] = (
                    valor_manual if valor_manual is not None
                    else terminaciones_legado_valores.get(t, 0.0) * cant_efectiva
                )
            costo_terminaciones = sum(detalle_terminaciones.values())

            detalle_estructuras = {}
            for e in estructuras:
                valor_manual = parsear_valor_manual(e)
                detalle_estructuras[e] = (
                    valor_manual if valor_manual is not None
                    else estructuras_legado_valores.get(e, 0.0) * cant_efectiva
                )
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
    Devuelve {neto, descuento, neto_total, iva, total}. kwargs se pasan tal
    cual a costo_producto (catálogos fijos para tests, ver ahí)."""
    neto = (sum(costo_producto(p, **kwargs)["total"] for p in productos)
            + (despacho or 0.0) + (instalacion or 0.0))
    descuento = neto * descuento_pct / 100
    neto_total = neto - descuento
    iva = neto_total * IVA_PORCENTAJE / 100
    total = neto_total + iva
    return {
        "neto":       neto,
        "descuento":  descuento,
        "neto_total": neto_total,
        "iva":        iva,
        "total":      total,
    }
