"""
tests/test_titulo_impresion.py
Verifica core/titulo_impresion.py y su uso en los dos documentos
imprimibles (core/presentar_cotizacion.py y core/presentar_op.py).

Lo que se prueba de verdad acá es el nombre con el que el usuario termina
guardando el PDF: al imprimir desde el navegador con "Guardar como PDF",
el nombre propuesto sale del <title> del documento. Formato pedido:
"{numero} • {nombre_trabajo} {cliente}".

Usa carpetas temporales (mock de _ruta_base de core.repositorio_ops y
core.repositorio_cotizaciones) para que generar_html() no toque
Dropbox/AppData reales — mismo criterio que tests/test_presentar_op.py.

Correr con:  python -m unittest tests.test_titulo_impresion -v
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_cotizaciones as repo_cot
import core.repositorio_ops as repo_ops
from core.titulo_impresion import titulo_impresion


def _titulo_del_html(ruta: Path) -> str:
    return re.search(r"<title>(.*?)</title>", ruta.read_text(encoding="utf-8")).group(1)


def _cotizacion(numero=1003, nombre="test minimo", empresa="Empresa Ejemplo"):
    return {
        "Cotizacion": numero,
        "Nombre": nombre,
        "Empresa": empresa,
        "Fecha": "08/09/2026",
        "Contacto": "Contacto Ejemplo",
        "Email": "contacto@ejemplo.cl",
        "Descuento": 0.0,
        "Condicion de pago": "30 días",
        "Descripcion": "",
        "productos": [{
            "producto": "Bandera", "Tela": "Bistretch",
            "Estructuras": [], "Terminaciones": [], "Impresion": "Cara única",
            "Ancho": 1.0, "Alto": 1.0, "Cantidad": 1, "Tema": "", "Obs": "",
        }],
    }


def _op(numero=1003, nombre="test minimo", empresa="Empresa Ejemplo"):
    return dict(_cotizacion(numero, nombre, empresa),
                Fecha_ingreso="08/09/2026", Fecha_entrega="15/09/2026")


class TestTituloImpresion(unittest.TestCase):

    def test_formato_pedido(self):
        self.assertEqual(titulo_impresion(1003, "test minimo", "Empresa Ejemplo"),
                         "1003 • test minimo Empresa Ejemplo")

    def test_sin_nombre_de_trabajo_no_deja_espacios_de_mas(self):
        self.assertEqual(titulo_impresion(1003, "", "Empresa Ejemplo"),
                         "1003 • Empresa Ejemplo")

    def test_solo_el_numero_si_no_hay_nada_mas(self):
        self.assertEqual(titulo_impresion(1003, "", ""), "1003")

    def test_saca_los_caracteres_que_no_valen_en_un_nombre_de_archivo(self):
        # Windows no admite \ / : * ? " < > | — si llegan al título, el
        # navegador los reemplaza por "_" al guardar el PDF.
        titulo = titulo_impresion(1003, 'Cubre alarma / cenefa', "Perez: Ltda")
        self.assertEqual(titulo, "1003 • Cubre alarma cenefa Perez Ltda")

    def test_escapa_para_meterlo_en_el_html(self):
        self.assertEqual(titulo_impresion(1003, "Telas & Co", ""), "1003 • Telas &amp; Co")


class TestTituloEnLosDocumentos(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        for modulo in (repo_cot, repo_ops):
            parche = mock.patch.object(modulo, "_ruta_base", lambda: Path(self._tmp.name))
            parche.start()
            self.addCleanup(parche.stop)

    def test_cotizacion_impresa(self):
        from core.presentar_cotizacion import generar_html
        self.assertEqual(_titulo_del_html(generar_html(_cotizacion())),
                         "1003 • test minimo Empresa Ejemplo")

    def test_op_impresa(self):
        from core.presentar_op import generar_html
        self.assertEqual(_titulo_del_html(generar_html(_op())),
                         "1003 • test minimo Empresa Ejemplo")

    def test_el_html_de_trabajo_sigue_llamandose_por_el_numero(self):
        # El archivo en disco NO cambia de nombre: se regenera y se pisa en
        # cada impresión (ver carpeta_html), el nombre que importa es el del
        # PDF que guarda el usuario.
        from core.presentar_cotizacion import generar_html
        self.assertEqual(generar_html(_cotizacion()).name, "1003.html")


if __name__ == "__main__":
    unittest.main()
