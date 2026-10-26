"""
tests/test_catalogo.py
Agregar textiles, estructuras y terminaciones, y renombrar textiles
(core/catalogo.py): que aparezcan en los catálogos que usa el resto de la
app, que un renombre se lleve los rollos y el precio, y que una cotización
hecha con el nombre anterior siga funcionando. Conf e Inventario van a
carpetas temporales y la base del catálogo es fija — no toca Dropbox ni los
catálogos reales (los de core.repositorio se restauran al terminar).

Correr con:  python -m unittest tests.test_catalogo -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.ajustes_globales as ajustes_globales
import core.config as config
import core.repositorio as repo
import core.repositorio_inventario as repo_inv
import core.repositorio_materiales as repo_mat
from core import catalogo, precios_componentes, precios_textiles
from core.precios import costo_producto

LONA, GASA = "Lona test", "Gasa test"
SEMILLAS = {
    "textiles": [LONA, GASA], "anchos": {LONA: 1.5, GASA: 1.4}, "valores": {LONA: 10000.0, GASA: 8000.0},
    "backlight": [GASA],
    "estructuras": (["Asta"], {"Asta": {"valorUNIT": 5000.0}}),
    "terminaciones": (["Basta"], {"Basta": {"valorUNIT": 2000.0}}),
    "productos": ["Pendón", "Bandera 3x2"],
}


def _producto(textil=LONA, alto=3.0):
    return {"producto": "Pendón", "textil": textil, "estructuras": [], "terminaciones": [],
            "impresion": "Cara única", "ancho": 1.0, "alto": alto, "cantidad": 1, "tema": "", "obs": ""}


class _Base(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.conf = base / "Conf"
        # Los catálogos de core.repositorio son objetos compartidos que
        # catalogo modifica en el lugar: se guardan y se restauran.
        for nombre in ("TEXTILES", "ESTRUCTURAS_LEGADO", "TERMINACIONES_LEGADO", "PRODUCTOS"):
            lista = getattr(repo, nombre)
            copia = list(lista)
            self.addCleanup(lista.__setitem__, slice(None), copia)
        parches = [
            mock.patch.object(ajustes_globales, "_CONF_DIR", self.conf),
            mock.patch.object(repo_inv, "_ruta_base", lambda: base / "Inventario"),
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
        catalogo._aplicar(catalogo._leer())   # la base, sin archivo


class TestTextiles(_Base):

    def test_sin_archivo_refrescar_no_toca_nada(self):
        repo.TEXTILES.append("Algo de un test")
        catalogo._olvidar()
        catalogo.refrescar()
        self.assertIn("Algo de un test", repo.TEXTILES)

    def test_agregar_un_textil(self):
        r = catalogo.agregar_textil("  Lino   nuevo ", "1,6", backlight=True, valor=13000)
        self.assertEqual(r, {"ok": True})
        self.assertEqual(repo.TEXTILES, [LONA, GASA, "Lino nuevo"])
        self.assertEqual(repo.TEXTILES_ANCHOS["Lino nuevo"], 1.6)
        self.assertIn("Lino nuevo", catalogo.telas_backlight())
        fila = next(t for t in precios_textiles.cargar()["textiles"] if t["nombre"] == "Lino nuevo")
        self.assertEqual((fila["cobro"], fila["valor"], fila["ancho"]), ("fijo", 13000.0, 1.6))

    def test_lo_que_no_se_deja_agregar(self):
        casos = {
            "nombre": dict(nombre="lona TEST", ancho=1.5, valor=1),
            "ancho": dict(nombre="Otro", ancho=0, valor=1),
            "valor": dict(nombre="Otro", ancho=1.5, valor=None),
        }
        for campo, datos in casos.items():
            r = catalogo.agregar_textil(**datos)
            self.assertFalse(r["ok"], campo)
            self.assertIn(campo, r["errores"])
        self.assertEqual(repo.TEXTILES, [LONA, GASA])

    def test_por_rollo_tambien_hace_falta_el_valor(self):
        precios_textiles.guardar({"modo": "rollo", "textiles": []})
        self.assertIn("valor", catalogo.agregar_textil("Otro", 1.5)["errores"])

    def test_otra_instalacion_lo_cambio_en_dropbox(self):
        self.conf.mkdir(parents=True)
        ruta = self.conf / "catalogo.json"
        ruta.write_text(json.dumps({"version": 1, "textiles_agregados": [{"nombre": "Remoto", "ancho": 2}]}), encoding="utf-8")
        catalogo.refrescar()
        self.assertIn("Remoto", repo.TEXTILES)
        ruta.write_text(json.dumps({"version": 1, "textiles_agregados": [{"nombre": "Remoto 2", "ancho": 2}]}), encoding="utf-8")
        os.utime(ruta, ns=(ruta.stat().st_mtime_ns + 10**9,) * 2)
        catalogo.refrescar()
        self.assertEqual(repo.TEXTILES, [LONA, GASA, "Remoto 2"])


class TestRenombrar(_Base):

    def test_renombrar_se_lleva_los_rollos_el_ancho_y_el_precio(self):
        precios_textiles.guardar({"modo": "fijo", "textiles": [
            {"nombre": LONA, "cobro": "fijo", "valor": 11000}, {"nombre": GASA, "cobro": "fijo", "valor": 8000}]})
        repo_inv.crear_rollo(LONA, 1.5, 50, valor=12000)
        r = catalogo.editar_textil(LONA, "Lona nueva", 1.5, False)
        self.assertEqual(r, {"ok": True, "rollos": 1})
        self.assertEqual(repo.TEXTILES, ["Lona nueva", GASA])
        self.assertEqual([x["nombre_textil"] for x in repo_inv.listar_rollos()], ["Lona nueva"])
        fila = next(t for t in precios_textiles.cargar()["textiles"] if t["nombre"] == "Lona nueva")
        self.assertEqual(fila["valor"], 11000.0)
        self.assertEqual(catalogo.textiles()[0]["anteriores"], [LONA])

    def test_una_cotizacion_con_el_nombre_anterior_sigue_funcionando(self):
        repo_inv.crear_rollo(LONA, 1.5, 50, valor=12000)
        catalogo.editar_textil(LONA, "Lona nueva", 1.5, False)
        d = _producto(LONA)
        costo = costo_producto(d, **repo_mat.kwargs_precios())
        self.assertAlmostEqual(costo["ml_o_area"], 3.0)            # encontró el ancho
        self.assertAlmostEqual(costo["costo_impresion"], 3 * 10000)  # y el precio
        self.assertEqual(repo_inv.calcular_faltantes([d]), [])     # y los rollos

    def test_renombrar_dos_veces_y_volver_al_original(self):
        catalogo.editar_textil(LONA, "B", 1.5, False)
        catalogo.editar_textil("B", "C", 1.5, False)
        self.assertEqual(catalogo.alias_textiles(), {LONA: "C", "B": "C"})
        self.assertTrue(catalogo.editar_textil("C", LONA, 1.5, False)["ok"])
        self.assertEqual(catalogo.alias_textiles(), {"B": LONA, "C": LONA})
        self.assertEqual(repo.TEXTILES, [LONA, GASA])

    def test_no_puede_tomar_el_nombre_anterior_de_otro(self):
        catalogo.editar_textil(LONA, "Lona nueva", 1.5, False)
        r = catalogo.editar_textil(GASA, LONA, 1.4, True)
        self.assertFalse(r["ok"])
        self.assertIn("Lona nueva", r["errores"]["nombre"])

    def test_cambiar_el_ancho_y_backlight(self):
        catalogo.editar_textil(GASA, GASA, "1,45", False)
        self.assertEqual(repo.TEXTILES_ANCHOS[GASA], 1.45)
        self.assertEqual(catalogo.telas_backlight(), [])


class TestComponentes(_Base):

    def test_agregar_una_estructura_por_ml(self):
        r = catalogo.agregar_componente("estructuras", "Riel", "ML", 900)
        self.assertEqual(r, {"ok": True})
        self.assertEqual(repo.ESTRUCTURAS_LEGADO, ["Asta", "Riel"])
        self.assertEqual(precios_componentes.valores("estructuras")["Riel"], {"valorML": 900.0})
        self.assertEqual(repo_mat.kwargs_precios()["estructuras_legado_valores"]["Riel"], {"valorML": 900.0})

    def test_agregar_una_terminacion_y_cobrarla(self):
        catalogo.agregar_componente("terminaciones", "Doblez", "un.", 1500)
        d = {**_producto(), "terminaciones": ["Doblez"]}
        self.assertAlmostEqual(costo_producto(d, **repo_mat.kwargs_precios())["costo_terminaciones"], 1500)

    def test_lo_que_no_se_deja_agregar(self):
        for datos, campo in ((("basta", "un.", 1), "nombre"), (("Otra", "kg", 1), "unidad"), (("Otra", "un.", 0), "valor")):
            r = catalogo.agregar_componente("terminaciones", *datos)
            self.assertIn(campo, r["errores"])
        self.assertEqual(repo.TERMINACIONES_LEGADO, ["Basta"])



class TestQuitar(_Base):
    """Quitar saca de las listas donde se elige, pero los datos siguen para
    las cotizaciones viejas; agregarlo de nuevo lo devuelve (2026-10-26)."""

    def test_quitar_un_textil(self):
        repo_inv.crear_rollo(LONA, 1.5, 50, valor=12000)
        self.assertEqual(catalogo.quitar_textil(LONA), {"ok": True, "rollos": 1})
        self.assertEqual(repo.TEXTILES, [GASA])
        self.assertEqual(repo.TEXTILES_ANCHOS[LONA], 1.5)                 # una cotización vieja sigue calculando
        self.assertNotIn(LONA, [t["nombre"] for t in precios_textiles.cargar()["textiles"]])
        self.assertEqual([r["nombre_textil"] for r in repo_inv.listar_rollos()], [LONA])   # el rollo queda

    def test_agregar_de_nuevo_un_textil_quitado_lo_devuelve(self):
        catalogo.quitar_textil(LONA)
        self.assertEqual(catalogo.agregar_textil("lona TEST", 1.6, valor=9000), {"ok": True})
        self.assertEqual(repo.TEXTILES, [LONA, GASA])                       # a su lugar, con su nombre
        self.assertEqual(repo.TEXTILES_ANCHOS[LONA], 1.6)

    def test_quitar_una_estructura_suelta_sus_materiales(self):
        catalogo.agregar_componente("estructuras", "Riel", "ML", 900)
        m = repo_mat.ingresar_material("Tornillo", 10)
        repo_mat.editar_material(m["id"], "Tornillo", "unidad", valor=10, tipo_consumo="fijo_por_producto",
                                 consumo_parametros={"n": 1}, estructuras_asociadas=["Riel", "Asta"])
        self.assertEqual(catalogo.quitar_componente("estructuras", "Riel"), {"ok": True, "materiales": 1})
        self.assertEqual(repo.ESTRUCTURAS_LEGADO, ["Asta"])
        self.assertIn("Riel", repo.ESTRUCTURAS_LEGADO_VALORES)             # su valor sigue
        self.assertNotIn("Riel", [f["nombre"] for f in precios_componentes.cargar_lista("estructuras")])
        self.assertEqual(repo_mat.obtener_material(m["id"])["estructuras_asociadas"], ["Asta"])

    def test_quitar_y_devolver_una_terminacion_de_la_app(self):
        self.assertTrue(catalogo.quitar_componente("terminaciones", "Basta")["ok"])
        self.assertEqual(repo.TERMINACIONES_LEGADO, [])
        self.assertTrue(catalogo.agregar_componente("terminaciones", "basta", "ML", 2500)["ok"])
        self.assertEqual(repo.TERMINACIONES_LEGADO, ["Basta"])
        self.assertEqual(precios_componentes.valores("terminaciones")["Basta"], {"valorUNIT": 2500.0})   # su unidad de siempre


if __name__ == "__main__":
    unittest.main()
