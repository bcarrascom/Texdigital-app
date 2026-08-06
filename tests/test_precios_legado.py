"""
tests/test_precios_legado.py
Verifica core/precios.py modelo="legado" — el catálogo "Demo", adoptado
como modelo PRINCIPAL de costo_producto (default). Usa los mismos campos
d["estructuras"]/d["terminaciones"] que el modelo "aditivo" (Neo, ver
tests/test_precios.py, código dejado intacto para una eventual vuelta
atrás) — lo que cambia es en qué catálogo se buscan los nombres y cómo se
valorizan: todo por unidad (Cantidad efectiva), sin distinción ML/unidad.

También cubre parsear_valor_manual (ajustes manuales de precio, ej.
"$10.000" agregado directo en vez de un nombre de catálogo).

Correr con:  python -m unittest tests.test_precios_legado -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.precios import costo_producto, parsear_valor_manual

TEXTILES_ANCHOS = {"TelaTest": 1.2}
TEXTILES_VALORES = {"TelaTest": 0.0}  # en 0 para aislar estructura/terminación

# Recortes reales derivados de "Lista vieja.pdf" — ver core/repositorio.py
# cargar_estructuras_legado/cargar_terminaciones_legado para el catálogo
# completo en recursos/estructuras_legado.json y terminaciones_legado.json.
TERMINACIONES_LEGADO = {
    "Basta": 10000,
    "Calce": 10000,
    "Cubre alarmas": 7000,
}
ESTRUCTURAS_LEGADO = {
    "Fleje plastico": 7500,
    "Madera y cancamos": 15000,
    "Tubo + Pletina + Candados": 12000,
}

CATALOGOS = dict(
    modelo="legado",
    textiles_valores=TEXTILES_VALORES,
    textiles_anchos=TEXTILES_ANCHOS,
    terminaciones_legado_valores=TERMINACIONES_LEGADO,
    estructuras_legado_valores=ESTRUCTURAS_LEGADO,
)


def _producto(**over):
    base = {
        "textil": "TelaTest", "impresion": "Cara única",
        "alto": 1.0, "ancho": 1.0, "cantidad": 1,
        "estructuras": [], "terminaciones": [],
    }
    base.update(over)
    return base


class TestPreciosLegado(unittest.TestCase):

    def test_es_el_modelo_por_defecto(self):
        # costo_producto(d) sin especificar modelo debe usar "legado" (Demo)
        d = _producto(terminaciones=["Cubre alarmas"])
        costo_default = costo_producto(d, textiles_valores=TEXTILES_VALORES,
                                        textiles_anchos=TEXTILES_ANCHOS,
                                        terminaciones_legado_valores=TERMINACIONES_LEGADO)
        self.assertEqual(costo_default["costo_terminaciones"], 7000)

    def test_terminaciones_legado_solas_cara_unica(self):
        # Basta 10.000 + Calce 10.000, Cantidad 1, Cara única
        # (cantidad efectiva = 1) -> total 20.000
        d = _producto(terminaciones=["Basta", "Calce"])
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_terminaciones"], 20000)
        self.assertEqual(costo["costo_estructuras"], 0)
        self.assertEqual(costo["total"], 20000)

    def test_estructura_legado_combinada_tubo_pletina_candados(self):
        # "Tubo + Pletina + Candados" (combo único, ver conversación —
        # nunca aparecen separados en la lista vieja) + Madera y cancamos,
        # Cantidad 2, Tiro y retiro (cantidad efectiva = 4)
        # -> (12000+15000)*4 = 108.000
        d = _producto(
            impresion="Tiro y retiro", cantidad=2,
            estructuras=["Tubo + Pletina + Candados", "Madera y cancamos"],
        )
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_estructuras"], 108000)

    def test_mezcla_estructuras_y_terminaciones_legado(self):
        d = _producto(
            estructuras=["Fleje plastico"],
            terminaciones=["Cubre alarmas"],
            cantidad=3,
        )
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_estructuras"], 3 * 7500)
        self.assertEqual(costo["costo_terminaciones"], 3 * 7000)
        self.assertEqual(costo["total"], 3 * (7500 + 7000))

    def test_sin_estructura_ni_terminacion_legado_da_cero(self):
        d = _producto()
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_terminaciones"], 0)
        self.assertEqual(costo["costo_estructuras"], 0)

    def test_ambos_modelos_leen_las_mismas_keys_pero_catalogos_distintos(self):
        # "Asta fibra de vidrio vela 2 mts" existe en AMBOS catálogos —
        # mismo nombre, incluso mismo valor (17.000) — pero "aditivo" lo
        # busca en estructuras_valores y "legado" en
        # estructuras_legado_valores; acá se prueba con valores DISTINTOS
        # a propósito para confirmar que cada modelo usa su propio catálogo.
        d = _producto(estructuras=["Poste"])
        costo_legado = costo_producto(
            d, modelo="legado", textiles_valores=TEXTILES_VALORES,
            textiles_anchos=TEXTILES_ANCHOS,
            estructuras_legado_valores={"Poste": 5000})
        costo_aditivo = costo_producto(
            d, modelo="aditivo", textiles_valores=TEXTILES_VALORES,
            textiles_anchos=TEXTILES_ANCHOS,
            estructuras_valores={"Poste": {"valorUNIT": 9000}})
        self.assertEqual(costo_legado["costo_estructuras"], 5000)
        self.assertEqual(costo_aditivo["costo_estructuras"], 9000)

    def test_piso_2ml_sube_impresion_de_producto_chico(self):
        # Bandera 0,5x0,5 estilo el caso reportado por el usuario: ML real
        # da bien por debajo de 2 (menos de un metro de tela) — se factura
        # como si fueran 2 ML, no el ML real.
        textiles_valores = {"TelaTest": 11000.0}
        d = _producto(alto=0.5, ancho=0.5, cantidad=1)
        costo = costo_producto(d, modelo="legado",
                                textiles_valores=textiles_valores,
                                textiles_anchos=TEXTILES_ANCHOS)
        self.assertEqual(costo["costo_impresion"], 2 * 11000)

    def test_piso_2ml_aplica_al_total_de_la_linea_no_por_unidad(self):
        # Lectura correcta del piso: se aplica al ML YA calculado para toda
        # la línea (que ya incluye Cantidad), no 2 ML por cada unidad. Dos
        # unidades de un producto que en total dan menos de 2 ML se
        # facturan como 2 ML en total, no como 2 × 2 = 4 ML.
        textiles_valores = {"TelaTest": 1000.0}
        d = _producto(alto=0.5, ancho=1.0, cantidad=2)  # ml real = 1.0
        costo = costo_producto(d, modelo="legado",
                                textiles_valores=textiles_valores,
                                textiles_anchos=TEXTILES_ANCHOS)
        self.assertEqual(costo["costo_impresion"], 2 * 1000)  # no 4 * 1000

    def test_piso_2ml_no_afecta_ml_o_area_ni_ml_real(self):
        # El piso solo sube lo que se COBRA — el ML real (usado para la
        # orden de producción y las columnas informativas del resumen)
        # sigue siendo el valor sin piso.
        textiles_valores = {"TelaTest": 11000.0}
        d = _producto(alto=0.5, ancho=0.5, cantidad=1)
        costo = costo_producto(d, modelo="legado",
                                textiles_valores=textiles_valores,
                                textiles_anchos=TEXTILES_ANCHOS)
        self.assertLess(costo["ml_o_area"], 2.0)

    def test_piso_2ml_no_aplica_si_ya_supera_el_piso(self):
        # Con ML por encima de 2, el piso no cambia nada.
        textiles_valores = {"TelaTest": 1000.0}
        d = _producto(alto=10, ancho=1, cantidad=1)  # ml real = 10
        costo = costo_producto(d, modelo="legado",
                                textiles_valores=textiles_valores,
                                textiles_anchos=TEXTILES_ANCHOS)
        self.assertEqual(costo["costo_impresion"], 10 * 1000)

    def test_piso_2m2_backlight_sube_impresion_de_producto_chico(self):
        # Mismo piso, pero en M² para Backlight (alto x ancho x cantidad).
        from core.precios import costo_producto as _cp
        d = {"tela": "Popelina Test", "caja": "Sin caja",
             "alto": 0.5, "ancho": 0.5, "cantidad": 1}  # area real = 0.25
        costo = _cp(d, modelo="legado",
                    textiles_valores={"Popelina Test": 1000.0},
                    textiles_anchos={"Popelina Test": 1.53})
        self.assertEqual(costo["costo_impresion"], 2 * 1000)
        self.assertLess(costo["ml_o_area"], 2.0)

    def test_catalogo_legado_completo_carga_desde_recursos(self):
        # Sin pasar catálogos fijos: debe usar core.repositorio.
        # ESTRUCTURAS_LEGADO_VALORES/TERMINACIONES_LEGADO_VALORES, cargados
        # desde recursos/estructuras_legado.json y terminaciones_legado.json.
        from core.repositorio import ESTRUCTURAS_LEGADO_VALORES, TERMINACIONES_LEGADO_VALORES
        self.assertEqual(TERMINACIONES_LEGADO_VALORES.get("Cubre alarmas"), 7000)
        self.assertEqual(TERMINACIONES_LEGADO_VALORES.get("Calce"), 10000)
        self.assertEqual(ESTRUCTURAS_LEGADO_VALORES.get("Asta fibra de vidrio vela 2 mts"), 17000)
        self.assertEqual(ESTRUCTURAS_LEGADO_VALORES.get("Tubo + Pletina + Candados"), 12000)


class TestValorManual(unittest.TestCase):
    """Ajuste manual de precio: si un ítem de Estructuras/Terminaciones es
    en realidad un monto en pesos ("10000", "10.000", "$10.000"), se suma
    directo al total de esa categoría — sin catálogo, sin multiplicar por
    Cantidad efectiva."""

    def test_parsear_valor_manual_formatos_tipicos(self):
        self.assertEqual(parsear_valor_manual("10000"), 10000.0)
        self.assertEqual(parsear_valor_manual("10.000"), 10000.0)
        self.assertEqual(parsear_valor_manual("$10.000"), 10000.0)
        self.assertEqual(parsear_valor_manual("$ 10.000"), 10000.0)
        self.assertEqual(parsear_valor_manual("10,000"), 10000.0)

    def test_parsear_valor_manual_nombre_de_catalogo_da_none(self):
        self.assertIsNone(parsear_valor_manual("Cubre alarmas"))
        self.assertIsNone(parsear_valor_manual("Tubo + Pletina + Candados"))
        self.assertIsNone(parsear_valor_manual(""))

    def test_ajuste_manual_se_suma_directo_sin_cantidad_efectiva(self):
        # $10.000 de ajuste manual en Terminaciones, Cantidad 5, Tiro y
        # retiro (cantidad efectiva 10) -> el ajuste NO se multiplica,
        # solo la Calce sí (10.000*10=100.000). Total: 100.000+10.000.
        d = _producto(
            impresion="Tiro y retiro", cantidad=5,
            terminaciones=["Calce", "$10.000"],
        )
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["detalle_terminaciones"]["$10.000"], 10000)
        self.assertEqual(costo["detalle_terminaciones"]["Calce"], 100000)
        self.assertEqual(costo["costo_terminaciones"], 110000)

    def test_ajuste_manual_en_estructuras(self):
        d = _producto(estructuras=["10.000"], cantidad=3)
        costo = costo_producto(d, **CATALOGOS)
        self.assertEqual(costo["costo_estructuras"], 10000)  # no x3


if __name__ == "__main__":
    unittest.main()
