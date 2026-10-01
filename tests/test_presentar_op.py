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
from core.presentar_op import _corte, _excedente_cm, _terminaciones_caja_de


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


class TestExcedente(unittest.TestCase):
    """_excedente_cm — rangos por m² del producto (Ancho×Alto, sin
    Cantidad), dados por Bruno (2026-09-23). Los bordes de cada rango son
    inclusivos hacia ABAJO (x ≤ N cae en el rango de N, no en el
    siguiente)."""

    def test_hasta_1m2_es_1cm(self):
        self.assertEqual(_excedente_cm(0.5), 1.0)
        self.assertEqual(_excedente_cm(1.0), 1.0)

    def test_entre_1_y_2m2_es_1_5cm(self):
        self.assertEqual(_excedente_cm(1.01), 1.5)
        self.assertEqual(_excedente_cm(2.0), 1.5)

    def test_entre_2_y_5m2_es_2cm(self):
        self.assertEqual(_excedente_cm(2.01), 2.0)
        self.assertEqual(_excedente_cm(5.0), 2.0)

    def test_mas_de_5m2_es_2_5cm(self):
        self.assertEqual(_excedente_cm(5.01), 2.5)
        self.assertEqual(_excedente_cm(20.0), 2.5)


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

    def test_backlight_muestra_excedente_propio_por_producto(self):
        # Un producto por rango (ver TestExcedente): 0,8×1 = 0,8 m² -> 1cm;
        # 1×1,5 = 1,5 m² -> 1,5cm; 1×3 = 3 m² -> 2cm; 2×3 = 6 m² -> 2,5cm.
        from core.presentar_op import generar_html
        op = _op_backlight(9008)
        op["productos"] = [
            {"Tela": "Popelina 155", "Caja": "Sin caja", "Ancho": 0.8, "Alto": 1.0,
             "Cantidad": 1, "Tema": "Uno", "Obs": ""},
            {"Tela": "Popelina 155", "Caja": "Sin caja", "Ancho": 1.0, "Alto": 1.5,
             "Cantidad": 1, "Tema": "Dos", "Obs": ""},
            {"Tela": "Popelina 155", "Caja": "Sin caja", "Ancho": 1.0, "Alto": 3.0,
             "Cantidad": 1, "Tema": "Tres", "Obs": ""},
            {"Tela": "Popelina 155", "Caja": "Sin caja", "Ancho": 2.0, "Alto": 3.0,
             "Cantidad": 1, "Tema": "Cuatro", "Obs": ""},
        ]
        ruta = generar_html(op)
        html = ruta.read_text(encoding="utf-8")
        self.assertIn("Excedente", html)
        self.assertIn("1 cm", html)
        self.assertIn("1,5 cm", html)
        self.assertIn("2 cm", html)
        self.assertIn("2,5 cm", html)

    def test_nombre_del_trabajo_aparece_entre_el_header_y_los_datos_del_cliente(self):
        from core.presentar_op import generar_html
        op = _op_normal(9007)
        op["Nombre"] = "Banderas plaza de armas"
        ruta = generar_html(op)
        html = ruta.read_text(encoding="utf-8")
        # Se busca en el CUERPO: el nombre del trabajo también sale en el
        # <title> del <head> (es el nombre con el que el navegador guarda
        # el PDF, ver core/titulo_impresion.py), y esa primera aparición
        # taparía la del bloque que se quiere ubicar acá.
        cuerpo = html[html.index("</head>"):]
        i_header = cuerpo.index("</header>")
        i_trabajo = cuerpo.index("Banderas plaza de armas")
        i_datos = cuerpo.index('class="datos"')
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


# ══════════════════════════════════════════════════════════════════════════════
# "Área visual" de verdad suma 2,3 cm (2026-10-01). El switch existía en la
# pantalla desde la UI HTML, pero el campo se quedaba en el frontend: no lo
# mapeaba _producto_a_interno, no lo guardaba mapear_producto, y presentar_op
# caía siempre al default. Reporte de planta: "sigue sumando 1.3 cms como si
# fuera medida de caja". Ahora el valor es POR PRODUCTO y viaja la cadena
# completa — estos tests cubren cada eslabón, para que no se vuelva a cortar.
# ══════════════════════════════════════════════════════════════════════════════

