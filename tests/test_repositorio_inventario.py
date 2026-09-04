"""
tests/test_repositorio_inventario.py
Verifica core/repositorio_inventario.py: alta/edición/decomiso de rollos
con ID autogenerado (secuencial, 4 dígitos, sin reusar IDs decomisionados)
y fecha de creación (backfill para rollos guardados antes de que existiera
el campo), metros_iniciales opcional al crear, ajustar_restante
(corrección manual absoluta, siempre logueada) y su deshacer (solo la
entrada más reciente — ver eliminar_ajuste), el cálculo de metros
necesarios/faltantes contra una cotización (conversión de área a metros
lineales para backlight, vía core/precios.py), y el consumo automático al
aprobar una cotización (consumir_para_op) — que prioriza el rollo con
MENOS metros restantes de cada textil (no el más viejo): pedido de Bruno
para forzar a terminar los rollos flacos que se acumulan en la oficina en
vez de siempre abrir uno nuevo.

Cada rollo es su propio archivo JSON (Activos/<id>.json,
Decomisionados/AAAA/MM/<id>.json — ver docstring del módulo). Usa una
carpeta temporal (mock de _ruta_base) — no toca Dropbox/AppData reales.
TEXTILES_ANCHOS también se mockea: core/precios.py lo importa por nombre
("from core.repositorio import TEXTILES_ANCHOS"), pero es el MISMO objeto
dict que core.repositorio.TEXTILES_ANCHOS (confirmado en vivo), así que un
solo mock.patch.dict sobre ese alcanza para los dos módulos — así los
metros necesarios no dependen del contenido real de recursos/textiles.json.

Correr con:  python -m unittest tests.test_repositorio_inventario -v
"""

import sys
import tempfile
import unittest
from datetime import datetime
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
        base = Path(self._tmp.name) / "Inventario"
        self._parche_ruta = mock.patch.object(repo_inv, "_ruta_base", lambda: base)
        self._parche_ruta.start()
        self.addCleanup(self._parche_ruta.stop)

        self._parche_anchos = mock.patch.dict("core.repositorio.TEXTILES_ANCHOS", _ANCHOS, clear=True)
        self._parche_anchos.start()
        self.addCleanup(self._parche_anchos.stop)


