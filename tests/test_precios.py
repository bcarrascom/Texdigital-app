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

from core.precios import calcular_ml, cantidad_efectiva, costo_producto, costo_cotizacion

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

    def test_uxa_redondea_como_el_excel_no_trunca(self):
        # Caso real reportado: Stretch (ancho tela 1.58), Ancho 0.45, Alto
        # 1.5, Cantidad 5. 1.58/0.45=3.5111 -> Excel REDONDEA a 4, no trunca
        # a 3 (ahí estaba el bug: truncar sobrestimaba el ML necesario).
        d = _producto(alto=1.5, ancho=0.45, cantidad=5)
        ratio, ml = calcular_ml(d, 1.58)
        self.assertAlmostEqual(ratio, 1.25)
        self.assertAlmostEqual(ml, 1.88, places=2)

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

    def test_tiro_y_retiro_duplica_antes_de_redondear_no_despues(self):
        # Caso real reportado: Stretch (ancho tela 1.58), Ancho 0.45, Alto
        # 1.5, Cantidad 5, Tiro y retiro. ratio=1.25, base=1.25*1.5=1.875
        # (exacto). El Excel duplica el valor EXACTO (1.875*2=3.75) y
        # recién ahí redondea — no redondea 1.875->1.88 primero y después
        # duplica (eso daría 3.76, $120 de más en la impresión: $45.120 en
        # vez de los $45.000 reales del Excel).
        d = _producto(ancho=0.45, alto=1.5, cantidad=5, impresion="Tiro y retiro")
        ratio, ml = calcular_ml(d, 1.58)
        self.assertAlmostEqual(ratio, 1.25)
        self.assertEqual(ml, 3.75)  # NO 3.76

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


if __name__ == "__main__":
    unittest.main()
