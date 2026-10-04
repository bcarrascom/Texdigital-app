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
from core.repositorio_ops import (
    actualizar_op_inser, cargar_op, op_inser_marcada,
)
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

    def test_caja_terminada_suma_15mm(self):
        self.assertAlmostEqual(_corte(1.48, "CAJA TERMINADA"), 1.495)

    def test_area_visual_suma_25mm(self):
        self.assertAlmostEqual(_corte(1.48, "AREA VISUAL"), 1.505)

    def test_valor_desconocido_se_trata_como_area_visual(self):
        # Cualquier valor que no sea exactamente "CAJA TERMINADA" (dato
        # viejo/corrupto, o el default del formulario si cambiara) cae al
        # margen más grande — más seguro que asumir el más chico.
        self.assertAlmostEqual(_corte(1.48, ""), 1.505)
        self.assertAlmostEqual(_corte(1.48, "algo raro"), 1.505)


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
        self.assertIn("1,495 m", html)  # 1.48 + 0.015
        self.assertIn("2,265 m", html)  # 2.25 + 0.015

    def test_backlight_area_visual_usa_el_margen_mas_grande(self):
        from core.presentar_op import generar_html
        ruta = generar_html(_op_backlight(9002, "AREA VISUAL", ancho=1.48, alto=2.25))
        html = ruta.read_text(encoding="utf-8")
        self.assertIn("1,505 m", html)  # 1.48 + 0.025
        self.assertIn("2,275 m", html)  # 2.25 + 0.025

    def test_backlight_sin_terminaciones_caja_guardado_usa_default(self):
        # OP vieja, guardada antes de este campo existir — no debe reventar,
        # y debe comportarse igual que "CAJA TERMINADA" (el default del
        # formulario, ver ui/formulario_cliente.py).
        from core.presentar_op import generar_html
        op = _op_backlight(9003, ancho=1.48, alto=2.25)
        del op["TerminacionesCaja"]
        ruta = generar_html(op)
        html = ruta.read_text(encoding="utf-8")
        self.assertIn("1,495 m", html)

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
# "Área visual" de verdad suma su margen (2026-10-01; desde esa fecha 2,5 cm). El switch existía en la
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
        self.assertIn("1,505", html)   # 1,48 + 0,025
        self.assertIn("2,275", html)   # 2,25 + 0,025
        self.assertNotIn("1,495", html)  # el margen de caja terminada NO aparece

    def test_caja_terminada_sigue_sumando_13cm(self):
        op = _op_backlight(9102)
        del op["TerminacionesCaja"]
        op["productos"] = [_producto_backlight_json("CAJA TERMINADA", ancho=1.48, alto=2.25)]
        html = self._html(op)
        self.assertIn("1,495", html)
        self.assertIn("2,265", html)

    def test_el_margen_se_escribe_bajo_las_medidas(self):
        op = _op_backlight(9103)
        del op["TerminacionesCaja"]
        op["productos"] = [_producto_backlight_json("AREA VISUAL")]
        html = self._html(op)
        self.assertIn("(+2,5 cms)", html)
        # En gris y chico: la misma clase que ya usa el excedente.
        self.assertIn('<div class="prod-obs">(+2,5 cms)</div>', html)
        # Sin la palabra "Corte": las columnas de al lado ya lo dicen.
        self.assertNotIn("Corte (+", html)

    def test_el_margen_de_caja_terminada_tambien_se_escribe(self):
        # Se muestra siempre, con los dos valores posibles: así el que corta
        # sabe de dónde salen las medidas sin acordarse de la fórmula.
        op = _op_backlight(9104)
        del op["TerminacionesCaja"]
        op["productos"] = [_producto_backlight_json("CAJA TERMINADA")]
        self.assertIn("(+1,5 cms)", self._html(op))

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
        self.assertIn("1,495", html)            # el de caja terminada
        self.assertIn("1,505", html)            # el de área visual
        self.assertIn("(+1,5 cms)", html)
        self.assertIn("(+2,5 cms)", html)


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


