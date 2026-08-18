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
    las laterales — TODO: confirmar la unidad real del precio de mallas
    (¿por malla completa o por tira?, ver recursos/precios_cajas.json);
    cuando se confirme, el fix es solo cambiar ese dato, no esta función."""
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
