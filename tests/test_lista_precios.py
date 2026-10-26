"""
tests/test_lista_precios.py
La lista de precios congelada de una cotización (core/lista_precios.py):
una cotización guardada se sigue calculando con los precios con que se hizo
aunque cambien, avisa qué cambió, y el usuario elige actualizarla o
mantenerla. Usa una carpeta temporal y catálogos fijos — no toca Dropbox,
AppData ni los catálogos reales.

Correr con:  python -m unittest tests.test_lista_precios -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio as repo
import core.repositorio_cotizaciones as repo_cot
import core.repositorio_materiales as repo_mat
from core import lista_precios
from core.repositorio_cotizaciones import mapear_producto

TEXTIL = "Tela de prueba"
TERMINACION = "Basta de prueba"


def _producto(cantidad=1):
    # 1 m × 3 m de una tela de 1,5 m de ancho: 3 ML impresos (sobre el mínimo de 2).
    return mapear_producto({
        "producto": "Pendón", "textil": TEXTIL, "estructuras": [], "terminaciones": [TERMINACION],
        "impresion": "Cara única", "ancho": 1.0, "alto": 3.0, "cantidad": cantidad, "tema": "", "obs": "",
    })


def _cotizacion(numero=7001):
    return {"Cotizacion": numero, "Empresa": "Cliente", "Fecha": "20/10/2026",
            "Descuento": 0, "productos": [_producto()]}


class _Base(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        parches = [
            mock.patch.object(repo_cot, "_ruta_base", lambda: base),
            # patch.dict cambia el dict EN EL LUGAR: core.precios importó estos
            # mismos objetos, así que el cálculo "con los precios de hoy" los ve.
            mock.patch.dict(repo.TEXTILES_VALORES, {TEXTIL: 10000.0}),
            mock.patch.dict(repo.TEXTILES_ANCHOS, {TEXTIL: 1.5}),
            mock.patch.dict(repo.TERMINACIONES_LEGADO_VALORES, {TERMINACION: {"valorUNIT": 2000.0}}),
            # Sin materiales de Inventario: el catálogo de estructuras tal cual.
            mock.patch.object(repo_mat, "kwargs_precios", lambda: {
                "estructuras_legado_valores": dict(repo.ESTRUCTURAS_LEGADO_VALORES),
                "cobro_materiales": lambda d: None,
            }),
        ]
        for p in parches:
            p.start()
            self.addCleanup(p.stop)
        repo_cot._migradas.clear()

    def guardar_con_lista(self, datos):
        internos = [repo_cot.producto_desde_json(p) for p in datos["productos"]]
        datos["ListaPrecios"] = lista_precios.armar(internos)
        repo_cot.recalcular_descuentos(datos)  # totales y guarda
        return repo_cot.cargar_cotizacion(datos["Cotizacion"])

    @staticmethod
    def total(datos):
        internos, kwargs = lista_precios.internos_congelados(datos)
        return lista_precios.totales(datos, internos, kwargs)["total"]


class TestCongelar(_Base):

    def test_la_lista_trae_solo_lo_que_usa_la_cotizacion(self):
        datos = self.guardar_con_lista(_cotizacion())
        lista = datos["ListaPrecios"]
        self.assertEqual(lista["textiles"], {TEXTIL: 10000.0})
        self.assertEqual(lista["anchos"], {TEXTIL: 1.5})
        self.assertEqual(lista["terminaciones"], {TERMINACION: {"valorUNIT": 2000.0}})
        self.assertEqual(lista["cajas"], {})

    def test_un_precio_nuevo_no_cambia_el_total_guardado(self):
        datos = self.guardar_con_lista(_cotizacion())
        antes = datos["Total"]
        # 3 ML × 10.000 + 1 × 2.000 = 32.000 neto, + IVA 19 %
        self.assertAlmostEqual(antes, 32000 * 1.19)
        repo.TEXTILES_VALORES[TEXTIL] = 15000.0
        reabierta = repo_cot.recalcular_descuentos(repo_cot.cargar_cotizacion(7001))
        self.assertAlmostEqual(reabierta["Total"], antes)
        self.assertAlmostEqual(self.total(reabierta), antes)

    def test_una_cotizacion_vieja_se_congela_con_los_precios_de_hoy(self):
        repo_cot.guardar_cotizacion(_cotizacion())        # sin ListaPrecios, como las de antes
        datos = repo_cot.recalcular_descuentos(repo_cot.cargar_cotizacion(7001))
        self.assertIn("ListaPrecios", repo_cot.cargar_cotizacion(7001))   # quedó guardada
        self.assertIsNone(lista_precios.cambios(datos))
        self.assertAlmostEqual(datos["Total"], 32000 * 1.19)


class TestCambios(_Base):

    def test_sin_cambios_de_precio_no_avisa(self):
        self.assertIsNone(lista_precios.cambios(self.guardar_con_lista(_cotizacion())))

    def test_avisa_que_cambio_y_cuanto(self):
        datos = self.guardar_con_lista(_cotizacion())
        repo.TEXTILES_VALORES[TEXTIL] = 15000.0
        repo.TERMINACIONES_LEGADO_VALORES[TERMINACION] = {"valorUNIT": 2500.0}
        c = lista_precios.cambios(datos)
        self.assertIsNotNone(c)
        por_tipo = {x["tipo"]: x for x in c["componentes"]}
        self.assertEqual((por_tipo["Textil"]["antes"], por_tipo["Textil"]["ahora"], por_tipo["Textil"]["unidad"]),
                         (10000.0, 15000.0, "/ML"))
        self.assertEqual((por_tipo["Terminación"]["antes"], por_tipo["Terminación"]["ahora"], por_tipo["Terminación"]["unidad"]),
                         (2000.0, 2500.0, "/un."))
        self.assertEqual(len(c["productos"]), 1)
        self.assertAlmostEqual(c["productos"][0]["antes"], 32000)
        self.assertAlmostEqual(c["productos"][0]["ahora"], 47500)
        self.assertAlmostEqual(c["total"]["ahora"], 47500 * 1.19)

    def test_un_cambio_en_algo_que_no_usa_no_avisa(self):
        datos = self.guardar_con_lista(_cotizacion())
        repo.TEXTILES_VALORES["Otra tela"] = 99999.0
        self.assertIsNone(lista_precios.cambios(datos))

    def test_mantener_no_vuelve_a_preguntar_hasta_otro_cambio(self):
        datos = self.guardar_con_lista(_cotizacion())
        repo.TEXTILES_VALORES[TEXTIL] = 15000.0
        lista_precios.mantener(datos)
        self.assertIsNone(lista_precios.cambios(datos))
        self.assertAlmostEqual(self.total(datos), 32000 * 1.19)   # sigue con sus precios
        repo.TEXTILES_VALORES[TEXTIL] = 18000.0                   # otro cambio: vuelve a avisar
        self.assertIsNotNone(lista_precios.cambios(datos))

    def test_actualizar_pasa_a_los_precios_de_hoy(self):
        datos = self.guardar_con_lista(_cotizacion())
        repo.TEXTILES_VALORES[TEXTIL] = 15000.0
        lista_precios.actualizar(datos)
        self.assertIsNone(lista_precios.cambios(datos))
        self.assertAlmostEqual(self.total(datos), 47000 * 1.19)

    def test_lo_que_cobraron_los_materiales_queda_congelado(self):
        cobro = {"estructuras": {}, "materiales_producto": {"Ojetillos": 500.0},
                 "detalle": {"Ojetillos": {"consumo": 10, "valor": 50.0, "monto": 500.0, "tipo": "unidad", "origen": "producto"}}}
        with mock.patch.object(repo_mat, "kwargs_precios", lambda: {
            "estructuras_legado_valores": dict(repo.ESTRUCTURAS_LEGADO_VALORES), "cobro_materiales": lambda d: cobro,
        }):
            datos = self.guardar_con_lista(_cotizacion())
            self.assertAlmostEqual(datos["Total"], 32500 * 1.19)
        mas_caro = {**cobro, "materiales_producto": {"Ojetillos": 800.0},
                    "detalle": {"Ojetillos": {**cobro["detalle"]["Ojetillos"], "valor": 80.0, "monto": 800.0}}}
        with mock.patch.object(repo_mat, "kwargs_precios", lambda: {
            "estructuras_legado_valores": dict(repo.ESTRUCTURAS_LEGADO_VALORES), "cobro_materiales": lambda d: mas_caro,
        }):
            self.assertAlmostEqual(self.total(datos), 32500 * 1.19)
            material = [x for x in lista_precios.cambios(datos)["componentes"] if x["tipo"] == "Material"][0]
            self.assertEqual((material["nombre"], material["antes"], material["ahora"], material["unidad"]),
                             ("Ojetillos", 50.0, 80.0, "/un."))



class TestCobrosPorProducto(_Base):
    """Lo que la cotización cobró, en sus cuatro formas, para los reportes de
    Inventario (decisión de Bruno, 2026-10-26)."""

    def test_con_el_descuento_del_contacto(self):
        datos = {**_cotizacion(), "Descuento": 10}
        datos = self.guardar_con_lista(datos)
        cobro = lista_precios.cobros_por_producto(datos)[0]["textil"]
        # 3 ML × $10.000, 10 % de descuento, IVA 19 %.
        self.assertEqual(cobro, {"sin_iva": 30000.0, "sin_iva_con_descuento": 27000.0,
                                 "con_iva": 35700.0, "con_iva_con_descuento": 32130.0})

    def test_sin_descuento(self):
        datos = self.guardar_con_lista(_cotizacion())
        cobro = lista_precios.cobros_por_producto(datos)[0]["textil"]
        self.assertEqual(cobro["sin_iva"], cobro["sin_iva_con_descuento"])


if __name__ == "__main__":
    unittest.main()