# ══════════════════════════════════════════════════════════════════════════════
# "OP Inser" dejó de ser un campo de texto (2026-10-01). El N° de ingreso en el
# proveedor de impresión Inser no se conoce cuando se arma la OP: se escribe con
# lápiz sobre la hoja ya impresa. Ahora es un booleano, y lo que se imprime es un
# recuadro VACÍO para escribir encima.
# ══════════════════════════════════════════════════════════════════════════════

class TestOpInserMarcada(unittest.TestCase):
    """La lectura del dato, incluida la migración del texto viejo."""

    def test_booleano_true(self):
        self.assertTrue(op_inser_marcada({"OpInser": True}))

    def test_booleano_false(self):
        self.assertFalse(op_inser_marcada({"OpInser": False}))

    def test_op_sin_el_campo_no_esta_marcada(self):
        self.assertFalse(op_inser_marcada({"Cotizacion": 1}))

    def test_texto_viejo_con_numero_cuenta_como_marcada(self):
        # Si alguien se tomó el trabajo de cargar el número, esa OP pasaba por
        # Inser: al reimprimirla tiene que seguir llevando el recuadro.
        self.assertTrue(op_inser_marcada({"OpIngresoInser": "A-4471"}))

    def test_texto_viejo_vacio_no_cuenta(self):
        self.assertFalse(op_inser_marcada({"OpIngresoInser": ""}))
        self.assertFalse(op_inser_marcada({"OpIngresoInser": "   "}))

    def test_el_booleano_le_gana_al_texto_viejo(self):
        # Desmarcar a mano una OP migrada tiene que quedar desmarcada, aunque el
        # texto viejo siga en el archivo.
        self.assertFalse(op_inser_marcada({"OpInser": False, "OpIngresoInser": "A-4471"}))


class TestActualizarOpInser(_ConCarpetaTemporal):
    """Marcar/desmarcar escribe en el JSON, en cualquiera de las carpetas donde
    pueda estar la OP."""

    def _guardar(self, op):
        from core.repositorio_ops import guardar_op
        guardar_op(op)

    def test_marcar_graba_true(self):
        self._guardar(_op_backlight(9201))
        self.assertTrue(actualizar_op_inser(9201, True))
        self.assertTrue(op_inser_marcada(cargar_op(9201)))

    def test_desmarcar_graba_false(self):
        self._guardar(_op_backlight(9202))
        actualizar_op_inser(9202, True)
        actualizar_op_inser(9202, False)
        self.assertFalse(op_inser_marcada(cargar_op(9202)))

    def test_desmarcar_una_op_migrada_queda_desmarcada(self):
        op = _op_backlight(9203)
        op["OpIngresoInser"] = "A-4471"
        self._guardar(op)
        self.assertTrue(op_inser_marcada(cargar_op(9203)))
        actualizar_op_inser(9203, False)
        self.assertFalse(op_inser_marcada(cargar_op(9203)))

    def test_no_borra_el_texto_viejo(self):
        # Es un dato que alguien tipeó: se deja de mostrar, no se destruye.
        op = _op_backlight(9204)
        op["OpIngresoInser"] = "A-4471"
        self._guardar(op)
        actualizar_op_inser(9204, False)
        self.assertEqual(cargar_op(9204)["OpIngresoInser"], "A-4471")

    def test_op_inexistente_devuelve_false(self):
        self.assertFalse(actualizar_op_inser(99999, True))


