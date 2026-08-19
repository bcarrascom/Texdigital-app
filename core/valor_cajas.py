"""
core/valor_cajas.py
Cálculo del valor (CLP) de una caja de backlight, a partir del resultado
de materiales de core.calculo_cajas.calcular_caja() + el catálogo de
precios (recursos/precios_cajas.json, ver core.repositorio.PRECIOS_CAJAS).

Función pura: no lee archivos ni toca la UI — recibe los precios ya
cargados, igual que calculo_cajas.py recibe los catálogos de luces/FP.

Fórmula (por caja; `ml` = mts_lineales_x_caja = (Ancho×2)+(Alto×2)):
    valor_caja  = iluminacion + traseras + armado + fp + perfil + otros_unit + pintura
    valor_total = valor_caja × Cantidad
"""

from core.calculo_cajas import lado_corto as _lado_corto, lado_largo as _lado_largo, mts_lineales_x_caja as _mts_lineales


def _tramo_armado(ml: float) -> str | None:
    """
    Tramo de tarifa de armado según ml — traducción literal del BUSCARV
    del Excel original. Los límites son intencionalmente mixtos (< en
    algunos, <= en otros): no es un solo criterio uniforme, así que esto
    NO se puede aplanar a un simple bucle "ml <= límite" genérico.
    """
    if ml == 0:
        return None
    if ml < 1:
        return "minimo"
    if ml <= 4:
        return "simple"
    if ml <= 6:
        return "medio"
    if ml < 8:
        return "complejo"
    return "jumbo"


def _valor_fila_luz(fila: dict, precios_luces: dict[str, float]) -> float:
    """precio_unidad × cantidad_x_caja de una fila "Luces 1"/"Luces 2".
    Mallas (Malla 150 / Malla 12v) usan exactamente la misma fórmula que
    las laterales — confirmado contra dos ejemplos reales del Excel
    original: precios_cajas.json["luces"] guarda el precio por UNIDAD de
    malla completa (no por tira ni por LED individual), la misma unidad
    que cuenta core.calculo_cajas.calcular_caja() (ver ese módulo)."""
    tipo = fila.get("tipo")
    if not tipo:
        return 0.0
    return precios_luces.get(tipo, 0.0) * fila.get("cantidad_x_caja", 0.0)


def calcular_valor_caja(
    resultado_materiales: dict,
    perfil: str,
    precios: dict,
    otros_unit: float = 0.0,
    cantidad: int = 1,
) -> dict:
    """
    resultado_materiales: dict devuelto por
        core.calculo_cajas.calcular_caja() (mismos ancho/alto/luces/perfil
        con los que se llamó esa función).
    perfil: nombre del perfil elegido (el mismo que se le pasó a
        calcular_caja(); no viene en su resultado, así que se repite acá).
    precios: dict con la forma de core.repositorio.PRECIOS_CAJAS.
    otros_unit: monto libre en CLP que ingresa el usuario a mano (único
        input manual de todo el cálculo). Default 0.
    cantidad: Cantidad de cajas del producto (para valor_total).

    Devuelve el desglose completo, para poder mostrarlo/depurarlo:
    {iluminacion, traseras, armado, fp, perfil, pintura, otros,
     valor_caja, valor_total}.
    """
    filas_por_material = {f["material"]: f for f in resultado_materiales["filas"]}
    ml = resultado_materiales["mts_lineales_x_caja"]

    iluminacion = (
        _valor_fila_luz(filas_por_material["Luces 1"], precios["luces"])
        + _valor_fila_luz(filas_por_material["Luces 2"], precios["luces"])
    )

    # Traseras se cobra por área real (Ancho×Alto), NO por la cantidad de
    # planchas redondeada hacia arriba que usa calculo_cajas.calcular_caja()
    # para saber cuánto material pedir. Son dos cálculos distintos a
    # propósito: cuánto material comprar se redondea (no existen "0.4
    # planchas" para pedir), pero cuánto cobrar es proporcional al área
    # real usada — confirmado contra una cotización real (Excel original):
    # área × $5.000/m² calzó exacto en 5 de 6 cajas; usar la cantidad
    # redondeada sobrestimaba fuerte las cajas chicas (cobraba 1 plancha
    # entera aunque se usara una fracción mínima).
    fila_traseras = filas_por_material["Traseras"]
    area = resultado_materiales["lado_corto"] * resultado_materiales["lado_largo"]
    traseras = precios["traseras"].get(fila_traseras["tipo"], 0.0) * area

    tramo = _tramo_armado(ml)
    armado = precios["armado"].get(tramo, 0.0) * ml if tramo else 0.0

    fp_info = resultado_materiales.get("fp")
    fp_valor = 0.0
    if fp_info:
        fila_fp = filas_por_material["FP"]
        fp_valor = precios["fp"].get(fp_info["watts_unidad"], 0.0) * fila_fp["cantidad_x_caja"]

    perfil_valor = precios["perfiles"].get(perfil, 0.0) * ml
    pintura = ml * precios.get("pintura_por_ml", 0.0)

    valor_caja = (
        iluminacion + traseras + armado + fp_valor + perfil_valor
        + otros_unit + pintura
    )
    valor_total = valor_caja * cantidad

    return {
        "iluminacion": iluminacion,
        "traseras":    traseras,
        "armado":      armado,
        "fp":          fp_valor,
        "perfil":      perfil_valor,
        "pintura":     pintura,
        "otros":       otros_unit,
        "valor_caja":  valor_caja,
        "valor_total": valor_total,
    }


