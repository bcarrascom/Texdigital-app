"""
tests/test_aprobar_cotizacion_materiales.py
Integración de punta a punta del enganche Inventario <-> aprobación de
cotizaciones (feature de 2026-08-29, ver ui/dialogo_aprobar.py y
ui/api_ver_cotizacion.py::aprobar_cotizacion/verificar_materiales):

  - Aprobar con stock suficiente: crea la OP, mueve la cotización a
    Historial, Y descuenta los metros lineales correspondientes de
    Inventario (core.repositorio_inventario.consumir_para_op).
  - Aprobar con stock insuficiente: NO crea la OP, NO mueve la
    cotización, NO toca el stock — devuelve {"ok": False, "faltantes": [...]}.
  - ApiCotizacion.verificar_materiales: mismo cálculo, pero sobre un
    borrador (productos del frontend) todavía sin guardar — el aviso de
    nueva-cotizacion.html.

Usa carpetas temporales para cotizaciones, OPs e inventario (mock de
_ruta_base en cada módulo) y un catálogo de anchos de
textil fijo — no toca Dropbox ni AppData reales, y no depende del
contenido real de recursos/textiles.json.

Correr con:  python -m unittest tests.test_aprobar_cotizacion_materiales -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_cotizaciones as repo_cot
import core.repositorio_inventario as repo_inv
import core.repositorio_ops as repo_ops
from ui.api_ver_cotizacion import ApiVerCotizacion
from ui.api_cotizacion import ApiCotizacion

_ANCHOS = {"TelaTest": 1.5}


def _cotizacion(numero, ancho=1.5, alto=10.0, cantidad=1):
    return {
        "Cotizacion": numero,
        "Empresa": f"Empresa {numero}",
        "Fecha": "20/08/2026",
        "RUT": "", "Razon Social": "", "Contacto": "", "Email": "",
        "Descuento": 0.0, "Condicion de pago": "", "Descripcion": "",
        "Neto": 0, "NetoTotal": 0, "IVA": 0, "Total": 0,
        "productos": [{
            "producto": "Pendón", "Tela": "TelaTest",
            "Estructuras": [], "Terminaciones": [], "Impresion": "Cara única",
            "Ancho": ancho, "Alto": alto, "Cantidad": cantidad,
            "Tema": "", "Obs": "",
        }],
    }


class _ConRutasTemporales(unittest.TestCase):
    """Aísla los TRES almacenamientos que toca aprobar_cotizacion: la
    cotización en sí, la OP que se crea, y el stock de Inventario."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)

        self._parches = [
            mock.patch.object(repo_cot, "_ruta_base", lambda: base / "Cotizaciones"),
            mock.patch.object(repo_ops, "_ruta_base", lambda: base / "OPs"),
            mock.patch.object(repo_inv, "_ruta_base", lambda: base / "Inventario"),
            mock.patch.dict("core.repositorio.TEXTILES_ANCHOS", _ANCHOS, clear=True),
        ]
        for p in self._parches:
            p.start()
            self.addCleanup(p.stop)
        repo_cot._migradas.clear()
        repo_ops._migradas.clear()

        self.api = ApiVerCotizacion()


class TestAprobarConStockSuficiente(_ConRutasTemporales):

    def test_aprobar_devuelve_ok(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 100)
        repo_cot.guardar_cotizacion(_cotizacion(4210))

        resultado = self.api.aprobar_cotizacion(4210, "2026-08-29", "2026-09-15")

        self.assertEqual(resultado, {"ok": True})

    def test_aprobar_crea_la_op_y_archiva_la_cotizacion(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 100)
        repo_cot.guardar_cotizacion(_cotizacion(4210))

        self.api.aprobar_cotizacion(4210, "2026-08-29", "2026-09-15")

        self.assertIsNotNone(repo_ops.cargar_op(4210))
        self.assertIsNone(repo_cot.cargar_cotizacion(4210))  # ya no está activa

    def test_aprobar_descuenta_el_stock_correcto(self):
        # necesita ml = alto (10) porque ancho tela == ancho producto == 1.5
        repo_inv.crear_rollo("TelaTest", 1.5, 100)
        repo_cot.guardar_cotizacion(_cotizacion(4210, ancho=1.5, alto=10.0, cantidad=1))

        self.api.aprobar_cotizacion(4210, "2026-08-29", "2026-09-15")

        stock = repo_inv.stock_por_textil()
        self.assertEqual(stock["TelaTest"], 90.0)

    def test_aprobar_graba_que_rollo_le_toco_a_cada_producto(self):
        # El panel de producción (display_op.html) lee esto directo del
        # JSON de la OP — no recalcula nada, la asignación se decide acá,
        # una sola vez, priorizando el rollo más chico (ver
        # core.repositorio_inventario.consumir_para_op).
        rollo_chico = repo_inv.crear_rollo("TelaTest", 1.5, 3)
        repo_inv.crear_rollo("TelaTest", 1.5, 100)
        repo_cot.guardar_cotizacion(_cotizacion(4210, ancho=1.5, alto=2.0, cantidad=1))  # necesita 2

        self.api.aprobar_cotizacion(4210, "2026-08-29", "2026-09-15")

        op = repo_ops.cargar_op(4210)
        self.assertEqual(op["productos"][0]["RollosUsados"], [{"id": rollo_chico["id"], "metros": 2.0}])