class TestRecuadroEnElDocumento(_ConCarpetaTemporal):
    """Lo que sale impreso: un recuadro VACÍO rotulado "OP Inser", solo si la OP
    está marcada."""

    def _html(self, op):
        from core.presentar_op import generar_html
        return Path(generar_html(op)).read_text(encoding="utf-8")

    def _bloque_datos(self, op):
        """Solo el <div class="datos"> renderizado. Buscar en el documento
        completo da falsos positivos: la plantilla trae el CSS de .inser-caja
        siempre, esté o no el recuadro."""
        html = self._html(op)
        ini = html.index('<div class="datos">')
        return html[ini:html.index("</table>", ini)]

    def test_marcada_imprime_el_recuadro(self):
        op = _op_backlight(9211)
        op["OpInser"] = True
        datos = self._bloque_datos(op)
        self.assertIn("OP Inser", datos)
        self.assertIn('<div class="inser-caja"></div>', datos)

    def test_el_recuadro_sale_vacio(self):
        # El punto del cambio: no se imprime ningún número, se reserva el lugar.
        op = _op_backlight(9212)
        op["OpInser"] = True
        datos = self._bloque_datos(op)
        # El recuadro se abre y se cierra sin nada en medio.
        self.assertIn('<div class="inser-caja"></div>', datos)

    def test_sin_marcar_no_imprime_nada(self):
        op = _op_backlight(9213)
        datos = self._bloque_datos(op)
        self.assertNotIn("inser-caja", datos)
        self.assertNotIn("OP Inser", datos)

    def test_una_op_vieja_con_numero_imprime_el_recuadro_vacio(self):
        op = _op_backlight(9214)
        op["OpIngresoInser"] = "A-4471"
        html = self._html(op)
        self.assertIn('<div class="inser-caja"></div>', self._bloque_datos(op))
        # El número viejo ya no se imprime: ahora el recuadro es para escribirlo
        # a mano, y dos números (uno impreso y uno a lápiz) se contradicen.
        self.assertNotIn("A-4471", html)


# ══════════════════════════════════════════════════════════════════════════════
# El switch de terminaciones de caja solo aplica cuando la caja NO es nuestra
# (decisión de Bruno, 2026-10-01). Con perfil propio el ancho×alto cotizado ES la
# caja —de ahí sale el cálculo del perfil— así que no hay nada que preguntar y el
# margen queda fijo en caja terminada. En la pantalla el switch se muestra solo
# sin perfil (ver aplicarTipo en nueva-cotizacion.html); acá se cubre que el dato
# GUARDADO respete lo mismo, que es lo que después corta el taller.
# ══════════════════════════════════════════════════════════════════════════════

class TestTerminacionesCajaSegunPerfil(unittest.TestCase):

    def test_con_perfil_se_fuerza_caja_terminada(self):
        from ui.api_cotizacion import _terminaciones_caja
        self.assertEqual(_terminaciones_caja("PERFIL 80 MM", "AREA VISUAL"), "CAJA TERMINADA")

    def test_sin_perfil_respeta_lo_elegido(self):
        from ui.api_cotizacion import _terminaciones_caja, SIN_CAJA
        self.assertEqual(_terminaciones_caja(SIN_CAJA, "AREA VISUAL"), "AREA VISUAL")
        self.assertEqual(_terminaciones_caja(SIN_CAJA, "CAJA TERMINADA"), "CAJA TERMINADA")

    def test_sin_perfil_sin_elegir_cae_al_default(self):
        from ui.api_cotizacion import _terminaciones_caja, SIN_CAJA
        self.assertEqual(_terminaciones_caja(SIN_CAJA, None), "CAJA TERMINADA")
        self.assertEqual(_terminaciones_caja(SIN_CAJA, ""), "CAJA TERMINADA")

    def test_valor_desconocido_cae_al_default(self):
        from ui.api_cotizacion import _terminaciones_caja, SIN_CAJA
        self.assertEqual(_terminaciones_caja(SIN_CAJA, "cualquier cosa"), "CAJA TERMINADA")

    def test_producto_con_perfil_se_guarda_como_caja_terminada(self):
        # El caso que el forzado del backend protege: un estado viejo del
        # frontend (o un borrador retomado) que trae "AREA VISUAL" junto con un
        # perfil no debe poder meter el margen grande.
        from ui.api_cotizacion import _producto_a_interno
        interno = _producto_a_interno({
            "tipo": "backlight", "tela": "Popelina 155", "perfil": "PERFIL 80 MM",
            "luces_1": "M12", "luces_2": "sin luces",
            "ancho": "1.48", "alto": "2.25", "cantidad": "1",
            "terminaciones_caja": "AREA VISUAL",
        })
        self.assertEqual(interno["terminaciones_caja"], "CAJA TERMINADA")

    def test_producto_sin_perfil_conserva_area_visual(self):
        from ui.api_cotizacion import _producto_a_interno
        interno = _producto_a_interno({
            "tipo": "backlight", "tela": "Popelina 155", "perfil": "Sin caja",
            "ancho": "1.48", "alto": "2.25", "cantidad": "1",
            "terminaciones_caja": "AREA VISUAL",
        })
        self.assertEqual(interno["terminaciones_caja"], "AREA VISUAL")