class TestCrearYEditarRollo(_ConRutaTemporalYCatalogo):

    def test_ids_autogenerados_secuenciales(self):
        r1 = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        r2 = repo_inv.crear_rollo("TelaTest", 1.5, 50)
        self.assertEqual(r1["id"], "0001")
        self.assertEqual(r2["id"], "0002")

    def test_metros_iniciales_siempre_igual_a_restantes(self):
        # Ya no lo ingresa el usuario (pedido de Bruno, 2026-09-03) — un
        # rollo SIEMPRE entra completo, sin excepción.
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        self.assertEqual(r["metros_iniciales"], 80.0)
        self.assertEqual(r["metros_restantes"], 80.0)

    def test_precio_compra_y_proveedor_quedan_guardados(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80, precio_compra=450000, proveedor="Textiles del Sur")
        self.assertEqual(r["precio_compra"], 450000.0)
        self.assertEqual(r["proveedor"], "Textiles del Sur")

    def test_precio_compra_y_proveedor_por_defecto_vacios(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        self.assertEqual(r["precio_compra"], 0.0)
        self.assertEqual(r["proveedor"], "")

    def test_rollo_nuevo_arranca_activo(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        self.assertEqual(r["estado"], "activo")

    def test_valor_explicito_se_respeta(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80, valor=9500)
        self.assertEqual(r["valor"], 9500.0)

    def test_valor_por_defecto_usa_el_del_ultimo_rollo_del_mismo_textil(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 80, valor=9000)
        repo_inv.crear_rollo("TelaTest", 1.5, 40, valor=9500)  # el más nuevo
        r3 = repo_inv.crear_rollo("TelaTest", 1.5, 60)  # sin valor -> hereda del último
        self.assertEqual(r3["valor"], 9500.0)

    def test_valor_por_defecto_sin_rollo_previo_usa_catalogo_de_textiles(self):
        with mock.patch.dict("core.repositorio.TEXTILES_VALORES", {"TelaTest": 11000.0}, clear=True):
            r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
            self.assertEqual(r["valor"], 11000.0)

    def test_valor_por_defecto_sin_rollo_previo_ni_catalogo_queda_none(self):
        with mock.patch.dict("core.repositorio.TEXTILES_VALORES", {}, clear=True):
            r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
            self.assertIsNone(r["valor"])

    def test_editar_rollo_actualiza_textil_ancho_precio_valor_y_proveedor(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        editado = repo_inv.editar_rollo(
            r["id"], "Backlight Test", 1.48,
            precio_compra=300000, valor=12000, proveedor="Proveedor X")
        self.assertEqual(editado["nombre_textil"], "Backlight Test")
        self.assertEqual(editado["ancho"], 1.48)
        self.assertEqual(editado["precio_compra"], 300000.0)
        self.assertEqual(editado["valor"], 12000.0)
        self.assertEqual(editado["proveedor"], "Proveedor X")
        self.assertEqual(editado["metros_restantes"], 80.0)  # no lo toca

    def test_editar_rollo_inexistente_da_none(self):
        self.assertIsNone(repo_inv.editar_rollo("9999", "X", 1.0))

    def test_crear_rollo_le_pone_fecha_de_hoy(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        self.assertEqual(r["fecha"], repo_inv._hoy_dma())

    def test_leer_hace_backfill_de_fecha_para_rollos_viejos(self):
        # Simula un rollo guardado antes de que existiera el campo "fecha"
        # (escribe directo el JSON, sin pasar por crear_rollo).
        repo_inv._escribir_rollo(repo_inv.carpeta_activos(), {
            "id": "0001", "nombre_textil": "TelaTest", "ancho": 1.5,
            "metros_iniciales": 10.0, "metros_restantes": 10.0, "usos": [],
        })
        rollos = repo_inv.listar_rollos()
        self.assertEqual(rollos[0]["fecha"], repo_inv._hoy_dma())
        # El backfill se guarda de verdad, no solo en la lectura en memoria.
        self.assertEqual(repo_inv.obtener_rollo("0001")["fecha"], repo_inv._hoy_dma())

    def test_rollo_viejo_sin_los_campos_nuevos_recibe_defaults_al_leer(self):
        # Simula un rollo guardado antes de precio_compra/valor/proveedor/
        # estado — a diferencia de "fecha", estos defaults NO se inventan
        # (valor queda None, no una adivinanza) y no se persisten solos.
        repo_inv._escribir_rollo(repo_inv.carpeta_activos(), {
            "id": "0002", "nombre_textil": "TelaTest", "ancho": 1.5,
            "metros_iniciales": 10.0, "metros_restantes": 10.0,
            "fecha": "01/01/2026", "usos": [],
        })
        r = repo_inv.obtener_rollo("0002")
        self.assertEqual(r["precio_compra"], 0.0)
        self.assertIsNone(r["valor"])
        self.assertEqual(r["proveedor"], "")
        self.assertEqual(r["estado"], "activo")


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

        archivos = list(repo_inv.carpeta_decomisionados().rglob("*.json"))
        self.assertEqual(len(archivos), 1)
        archivado = repo_inv._leer_rollo(archivos[0])
        self.assertEqual(archivado["id"], r["id"])
        self.assertEqual(archivado["metros_restantes"], 40.0)
        self.assertEqual(len(archivado["usos"]), 1)   # el historial de ajustes no se pierde
        self.assertEqual(archivado["fecha_decomiso"], repo_inv._hoy_dma())

        hoy = datetime.now()
        ruta_esperada = (repo_inv.carpeta_decomisionados()
                          / f"{hoy.year:04d}" / f"{hoy.month:02d}" / f"{r['id']}.json")
        self.assertEqual(archivos[0], ruta_esperada)

    def test_decomisionar_no_afecta_otros_rollos(self):
        r1 = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        r2 = repo_inv.crear_rollo("TelaTest", 1.5, 40)
        repo_inv.decomisionar_rollo(r1["id"])
        self.assertIsNotNone(repo_inv.obtener_rollo(r2["id"]))
        self.assertEqual(len(repo_inv.listar_rollos()), 1)

    def test_id_de_rollo_decomisionado_no_se_reusa(self):
        r1 = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        repo_inv.decomisionar_rollo(r1["id"])
        r2 = repo_inv.crear_rollo("TelaTest", 1.5, 40)
        self.assertNotEqual(r2["id"], r1["id"])


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
        r = repo_inv.crear_rollo("TelaTest", 1.5, 50)
        actualizado = repo_inv.ajustar_restante(r["id"], 80, "Encontramos más stock")
        self.assertEqual(actualizado["metros_restantes"], 80.0)
        self.assertEqual(actualizado["metros_iniciales"], 80.0)

    def test_ajuste_que_no_supera_iniciales_no_lo_toca(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 150)  # iniciales también queda en 150
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
        # + 1 de MARGEN_TENSION_ML (ver core.repositorio_inventario) = 11
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)
        necesarios = repo_inv.metros_necesarios([p])
        self.assertAlmostEqual(necesarios["TelaTest"], 11.0)

    def test_producto_backlight_convierte_area_a_metros_lineales(self):
        # área = 2*2*60 = 240 m²; ancho catálogo 1.48 -> 240/1.48 metros
        # lineales + 1 de MARGEN_TENSION_ML
        p = _producto_backlight(ancho=2.0, alto=2.0, cantidad=60)
        necesarios = repo_inv.metros_necesarios([p])
        self.assertAlmostEqual(necesarios["Backlight Test"], 240 / 1.48 + 1.0, places=2)

    def test_agrupa_por_textil_sumando_varios_productos(self):
        # 5+1 (margen) + 3+1 (margen) = 10 — el margen es POR PRODUCTO, no
        # una vez por textil (ver MARGEN_TENSION_ML).
        p1 = _producto_estandar(ancho=1.5, alto=5.0, cantidad=1)
        p2 = _producto_estandar(ancho=1.5, alto=3.0, cantidad=1)
        necesarios = repo_inv.metros_necesarios([p1, p2])
        self.assertAlmostEqual(necesarios["TelaTest"], 10.0)

    def test_producto_sin_textil_no_cuenta(self):
        p = _producto_estandar(textil="", ancho=1.5, alto=10.0, cantidad=1)
        self.assertEqual(repo_inv.metros_necesarios([p]), {})

    def test_calcular_faltantes_vacio_con_stock_suficiente(self):
        # Necesita 10 + 1 de margen = 11; 100 alcanza de sobra.
        repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)
        self.assertEqual(repo_inv.calcular_faltantes([p]), [])

    def test_calcular_faltantes_reporta_textil_corto(self):
        # Necesita 10 + 1 de margen = 11; hay 5 -> faltan 6.
        repo_inv.crear_rollo("TelaTest", 1.5, 5)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)
        faltantes = repo_inv.calcular_faltantes([p])
        self.assertEqual(len(faltantes), 1)
        self.assertEqual(faltantes[0]["textil"], "TelaTest")
        self.assertAlmostEqual(faltantes[0]["necesario"], 11.0)
        self.assertAlmostEqual(faltantes[0]["disponible"], 5.0)
        self.assertAlmostEqual(faltantes[0]["faltante"], 6.0)

    def test_calcular_faltantes_sin_stock_de_ese_textil(self):
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)
        faltantes = repo_inv.calcular_faltantes([p])
        self.assertEqual(faltantes[0]["disponible"], 0.0)

    def test_calcular_faltantes_suma_stock_de_varios_rollos(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 6)
        repo_inv.crear_rollo("TelaTest", 1.5, 6)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10+1
        self.assertEqual(repo_inv.calcular_faltantes([p]), [])  # 6+6=12 >= 11