def _producto_backlight_json(terminaciones_caja=None, ancho=1.48, alto=2.25, cantidad=1):
    p = {
        "Tela": "Popelina 155", "Caja": "Sin caja",
        "Ancho": ancho, "Alto": alto, "Cantidad": cantidad, "Tema": "", "Obs": "",
    }
    if terminaciones_caja is not None:
        p["TerminacionesCaja"] = terminaciones_caja
    return p


class TestTerminacionesCajaPorProducto(unittest.TestCase):
    """El valor del PRODUCTO manda; el de la OP completa queda como respaldo
    para el esquema viejo (un solo valor para todos los productos)."""

    def test_el_del_producto_le_gana_al_de_la_op(self):
        p = _producto_backlight_json("AREA VISUAL")
        self.assertEqual(_terminaciones_caja_de(p, "CAJA TERMINADA"), "AREA VISUAL")

    def test_sin_valor_en_el_producto_usa_el_de_la_op(self):
        p = _producto_backlight_json()
        self.assertEqual(_terminaciones_caja_de(p, "AREA VISUAL"), "AREA VISUAL")

    def test_sin_valor_en_ninguno_cae_a_caja_terminada(self):
        # Una OP de antes de que el campo existiera: se reimprime con el mismo
        # margen con el que se imprimió la primera vez.
        self.assertEqual(_terminaciones_caja_de(_producto_backlight_json(), ""), "CAJA TERMINADA")


