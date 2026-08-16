"""
tests/test_escala.py
Verifica core/escala.py — en particular que el piso de escala para texto
(F_FUENTE) sea más alto que el de geometría (F). Confirmado a mano: un
MacBook con pantalla Retina puede reportar una resolución LÓGICA chica
(ej. 1440×900 puntos en un 13"), aunque la pantalla sea de alta densidad
— antes de este fix, esa resolución lógica chica hacía caer F al piso
(0.60) y con eso el texto (FUENTE_LABEL 13pt en macOS) a 7-8pt, casi
ilegible, sin que la pantalla fuera chica de verdad.

Correr con:  python -m unittest tests.test_escala -v
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.escala as escala


def _pantalla_falsa(ancho, alto):
    fake = mock.MagicMock()
    fake.winfo_screenwidth.return_value = ancho
    fake.winfo_screenheight.return_value = alto
    return fake


class TestCalcular(unittest.TestCase):

    def test_pantalla_grande_no_escala(self):
        with mock.patch.object(escala._tk, "Tk", return_value=_pantalla_falsa(3840, 2160)):
            self.assertEqual(escala._calcular(), 1.0)

    def test_pantalla_muy_chica_toca_el_piso(self):
        with mock.patch.object(escala._tk, "Tk", return_value=_pantalla_falsa(1024, 640)):
            self.assertEqual(escala._calcular(), 0.60)

    def test_resolucion_logica_compacta_de_mac_retina_escala_por_debajo_de_1(self):
        # MacBook 13" Retina: 1440x900 puntos lógicos — de verdad una
        # pantalla de alta densidad, pero winfo_screenwidth/height
        # devuelve la resolución lógica, no los píxeles físicos.
        with mock.patch.object(escala._tk, "Tk", return_value=_pantalla_falsa(1440, 900)):
            f = escala._calcular()
        self.assertLess(f, 1.0)


class TestPisoDeFuenteMasAltoQueGeometria(unittest.TestCase):
    # F_FUENTE se calcula una sola vez al importar el módulo — para
    # probar pt()/px() con distintos factores, se parchea F/F_FUENTE
    # directamente en vez de re-simular la pantalla.

    def test_f_fuente_nunca_es_menor_que_085(self):
        self.assertGreaterEqual(escala.F_FUENTE, 0.85)

    def test_f_fuente_es_al_menos_tan_grande_como_f(self):
        self.assertGreaterEqual(escala.F_FUENTE, escala.F)

    def test_pt_con_factor_de_geometria_bajo_no_produce_texto_diminuto(self):
        # Caso real: Mac con resolución lógica chica, F cae al piso 0.60.
        # Sin el piso de fuente, un FUENTE_LABEL de 13pt (macOS) caía a
        # 13*0.60=7.8 -> 8pt. Con el piso, no debería bajar de 13*0.85=11.05 -> 11pt.
        with mock.patch.object(escala, "F_FUENTE", 0.85):
            self.assertEqual(escala.pt(13), 11)
            self.assertGreaterEqual(escala.pt(13), 11)

    def test_px_si_seguia_pudiendo_bajar_hasta_el_piso_de_geometria(self):
        # La geometría de ventanas/canvas debe seguir pudiendo achicarse
        # tanto como haga falta para entrar en una pantalla chica de verdad
        # — el piso más alto es solo para pt(), no para px().
        with mock.patch.object(escala, "F", 0.60):
            self.assertEqual(escala.px(100), 60)

    def test_pt_nunca_baja_del_piso_absoluto_de_7(self):
        with mock.patch.object(escala, "F_FUENTE", 0.85):
            self.assertGreaterEqual(escala.pt(1), 7)


if __name__ == "__main__":
    unittest.main()