class TestAprobarConStockInsuficiente(_ConRutasTemporales):

    def test_aprobar_devuelve_faltantes_sin_aprobar(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 5)  # necesita 10, hay 5
        repo_cot.guardar_cotizacion(_cotizacion(4210, ancho=1.5, alto=10.0, cantidad=1))

        resultado = self.api.aprobar_cotizacion(4210, "2026-08-29", "2026-09-15")

        self.assertFalse(resultado["ok"])
        self.assertEqual(len(resultado["faltantes"]), 1)
        self.assertEqual(resultado["faltantes"][0]["textil"], "TelaTest")
        self.assertAlmostEqual(resultado["faltantes"][0]["faltante"], 5.0)

    def test_aprobar_bloqueado_no_crea_op_ni_toca_stock(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 5)
        repo_cot.guardar_cotizacion(_cotizacion(4210, ancho=1.5, alto=10.0, cantidad=1))

        self.api.aprobar_cotizacion(4210, "2026-08-29", "2026-09-15")

        self.assertIsNone(repo_ops.cargar_op(4210))
        self.assertIsNotNone(repo_cot.cargar_cotizacion(4210))  # sigue activa
        self.assertEqual(repo_inv.stock_por_textil()["TelaTest"], 5.0)  # intacto

    def test_verificar_materiales_del_boton_aprobar_da_lo_mismo_que_el_bloqueo(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 5)
        repo_cot.guardar_cotizacion(_cotizacion(4210, ancho=1.5, alto=10.0, cantidad=1))

        faltantes = self.api.verificar_materiales(4210)

        self.assertEqual(len(faltantes), 1)
        self.assertEqual(faltantes[0]["textil"], "TelaTest")

    def test_cotizacion_inexistente_no_revienta(self):
        resultado = self.api.aprobar_cotizacion(9999, "2026-08-29", "2026-09-15")
        self.assertEqual(resultado, {"ok": False, "faltantes": []})


class TestVerificarMaterialesDeBorrador(_ConRutasTemporales):
    """ApiCotizacion.verificar_materiales — el aviso de nueva-cotizacion.html,
    sobre productos del FRONTEND (todavía no guardados como cotización)."""

    def setUp(self):
        super().setUp()
        self.api_cot = ApiCotizacion()

    def _producto_frontend(self, ancho="1,5", alto="10", cantidad="1"):
        return {
            "tipo": "estandar", "producto": "Pendón", "textil": "TelaTest",
            "impresion": "Cara única", "estructuras": [], "terminaciones": [],
            "ancho": ancho, "alto": alto, "cantidad": cantidad,
            "tema": "", "obs": "",
        }

    def test_borrador_con_stock_suficiente_no_reporta_nada(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 100)
        faltantes = self.api_cot.verificar_materiales([self._producto_frontend()])
        self.assertEqual(faltantes, [])

    def test_borrador_con_stock_insuficiente_reporta_faltante(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 5)
        faltantes = self.api_cot.verificar_materiales([self._producto_frontend()])
        self.assertEqual(len(faltantes), 1)
        self.assertEqual(faltantes[0]["textil"], "TelaTest")

    def test_producto_incompleto_sin_medidas_no_cuenta(self):
        # ancho/alto/cantidad vacíos -> se ignora (todavía no se cargó nada)
        incompleto = self._producto_frontend(ancho="", alto="", cantidad="")
        faltantes = self.api_cot.verificar_materiales([incompleto])
        self.assertEqual(faltantes, [])


if __name__ == "__main__":
    unittest.main()
