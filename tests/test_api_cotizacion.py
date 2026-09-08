"""
tests/test_api_cotizacion.py
Verifica el cálculo en vivo de ui/api_cotizacion.py — el que alimenta la
tabla de Resumen de nueva-cotizacion.html.

La regla que se prueba acá: ese resumen tiene que dar EXACTAMENTE lo mismo
que la cotización una vez guardada (core.precios.costo_cotizacion, que es
lo que muestra ver-cotizacion.html). Se rompía con el piso mínimo de
facturación: el cotizador calculaba producto por producto, así que le
cobraba el mínimo (2 ML) a cada línea chica por separado, mientras que la
cotización guardada aplica el piso por GRUPO DE TEXTIL (ver "Piso mínimo de
facturación" en core/precios.py) — dos productos de Felpa gruesa de 1 ML y
2,43 ML aparecían como $53.217 en el cotizador y $41.217 al abrirla.

Usa los catálogos reales (los mismos que usa la pantalla, no unos fijos):
lo que se compara son dos caminos de código contra el mismo catálogo, así
que el test vale con cualquier lista de precios. Si en esta máquina no hay
catálogo cargado, los tests se saltan.

Correr con:  python -m unittest tests.test_api_cotizacion -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.precios import ML_MINIMO_POR_PRODUCTO, costo_cotizacion
from core.repositorio import TEXTILES_ANCHOS, TEXTILES_VALORES
from ui.api_cotizacion import ApiCotizacion, _producto_a_interno


def _textil_de_prueba():
    """Un textil del catálogo real con ancho y valor por ML — sin valor no
    hay diferencia de plata que medir (todo daría 0)."""
    for nombre, ancho in TEXTILES_ANCHOS.items():
        if ancho and TEXTILES_VALORES.get(nombre, 0.0) > 0:
            return nombre
    return None


TEXTIL = _textil_de_prueba()


def _producto(ancho, alto, cantidad="1", textil=TEXTIL):
    return {
        "tipo": "estandar", "producto": "Estampado", "textil": textil,
        "estructuras": [], "terminaciones": [], "impresion": "Cara única",
        "ancho": ancho, "alto": alto, "cantidad": cantidad,
        "tema": "", "obs": "", "forzar": False, "calc": None,
    }


@unittest.skipIf(TEXTIL is None, "no hay catálogo de textiles en esta máquina")
class CalculoEnVivoDelCotizador(unittest.TestCase):

    def setUp(self):
        self.api = ApiCotizacion()

    def _neto_guardado(self, productos):
        """Lo que va a mostrar la cotización una vez guardada."""
        internos = [_producto_a_interno(p) for p in productos]
        return costo_cotizacion(internos, 0.0)["neto"]

    def _total_resumen(self, productos):
        """Lo que muestra la tabla de Resumen del cotizador."""
        calculos = self.api.calcular_productos(productos)
        return sum(c["total"] for c in calculos if c)

    def test_dos_productos_del_mismo_textil_no_pagan_el_minimo_cada_uno(self):
        # Juntos superan el piso, así que ninguno de los dos lo paga (el
        # caso real: 1 ML + 2,43 ML de Felpa gruesa).
        productos = [_producto("1", "1"), _producto("1,4", "2,4")]
        calculos = self.api.calcular_productos(productos)
        self.assertAlmostEqual(calculos[0]["ml"], 1.0)
        self.assertGreater(calculos[0]["ml"] + calculos[1]["ml"], ML_MINIMO_POR_PRODUCTO)

        valor_ml = TEXTILES_VALORES[TEXTIL]
        self.assertAlmostEqual(calculos[0]["costo_impresion"], 1.0 * valor_ml)
        self.assertAlmostEqual(self._total_resumen(productos), self._neto_guardado(productos))

    def test_un_producto_chico_solo_sigue_pagando_el_minimo(self):
        productos = [_producto("1", "1")]
        calculos = self.api.calcular_productos(productos)
        valor_ml = TEXTILES_VALORES[TEXTIL]
        self.assertAlmostEqual(calculos[0]["costo_impresion"],
                               ML_MINIMO_POR_PRODUCTO * valor_ml)
        self.assertAlmostEqual(self._total_resumen(productos), self._neto_guardado(productos))

    def test_el_minimo_del_grupo_se_reparte_entre_los_chicos(self):
        # 1 ML + 0,5 ML = 1,5 ML: el grupo entero queda bajo el piso, se
        # sube a 2 ML repartidos proporcional (no 2 ML para cada uno).
        productos = [_producto("1", "1"), _producto("1", "0,5")]
        calculos = self.api.calcular_productos(productos)
        valor_ml = TEXTILES_VALORES[TEXTIL]
        impresion = calculos[0]["costo_impresion"] + calculos[1]["costo_impresion"]
        self.assertAlmostEqual(impresion, ML_MINIMO_POR_PRODUCTO * valor_ml)
        self.assertGreater(calculos[0]["costo_impresion"], calculos[1]["costo_impresion"])
        self.assertAlmostEqual(self._total_resumen(productos), self._neto_guardado(productos))

    def test_un_producto_sin_medidas_no_desarma_el_calculo(self):
        # Los paneles recién agregados vienen vacíos: no aportan al grupo y
        # devuelven None, sin romper el cálculo de los demás (guardar sí
        # exige tenerlos todos completos, ver guardarCotizacion() en
        # nueva-cotizacion.html — por eso acá no se compara contra el neto
        # guardado, que no admite productos a medio cargar).
        completos = [_producto("1", "1"), _producto("1,4", "2,4")]
        productos = [completos[0], _producto("", ""), completos[1]]
        calculos = self.api.calcular_productos(productos)
        self.assertEqual(len(calculos), 3)
        self.assertIsNone(calculos[1])
        self.assertAlmostEqual(calculos[0]["ml"], 1.0)
        self.assertAlmostEqual(self._total_resumen(productos), self._neto_guardado(completos))

    def test_calcular_producto_suelto_sigue_aplicando_su_propio_piso(self):
        # La API de a uno (calcular_producto) no cambió: sin el ML del
        # grupo, cada línea es su propio grupo.
        p = _producto("1", "1")
        suelto = self.api.calcular_producto(p)
        valor_ml = TEXTILES_VALORES[TEXTIL]
        self.assertAlmostEqual(suelto["costo_impresion"], ML_MINIMO_POR_PRODUCTO * valor_ml)
        self.assertIsNone(self.api.calcular_producto(_producto("", "")))


if __name__ == "__main__":
    unittest.main()
