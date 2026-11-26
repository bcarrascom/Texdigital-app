"""
tests/test_presentar_cotizacion.py
Verifica core/presentar_cotizacion.py — puntualmente, que la Observación de
cada producto se muestre al imprimir la cotización (pedido de Bruno,
2026-09-16, tras notar que "Obs" no aparecía en ningún lado del documento —
a diferencia de core/presentar_op.py, que sí la mostraba desde antes).

Usa una carpeta temporal (mock de _ruta_base de core.repositorio_cotizaciones)
para que generar_html() no toque Dropbox/AppData reales.

Correr con:  python -m unittest tests.test_presentar_cotizacion -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_cotizaciones as repo_cot
from core.presentar_cotizacion import generar_html


def _cotizacion_estandar(numero, obs="", tema=""):
    return {
        "Cotizacion": numero,
        "Empresa": "Cliente X",
        "Fecha": "16/09/2026",
        "productos": [{
            "producto": "Bandera", "Tela": "Bistretch",
            "Estructuras": [], "Terminaciones": [], "Impresion": "Cara única",
            "Ancho": 1.0, "Alto": 1.0, "Cantidad": 1, "Tema": tema, "Obs": obs,
        }],
    }


def _cotizacion_backlight(numero, obs=""):
    return {
        "Cotizacion": numero,
        "Empresa": "Cliente Y",
        "Fecha": "16/09/2026",
        "productos": [{
            "Tela": "Popelina 155", "Caja": "Sin caja",
            "Ancho": 1.0, "Alto": 1.0, "Cantidad": 1, "Tema": "", "Obs": obs,
        }],
    }


class _ConRutaTemporal(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self._parche = mock.patch.object(repo_cot, "_ruta_base", lambda: base)
        self._parche.start()
        self.addCleanup(self._parche.stop)


class TestObservacionAlImprimir(_ConRutaTemporal):

    def test_muestra_la_observacion_de_un_producto_estandar(self):
        ruta = generar_html(_cotizacion_estandar(9001, obs="Ojales cada 50cm"))
        html = ruta.read_text(encoding="utf-8")
        self.assertIn('<div class="prod-obs">Observación: Ojales cada 50cm</div>', html)

    def test_muestra_la_observacion_de_un_producto_backlight(self):
        ruta = generar_html(_cotizacion_backlight(9002, obs="Cuidado con dobleces"))
        html = ruta.read_text(encoding="utf-8")
        self.assertIn('<div class="prod-obs">Observación: Cuidado con dobleces</div>', html)

    def test_sin_observacion_no_deja_el_div_vacio(self):
        # "prod-obs" sí aparece en el <style> del documento (la regla CSS,
        # ver recursos/plantilla_cotizacion.html) — lo que no debe aparecer
        # es el <div> en sí en el cuerpo, sin producto que lo pida.
        ruta = generar_html(_cotizacion_estandar(9003, obs=""))
        html = ruta.read_text(encoding="utf-8")
        self.assertNotIn('<div class="prod-obs">', html)

    def test_observacion_no_pisa_el_tema(self):
        ruta = generar_html(_cotizacion_estandar(9004, obs="Ojales cada 50cm", tema="Logo azul"))
        html = ruta.read_text(encoding="utf-8")
        self.assertIn("Tema: Logo azul", html)
        self.assertIn('<div class="prod-obs">Observación: Ojales cada 50cm</div>', html)


class TestBacklightConTerminaciones(_ConRutaTemporal):
    """Un backlight también puede llevar terminaciones (pedido de Bruno,
    2026-11-26): ya no es "solo tela impresa"."""

    def test_sin_terminaciones_sigue_diciendo_solo_tela_impresa(self):
        html = generar_html(_cotizacion_backlight(9010)).read_text(encoding="utf-8")
        self.assertIn("Solo tela impresa", html)

    def test_con_terminaciones_las_muestra_y_no_dice_solo_tela(self):
        cot = _cotizacion_backlight(9011)
        cot["productos"][0]["Terminaciones"] = ["Ojetillos"]
        html = generar_html(cot).read_text(encoding="utf-8")
        self.assertNotIn("Solo tela impresa", html)
        self.assertIn("<b>Terminaciones:</b> Ojetillos", html)

    def test_un_monto_a_mano_no_se_muestra_ni_cambia_el_detalle(self):
        cot = _cotizacion_backlight(9012)
        cot["productos"][0]["Terminaciones"] = ["$5.000"]
        html = generar_html(cot).read_text(encoding="utf-8")
        self.assertIn("Solo tela impresa", html)
        self.assertNotIn("$5.000</", html)


if __name__ == "__main__":
    unittest.main()
