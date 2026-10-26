"""
tests/test_precios_textiles.py
Cómo se cobra cada textil (core/precios_textiles.py): por un valor fijo o
por el valor del rollo del que sale, con el interruptor general de tres
posiciones; qué no se deja guardar; y que una cotización guarde el valor
que cobró cada producto (core/lista_precios.py). Usa carpetas temporales
para Conf e Inventario y catálogos fijos — no toca Dropbox ni los reales.

Correr con:  python -m unittest tests.test_precios_textiles -v
"""

import json
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
from core import lista_precios, precios_textiles
from core.precios import costo_producto

LONA, GASA = "Lona test", "Gasa test"


def _producto(textil=LONA, alto=3.0):
    # 1,5 m de ancho de tela: alto ML impresos (+1 de margen al elegir rollo).
    return {"producto": "Pendón", "textil": textil, "estructuras": [], "terminaciones": [],
            "impresion": "Cara única", "ancho": 1.5, "alto": alto, "cantidad": 1, "tema": "", "obs": ""}


def _fila(datos, nombre):
    return next(t for t in datos["textiles"] if t["nombre"] == nombre)


class _Base(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.conf = base / "Conf"
        parches = [
            mock.patch.object(ajustes_globales, "_CONF_DIR", self.conf),
            mock.patch.object(repo_inv, "_ruta_base", lambda: base / "Inventario"),
            mock.patch.object(repo, "TEXTILES", [LONA, GASA]),
            mock.patch.dict(repo.TEXTILES_VALORES, {LONA: 10000.0, GASA: 8000.0}, clear=True),
            mock.patch.dict(repo.TEXTILES_ANCHOS, {LONA: 1.5, GASA: 1.5}),
            mock.patch.dict(config.MODULOS_HABILITADOS, {"inventario": True}),
        ]
        for p in parches:
            p.start()
            self.addCleanup(p.stop)

    def guardar(self, modo, **textiles):
        """textiles: nombre=(cobro, valor)."""
        filas = [{"nombre": n, "cobro": c, "valor": v} for n, (c, v) in textiles.items()]
        return precios_textiles.guardar({"modo": modo, "textiles": filas})

    @staticmethod
    def valor(d):
        return precios_textiles.valorizador()(d)


class TestLeerYGuardar(_Base):

    def test_sin_archivo_parte_del_catalogo(self):
        datos = precios_textiles.cargar()
        self.assertEqual(datos["modo"], "fijo")
        self.assertEqual(_fila(datos, LONA), {"nombre": LONA, "ancho": 1.5, "cobro": "fijo", "valor": 10000.0})

    def test_guardar_y_volver_a_leer(self):
        self.assertEqual(self.guardar("por_textil", **{LONA: ("rollo", 7000), GASA: ("fijo", 9000)}), {"ok": True})
        datos = precios_textiles.cargar()
        self.assertEqual(datos["modo"], "por_textil")
        self.assertEqual((_fila(datos, LONA)["cobro"], _fila(datos, LONA)["valor"]), ("rollo", 7000.0))
        self.assertEqual(_fila(datos, GASA)["valor"], 9000.0)

    def test_lo_que_no_conoce_esta_version_se_conserva(self):
        self.conf.mkdir(parents=True)
        (self.conf / "precios_textiles.json").write_text(json.dumps({
            "version": 1, "modo": "fijo", "redondeo": 100,
            "textiles": {"Tela que esta versión no tiene": {"cobro": "fijo", "valor": 5}},
        }), encoding="utf-8")
        self.guardar("fijo", **{LONA: ("fijo", 1), GASA: ("fijo", 2)})
        guardado = json.loads((self.conf / "precios_textiles.json").read_text(encoding="utf-8"))
        self.assertEqual(guardado["redondeo"], 100)
        self.assertIn("Tela que esta versión no tiene", guardado["textiles"])

    def test_no_pisa_un_archivo_de_una_version_mas_nueva(self):
        self.conf.mkdir(parents=True)
        ruta = self.conf / "precios_textiles.json"
        ruta.write_text(json.dumps({"version": 99, "modo": "rollo"}), encoding="utf-8")
        self.assertTrue(precios_textiles.solo_lectura())
        r = self.guardar("fijo", **{LONA: ("fijo", 1), GASA: ("fijo", 2)})
        self.assertFalse(r["ok"])
        self.assertEqual(json.loads(ruta.read_text(encoding="utf-8"))["version"], 99)


class TestValidar(_Base):

    def test_todos_fijos_con_uno_sin_valor_no_se_guarda(self):
        r = self.guardar("fijo", **{LONA: ("fijo", 10000), GASA: ("rollo", None)})
        self.assertFalse(r["ok"])
        self.assertEqual([(e["textil"], e["mensaje"]) for e in r["errores"]], [(GASA, "Falta el valor por metro.")])
        self.assertFalse((self.conf / "precios_textiles.json").exists())

    def test_por_rollo_tambien_hace_falta_el_valor_fijo(self):
        # Es lo que se cobra si ningún rollo alcanza (decisión de Bruno, 2026-10-26).
        r = self.guardar("rollo", **{LONA: ("fijo", None), GASA: ("fijo", 1)})
        self.assertEqual([e["textil"] for e in r["errores"]], [LONA])
        r = self.guardar("por_textil", **{LONA: ("rollo", None), GASA: ("fijo", 1)})
        self.assertEqual([e["textil"] for e in r["errores"]], [LONA])
        self.assertTrue(self.guardar("por_textil", **{LONA: ("rollo", 5), GASA: ("fijo", 1)})["ok"])

    def test_un_valor_cero_o_negativo_no_vale(self):
        for malo in (0, -5, "abc"):
            r = self.guardar("rollo", **{LONA: ("fijo", malo), GASA: ("fijo", 1)})
            self.assertFalse(r["ok"], malo)

    def test_por_rollo_sin_inventario_no_vale(self):
        config.MODULOS_HABILITADOS["inventario"] = False
        self.assertFalse(self.guardar("rollo", **{LONA: ("fijo", 1), GASA: ("fijo", 1)})["ok"])


class TestValorizar(_Base):

    def rollos(self):
        # Lona: uno chico (6 m, $12.000) y uno grande (50 m, $14.000), el más nuevo.
        self.chico = repo_inv.crear_rollo(LONA, 1.5, 6, valor=12000)
        self.grande = repo_inv.crear_rollo(LONA, 1.5, 50, valor=14000)

    def test_fijo_usa_el_valor_de_configuracion(self):
        self.rollos()
        self.guardar("fijo", **{LONA: ("rollo", 11000), GASA: ("fijo", 1)})
        self.assertEqual(self.valor(_producto()), 11000.0)

    def test_por_rollo_usa_el_rollo_del_que_saldria(self):
        self.rollos()
        self.guardar("rollo", **{LONA: ("fijo", 11000), GASA: ("fijo", 1)})
        self.assertEqual(self.valor(_producto(alto=3)), 12000.0)    # 3 + 1 m entra en el chico
        self.assertEqual(self.valor(_producto(alto=10)), 14000.0)   # 11 m solo entran en el grande

    def test_por_rollo_sin_rollo_que_alcance_cobra_el_fijo(self):
        self.rollos()
        self.guardar("rollo", **{LONA: ("fijo", 11000), GASA: ("fijo", 1)})
        self.assertEqual(self.valor(_producto(alto=80)), 11000.0)
        self.assertEqual(precios_textiles.valorizador().detalle(_producto(alto=80))["origen"], "sin_rollo")

    def test_por_rollo_sin_rollos_cobra_el_fijo(self):
        self.guardar("rollo", **{LONA: ("fijo", 11000), GASA: ("fijo", 1)})
        self.assertEqual(self.valor(_producto()), 11000.0)

    def test_segun_cada_textil(self):
        self.rollos()
        repo_inv.crear_rollo(GASA, 1.5, 50, valor=9999)
        self.guardar("por_textil", **{LONA: ("rollo", 9999), GASA: ("fijo", 8500)})
        self.assertEqual(self.valor(_producto(LONA)), 12000.0)
        self.assertEqual(self.valor(_producto(GASA)), 8500.0)

    def test_costo_producto_cobra_con_el_valor_del_rollo(self):
        self.rollos()
        self.guardar("rollo", **{LONA: ("fijo", 1), GASA: ("fijo", 1)})
        costo = costo_producto(_producto(alto=3), **repo_mat.kwargs_precios())
        self.assertAlmostEqual(costo["costo_impresion"], 3 * 12000)

    def test_cambiar_todos_los_rollos_de_un_textil(self):
        self.rollos()
        repo_inv.crear_rollo(GASA, 1.5, 50, valor=9999)
        self.assertEqual(repo_inv.fijar_valor_rollos(LONA, 13000), 2)
        valores = {r["nombre_textil"]: set() for r in repo_inv.listar_rollos()}
        for r in repo_inv.listar_rollos():
            valores[r["nombre_textil"]].add(r["valor"])
        self.assertEqual(valores, {LONA: {13000.0}, GASA: {9999.0}})


    def test_detalle_dice_de_donde_sale_el_valor(self):
        self.rollos()
        self.assertTrue(self.guardar("por_textil", **{LONA: ("rollo", 11000), GASA: ("rollo", 7000)})["ok"])
        detalle = precios_textiles.valorizador().detalle
        self.assertEqual(detalle(_producto(alto=3))["origen"], "rollo")
        self.assertEqual((detalle(_producto(alto=80))["origen"], detalle(_producto(alto=80))["valor"]), ("sin_rollo", 11000.0))
        # Sin rollos: el fijo.
        self.assertEqual(detalle(_producto(GASA)), {"textil": GASA, "cobro": "rollo", "valor": 7000.0, "origen": "sin_rollo", "rollo": None})

    def test_textiles_sin_precio(self):
        # Solo con datos de antes de que el valor fijo fuera obligatorio.
        self.conf.mkdir(parents=True)
        (self.conf / "precios_textiles.json").write_text(json.dumps({
            "version": 1, "modo": "rollo", "textiles": {GASA: {"cobro": "rollo", "valor": None}}}), encoding="utf-8")
        self.assertEqual(precios_textiles.textiles_sin_precio(), [GASA])



class TestCotizacionPorRollo(_Base):
    """Por rollo, dos productos del mismo textil pueden cobrar distinto: la
    lista congelada guarda el valor de cada uno."""

    def setUp(self):
        super().setUp()
        mats = mock.patch.object(repo_mat, "estructuras_legado_valores_efectivos", lambda: dict(repo.ESTRUCTURAS_LEGADO_VALORES))
        cobro = mock.patch.object(repo_mat, "cobro_materiales_producto", lambda d: None)
        for p in (mats, cobro):
            p.start()
            self.addCleanup(p.stop)
        repo_inv.crear_rollo(LONA, 1.5, 6, valor=12000)
        self.grande = repo_inv.crear_rollo(LONA, 1.5, 50, valor=14000)
        self.guardar("rollo", **{LONA: ("fijo", 1), GASA: ("fijo", 1)})
        self.internos = [_producto(alto=3), _producto(alto=10)]

    def datos(self):
        return {"Cotizacion": 1, "Descuento": 0, "productos": [],
                "ListaPrecios": lista_precios.armar(self.internos)}

    def test_guarda_el_valor_de_cada_producto(self):
        lista = self.datos()["ListaPrecios"]
        self.assertEqual(lista["valores_textil"], [12000.0, 14000.0])
        kwargs = lista_precios.kwargs_congelados(lista)
        for d, v in zip(self.internos, lista["valores_textil"]):
            d["_valor_textil"] = v
        self.assertEqual([costo_producto(d, **kwargs)["costo_impresion"] for d in self.internos],
                         [3 * 12000.0, 10 * 14000.0])

    def test_el_cambio_de_un_rollo_se_ve_por_producto(self):
        datos = self.datos()
        repo_inv.fijar_valor_rollos(LONA, 15000)
        filas = lista_precios._textiles(datos["ListaPrecios"], lista_precios.armar(self.internos), self.internos)
        self.assertEqual([(a, b) for _, a, b, _ in filas], [(12000.0, 15000.0), (14000.0, 15000.0)])
        self.assertTrue(all(n.startswith(f"{LONA} · ") for n, *_ in filas))


if __name__ == "__main__":
    unittest.main()
