"""
tests/test_repositorio_inventario.py
Verifica core/repositorio_inventario.py: alta/edición/decomiso de rollos
con ID autogenerado (secuencial, 4 dígitos) y fecha de creación
(backfill para rollos guardados antes de que existiera el campo),
metros_iniciales opcional al crear, ajustar_restante (corrección manual
absoluta, siempre logueada) y su deshacer (solo la entrada más reciente —
ver eliminar_ajuste), el cálculo de metros necesarios/faltantes contra una
cotización (conversión de área a metros lineales para backlight, vía
core/precios.py), y el consumo automático al aprobar una cotización
(consumir_para_op) — que prioriza el rollo con MENOS metros restantes de
cada textil (no el más viejo): pedido de Bruno para forzar a terminar los
rollos flacos que se acumulan en la oficina en vez de siempre abrir uno
nuevo.

Usa un archivo temporal (mock de ROLLOS_PATH/HISTORIAL_PATH) — no toca
Dropbox/AppData reales. TEXTILES_ANCHOS también se mockea: core/precios.py
lo importa por nombre ("from core.repositorio import TEXTILES_ANCHOS"),
pero es el MISMO objeto dict que core.repositorio.TEXTILES_ANCHOS
(confirmado en vivo), así que un solo mock.patch.dict sobre ese alcanza
para los dos módulos — así los metros necesarios no dependen del
contenido real de recursos/textiles.json.

Correr con:  python -m unittest tests.test_repositorio_inventario -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_inventario as repo_inv

_ANCHOS = {"TelaTest": 1.5, "Backlight Test": 1.48}


def _producto_estandar(textil="TelaTest", ancho=1.5, alto=10.0, cantidad=1, impresion="Cara única"):
    return {
        "producto": "Pendón", "textil": textil, "estructuras": [], "terminaciones": [],
        "impresion": impresion, "ancho": ancho, "alto": alto, "cantidad": cantidad,
        "tema": "", "obs": "",
    }


def _producto_backlight(tela="Backlight Test", ancho=1.0, alto=1.0, cantidad=1):
    return {
        "tela": tela, "caja": "Sin caja", "ancho": ancho, "alto": alto,
        "cantidad": cantidad, "tema": "", "obs": "",
    }


class _ConRutaTemporalYCatalogo(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._parche_ruta = mock.patch.object(repo_inv, "ROLLOS_PATH", Path(self._tmp.name) / "rollos_tela.json")
        self._parche_ruta.start()
        self.addCleanup(self._parche_ruta.stop)
        self._parche_historial = mock.patch.object(
            repo_inv, "HISTORIAL_PATH", Path(self._tmp.name) / "rollos_tela_historial.json")
        self._parche_historial.start()
        self.addCleanup(self._parche_historial.stop)

        self._parche_anchos = mock.patch.dict("core.repositorio.TEXTILES_ANCHOS", _ANCHOS, clear=True)
        self._parche_anchos.start()
        self.addCleanup(self._parche_anchos.stop)


class TestCrearYEditarRollo(_ConRutaTemporalYCatalogo):

    def test_ids_autogenerados_secuenciales(self):
        r1 = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        r2 = repo_inv.crear_rollo("TelaTest", 1.5, 50)
        self.assertEqual(r1["id"], "0001")
        self.assertEqual(r2["id"], "0002")

    def test_metros_iniciales_opcional_por_defecto_igual_a_restantes(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        self.assertEqual(r["metros_iniciales"], 80.0)
        self.assertEqual(r["metros_restantes"], 80.0)

    def test_metros_iniciales_explicito_se_respeta(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80, 150)
        self.assertEqual(r["metros_iniciales"], 150.0)
        self.assertEqual(r["metros_restantes"], 80.0)

    def test_editar_rollo_solo_toca_textil_y_ancho(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        editado = repo_inv.editar_rollo(r["id"], "Backlight Test", 1.48)
        self.assertEqual(editado["nombre_textil"], "Backlight Test")
        self.assertEqual(editado["ancho"], 1.48)
        self.assertEqual(editado["metros_restantes"], 80.0)

    def test_editar_rollo_inexistente_da_none(self):
        self.assertIsNone(repo_inv.editar_rollo("9999", "X", 1.0))

    def test_crear_rollo_le_pone_fecha_de_hoy(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        self.assertEqual(r["fecha"], repo_inv._hoy_dma())

    def test_leer_hace_backfill_de_fecha_para_rollos_viejos(self):
        # Simula un rollo guardado antes de que existiera el campo "fecha"
        # (escribe directo el JSON, sin pasar por crear_rollo).
        repo_inv._escribir([{
            "id": "0001", "nombre_textil": "TelaTest", "ancho": 1.5,
            "metros_iniciales": 10.0, "metros_restantes": 10.0, "usos": [],
        }])
        rollos = repo_inv.listar_rollos()
        self.assertEqual(rollos[0]["fecha"], repo_inv._hoy_dma())
        # El backfill se guarda de verdad, no solo en la lectura en memoria.
        self.assertEqual(repo_inv._leer_json(repo_inv.ROLLOS_PATH)[0]["fecha"], repo_inv._hoy_dma())


class TestDecomisionarRollo(_ConRutaTemporalYCatalogo):

    def test_decomisionar_saca_el_rollo_de_la_lista_activa(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        self.assertTrue(repo_inv.decomisionar_rollo(r["id"]))
        self.assertIsNone(repo_inv.obtener_rollo(r["id"]))

    def test_decomisionar_inexistente_da_false(self):
        self.assertFalse(repo_inv.decomisionar_rollo("9999"))

    def test_decomisionar_archiva_el_registro_completo_con_fecha_de_decomiso(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        repo_inv.ajustar_restante(r["id"], 40, "Se usó a mano")
        repo_inv.decomisionar_rollo(r["id"])

        historial = repo_inv._leer_json(repo_inv.HISTORIAL_PATH)
        self.assertEqual(len(historial), 1)
        archivado = historial[0]
        self.assertEqual(archivado["id"], r["id"])
        self.assertEqual(archivado["metros_restantes"], 40.0)
        self.assertEqual(len(archivado["usos"]), 1)   # el historial de ajustes no se pierde
        self.assertEqual(archivado["fecha_decomiso"], repo_inv._hoy_dma())

    def test_decomisionar_no_afecta_otros_rollos(self):
        r1 = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        r2 = repo_inv.crear_rollo("TelaTest", 1.5, 40)
        repo_inv.decomisionar_rollo(r1["id"])
        self.assertIsNotNone(repo_inv.obtener_rollo(r2["id"]))
        self.assertEqual(len(repo_inv.listar_rollos()), 1)


class TestAjustarRestante(_ConRutaTemporalYCatalogo):

    def test_ajuste_baja_queda_logueado(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        actualizado = repo_inv.ajustar_restante(r["id"], 60, "Se usaron 40m sin registrar")
        self.assertEqual(actualizado["metros_restantes"], 60.0)
        self.assertEqual(len(actualizado["usos"]), 1)
        entrada = actualizado["usos"][0]
        self.assertEqual(entrada["tipo"], "ajuste")
        self.assertEqual(entrada["metros_restantes_anterior"], 100.0)
        self.assertEqual(entrada["metros_restantes_nuevo"], 60.0)
        self.assertEqual(entrada["descripcion"], "Se usaron 40m sin registrar")

    def test_ajuste_que_supera_iniciales_tambien_sube_iniciales(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 50, 50)
        actualizado = repo_inv.ajustar_restante(r["id"], 80, "Encontramos más stock")
        self.assertEqual(actualizado["metros_restantes"], 80.0)
        self.assertEqual(actualizado["metros_iniciales"], 80.0)

    def test_ajuste_que_no_supera_iniciales_no_lo_toca(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 50, 150)
        actualizado = repo_inv.ajustar_restante(r["id"], 80, "Recuento")
        self.assertEqual(actualizado["metros_iniciales"], 150.0)

    def test_ajuste_de_rollo_inexistente_da_none(self):
        self.assertIsNone(repo_inv.ajustar_restante("9999", 10, "x"))

    def test_eliminar_ajuste_mas_reciente_restaura_valor_anterior(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        actualizado = repo_inv.ajustar_restante(r["id"], 60, "Ajuste 1")
        id_ajuste = actualizado["usos"][-1]["id"]
        restaurado = repo_inv.eliminar_ajuste(r["id"], id_ajuste)
        self.assertEqual(restaurado["metros_restantes"], 100.0)
        self.assertEqual(restaurado["usos"], [])

    def test_eliminar_ajuste_que_no_es_el_mas_reciente_no_hace_nada(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        primero = repo_inv.ajustar_restante(r["id"], 60, "Ajuste 1")
        id_primero = primero["usos"][-1]["id"]
        repo_inv.ajustar_restante(r["id"], 40, "Ajuste 2")

        resultado = repo_inv.eliminar_ajuste(r["id"], id_primero)

        self.assertIsNone(resultado)
        actual = repo_inv.obtener_rollo(r["id"])
        self.assertEqual(actual["metros_restantes"], 40.0)
        self.assertEqual(len(actual["usos"]), 2)

    def test_eliminar_ajuste_de_rollo_inexistente_da_none(self):
        self.assertIsNone(repo_inv.eliminar_ajuste("9999", "loquesea"))


class TestMetrosNecesariosYFaltantes(_ConRutaTemporalYCatalogo):

    def test_producto_estandar_metros_es_ml_directo(self):
        # ancho tela = ancho producto = 1.5 -> UxA=1, ratio=1, ml=alto=10
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)
        necesarios = repo_inv.metros_necesarios([p])
        self.assertAlmostEqual(necesarios["TelaTest"], 10.0)

    def test_producto_backlight_convierte_area_a_metros_lineales(self):
        # área = 2*2*60 = 240 m²; ancho catálogo 1.48 -> 240/1.48 metros lineales
        p = _producto_backlight(ancho=2.0, alto=2.0, cantidad=60)
        necesarios = repo_inv.metros_necesarios([p])
        self.assertAlmostEqual(necesarios["Backlight Test"], 240 / 1.48, places=2)

    def test_agrupa_por_textil_sumando_varios_productos(self):
        p1 = _producto_estandar(ancho=1.5, alto=5.0, cantidad=1)
        p2 = _producto_estandar(ancho=1.5, alto=3.0, cantidad=1)
        necesarios = repo_inv.metros_necesarios([p1, p2])
        self.assertAlmostEqual(necesarios["TelaTest"], 8.0)

    def test_producto_sin_textil_no_cuenta(self):
        p = _producto_estandar(textil="", ancho=1.5, alto=10.0, cantidad=1)
        self.assertEqual(repo_inv.metros_necesarios([p]), {})

    def test_calcular_faltantes_vacio_con_stock_suficiente(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)
        self.assertEqual(repo_inv.calcular_faltantes([p]), [])

    def test_calcular_faltantes_reporta_textil_corto(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 5)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)
        faltantes = repo_inv.calcular_faltantes([p])
        self.assertEqual(len(faltantes), 1)
        self.assertEqual(faltantes[0]["textil"], "TelaTest")
        self.assertAlmostEqual(faltantes[0]["necesario"], 10.0)
        self.assertAlmostEqual(faltantes[0]["disponible"], 5.0)
        self.assertAlmostEqual(faltantes[0]["faltante"], 5.0)

    def test_calcular_faltantes_sin_stock_de_ese_textil(self):
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)
        faltantes = repo_inv.calcular_faltantes([p])
        self.assertEqual(faltantes[0]["disponible"], 0.0)

    def test_calcular_faltantes_suma_stock_de_varios_rollos(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 6)
        repo_inv.crear_rollo("TelaTest", 1.5, 6)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10
        self.assertEqual(repo_inv.calcular_faltantes([p]), [])  # 6+6=12 >= 10


class TestConsumirParaOp(_ConRutaTemporalYCatalogo):

    def test_consume_de_un_solo_rollo_si_alcanza(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10
        asignaciones = repo_inv.consumir_para_op([p], 4210, "Cliente ABC")

        actualizado = repo_inv.obtener_rollo(r["id"])
        self.assertEqual(actualizado["metros_restantes"], 90.0)
        self.assertEqual(len(actualizado["usos"]), 1)
        entrada = actualizado["usos"][0]
        self.assertEqual(entrada["tipo"], "consumo")
        self.assertIn("4210", entrada["descripcion"])
        self.assertIn("Cliente ABC", entrada["descripcion"])

        # El retorno es lo que ui/dialogo_aprobar.py graba como
        # producto["RollosUsados"] — el panel de producción lo lee tal cual.
        self.assertEqual(asignaciones, [[{"id": r["id"], "metros": 10.0}]])

    def test_prioriza_el_rollo_con_menos_metros_restantes_no_el_mas_viejo(self):
        # r1 (0001, "más viejo") tiene MÁS tela que r2 (0002, más nuevo) —
        # el consumo tiene que ir al que tiene MENOS, sin importar el ID.
        r1 = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        r2 = repo_inv.crear_rollo("TelaTest", 1.5, 6)
        p = _producto_estandar(ancho=1.5, alto=4.0, cantidad=1)  # necesita 4, r2 alcanza solo

        asignaciones = repo_inv.consumir_para_op([p], 4210)

        self.assertEqual(repo_inv.obtener_rollo(r1["id"])["metros_restantes"], 100.0)  # intacto
        self.assertEqual(repo_inv.obtener_rollo(r2["id"])["metros_restantes"], 2.0)
        self.assertEqual(asignaciones, [[{"id": r2["id"], "metros": 4.0}]])

    def test_un_producto_se_reparte_entre_varios_rollos_si_el_mas_chico_no_alcanza(self):
        r_chico = repo_inv.crear_rollo("TelaTest", 1.5, 3)
        r_grande = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10

        asignaciones = repo_inv.consumir_para_op([p], 4210)

        self.assertEqual(repo_inv.obtener_rollo(r_chico["id"])["metros_restantes"], 0.0)
        self.assertEqual(repo_inv.obtener_rollo(r_grande["id"])["metros_restantes"], 93.0)
        self.assertEqual(asignaciones, [[
            {"id": r_chico["id"], "metros": 3.0},
            {"id": r_grande["id"], "metros": 7.0},
        ]])

    def test_dos_productos_del_mismo_textil_no_pisan_el_stock_entre_si(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p1 = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10
        p2 = _producto_estandar(ancho=1.5, alto=5.0, cantidad=1)   # necesita 5

        asignaciones = repo_inv.consumir_para_op([p1, p2], 4210)

        self.assertEqual(repo_inv.obtener_rollo(r["id"])["metros_restantes"], 85.0)
        self.assertEqual(asignaciones, [
            [{"id": r["id"], "metros": 10.0}],
            [{"id": r["id"], "metros": 5.0}],
        ])
        self.assertEqual(len(repo_inv.obtener_rollo(r["id"])["usos"]), 2)

    def test_producto_sin_textil_da_lista_vacia_para_ese_indice(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p_vacio = _producto_estandar(textil="", ancho=1.5, alto=10.0, cantidad=1)
        p_real = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)

        asignaciones = repo_inv.consumir_para_op([p_vacio, p_real], 4210)

        self.assertEqual(asignaciones[0], [])
        self.assertEqual(asignaciones[1], [{"id": r["id"], "metros": 10.0}])

    def test_sin_productos_no_toca_nada(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        asignaciones = repo_inv.consumir_para_op([], 4210)
        self.assertEqual(asignaciones, [])
        self.assertEqual(repo_inv.obtener_rollo(r["id"])["metros_restantes"], 100.0)


class TestStockPorTextil(_ConRutaTemporalYCatalogo):

    def test_suma_por_textil(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 10)
        repo_inv.crear_rollo("TelaTest", 1.5, 5)
        repo_inv.crear_rollo("Backlight Test", 1.48, 20)
        stock = repo_inv.stock_por_textil()
        self.assertEqual(stock["TelaTest"], 15.0)
        self.assertEqual(stock["Backlight Test"], 20.0)


if __name__ == "__main__":
    unittest.main()
