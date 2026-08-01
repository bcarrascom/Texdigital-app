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
