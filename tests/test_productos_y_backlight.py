"""
tests/test_productos_y_backlight.py
Lo agregado a Configuración el 2026-10-25:
  - la lista de productos (core/catalogo.py): agregar, renombrar y quitar,
    llevándose las asociaciones de materiales de Inventario;
  - "Backlight + Caja" y los perfiles de caja como claves de asociación de
    materiales (core/repositorio_materiales.claves_consumo), y que el perfil
    con materiales asociados cobre sus materiales ADEMÁS del precio del perfil;
  - los márgenes de corte de backlight (core/corte_backlight.py).
Conf e Inventario van a carpetas temporales — no toca Dropbox.

Correr con:  python -m unittest tests.test_productos_y_backlight -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.ajustes_globales as ajustes_globales
import core.config as config
import core.repositorio as repo
import core.repositorio_materiales as repo_mat
from core import catalogo, corte_backlight
from core.precios import costo_producto

SEMILLAS = {
    "textiles": [], "anchos": {}, "valores": {}, "backlight": [],
    "estructuras": ([], {}), "terminaciones": ([], {}),
    "productos": ["Pendón", "Bandera 3x2"],
}


class _Base(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        for nombre in ("TEXTILES", "ESTRUCTURAS_LEGADO", "TERMINACIONES_LEGADO", "PRODUCTOS"):
            lista = getattr(repo, nombre)
            self.addCleanup(lista.__setitem__, slice(None), list(lista))
        parches = [
            mock.patch.object(ajustes_globales, "_CONF_DIR", base / "Conf"),
            mock.patch.object(repo_mat, "_ruta_base", lambda: base / "Inventario"),
            mock.patch.object(catalogo, "_semillas_cache", SEMILLAS),
            mock.patch.dict(repo.TEXTILES_ANCHOS, {}),
            mock.patch.dict(repo.TEXTILES_VALORES, {}),
            mock.patch.dict(repo.ESTRUCTURAS_LEGADO_VALORES, {}),
            mock.patch.dict(repo.TERMINACIONES_LEGADO_VALORES, {}),
            mock.patch.dict(config.MODULOS_HABILITADOS, {"inventario": True}),
        ]
        for p in parches:
            p.start()
            self.addCleanup(p.stop)
        catalogo._olvidar()
        self.addCleanup(catalogo._olvidar)
        catalogo._aplicar(catalogo._leer())

    def material(self, nombre, productos=(), estructuras=(), valor=100, consumo="fijo_por_producto"):
        m = repo_mat.ingresar_material(nombre, 100)
        repo_mat.editar_material(m["id"], nombre, "unidad", valor=valor, tipo_consumo=consumo,
                                 consumo_parametros={"n": 1}, productos_asociados=list(productos),
                                 estructuras_asociadas=list(estructuras))
        return repo_mat.obtener_material(m["id"])


class TestProductos(_Base):

    def test_agregar(self):
        self.assertEqual(catalogo.agregar_producto("  Gorro   lana "), {"ok": True})
        self.assertEqual(repo.PRODUCTOS, ["Pendón", "Bandera 3x2", "Gorro lana"])

    def test_lo_que_no_se_deja_agregar(self):
        for nombre in ("pendón", "", "Backlight", "backlight + caja"):
            self.assertFalse(catalogo.agregar_producto(nombre)["ok"], nombre)

    def test_renombrar_se_lleva_los_materiales_y_deja_alias(self):
        m = self.material("Ojetillo", productos=["Pendón"])
        self.assertEqual(catalogo.renombrar_producto("Pendón", "Pendón roller"), {"ok": True, "materiales": 1})
        self.assertEqual(repo.PRODUCTOS, ["Pendón roller", "Bandera 3x2"])
        self.assertEqual(repo_mat.obtener_material(m["id"])["productos_asociados"], ["Pendón roller"])
        self.assertEqual(catalogo.productos_detalle()[0]["anteriores"], ["Pendón"])
        # Una cotización vieja con el nombre anterior sigue gastando ese material.
        nombres, _ = repo_mat.claves_consumo({"producto": "Pendón", "textil": "T", "estructuras": []})
        self.assertEqual([x["nombre"] for x in repo_mat.materiales_para_producto(nombres)], ["Ojetillo"])

    def test_quitar_y_volver_a_agregar(self):
        m = self.material("Ojetillo", productos=["Pendón", "Bandera 3x2"])
        self.assertEqual(catalogo.quitar_producto("Pendón"), {"ok": True, "materiales": 1})
        self.assertEqual(repo.PRODUCTOS, ["Bandera 3x2"])
        self.assertEqual(repo_mat.obtener_material(m["id"])["productos_asociados"], ["Bandera 3x2"])
        self.assertTrue(catalogo.agregar_producto("pendón")["ok"])
        self.assertEqual(repo.PRODUCTOS, ["Pendón", "Bandera 3x2"])   # vuelve a su lugar

    def test_quitar_uno_agregado(self):
        catalogo.agregar_producto("Gorro")
        catalogo.quitar_producto("Gorro")
        self.assertEqual(catalogo._leer()["productos_agregados"], [])


def _backlight(perfil=None, cantidad=1):
    caja = {"perfil": perfil, "ancho": 1.0, "alto": 1.0} if perfil else "Sin caja"
    return {"tela": "Popelina", "caja": caja, "ancho": 1.0, "alto": 1.0, "cantidad": cantidad}


class TestBacklightCajaYPerfiles(_Base):

    def test_claves_de_un_backlight(self):
        self.assertEqual(repo_mat.claves_consumo(_backlight()), (["Backlight"], []))
        self.assertEqual(repo_mat.claves_consumo(_backlight("PERFIL 60 MM")),
                         (["Backlight", "Backlight + Caja"], ["PERFIL 60 MM"]))

    def test_backlight_mas_caja_solo_aplica_con_caja(self):
        self.material("Esquinero", productos=["Backlight + Caja"])
        self.material("Silicona", productos=["Backlight"])
        con = [m["nombre"] for m in repo_mat.materiales_para_producto(*repo_mat.claves_consumo(_backlight("PERFIL 60 MM")))]
        sin = [m["nombre"] for m in repo_mat.materiales_para_producto(*repo_mat.claves_consumo(_backlight()))]
        self.assertEqual(sorted(con), ["Esquinero", "Silicona"])
        self.assertEqual(sin, ["Silicona"])

    def test_un_material_de_backlight_y_backlight_mas_caja_se_cobra_una_vez(self):
        self.material("Silicona", productos=["Backlight", "Backlight + Caja"], valor=100)
        cobro = repo_mat.cobro_materiales_producto(_backlight("PERFIL 60 MM"))
        self.assertEqual(cobro["materiales_producto"], {"Silicona": 100.0})

    def test_un_perfil_con_materiales_los_cobra_ademas_del_precio_del_perfil(self):
        self.material("Aluminio 60", estructuras=["PERFIL 60 MM"], valor=700)
        cobro = repo_mat.cobro_materiales_producto(_backlight("PERFIL 60 MM", cantidad=2))
        self.assertEqual(cobro["estructuras"], {"PERFIL 60 MM": 1400.0})   # 1 por pieza × 2
        detalle = {"iluminacion": 0, "traseras": 0, "armado": 0, "fp": 0, "perfil": 5000.0,
                   "pintura": 0, "otros": 0, "valor_caja": 8000.0, "valor_total": 16000.0}
        d = _backlight("PERFIL 60 MM", cantidad=2)
        with mock.patch("core.precios.valor_caja_desde_guardado", lambda *a, **k: dict(detalle)):
            costo = costo_producto(d, textiles_valores={"Popelina": 0.0}, cobro_materiales=repo_mat.cobro_materiales_producto)
        self.assertEqual(costo["costo_caja"], 16000.0)        # el perfil sigue en la caja
        self.assertEqual(costo["costo_materiales"], 1400.0)  # y sus materiales se suman
        self.assertEqual(costo["total"], 16000.0 + 1400.0)

    def test_un_perfil_puede_valer_cero(self):
        from core import precios_componentes
        base = {"luces": {}, "traseras": {}, "armado": {}, "fp": {}, "perfiles": {"PERFIL 60 MM": 6974}, "pintura_por_ml": 4000}
        with mock.patch.dict(repo.PRECIOS_CAJAS, base, clear=True):
            datos = {**base, "perfiles": {"PERFIL 60 MM": 0}}
            self.assertEqual(precios_componentes.guardar_cajas(datos), {"ok": True})
            self.assertEqual(precios_componentes.cajas()["perfiles"]["PERFIL 60 MM"], 0.0)
            self.assertFalse(precios_componentes.guardar_cajas({**base, "pintura_por_ml": 0})["ok"])   # el resto no

    def test_otro_perfil_no_lo_gasta(self):
        self.material("Aluminio 60", estructuras=["PERFIL 60 MM"])
        self.assertEqual(repo_mat.materiales_para_producto(*repo_mat.claves_consumo(_backlight("PERFIL 80 MM"))), [])


class TestCorteBacklight(_Base):

    def test_por_defecto(self):
        self.assertEqual(corte_backlight.cargar(), {"caja_terminada": 0.015, "area_visual": 0.025})
        self.assertEqual(corte_backlight.margen("CAJA TERMINADA"), 0.015)
        self.assertEqual(corte_backlight.margen("AREA VISUAL"), 0.025)
        self.assertEqual(corte_backlight.margen("otra cosa"), 0.025)

    def test_guardar_y_la_op_lo_usa(self):
        from core import presentar_op
        self.assertEqual(corte_backlight.guardar({"caja_terminada": 0.02, "area_visual": 0.03}), {"ok": True})
        self.assertAlmostEqual(presentar_op._corte(1.0, "CAJA TERMINADA"), 1.02)
        self.assertEqual(presentar_op._fmt_margen_cm("AREA VISUAL"), "(+3 cms)")

    def test_fuera_de_rango_no_se_guarda(self):
        r = corte_backlight.guardar({"caja_terminada": -0.01, "area_visual": 0.5})
        self.assertEqual(set(r["errores"]), {"caja_terminada", "area_visual"})


if __name__ == "__main__":
    unittest.main()