def valor_caja_desde_guardado(
    caja: dict,
    precios: dict,
    otros_unit: float = 0.0,
    cantidad: int = 1,
    ancho: float | None = None,
    alto: float | None = None,
) -> dict:
    """
    Igual que calcular_valor_caja(), pero a partir del dict ya guardado en
    datos["caja"] (ver ui.cotizador_backlight._valor_caja_guardado) en vez
    del resultado crudo de calcular_caja(). No necesita los catálogos de
    luces/FP (catalogo_luces, catalogo_fp) — la selección de materiales ya
    quedó fija al guardar la cotización; acá solo se re-valoriza en pesos
    con los precios actuales del catálogo de cajas.

    `caja` debe traer perfil, traseras/luces_1/luces_2/fp ({tipo,
    cantidad_x_caja, ...}, y fp además con "watts_unidad"). lado_corto/
    lado_largo/mts_lineales_x_caja idealmente vienen en `caja` (formato
    nuevo); si no están (cotizaciones guardadas antes de este cálculo,
    formato viejo), se derivan de `ancho`/`alto` (las medidas del producto,
    que también son las de la caja — ver core.calculo_cajas).
    """
    lc = caja.get("lado_corto")
    ll = caja.get("lado_largo")
    ml = caja.get("mts_lineales_x_caja")
    if lc is None or ll is None or ml is None:
        ancho = ancho or 0.0
        alto = alto or 0.0
        lc = _lado_corto(ancho, alto)
        ll = _lado_largo(ancho, alto)
        ml = _mts_lineales(ancho, alto)

    filas = [
        {"material": "Traseras", "tipo": caja["traseras"].get("tipo"),
         "cantidad_x_caja": caja["traseras"].get("cantidad_x_caja", 0.0)},
        {"material": "Luces 1", "tipo": caja["luces_1"].get("tipo"),
         "cantidad_x_caja": caja["luces_1"].get("cantidad_x_caja", 0.0)},
        {"material": "Luces 2", "tipo": caja["luces_2"].get("tipo"),
         "cantidad_x_caja": caja["luces_2"].get("cantidad_x_caja", 0.0)},
        {"material": "FP", "tipo": caja["fp"].get("tipo"),
         "cantidad_x_caja": caja["fp"].get("cantidad_x_caja", 0.0)},
    ]
    watts_unidad = caja["fp"].get("watts_unidad")
    fp_info = {"watts_unidad": watts_unidad} if watts_unidad is not None else None

    resultado_materiales = {
        "filas": filas,
        "fp": fp_info,
        "lado_corto": lc,
        "lado_largo": ll,
        "mts_lineales_x_caja": ml,
    }
    return calcular_valor_caja(
        resultado_materiales, caja["perfil"], precios,
        otros_unit=otros_unit, cantidad=cantidad,
    )