class TestBloqueMaterialesDeInventario(_ConCarpetaTemporal):
    """La OP lista los materiales no textiles que el trabajo va a gastar (pedido
    de Bruno, 2026-10-01). Antes no aparecían para NINGÚN tipo de producto, ni
    backlight ni estándar, aunque sí se descontaban del stock al aprobar."""

    def setUp(self):
        super().setUp()
        # Inventario en carpeta temporal: el bloque se arma desde ahí.
        import core.repositorio_materiales as repo_mat
        self._repo_mat = repo_mat
        self._tmp_inv = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_inv.cleanup)
        parche = mock.patch.object(repo_mat, "_ruta_base",
                                   lambda: Path(self._tmp_inv.name))
        parche.start()
        self.addCleanup(parche.stop)

    def _silicona(self):
        m = self._repo_mat.ingresar_material("Silicona", 500, tipo="metro", costo_unitario=900)
        self._repo_mat.editar_material(
            m["id"], "Silicona", "metro", valor=2600,
            tipo_consumo="perimetro", consumo_parametros={"n": 1},
            productos_asociados=[self._repo_mat.PRODUCTO_BACKLIGHT])

    def _materiales(self, op):
        from core.presentar_op import generar_html
        html = Path(generar_html(op)).read_text(encoding="utf-8")
        if '<div class="materiales"' not in html:
            return ""
        sec = html[html.index('<div class="materiales"'):]
        return sec[:sec.index("<button")]

    def test_un_backlight_lista_la_silicona_con_su_cantidad(self):
        self._silicona()
        op = _op_backlight(9401, ancho=1.0, alto=2.0, cantidad=2)
        sec = self._materiales(op)
        self.assertIn("<h3>Materiales</h3>", sec)
        self.assertIn("Silicona", sec)
        self.assertIn("12 ML", sec)   # 2 x (1 + 2) = 6 m por pieza x 2

    def test_sin_materiales_asociados_no_hay_bloque(self):
        op = _op_backlight(9402, ancho=1.0, alto=2.0, cantidad=2)
        self.assertNotIn("<h3>Materiales</h3>", self._materiales(op))

    def test_un_producto_estandar_tambien_lo_lista(self):
        m = self._repo_mat.ingresar_material("Ojalillo", 5000, costo_unitario=40)
        self._repo_mat.editar_material(
            m["id"], "Ojalillo", "unidad", valor=120,
            tipo_consumo="fijo_por_producto", consumo_parametros={"n": 6},
            productos_asociados=["Bandera"])
        op = _op_normal(9403)
        op["productos"][0]["Cantidad"] = 10
        sec = self._materiales(op)
        self.assertIn("<h3>Materiales</h3>", sec)
        self.assertIn("60 un.", sec)   # 6 por pieza x 10

    def test_la_unidad_sale_del_tipo_del_material(self):
        self._silicona()
        self.assertIn("ML", self._materiales(_op_backlight(9404, ancho=1.0, alto=2.0)))