class _ConCarpetaTemporal(unittest.TestCase):
    """Mismo mock de _ruta_base que TestGenerarHtml, para que generar_html() no
    escriba en Dropbox/AppData reales."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._parche = mock.patch.object(repo_ops, "_ruta_base", lambda: Path(self._tmp.name))
        self._parche.start()
        self.addCleanup(self._parche.stop)


class TestMargenEnElDocumento(_ConCarpetaTemporal):
    """Lo que el taller ve impreso: la medida de corte, el margen que se le
    sumó en gris bajo las medidas, y qué se midió (caja terminada / área
    visual) en la línea del producto."""

    def _html(self, op):
        from core.presentar_op import generar_html
        return Path(generar_html(op)).read_text(encoding="utf-8")

    def test_area_visual_por_producto_suma_23cm(self):
        op = _op_backlight(9101)
        del op["TerminacionesCaja"]
        op["productos"] = [_producto_backlight_json("AREA VISUAL", ancho=1.48, alto=2.25)]
        html = self._html(op)
        self.assertIn("1,503", html)   # 1,48 + 0,023
        self.assertIn("2,273", html)   # 2,25 + 0,023
        self.assertNotIn("1,493", html)  # el margen de caja terminada NO aparece

    def test_caja_terminada_sigue_sumando_13cm(self):
        op = _op_backlight(9102)
        del op["TerminacionesCaja"]
        op["productos"] = [_producto_backlight_json("CAJA TERMINADA", ancho=1.48, alto=2.25)]
        html = self._html(op)
        self.assertIn("1,493", html)
        self.assertIn("2,263", html)

    def test_el_margen_se_escribe_bajo_las_medidas(self):
        op = _op_backlight(9103)
        del op["TerminacionesCaja"]
        op["productos"] = [_producto_backlight_json("AREA VISUAL")]
        html = self._html(op)
        self.assertIn("(+2,3 cms)", html)
        # En gris y chico: la misma clase que ya usa el excedente.
        self.assertIn('<div class="prod-obs">(+2,3 cms)</div>', html)
        # Sin la palabra "Corte": las columnas de al lado ya lo dicen.
        self.assertNotIn("Corte (+", html)

    def test_el_margen_de_caja_terminada_tambien_se_escribe(self):
        # Se muestra siempre, con los dos valores posibles: así el que corta
        # sabe de dónde salen las medidas sin acordarse de la fórmula.
        op = _op_backlight(9104)
        del op["TerminacionesCaja"]
        op["productos"] = [_producto_backlight_json("CAJA TERMINADA")]
        self.assertIn("(+1,3 cms)", self._html(op))

    def test_el_producto_queda_marcado_como_area_visual(self):
        op = _op_backlight(9105)
        del op["TerminacionesCaja"]
        op["productos"] = [_producto_backlight_json("AREA VISUAL")]
        self.assertIn("Área visual", self._html(op))

    def test_el_producto_queda_marcado_como_caja_terminada(self):
        op = _op_backlight(9106)
        del op["TerminacionesCaja"]
        op["productos"] = [_producto_backlight_json("CAJA TERMINADA")]
        self.assertIn("Caja terminada", self._html(op))

    def test_una_op_puede_mezclar_los_dos(self):
        # El motivo de que el campo sea por producto y no por OP.
        op = _op_backlight(9107)
        del op["TerminacionesCaja"]
        op["productos"] = [
            _producto_backlight_json("CAJA TERMINADA", ancho=1.48, alto=2.25),
            _producto_backlight_json("AREA VISUAL", ancho=1.48, alto=2.25),
        ]
        html = self._html(op)
        self.assertIn("1,493", html)            # el de caja terminada
        self.assertIn("1,503", html)            # el de área visual
        self.assertIn("(+1,3 cms)", html)
        self.assertIn("(+2,3 cms)", html)


class TestTerminacionesCajaViajaEnLaCadena(unittest.TestCase):
    """Los eslabones donde el campo se perdía: frontend -> interno -> JSON
    guardado -> interno. Si cualquiera de los tres se rompe, elegir "Área
    visual" deja de hacer efecto sin que nada falle a la vista."""

    def test_del_frontend_al_esquema_interno(self):
        from ui.api_cotizacion import _producto_a_interno
        interno = _producto_a_interno({
            "tipo": "backlight", "tela": "Popelina 155", "perfil": "Sin caja",
            "ancho": "1.48", "alto": "2.25", "cantidad": "1",
            "terminaciones_caja": "AREA VISUAL",
        })
        self.assertEqual(interno["terminaciones_caja"], "AREA VISUAL")

    def test_el_frontend_sin_el_campo_cae_a_caja_terminada(self):
        from ui.api_cotizacion import _producto_a_interno
        interno = _producto_a_interno({
            "tipo": "backlight", "tela": "Popelina 155", "perfil": "Sin caja",
            "ancho": "1.48", "alto": "2.25", "cantidad": "1",
        })
        self.assertEqual(interno["terminaciones_caja"], "CAJA TERMINADA")

    def test_ida_y_vuelta_por_el_json_guardado(self):
        from core.repositorio_cotizaciones import mapear_producto, producto_desde_json
        interno = {
            "tela": "Popelina 155", "caja": "Sin caja", "ancho": 1.48, "alto": 2.25,
            "cantidad": 1, "tema": "", "obs": "", "terminaciones_caja": "AREA VISUAL",
        }
        guardado = mapear_producto(interno)
        self.assertEqual(guardado["TerminacionesCaja"], "AREA VISUAL")
        self.assertEqual(producto_desde_json(guardado)["terminaciones_caja"], "AREA VISUAL")

    def test_un_producto_guardado_viejo_se_lee_como_caja_terminada(self):
        from core.repositorio_cotizaciones import producto_desde_json
        viejo = {"Tela": "Popelina 155", "Caja": "Sin caja", "Ancho": 1.48,
                 "Alto": 2.25, "Cantidad": 1, "Tema": "", "Obs": ""}
        self.assertEqual(producto_desde_json(viejo)["terminaciones_caja"], "CAJA TERMINADA")

    def test_el_switch_vuelve_al_frontend_al_editar(self):
        # Reabrir una cotización guardada tiene que dejar el switch donde estaba.
        from ui.api_cotizacion import _interno_a_frontend
        frontend = _interno_a_frontend({
            "tela": "Popelina 155", "caja": "Sin caja", "ancho": 1.48, "alto": 2.25,
            "cantidad": 1, "terminaciones_caja": "AREA VISUAL",
        })
        self.assertEqual(frontend["terminaciones_caja"], "AREA VISUAL")


if __name__ == "__main__":
    unittest.main()
