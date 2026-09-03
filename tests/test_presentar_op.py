"""
tests/test_presentar_op.py
Verifica core/presentar_op.py — en particular las columnas nuevas "Corte
ancho"/"Corte alto" para OPs backlight (v1.2.7): el margen de costura que
se suma a Ancho/Alto depende de TerminacionesCaja (mismo campo único por
cotización/OP que ya existía para el Excel, ver ui/formulario_cliente.py),
y las columnas solo deben aparecer en OPs backlight — las de productos
normales quedan exactamente igual que antes.

Usa una carpeta temporal (mock de _ruta_base de core.repositorio_ops) para
que generar_html() no toque Dropbox/AppData reales.

Correr con:  python -m unittest tests.test_presentar_op -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_ops as repo_ops
from core.presentar_op import _corte


def _op_backlight(numero, terminaciones_caja="CAJA TERMINADA", ancho=1.48, alto=2.25, cantidad=1):
    return {
        "Cotizacion": numero,
        "Empresa": "Cliente X",
        "Fecha_ingreso": "10/08/2026",
        "Fecha_entrega": "20/08/2026",
        "TerminacionesCaja": terminaciones_caja,
        "productos": [{
            "Tela": "Popelina 155", "Caja": "Sin caja",
            "Ancho": ancho, "Alto": alto, "Cantidad": cantidad,
            "Tema": "", "Obs": "",
        }],
    }


def _op_normal(numero):
    return {
        "Cotizacion": numero,
        "Empresa": "Cliente Y",
        "Fecha_ingreso": "10/08/2026",
        "Fecha_entrega": "20/08/2026",
        "productos": [{
            "producto": "Bandera", "Tela": "Bistretch",
            "Estructuras": [], "Terminaciones": [], "Impresion": "Cara única",
            "Ancho": 1.0, "Alto": 1.0, "Cantidad": 1, "Tema": "", "Obs": "",
        }],
    }


class TestCorte(unittest.TestCase):

    def test_caja_terminada_suma_13mm(self):
        self.assertAlmostEqual(_corte(1.48, "CAJA TERMINADA"), 1.493)

    def test_area_visual_suma_23mm(self):
        self.assertAlmostEqual(_corte(1.48, "AREA VISUAL"), 1.503)

    def test_valor_desconocido_se_trata_como_area_visual(self):
        # Cualquier valor que no sea exactamente "CAJA TERMINADA" (dato
        # viejo/corrupto, o el default del formulario si cambiara) cae al
        # margen más grande — más seguro que asumir el más chico.
        self.assertAlmostEqual(_corte(1.48, ""), 1.503)
        self.assertAlmostEqual(_corte(1.48, "algo raro"), 1.503)


class TestGenerarHtml(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._parche = mock.patch.object(repo_ops, "_ruta_base", lambda: Path(self._tmp.name))
        self._parche.start()
        self.addCleanup(self._parche.stop)

    def test_backlight_caja_terminada_muestra_columnas_de_corte(self):
        from core.presentar_op import generar_html
        ruta = generar_html(_op_backlight(9001, "CAJA TERMINADA", ancho=1.48, alto=2.25))
        html = ruta.read_text(encoding="utf-8")
        self.assertIn("Corte ancho", html)
        self.assertIn("Corte alto", html)
        self.assertIn("1,493 m", html)  # 1.48 + 0.013
        self.assertIn("2,263 m", html)  # 2.25 + 0.013

    def test_backlight_area_visual_usa_el_margen_mas_grande(self):
        from core.presentar_op import generar_html
        ruta = generar_html(_op_backlight(9002, "AREA VISUAL", ancho=1.48, alto=2.25))
        html = ruta.read_text(encoding="utf-8")
        self.assertIn("1,503 m", html)  # 1.48 + 0.023
        self.assertIn("2,273 m", html)  # 2.25 + 0.023

    def test_backlight_sin_terminaciones_caja_guardado_usa_default(self):
        # OP vieja, guardada antes de este campo existir — no debe reventar,
        # y debe comportarse igual que "CAJA TERMINADA" (el default del
        # formulario, ver ui/formulario_cliente.py).
        from core.presentar_op import generar_html
        op = _op_backlight(9003, ancho=1.48, alto=2.25)
        del op["TerminacionesCaja"]
        ruta = generar_html(op)
        html = ruta.read_text(encoding="utf-8")
        self.assertIn("1,493 m", html)

    def test_no_backlight_no_muestra_columnas_de_corte(self):
        from core.presentar_op import generar_html
        ruta = generar_html(_op_normal(9004))
        html = ruta.read_text(encoding="utf-8")
        self.assertNotIn("Corte ancho", html)
        self.assertNotIn("Corte alto", html)

    def test_no_backlight_fila_totales_tiene_5_celdas(self):
        from core.presentar_op import generar_html
        ruta = generar_html(_op_normal(9005))
        html = ruta.read_text(encoding="utf-8")
        fila_totales = html[html.index('class="fila-totales"'):]
        fila_totales = fila_totales[:fila_totales.index("</tr>")]
        self.assertEqual(fila_totales.count("<td"), 5)

    def test_backlight_fila_totales_tiene_7_celdas(self):
        from core.presentar_op import generar_html
        ruta = generar_html(_op_backlight(9006))
        html = ruta.read_text(encoding="utf-8")
        fila_totales = html[html.index('class="fila-totales"'):]
        fila_totales = fila_totales[:fila_totales.index("</tr>")]
        self.assertEqual(fila_totales.count("<td"), 7)

    def test_nombre_del_trabajo_aparece_entre_el_header_y_los_datos_del_cliente(self):
        from core.presentar_op import generar_html
        op = _op_normal(9007)
        op["Nombre"] = "Banderas plaza de armas"
        ruta = generar_html(op)
        html = ruta.read_text(encoding="utf-8")
        i_header = html.index("</header>")
        i_trabajo = html.index("Banderas plaza de armas")
        i_datos = html.index('class="datos"')
        self.assertTrue(i_header < i_trabajo < i_datos)

    def test_sin_nombre_no_deja_un_bloque_vacio(self):
        from core.presentar_op import generar_html
        ruta = generar_html(_op_normal(9008))  # _op_normal no trae "Nombre"
        html = ruta.read_text(encoding="utf-8")
        self.assertNotIn('class="trabajo"', html)

    def test_obs_del_producto_aparece_bajo_el_tema(self):
        from core.presentar_op import generar_html
        op = _op_normal(9009)
        op["productos"][0]["Tema"] = "Logo azul"
        op["productos"][0]["Obs"] = "Ojales cada 50cm"
        ruta = generar_html(op)
        html = ruta.read_text(encoding="utf-8")
        i_tema = html.index("Logo azul")
        i_obs = html.index('class="prod-obs"')
        self.assertTrue(i_tema < i_obs)  # la obs va DEBAJO del tema, en la misma celda
        self.assertIn("Observación: Ojales cada 50cm", html)

    def test_sin_obs_no_deja_el_bloque_vacio(self):
        from core.presentar_op import generar_html
        ruta = generar_html(_op_normal(9010))  # _op_normal trae "Obs": ""
        html = ruta.read_text(encoding="utf-8")
        self.assertNotIn('class="prod-obs"', html)


if __name__ == "__main__":
    unittest.main()