class TestConsumirParaOp(_ConRutaTemporalYCatalogo):

    def test_consume_de_un_solo_rollo_si_alcanza(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10+1 (margen)
        asignaciones = repo_inv.consumir_para_op([p], 4210, "Cliente ABC")

        actualizado = repo_inv.obtener_rollo(r["id"])
        self.assertEqual(actualizado["metros_restantes"], 89.0)
        self.assertEqual(len(actualizado["usos"]), 1)
        entrada = actualizado["usos"][0]
        self.assertEqual(entrada["tipo"], "consumo")
        self.assertIn("4210", entrada["descripcion"])
        self.assertIn("Cliente ABC", entrada["descripcion"])

        # El retorno es lo que ui/dialogo_aprobar.py graba como
        # producto["RollosUsados"] — el panel de producción lo lee tal cual.
        self.assertEqual(asignaciones, [[{"id": r["id"], "metros": 11.0}]])

    def test_un_rollo_justo_al_ml_real_no_alcanza_por_el_margen_de_tension(self):
        # Pedido de Bruno (2026-09-03): un rollo de exactamente 7 m NO puede
        # cubrir un producto que necesita 7 ML reales — hacen falta 8 (7 +
        # MARGEN_TENSION_ML) para que la máquina mantenga la tensión.
        r_justo = repo_inv.crear_rollo("TelaTest", 1.5, 7)
        r_con_margen = repo_inv.crear_rollo("TelaTest", 1.5, 8)
        p = _producto_estandar(ancho=1.5, alto=7.0, cantidad=1)  # necesita 7+1=8

        asignaciones = repo_inv.consumir_para_op([p], 4210)

        # r_justo (7m, el "más chico") no cubre solo los 8 que hacen falta,
        # así que se reparte con r_con_margen — no se lo deja en 0 en falso.
        self.assertEqual(repo_inv.obtener_rollo(r_justo["id"])["metros_restantes"], 0.0)
        self.assertEqual(repo_inv.obtener_rollo(r_con_margen["id"])["metros_restantes"], 7.0)
        self.assertEqual(asignaciones, [[
            {"id": r_justo["id"], "metros": 7.0},
            {"id": r_con_margen["id"], "metros": 1.0},
        ]])

    def test_prioriza_el_rollo_con_menos_metros_restantes_no_el_mas_viejo(self):
        # r1 (0001, "más viejo") tiene MÁS tela que r2 (0002, más nuevo) —
        # el consumo tiene que ir al que tiene MENOS, sin importar el ID.
        r1 = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        r2 = repo_inv.crear_rollo("TelaTest", 1.5, 6)
        p = _producto_estandar(ancho=1.5, alto=4.0, cantidad=1)  # necesita 4+1=5, r2 alcanza solo

        asignaciones = repo_inv.consumir_para_op([p], 4210)

        self.assertEqual(repo_inv.obtener_rollo(r1["id"])["metros_restantes"], 100.0)  # intacto
        self.assertEqual(repo_inv.obtener_rollo(r2["id"])["metros_restantes"], 1.0)
        self.assertEqual(asignaciones, [[{"id": r2["id"], "metros": 5.0}]])

    def test_un_producto_se_reparte_entre_varios_rollos_si_el_mas_chico_no_alcanza(self):
        r_chico = repo_inv.crear_rollo("TelaTest", 1.5, 3)
        r_grande = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10+1=11

        asignaciones = repo_inv.consumir_para_op([p], 4210)

        self.assertEqual(repo_inv.obtener_rollo(r_chico["id"])["metros_restantes"], 0.0)
        self.assertEqual(repo_inv.obtener_rollo(r_grande["id"])["metros_restantes"], 92.0)
        self.assertEqual(asignaciones, [[
            {"id": r_chico["id"], "metros": 3.0},
            {"id": r_grande["id"], "metros": 8.0},
        ]])

    def test_dos_productos_del_mismo_textil_no_pisan_el_stock_entre_si(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p1 = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10+1=11
        p2 = _producto_estandar(ancho=1.5, alto=5.0, cantidad=1)   # necesita 5+1=6

        asignaciones = repo_inv.consumir_para_op([p1, p2], 4210)

        self.assertEqual(repo_inv.obtener_rollo(r["id"])["metros_restantes"], 83.0)
        self.assertEqual(asignaciones, [
            [{"id": r["id"], "metros": 11.0}],
            [{"id": r["id"], "metros": 6.0}],
        ])
        self.assertEqual(len(repo_inv.obtener_rollo(r["id"])["usos"]), 2)

    def test_producto_sin_textil_da_lista_vacia_para_ese_indice(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        p_vacio = _producto_estandar(textil="", ancho=1.5, alto=10.0, cantidad=1)
        p_real = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10+1=11

        asignaciones = repo_inv.consumir_para_op([p_vacio, p_real], 4210)

        self.assertEqual(asignaciones[0], [])
        self.assertEqual(asignaciones[1], [{"id": r["id"], "metros": 11.0}])

    def test_sin_productos_no_toca_nada(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        asignaciones = repo_inv.consumir_para_op([], 4210)
        self.assertEqual(asignaciones, [])
        self.assertEqual(repo_inv.obtener_rollo(r["id"])["metros_restantes"], 100.0)

    def test_rollo_inactivo_no_se_puede_consumir(self):
        # Aunque sea el único rollo del textil y le sobre tela, un rollo
        # "inactivo" (ver cambiar_estado_rollo) queda afuera del reparto —
        # el producto se queda sin cubrir, como si no hubiera stock.
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        repo_inv.cambiar_estado_rollo(r["id"], activo=False)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10+1=11

        asignaciones = repo_inv.consumir_para_op([p], 4210)

        self.assertEqual(asignaciones, [[]])
        self.assertEqual(repo_inv.obtener_rollo(r["id"])["metros_restantes"], 100.0)  # intacto


class TestStockPorTextil(_ConRutaTemporalYCatalogo):

    def test_suma_por_textil(self):
        repo_inv.crear_rollo("TelaTest", 1.5, 10)
        repo_inv.crear_rollo("TelaTest", 1.5, 5)
        repo_inv.crear_rollo("Backlight Test", 1.48, 20)
        stock = repo_inv.stock_por_textil()
        self.assertEqual(stock["TelaTest"], 15.0)
        self.assertEqual(stock["Backlight Test"], 20.0)

    def test_rollo_inactivo_no_cuenta_para_el_stock(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 10)
        repo_inv.crear_rollo("TelaTest", 1.5, 5)
        repo_inv.cambiar_estado_rollo(r["id"], activo=False)
        stock = repo_inv.stock_por_textil()
        self.assertEqual(stock["TelaTest"], 5.0)


class TestCambiarEstadoRollo(_ConRutaTemporalYCatalogo):

    def test_inactivar_y_reactivar(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        inactivado = repo_inv.cambiar_estado_rollo(r["id"], activo=False)
        self.assertEqual(inactivado["estado"], "inactivo")
        reactivado = repo_inv.cambiar_estado_rollo(r["id"], activo=True)
        self.assertEqual(reactivado["estado"], "activo")

    def test_rollo_inexistente_da_none(self):
        self.assertIsNone(repo_inv.cambiar_estado_rollo("9999", activo=False))

    def test_rollo_inactivo_sigue_apareciendo_en_listar_rollos(self):
        # Estado inactivo NO lo saca de la tabla — solo del cálculo de
        # stock/consumo (ver test_rollo_inactivo_no_cuenta_para_el_stock y
        # TestConsumirParaOp.test_rollo_inactivo_no_se_puede_consumir).
        r = repo_inv.crear_rollo("TelaTest", 1.5, 80)
        repo_inv.cambiar_estado_rollo(r["id"], activo=False)
        ids = [x["id"] for x in repo_inv.listar_rollos()]
        self.assertIn(r["id"], ids)

    def test_rollo_inactivo_hace_que_calcular_faltantes_lo_ignore(self):
        r = repo_inv.crear_rollo("TelaTest", 1.5, 100)
        repo_inv.cambiar_estado_rollo(r["id"], activo=False)
        p = _producto_estandar(ancho=1.5, alto=10.0, cantidad=1)  # necesita 10+1=11
        faltantes = repo_inv.calcular_faltantes([p])
        self.assertEqual(len(faltantes), 1)
        self.assertEqual(faltantes[0]["disponible"], 0.0)


class TestMigrarFormatoViejo(_ConRutaTemporalYCatalogo):
    """Migración de rollos_tela.json/rollos_tela_historial.json (formato
    de antes, una lista JSON única) al formato actual (un archivo por
    rollo). No usa _ConRutaTemporalYCatalogo.setUp para ROLLOS_PATH_VIEJO/
    HISTORIAL_PATH_VIEJO — esos se mockean acá, por test, para no
    depender de _CONF_DIR real."""

    def setUp(self):
        super().setUp()
        self._viejo_rollos = Path(self._tmp.name) / "rollos_tela.json"
        self._viejo_historial = Path(self._tmp.name) / "rollos_tela_historial.json"
        self._parche_viejo_rollos = mock.patch.object(repo_inv, "ROLLOS_PATH_VIEJO", self._viejo_rollos)
        self._parche_viejo_rollos.start()
        self.addCleanup(self._parche_viejo_rollos.stop)
        self._parche_viejo_historial = mock.patch.object(repo_inv, "HISTORIAL_PATH_VIEJO", self._viejo_historial)
        self._parche_viejo_historial.start()
        self.addCleanup(self._parche_viejo_historial.stop)

    def test_migra_rollos_activos_a_un_archivo_por_rollo(self):
        self._viejo_rollos.write_text(
            '[{"id": "0001", "nombre_textil": "TelaTest", "ancho": 1.5, '
            '"metros_iniciales": 10.0, "metros_restantes": 10.0, "fecha": "01/01/2026", "usos": []}]',
            encoding="utf-8",
        )
        repo_inv.migrar_formato_viejo()

        rollo = repo_inv.obtener_rollo("0001")
        self.assertIsNotNone(rollo)
        self.assertEqual(rollo["nombre_textil"], "TelaTest")
        self.assertFalse(self._viejo_rollos.exists())
        self.assertTrue(self._viejo_rollos.with_name("rollos_tela.json.migrado").exists())

    def test_migra_historial_a_decomisionados_por_mes(self):
        self._viejo_historial.write_text(
            '[{"id": "0002", "nombre_textil": "TelaTest", "ancho": 1.5, '
            '"metros_iniciales": 10.0, "metros_restantes": 0.0, "fecha": "01/01/2026", '
            '"usos": [], "fecha_decomiso": "15/03/2026"}]',
            encoding="utf-8",
        )
        repo_inv.migrar_formato_viejo()

        destino = repo_inv.carpeta_decomisionados() / "2026" / "03" / "0002.json"
        self.assertTrue(destino.exists())
        self.assertFalse(self._viejo_historial.exists())

    def test_migrar_sin_archivos_viejos_no_hace_nada(self):
        repo_inv.migrar_formato_viejo()  # no debe reventar
        self.assertEqual(repo_inv.listar_rollos(), [])

    def test_migrar_es_idempotente(self):
        self._viejo_rollos.write_text(
            '[{"id": "0001", "nombre_textil": "TelaTest", "ancho": 1.5, '
            '"metros_iniciales": 10.0, "metros_restantes": 10.0, "fecha": "01/01/2026", "usos": []}]',
            encoding="utf-8",
        )
        repo_inv.migrar_formato_viejo()
        repo_inv.migrar_formato_viejo()  # no debe reventar ni duplicar
        self.assertEqual(len(repo_inv.listar_rollos()), 1)


if __name__ == "__main__":
    unittest.main()
