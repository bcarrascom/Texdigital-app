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


if __name__ == "__main__":
    unittest.main()
