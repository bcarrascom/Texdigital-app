"""
tests/test_precios.py
Verifica core/precios.py modelo="aditivo" (modelo "Neo", por ML — ya NO es
el default de costo_producto, ver tests/test_precios_legado.py para el
modelo "Demo" que se adoptó como principal, pero el código de Neo se dejó
intacto para una eventual vuelta atrás) contra los ejemplos del prompt de
estructuras/terminaciones aditivas. Usa catálogos fijos (no los de
Dropbox/SGTD/Conf) para que el test sea autocontenido y no dependa del
estado de la máquina donde corre — mismo criterio que
tests/test_calculo_cajas.py.

Correr con:  python -m unittest tests.test_precios -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.precios import (
    calcular_ml, cantidad_efectiva, costo_producto, costo_cotizacion,
    descuento_textil, tramo_descuento_textil,
)

TEXTILES_ANCHOS = {"TelaTest": 1.2, "Popelina Test": 1.53}
TEXTILES_VALORES = {"TelaTest": 0.0, "Popelina Test": 1000.0}
ESTRUCTURAS_VALORES = {
    "Asta 2 mts":     {"valorUNIT": 17000},
    "Estaca":         {"valorUNIT": 10000},
    "Tubo aluminio":  {"valorML": 2000},
}
TERMINACIONES_VALORES = {"Basta": 1140, "Bolsillos": 1200}

CATALOGOS = dict(
    modelo="aditivo",
    textiles_anchos=TEXTILES_ANCHOS,
    textiles_valores=TEXTILES_VALORES,
    estructuras_valores=ESTRUCTURAS_VALORES,
    terminaciones_valores=TERMINACIONES_VALORES,
)


def _producto(**over):
    base = {
        "textil": "TelaTest", "estructuras": [], "terminaciones": [],
        "impresion": "Cara única", "alto": 1.0, "ancho": 1.0, "cantidad": 1,
    }
    base.update(over)
    return base


class TestPrecios(unittest.TestCase):

    def test_ml_10_via_ancho_tela_y_cantidad(self):
        # ancho_tela=1.2, ancho_producto=1 -> uxa=1 (un solo ancho entra);
        # ratio=cantidad/uxa=1; ml=ratio*alto=10.
        d = _producto(alto=10, ancho=1, cantidad=1)
        _, ml = calcular_ml(d, TEXTILES_ANCHOS["TelaTest"])
        self.assertEqual(ml, 10)

    def test_uxa_trunca_siempre_hacia_abajo(self):
        # UxA son las unidades que caben físicamente a lo ancho del rollo de
        # tela — no se puede cortar "una unidad y tanto". Stretch (ancho
        # tela 1.58), Ancho 0.45, Alto 1.5, Cantidad 5: 1.58/0.45=3.5111,
        # caben 3 unidades por pasada (no 4 — 3.9->3, 4.1->4, siempre hacia
        # abajo).
        d = _producto(alto=1.5, ancho=0.45, cantidad=5)
        ratio, ml = calcular_ml(d, 1.58)
        self.assertAlmostEqual(ratio, 5 / 3)
        self.assertAlmostEqual(ml, 2.5)

    def test_uxa_trunca_un_entero_exacto_pese_al_error_de_punto_flotante(self):
        # 1.2/0.4 matemáticamente es 3 exacto, pero en punto flotante da
        # 2.9999999999999996 — sin tolerancia, truncar de más daría UxA=2.
        d = _producto(alto=1, ancho=0.4, cantidad=3)
        ratio, ml = calcular_ml(d, 1.2)
        self.assertEqual(ratio, 1)  # UxA=3, cantidad=3 -> ratio=1, no 1.5

    def test_uxa_fraccionario_cuando_ancho_no_entra_ni_una_vez(self):
        # Si ni una unidad entra a lo ancho del rollo (truncado < 1), el
        # Excel NO redondea a 1 — deja el valor fraccionario tal cual
        # (ratio queda > cantidad, reflejando que hace falta más de un
        # "paso" de rollo por cada unidad). Es el mismo caso que habilita
        # el checkbox "Forzar" (ver ui/pantalla_medidas_base.py): un Ancho
        # mayor al ancho de tela ya cae acá solo, sin necesitar ningún
        # ajuste especial en calcular_ml para ese caso.
        d = _producto(alto=1.0, ancho=1.5, cantidad=1)
        ratio, ml = calcular_ml(d, 1.0)  # 1.0/1.5 = 0.667, truncado = 0
        self.assertAlmostEqual(ratio, 1.5)   # cantidad(1) / 0.667
        self.assertAlmostEqual(ml, 1.5)

    def test_1_terminaciones_solas(self):
        # Basta 1140 + Bolsillos 1200, Cantidad 1 (sin Tiro y retiro,
        # cantidad efectiva = cantidad) -> (1140+1200) * 1 = 2.340. Las
        # terminaciones son un valor FIJO por catálogo, no dependen del ML.
        d = _producto(alto=10, ancho=1, cantidad=1,
                       terminaciones=["Basta", "Bolsillos"])
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_terminaciones"], 2340)
        self.assertEqual(costo["costo_impresion"], 0)  # TelaTest vale 0
        self.assertEqual(costo["costo_estructuras"], 0)
        self.assertEqual(costo["total"], 2340)

    def test_1b_terminaciones_no_dependen_del_ml_ni_del_ancho_de_tela(self):
        # Caso reportado: Cubre Sensores. ancho_tela=1.2, ancho_producto=0.4
        # -> uxa=3 (caben 3 unidades a lo ancho del rollo), cantidad=6,
        # alto=1. ML impresión = (6/3)*1 = 2 (correcto: se gasta menos tela
        # al cortar 3 piezas por pasada). La terminación (Basta) es un valor
        # fijo por catálogo × cantidad efectiva — no se ve afectada por el
        # ahorro de tela ni por el ML: 1140 * 6 = 6.840, no 1140 * 2.
        d = _producto(alto=1, ancho=0.4, cantidad=6, terminaciones=["Basta"])
        _, ml = calcular_ml(d, 1.2)
        self.assertEqual(ml, 2)  # ML de impresión sí se beneficia del uxa
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_terminaciones"], 6 * 1140)  # no 2 * 1140

    def test_2_estructura_unitaria_sola(self):
        # Asta 2 mts (valorUNIT 17000), Cantidad 3 -> 51.000, sin importar medidas
        d = _producto(alto=3, ancho=2, cantidad=3, estructuras=["Asta 2 mts"])
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_estructuras"], 51000)
        self.assertEqual(costo["total"], 51000)

    def test_2b_estructura_unitaria_y_terminacion_duplican_con_tiro_y_retiro(self):
        # Confirmado con el usuario: Tiro y retiro también duplica cuánta
        # estructura-unitaria y terminación se aplica (no solo el ML de
        # impresión) — Asta 2 mts (valorUNIT 17000) y Basta (1140),
        # Cantidad 3 -> cantidad efectiva 6 -> 6*17000 + 6*1140 = 109.680
        d = _producto(alto=3, ancho=2, cantidad=3, impresion="Tiro y retiro",
                       estructuras=["Asta 2 mts"], terminaciones=["Basta"])
        self.assertEqual(cantidad_efectiva(d), 6)
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_estructuras"], 6 * 17000)
        self.assertEqual(costo["costo_terminaciones"], 6 * 1140)

    def test_3_mezcla_ml_y_unitaria(self):
        # ML 5 (ancho_tela=1.2, ancho=1, cantidad=2, alto=2.5), Cantidad 2:
        # Tubo aluminio (valorML 2000) + Estaca (valorUNIT 10000)
        # -> 5*2000 + 2*10000 = 30.000
        d = _producto(alto=2.5, ancho=1, cantidad=2,
                       estructuras=["Tubo aluminio", "Estaca"])
        _, ml = calcular_ml(d, TEXTILES_ANCHOS["TelaTest"])
        self.assertEqual(ml, 5)
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_estructuras"], 30000)
        self.assertEqual(costo["total"], 30000)
        # Desglose por ítem, usado para mostrar el $ junto a cada fila en la UI.
        self.assertEqual(costo["detalle_estructuras"]["Tubo aluminio"], 10000)  # 5*2000
        self.assertEqual(costo["detalle_estructuras"]["Estaca"], 20000)         # 2*10000

    def test_4_backlight_sin_caja_es_m2_por_valor_tela(self):
        d = {"tela": "Popelina Test", "caja": "Sin caja",
             "alto": 2.0, "ancho": 1.0, "cantidad": 3}
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["ml_o_area"], 6.0)          # 2*1*3
        self.assertEqual(costo["costo_impresion"], 6000.0)  # 6 * 1000
        self.assertEqual(costo["costo_terminaciones"], 0.0)
        self.assertEqual(costo["costo_estructuras"], 0.0)
        self.assertEqual(costo["total"], 6000.0)
        self.assertEqual(costo["valor_unitario"], 2000.0)   # 6000 / 3

    def test_5_tiro_y_retiro_dobla_el_ml_y_la_cantidad_efectiva(self):
        d = _producto(alto=10, ancho=1, cantidad=1, impresion="Tiro y retiro",
                       terminaciones=["Basta"])
        _, ml = calcular_ml(d, TEXTILES_ANCHOS["TelaTest"])
        self.assertEqual(ml, 20)  # 10 normal, x2 por tiro y retiro
        costo = costo_producto(d, **CATALOGOS)
        # Terminación: valor fijo (1140) * cantidad efectiva (1*2=2), no ML
        self.assertEqual(costo["costo_terminaciones"], 2 * 1140)

    def test_tiro_y_retiro_duplica_el_ml_completo(self):
        # Stretch (ancho tela 1.58), Ancho 0.45, Alto 1.5, Cantidad 5, Tiro
        # y retiro. UxA=3 (truncado), ratio=5/3, base=ratio*1.5=2.5
        # (exacto) -> Tiro y retiro duplica ese valor ya calculado: 5.0.
        d = _producto(ancho=0.45, alto=1.5, cantidad=5, impresion="Tiro y retiro")
        ratio, ml = calcular_ml(d, 1.58)
        self.assertAlmostEqual(ratio, 5 / 3)
        self.assertEqual(ml, 5.0)

    def test_cubre_alarma_reconciliacion_con_excel_real(self):
        # Cotización real (Excel adjunto): Cubre alarma, textil Stretch
        # (ancho tela 1.58, valor 12.000/ML), Ancho 0.49, Alto 1.5,
        # Cantidad 80, Tiro y retiro, terminación "Cubre alarmas" ($3.500).
        # La hoja "nota de venta" duplica la cantidad a mano (160) para
        # simular Tiro y retiro y da: Valor Impresión total = 960.000,
        # Terminaciones = 3.500 (por cada una de las 160 unidades
        # "efectivas") -> Valor total neto = 1.520.000. La hoja de
        # cotización (cliente) muestra esto como 80 unidades reales a
        # $19.000 c/u = 1.520.000. Este test verifica que el programa
        # reproduce esos montos exactos usando Cantidad real (80) +
        # Tiro y retiro, sin necesidad de duplicar la cantidad a mano.
        catalogos = dict(
            modelo="aditivo",
            textiles_valores={"Stretch": 12000},
            textiles_anchos={"Stretch": 1.58},
            estructuras_valores={},
            terminaciones_valores={"Cubre alarmas": 3500},
        )
        d = _producto(textil="Stretch", ancho=0.49, alto=1.5, cantidad=80,
                       impresion="Tiro y retiro", terminaciones=["Cubre alarmas"])
        costo = costo_producto(d, **catalogos)
        self.assertEqual(costo["costo_impresion"], 960000)
        self.assertEqual(costo["costo_terminaciones"], 560000)  # 3500 * 160
        self.assertEqual(costo["total"], 1520000)
        self.assertEqual(costo["valor_unitario"], 19000)  # 1.520.000 / 80

    def test_6_costo_cotizacion_con_descuento_e_iva(self):
        no_backlight = _producto(alto=10, ancho=1, cantidad=1,
                                  terminaciones=["Basta", "Bolsillos"])  # total 2.340
        backlight = {"tela": "Popelina Test", "caja": "Sin caja",
                     "alto": 2.0, "ancho": 1.0, "cantidad": 3}          # total 6.000
        totales = costo_cotizacion([no_backlight, backlight], descuento_pct=10, **CATALOGOS)

        neto_esperado = 2340 + 6000
        descuento_esperado = neto_esperado * 0.10
        neto_total_esperado = neto_esperado - descuento_esperado
        iva_esperado = neto_total_esperado * 0.19
        total_esperado = neto_total_esperado + iva_esperado

        self.assertAlmostEqual(totales["neto"], neto_esperado)
        self.assertAlmostEqual(totales["descuento"], descuento_esperado)
        self.assertAlmostEqual(totales["neto_total"], neto_total_esperado)
        self.assertAlmostEqual(totales["iva"], iva_esperado)
        self.assertAlmostEqual(totales["total"], total_esperado)

    def test_7_costo_cotizacion_con_despacho(self):
        # El despacho no es un producto (sin medidas, no va en la lista
        # `productos`) — se suma directo al neto antes de descuento/IVA,
        # como un ítem más de la cotización. Aún no se generan guías de
        # despacho, así que este monto se cobra a mano.
        no_backlight = _producto(alto=10, ancho=1, cantidad=1,
                                  terminaciones=["Basta"])  # total 1.140
        totales = costo_cotizacion([no_backlight], descuento_pct=0,
                                    despacho=15000, **CATALOGOS)

        neto_esperado = 1140 + 15000
        self.assertAlmostEqual(totales["neto"], neto_esperado)
        self.assertAlmostEqual(totales["neto_total"], neto_esperado)
        self.assertAlmostEqual(totales["iva"], neto_esperado * 0.19)
        self.assertAlmostEqual(totales["total"], neto_esperado * 1.19)

    def test_8_costo_cotizacion_sin_despacho_es_compatible_con_cotizaciones_viejas(self):
        # Sin pasar `despacho` (o pasando None/0), el comportamiento debe
        # ser idéntico a antes de que existiera este parámetro.
        no_backlight = _producto(alto=10, ancho=1, cantidad=1,
                                  terminaciones=["Basta"])
        totales_sin_kwarg = costo_cotizacion([no_backlight], descuento_pct=0, **CATALOGOS)
        totales_con_cero  = costo_cotizacion([no_backlight], descuento_pct=0,
                                              despacho=0.0, **CATALOGOS)
        self.assertEqual(totales_sin_kwarg["neto"], totales_con_cero["neto"])
        self.assertEqual(totales_sin_kwarg["neto"], 1140)

    def test_9_costo_cotizacion_con_instalacion(self):
        # La instalación, igual que el despacho, no es un producto — se
        # suma directo al neto antes de descuento/IVA.
        no_backlight = _producto(alto=10, ancho=1, cantidad=1,
                                  terminaciones=["Basta"])  # total 1.140
        totales = costo_cotizacion([no_backlight], descuento_pct=0,
                                    instalacion=20000, **CATALOGOS)

        neto_esperado = 1140 + 20000
        self.assertAlmostEqual(totales["neto"], neto_esperado)
        self.assertAlmostEqual(totales["neto_total"], neto_esperado)
        self.assertAlmostEqual(totales["iva"], neto_esperado * 0.19)
        self.assertAlmostEqual(totales["total"], neto_esperado * 1.19)

    def test_10_costo_cotizacion_con_despacho_e_instalacion(self):
        # Ambos son montos aparte, se suman los dos al mismo neto.
        no_backlight = _producto(alto=10, ancho=1, cantidad=1,
                                  terminaciones=["Basta"])  # total 1.140
        totales = costo_cotizacion([no_backlight], descuento_pct=0,
                                    despacho=15000, instalacion=20000, **CATALOGOS)

        neto_esperado = 1140 + 15000 + 20000
        self.assertAlmostEqual(totales["neto"], neto_esperado)
        self.assertAlmostEqual(totales["total"], neto_esperado * 1.19)

    def test_11_costo_cotizacion_sin_instalacion_es_compatible_con_cotizaciones_viejas(self):
        # Sin pasar `instalacion` (o pasando None/0), el comportamiento debe
        # ser idéntico a antes de que existiera este parámetro.
        no_backlight = _producto(alto=10, ancho=1, cantidad=1,
                                  terminaciones=["Basta"])
        totales_sin_kwarg = costo_cotizacion([no_backlight], descuento_pct=0, **CATALOGOS)
        totales_con_cero  = costo_cotizacion([no_backlight], descuento_pct=0,
                                              instalacion=0.0, **CATALOGOS)
        self.assertEqual(totales_sin_kwarg["neto"], totales_con_cero["neto"])
        self.assertEqual(totales_sin_kwarg["neto"], 1140)


class TestDescuentoTextil(unittest.TestCase):

    def test_tramos_por_m2(self):
        self.assertEqual(tramo_descuento_textil(9.99), 0)
        self.assertEqual(tramo_descuento_textil(10), 5)
        self.assertEqual(tramo_descuento_textil(19.99), 5)
        self.assertEqual(tramo_descuento_textil(20), 10)
        self.assertEqual(tramo_descuento_textil(49.99), 10)
        self.assertEqual(tramo_descuento_textil(50), 20)
        self.assertEqual(tramo_descuento_textil(100), 20)

    def test_backlight_un_solo_tramo_para_toda_la_cotizacion(self):
        # Popelina Test vale 1000/m². area1=2*2*3=12, area2=1*1*3=3 ->
        # total 15 m² -> tramo 5% (10-20), aplicado sobre el total (backlight
        # no tiene estructuras/terminaciones que descontar aparte).
        p1 = {"tela": "Popelina Test", "caja": "Sin caja", "alto": 2, "ancho": 2, "cantidad": 3}
        p2 = {"tela": "Popelina Test", "caja": "Sin caja", "alto": 1, "ancho": 1, "cantidad": 3}
        res = descuento_textil([p1, p2], **CATALOGOS)
        self.assertAlmostEqual(res["neto"], 15000)  # 12*1000 + 3*1000
        self.assertAlmostEqual(res["monto"], 750)    # 15000 * 5%
        self.assertAlmostEqual(res["pct_visual"], 5.0)

    def test_no_backlight_tramo_independiente_por_textil(self):
        # Grupo "Popelina Test": ancho_producto=ancho_tela (uxa=1),
        # cantidad=3, alto=5 -> ml=15, area=5*1.53*3=22.95 -> tramo 10%.
        # costo_impresion=15*1000=15000 -> descuento de este grupo=1500.
        # Grupo "TelaTest" (valor 0): area=10 -> tramo 5%, pero como el
        # textil vale 0 el $ que aporta es 0 igual — confirma que cada
        # grupo se evalúa por separado sin contaminar al otro.
        popelina = _producto(textil="Popelina Test", alto=5, ancho=1.53, cantidad=3)
        telatest = _producto(alto=10, ancho=1, cantidad=1)
        res = descuento_textil([popelina, telatest], **CATALOGOS)
        self.assertAlmostEqual(res["neto"], 15000)   # 15000 (Popelina) + 0 (TelaTest)
        self.assertAlmostEqual(res["monto"], 1500)
        self.assertAlmostEqual(res["pct_visual"], 10.0)

    def test_no_backlight_no_descuenta_estructuras_ni_terminaciones(self):
        # El % de textil se aplica SOLO al costo de impresión de esa línea
        # (confirmado con el usuario) — una estructura/terminación sumada a
        # la misma línea no debe verse afectada por el descuento-textil.
        # Asta 2 mts (valorUNIT 17000) × cantidad efectiva 3 = 51.000, sin
        # descuento.
        d = _producto(textil="Popelina Test", alto=5, ancho=1.53, cantidad=3,
                       estructuras=["Asta 2 mts"])
        res = descuento_textil([d], **CATALOGOS)
        # costo_impresion=15000 (tramo 10% -> 1500), estructuras=51000 intactas
        self.assertAlmostEqual(res["neto"], 15000 + 51000)
        self.assertAlmostEqual(res["monto"], 1500)

    def test_costo_cotizacion_aplica_solo_el_mas_alto(self):
        # Un solo producto no-backlight: descuento-textil daría 1500 (10%
        # de 15000). Con descuento manual 5% (750, menor) debe ganar el
        # textil; con 20% (3000, mayor) debe ganar el normal — pero
        # descuento_textil_pct se sigue informando en los dos casos (solo
        # visual, no depende de cuál ganó).
        d = _producto(textil="Popelina Test", alto=5, ancho=1.53, cantidad=3)

        totales_gana_textil = costo_cotizacion([d], descuento_pct=5, **CATALOGOS)
        self.assertEqual(totales_gana_textil["fuente_descuento"], "textil")
        self.assertAlmostEqual(totales_gana_textil["descuento"], 1500)
        self.assertAlmostEqual(totales_gana_textil["descuento_textil_pct"], 10.0)

        totales_gana_normal = costo_cotizacion([d], descuento_pct=20, **CATALOGOS)
        self.assertEqual(totales_gana_normal["fuente_descuento"], "normal")
        self.assertAlmostEqual(totales_gana_normal["descuento"], 3000)
        self.assertAlmostEqual(totales_gana_normal["descuento_textil_pct"], 10.0)

    def test_descuento_textil_no_afecta_despacho_ni_instalacion(self):
        # despacho/instalación no son tela — el descuento-textil se calcula
        # solo sobre productos, aunque termine ganando y aplicándose al
        # neto completo de la cotización (igual que el % normal).
        d = _producto(textil="Popelina Test", alto=5, ancho=1.53, cantidad=3)
        totales = costo_cotizacion([d], descuento_pct=0, despacho=5000, **CATALOGOS)
        self.assertEqual(totales["fuente_descuento"], "textil")
        self.assertAlmostEqual(totales["descuento"], 1500)  # no 1550
        self.assertAlmostEqual(totales["neto"], 15000 + 5000)


if __name__ == "__main__":
    unittest.main()
