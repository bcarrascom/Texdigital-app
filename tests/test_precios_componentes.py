"""
tests/test_precios_componentes.py
Los precios de estructuras, terminaciones y cajas (core/precios_componentes.py)
y las reglas de cobro (core/reglas_cobro.py), editables en Configuración:
valores por defecto, qué no se deja guardar, que el cálculo los use, y que
una cotización guardada siga con los suyos. Conf va a una carpeta temporal y
los catálogos son fijos — no toca Dropbox ni los reales.

Correr con:  python -m unittest tests.test_precios_componentes -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.ajustes_globales as ajustes_globales
import core.repositorio as repo
import core.repositorio_cotizaciones as repo_cot
import core.repositorio_materiales as repo_mat
from core import lista_precios, precios_componentes, reglas_cobro
from core.precios import costo_cotizacion, tramo_descuento_textil
from core.repositorio_cotizaciones import mapear_producto

TEXTIL, TERMINACION = "Tela de prueba", "Basta de prueba"
CAJAS = {"luces": {"M3": 100.0}, "traseras": {"Trovicel": 200.0}, "armado": {"minimo": 10.0},
         "fp": {35: 300.0}, "perfiles": {"P60": 400.0}, "pintura_por_ml": 50.0}


def _producto(alto=3.0):
    return mapear_producto({"producto": "Pendón", "textil": TEXTIL, "estructuras": [], "terminaciones": [TERMINACION],
                            "impresion": "Cara única", "ancho": 1.0, "alto": alto, "cantidad": 1, "tema": "", "obs": ""})


class _Base(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.conf = base / "Conf"
        parches = [
            mock.patch.object(ajustes_globales, "_CONF_DIR", self.conf),
            mock.patch.object(repo_cot, "_ruta_base", lambda: base / "Cotizaciones"),
            mock.patch.object(repo, "TEXTILES", [TEXTIL]),
            mock.patch.dict(repo.TEXTILES_VALORES, {TEXTIL: 10000.0}, clear=True),
            mock.patch.dict(repo.TEXTILES_ANCHOS, {TEXTIL: 1.5}),
            mock.patch.dict(repo.TERMINACIONES_LEGADO_VALORES, {TERMINACION: {"valorUNIT": 2000.0}}, clear=True),
            mock.patch.dict(repo.ESTRUCTURAS_LEGADO_VALORES, {"Asta": {"valorUNIT": 5000.0}, "Riel": {"valorML": 900.0}}, clear=True),
            mock.patch.dict(repo.PRECIOS_CAJAS, CAJAS, clear=True),
            # Sin materiales de Inventario.
            mock.patch.object(repo_mat, "valores_legado_materiales", lambda: {}),
            mock.patch.object(repo_mat, "cobro_materiales_producto", lambda d: None),
        ]
        for p in parches:
            p.start()
            self.addCleanup(p.stop)
        repo_cot._migradas.clear()


class TestEstructurasYTerminaciones(_Base):

    def test_sin_archivo_valen_los_del_catalogo(self):
        self.assertEqual(precios_componentes.cargar_lista("estructuras"), [
            {"nombre": "Asta", "valor": 5000.0, "unidad": "un."},
            {"nombre": "Riel", "valor": 900.0, "unidad": "ML"},
        ])

    def test_guardar_cambia_el_valor_y_conserva_la_unidad(self):
        r = precios_componentes.guardar_lista("estructuras", [{"nombre": "Asta", "valor": 6000}, {"nombre": "Riel", "valor": 950}])
        self.assertEqual(r, {"ok": True})
        self.assertEqual(precios_componentes.valores("estructuras"), {"Asta": {"valorUNIT": 6000.0}, "Riel": {"valorML": 950.0}})
        self.assertEqual(repo_mat.estructuras_legado_valores_efectivos()["Asta"], {"valorUNIT": 6000.0})

    def test_sin_valor_o_en_cero_no_se_guarda(self):
        for malo in (None, "", 0, -1):
            r = precios_componentes.guardar_lista("terminaciones", [{"nombre": TERMINACION, "valor": malo}])
            self.assertFalse(r["ok"], malo)
            self.assertEqual(r["errores"][0]["nombre"], TERMINACION)
        self.assertFalse((self.conf / "precios_terminaciones.json").exists())

    def test_el_cotizador_cobra_la_terminacion_nueva(self):
        precios_componentes.guardar_lista("terminaciones", [{"nombre": TERMINACION, "valor": 2500}])
        totales = costo_cotizacion([repo_cot.producto_desde_json(_producto())], **repo_mat.kwargs_precios())
        self.assertAlmostEqual(totales["neto"], 3 * 10000 + 2500)


class TestCajas(_Base):

    def datos(self, **cambios):
        datos = {"luces": {"M3": 100}, "traseras": {"Trovicel": 200}, "armado": {"minimo": 10},
                 "fp": {"35": 300}, "perfiles": {"P60": 400}, "pintura_por_ml": 50}
        datos.update(cambios)
        return datos

    def test_guardar_y_leer_con_los_watts_como_numero(self):
        self.assertEqual(precios_componentes.guardar_cajas(self.datos(fp={"35": 333})), {"ok": True})
        cajas = precios_componentes.cajas()
        self.assertEqual(cajas["fp"], {35: 333.0})
        self.assertEqual(cajas["pintura_por_ml"], 50.0)

    def test_un_valor_que_falta_no_se_guarda(self):
        r = precios_componentes.guardar_cajas(self.datos(luces={"M3": ""}))
        self.assertEqual([(e["seccion"], e["clave"]) for e in r["errores"]], [("luces", "M3")])
        r = precios_componentes.guardar_cajas(self.datos(pintura_por_ml=None))
        self.assertEqual(r["errores"][0]["seccion"], "pintura_por_ml")

    def test_la_lista_congelada_lee_los_watts_guardados_como_texto(self):
        lista = json.loads(json.dumps({"cajas": precios_componentes.cajas()}))   # como sale del archivo
        self.assertEqual(lista_precios.kwargs_congelados(lista)["precios_cajas"]["fp"], {35: 300.0})


class TestReglas(_Base):

    def reglas(self, **cambios):
        return {**reglas_cobro.POR_DEFECTO, **cambios}

    def test_sin_archivo_valen_las_de_siempre(self):
        self.assertEqual(reglas_cobro.cargar(), {"iva": 19.0, "ml_minimo": 2.0, "m2_minimo": 2.0,
                                                  "tramos_descuento": [[50.0, 20.0], [20.0, 10.0], [10.0, 5.0]]})

    def test_guardar_ordena_los_tramos(self):
        r = reglas_cobro.guardar(self.reglas(iva=21, tramos_descuento=[[10, 5], [30, 15]]))
        self.assertEqual(r, {"ok": True})
        self.assertEqual(reglas_cobro.cargar()["tramos_descuento"], [[30.0, 15.0], [10.0, 5.0]])
        self.assertEqual(reglas_cobro.cargar()["iva"], 21.0)

    def test_sin_tramos_no_hay_descuento_por_volumen(self):
        self.assertTrue(reglas_cobro.guardar(self.reglas(tramos_descuento=[]))["ok"])
        self.assertEqual(tramo_descuento_textil(500, reglas_cobro.cargar()["tramos_descuento"]), 0.0)

    def test_lo_que_no_se_deja_guardar(self):
        casos = {
            "iva": self.reglas(iva=100), "ml_minimo": self.reglas(ml_minimo=-1), "m2_minimo": self.reglas(m2_minimo=""),
            "tramo:1": self.reglas(tramos_descuento=[[10, 5], [10, 8]]),
            "tramo:0": self.reglas(tramos_descuento=[[10, 0]]),
        }
        for campo, datos in casos.items():
            r = reglas_cobro.guardar(datos)
            self.assertFalse(r["ok"], campo)
            self.assertEqual(r["errores"][0]["campo"], campo)

    def test_el_calculo_usa_las_reglas(self):
        reglas_cobro.guardar(self.reglas(iva=10, ml_minimo=5))
        # 3 ML, con mínimo de 5: se cobran 5 ML.
        totales = costo_cotizacion([repo_cot.producto_desde_json(_producto(alto=3))], **repo_mat.kwargs_precios())
        self.assertAlmostEqual(totales["neto"], 5 * 10000 + 2000)
        self.assertAlmostEqual(totales["iva"], totales["neto_total"] * 0.10)
        self.assertEqual(totales["iva_pct"], 10.0)


class TestCotizacionCongelada(_Base):

    def guardada(self):
        datos = {"Cotizacion": 7001, "Empresa": "Cliente", "Descuento": 0, "productos": [_producto()]}
        internos = [repo_cot.producto_desde_json(p) for p in datos["productos"]]
        datos["ListaPrecios"] = lista_precios.armar(internos)
        repo_cot.recalcular_descuentos(datos)
        return repo_cot.cargar_cotizacion(7001)

    def test_cambiar_el_iva_no_cambia_una_cotizacion_guardada_pero_avisa(self):
        datos = self.guardada()
        self.assertAlmostEqual(datos["Total"], 32000 * 1.19)
        reglas_cobro.guardar({**reglas_cobro.POR_DEFECTO, "iva": 21})
        reabierta = repo_cot.recalcular_descuentos(repo_cot.cargar_cotizacion(7001))
        self.assertAlmostEqual(reabierta["Total"], 32000 * 1.19)
        c = lista_precios.cambios(reabierta)
        self.assertEqual([(x["nombre"], x["antes"], x["ahora"]) for x in c["componentes"]], [("IVA", 19.0, 21.0)])
        self.assertAlmostEqual(c["total"]["ahora"], 32000 * 1.21)

    def test_una_lista_sin_reglas_usa_las_de_siempre(self):
        datos = self.guardada()
        del datos["ListaPrecios"]["reglas"]
        reglas_cobro.guardar({**reglas_cobro.POR_DEFECTO, "iva": 21})
        internos, kwargs = lista_precios.internos_congelados(datos)
        self.assertAlmostEqual(lista_precios.totales(datos, internos, kwargs)["total"], 32000 * 1.19)


if __name__ == "__main__":
    unittest.main()