class TestCajaNuestraFuerzaElMargen(unittest.TestCase):
    """Un producto con caja nuestra se corta siempre con el margen de caja
    terminada, sin importar lo que diga el JSON guardado: el ancho×alto cotizado
    ES la caja. La regla vive en el backend al guardar Y acá al imprimir, porque
    esto es lo que el taller corta."""

    def _con_caja(self, tc):
        return {"Tela": "Popelina 155", "Caja": {"perfil": "PERFIL 80 MM"},
                "Ancho": 1.48, "Alto": 2.25, "Cantidad": 1, "TerminacionesCaja": tc}

    def test_ignora_un_area_visual_guardado(self):
        self.assertEqual(_terminaciones_caja_de(self._con_caja("AREA VISUAL"), ""),
                          "CAJA TERMINADA")

    def test_ignora_tambien_el_valor_de_la_op_completa(self):
        p = {"Tela": "Popelina 155", "Caja": {"perfil": "PERFIL 80 MM"},
             "Ancho": 1.48, "Alto": 2.25, "Cantidad": 1}
        self.assertEqual(_terminaciones_caja_de(p, "AREA VISUAL"), "CAJA TERMINADA")

    def test_el_corte_sale_con_el_margen_chico(self):
        tc = _terminaciones_caja_de(self._con_caja("AREA VISUAL"), "")
        self.assertAlmostEqual(_corte(1.48, tc), 1.495)

    def test_sin_caja_no_se_fuerza(self):
        p = {"Tela": "Popelina 155", "Caja": "Sin caja", "Ancho": 1.48,
             "Alto": 2.25, "Cantidad": 1, "TerminacionesCaja": "AREA VISUAL"}
        self.assertEqual(_terminaciones_caja_de(p, ""), "AREA VISUAL")
        self.assertAlmostEqual(_corte(1.48, _terminaciones_caja_de(p, "")), 1.505)


class TestRotuloSegunCaja(_ConCarpetaTemporal):
    """En el impreso, el rótulo "Caja terminada"/"Área visual" solo va cuando la
    caja NO es nuestra: ahí hubo una elección que comunicar. El margen en gris se
    imprime siempre — es lo que el que corta necesita."""

    def _fila(self, op):
        from core.presentar_op import generar_html
        html = Path(generar_html(op)).read_text(encoding="utf-8")
        return html[html.index("<tbody>"):html.index("</tbody>")]

    def _op(self, numero, caja, tc):
        op = _op_backlight(numero)
        del op["TerminacionesCaja"]
        op["productos"] = [{
            "Tela": "Popelina 155", "Caja": caja,
            "Ancho": 1.48, "Alto": 2.25, "Cantidad": 1, "Tema": "", "Obs": "",
            "TerminacionesCaja": tc,
        }]
        return op

    def test_con_caja_nuestra_no_se_rotula(self):
        fila = self._fila(self._op(9301, {"perfil": "PERFIL 80 MM"}, "CAJA TERMINADA"))
        self.assertIn("PERFIL 80 MM", fila)
        self.assertNotIn("Caja terminada", fila)
        self.assertNotIn("Área visual", fila)

    def test_con_caja_nuestra_el_margen_igual_se_imprime(self):
        fila = self._fila(self._op(9302, {"perfil": "PERFIL 80 MM"}, "CAJA TERMINADA"))
        self.assertIn("(+1,5 cms)", fila)
        self.assertIn("1,495", fila)

    def test_con_caja_nuestra_un_area_visual_guardado_no_cambia_el_corte(self):
        # Dato inconsistente (perfil + área visual): al imprimir se corta con el
        # margen que corresponde, no con el que quedó guardado.
        fila = self._fila(self._op(9305, {"perfil": "PERFIL 80 MM"}, "AREA VISUAL"))
        self.assertIn("(+1,5 cms)", fila)
        self.assertIn("1,495", fila)
        self.assertNotIn("1,505", fila)

    def test_sin_caja_si_se_rotula(self):
        fila = self._fila(self._op(9303, "Sin caja", "AREA VISUAL"))
        self.assertIn("Área visual", fila)
        self.assertIn("(+2,5 cms)", fila)
        self.assertIn("1,505", fila)

    def test_sin_caja_con_caja_terminada_tambien_se_rotula(self):
        fila = self._fila(self._op(9304, "Sin caja", "CAJA TERMINADA"))
        self.assertIn("Caja terminada", fila)
        self.assertIn("(+1,5 cms)", fila)


if __name__ == "__main__":
    unittest.main()
