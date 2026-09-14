"""
tests/test_repositorio_materiales.py
Verifica core/repositorio_materiales.py: ingresar_material crea o suma a un
material existente (buscado por nombre, no por ID — no hay ID visible),
costo_total/costo_unitario se autocompletan entre sí, editar_material
cambia tipo/valor/proveedor sin tocar cantidad, registrar_uso/
ajustar_cantidad/eliminar_ultimo_historial (deshacer solo la entrada más
reciente), gasto_del_mes, y el archivado anual del historial (mismo
mecanismo que Decomisionados/AAAA/MM de rollos, pero acá vacía+archiva el
array completo apenas se detecta un año vencido).

Usa una carpeta temporal (mock de _ruta_base) — no toca Dropbox/AppData
reales.

Correr con:  python -m unittest tests.test_repositorio_materiales -v
"""

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_materiales as repo_mat


class _ConRutaTemporal(unittest.TestCase):
    """Además de la carpeta temporal (mock de _ruta_base), mockea el
    catálogo estático a VACÍO por default — listar_materiales() siembra un
    registro en cero por cada nombre de core.repositorio.ESTRUCTURAS_LEGADO
    (ver _sembrar_desde_catalogo), y con el catálogo real de
    recursos/estructuras_legado.json esa siembra ensuciaría cualquier test
    que cuente materiales o dependa de que un nombre "no existía todavía".
    TestSiembraDesdeCatalogo pisa este mock con su propio catálogo de
    prueba cuando quiere probar la siembra en sí."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._base = Path(self._tmp.name)
        self._parche = mock.patch.object(repo_mat, "_ruta_base", lambda: self._base)
        self._parche.start()
        self.addCleanup(self._parche.stop)

        self._parche_catalogo = mock.patch.multiple(
            "core.repositorio", ESTRUCTURAS_LEGADO=[], ESTRUCTURAS_LEGADO_VALORES={},
        )
        self._parche_catalogo.start()
        self.addCleanup(self._parche_catalogo.stop)


class TestIngresarMaterial(_ConRutaTemporal):

    def test_material_nuevo_se_crea_con_id_oculto_y_uuid(self):
        m = repo_mat.ingresar_material("Base auto", 5)
        self.assertEqual(m["nombre"], "Base auto")
        self.assertEqual(m["cantidad"], 5.0)
        self.assertEqual(len(m["id"]), 32)  # uuid4hex

    def test_segundo_ingreso_mismo_nombre_suma_en_vez_de_duplicar(self):
        repo_mat.ingresar_material("Base auto", 5)
        m = repo_mat.ingresar_material("Base auto", 3)
        self.assertEqual(m["cantidad"], 8.0)
        self.assertEqual(len(repo_mat.listar_materiales()), 1)

    def test_busqueda_por_nombre_es_case_insensitive(self):
        repo_mat.ingresar_material("Base Auto", 5)
        m = repo_mat.ingresar_material("base auto", 2)
        self.assertEqual(m["cantidad"], 7.0)
        self.assertEqual(len(repo_mat.listar_materiales()), 1)

    def test_costo_unitario_se_deriva_de_costo_total(self):
        m = repo_mat.ingresar_material("Estaca", 10, costo_total=100000)
        self.assertEqual(m["historial"][-1]["costo_unitario"], 10000.0)

    def test_costo_total_se_deriva_de_costo_unitario(self):
        m = repo_mat.ingresar_material("Estaca", 10, costo_unitario=10000)
        self.assertEqual(m["historial"][-1]["costo_total"], 100000.0)

    def test_material_nuevo_con_costo_siembra_valor_inicial(self):
        m = repo_mat.ingresar_material("Estaca", 10, costo_unitario=10000)
        self.assertEqual(m["valor"], 10000.0)

    def test_material_nuevo_sin_costo_queda_sin_valor(self):
        m = repo_mat.ingresar_material("Estaca", 10)
        self.assertIsNone(m["valor"])

    def test_ingreso_a_material_existente_no_pisa_valor(self):
        repo_mat.ingresar_material("Estaca", 10, costo_unitario=10000)
        m = repo_mat.ingresar_material("Estaca", 5, costo_unitario=99999)
        self.assertEqual(m["valor"], 10000.0)  # sigue el original, no el de la 2da compra

    def test_tipo_solo_se_aplica_si_el_material_es_nuevo(self):
        repo_mat.ingresar_material("Estaca", 10, tipo="metro")
        m = repo_mat.ingresar_material("Estaca", 5, tipo="unidad")
        self.assertEqual(m["tipo"], "metro")

    def test_tipo_invalido_cae_a_unidad(self):
        m = repo_mat.ingresar_material("Estaca", 10, tipo="litros")
        self.assertEqual(m["tipo"], "unidad")

    def test_proveedor_vacio_no_borra_el_ya_cargado(self):
        repo_mat.ingresar_material("Estaca", 10, proveedor="Ferretería X")
        m = repo_mat.ingresar_material("Estaca", 5, proveedor="")
        self.assertEqual(m["proveedor"], "Ferretería X")

    def test_proveedor_nuevo_reemplaza_al_anterior(self):
        repo_mat.ingresar_material("Estaca", 10, proveedor="Ferretería X")
        m = repo_mat.ingresar_material("Estaca", 5, proveedor="Ferretería Y")
        self.assertEqual(m["proveedor"], "Ferretería Y")

    def test_entrada_de_historial_queda_tipo_compra(self):
        m = repo_mat.ingresar_material("Estaca", 10)
        self.assertEqual(m["historial"][-1]["tipo"], "compra")
        self.assertEqual(m["historial"][-1]["cantidad_anterior"], 0.0)
        self.assertEqual(m["historial"][-1]["cantidad_nueva"], 10.0)


class TestEditarMaterial(_ConRutaTemporal):

    def test_edita_nombre_tipo_valor_proveedor(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        editado = repo_mat.editar_material(creado["id"], "Estaca grande", "metro", valor=5000, proveedor="Prov X")
        self.assertEqual(editado["nombre"], "Estaca grande")
        self.assertEqual(editado["tipo"], "metro")
        self.assertEqual(editado["valor"], 5000.0)
        self.assertEqual(editado["proveedor"], "Prov X")

    def test_editar_no_toca_cantidad_ni_historial(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        editado = repo_mat.editar_material(creado["id"], "Estaca", "unidad", valor=1000)
        self.assertEqual(editado["cantidad"], 10.0)
        self.assertEqual(len(editado["historial"]), 1)

    def test_valor_none_limpia_el_valor(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_unitario=5000)
        editado = repo_mat.editar_material(creado["id"], "Estaca", "unidad", valor=None)
        self.assertIsNone(editado["valor"])

    def test_material_inexistente_da_none(self):
        self.assertIsNone(repo_mat.editar_material("no-existe", "X", "unidad"))


class TestUsoYAjuste(_ConRutaTemporal):

    def test_registrar_uso_resta_y_loguea(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        m = repo_mat.registrar_uso(creado["id"], 3, descripcion="Se usaron en OP 1001")
        self.assertEqual(m["cantidad"], 7.0)
        self.assertEqual(m["historial"][-1]["tipo"], "uso")
        self.assertEqual(m["historial"][-1]["cantidad_anterior"], 10.0)
        self.assertEqual(m["historial"][-1]["cantidad_nueva"], 7.0)

    def test_ajustar_cantidad_es_absoluto_no_delta(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        m = repo_mat.ajustar_cantidad(creado["id"], 25, descripcion="Recuento físico")
        self.assertEqual(m["cantidad"], 25.0)
        self.assertEqual(m["historial"][-1]["tipo"], "ajuste")

    def test_eliminar_ultimo_historial_deshace_uso(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        usado = repo_mat.registrar_uso(creado["id"], 3)
        id_entrada = usado["historial"][-1]["id"]
        m = repo_mat.eliminar_ultimo_historial(creado["id"], id_entrada)
        self.assertEqual(m["cantidad"], 10.0)
        self.assertEqual(len(m["historial"]), 1)  # solo queda la compra original

    def test_eliminar_no_ultimo_no_hace_nada(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        primera_id = creado["historial"][-1]["id"]
        repo_mat.registrar_uso(creado["id"], 3)
        self.assertIsNone(repo_mat.eliminar_ultimo_historial(creado["id"], primera_id))

    def test_material_inexistente_da_none_en_uso_y_ajuste(self):
        self.assertIsNone(repo_mat.registrar_uso("no-existe", 1))
        self.assertIsNone(repo_mat.ajustar_cantidad("no-existe", 1))


class TestGastoDelMes(_ConRutaTemporal):

    def test_solo_suma_compras_del_mes_en_curso(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_total=50000)
        m = repo_mat.obtener_material(creado["id"])
        # Fuerzo una compra vieja (otro mes) a mano, agregándola al historial.
        m["historial"].insert(0, {
            "id": "vieja", "fecha": "01/01/2020", "tipo": "compra",
            "cantidad_anterior": 0.0, "cantidad_nueva": 100.0,
            "descripcion": "", "proveedor": "", "costo_total": 999999.0, "costo_unitario": None,
        })
        repo_mat._escribir_material(m)
        m = repo_mat.obtener_material(creado["id"])
        self.assertEqual(repo_mat.gasto_del_mes(m), 50000.0)

    def test_deriva_costo_desde_costo_unitario_si_falta_total(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_unitario=5000)
        m = repo_mat.obtener_material(creado["id"])
        self.assertEqual(repo_mat.gasto_del_mes(m), 50000.0)

    def test_ajustes_y_usos_no_cuentan_como_gasto(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_total=50000)
        repo_mat.registrar_uso(creado["id"], 2)
        repo_mat.ajustar_cantidad(creado["id"], 20)
        m = repo_mat.obtener_material(creado["id"])
        self.assertEqual(repo_mat.gasto_del_mes(m), 50000.0)

    def test_sin_compras_da_cero(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        m = repo_mat.obtener_material(creado["id"])
        m["historial"] = []
        self.assertEqual(repo_mat.gasto_del_mes(m), 0.0)


class TestValoresLegadoYPrecios(_ConRutaTemporal):

    def test_material_sin_valor_no_aparece(self):
        repo_mat.ingresar_material("Estaca", 10)
        self.assertEqual(repo_mat.valores_legado_materiales(), {})

    def test_tipo_unidad_da_valorUNIT(self):
        repo_mat.ingresar_material("Estaca", 10, costo_unitario=5000)
        self.assertEqual(repo_mat.valores_legado_materiales(), {"Estaca": {"valorUNIT": 5000.0}})

    def test_tipo_metro_da_valorML(self):
        creado = repo_mat.ingresar_material("Cinta", 10, tipo="metro", costo_unitario=200)
        self.assertEqual(repo_mat.valores_legado_materiales(), {"Cinta": {"valorML": 200.0}})

    def test_efectivos_mezcla_catalogo_estatico_con_materiales(self):
        repo_mat.ingresar_material("Base auto", 5, costo_unitario=15000)
        catalogo_mock = {"Base auto": {"valorUNIT": 11000.0}, "Estaca": {"valorUNIT": 10000.0}}
        with mock.patch("core.repositorio.ESTRUCTURAS_LEGADO_VALORES", catalogo_mock):
            efectivos = repo_mat.estructuras_legado_valores_efectivos()
        self.assertEqual(efectivos["Base auto"], {"valorUNIT": 15000.0})  # material pisa al catálogo
        self.assertEqual(efectivos["Estaca"], {"valorUNIT": 10000.0})     # sin material, queda el catálogo


class TestArchivadoAnual(_ConRutaTemporal):

    def test_material_de_anio_vencido_se_archiva_y_vacia_al_leer(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_total=10000)
        m = repo_mat.obtener_material(creado["id"])
        m["anio_historial"] = 2020
        repo_mat._escribir_material(m)

        releido = repo_mat.obtener_material(creado["id"])

        self.assertEqual(releido["historial"], [])
        self.assertEqual(releido["anio_historial"], datetime.now().year)
        archivo = self._base / "Historial" / "2020" / "Materiales" / f"{creado['id']}.json"
        self.assertTrue(archivo.exists())

    def test_material_del_anio_en_curso_no_se_toca(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        releido = repo_mat.obtener_material(creado["id"])
        self.assertEqual(len(releido["historial"]), 1)
        archivo = self._base / "Historial" / str(datetime.now().year) / "Materiales" / f"{creado['id']}.json"
        self.assertFalse(archivo.exists())


class TestSiembraDesdeCatalogo(_ConRutaTemporal):
    """listar_materiales() tiene que mostrar TODOS los materiales del
    catálogo estático, aunque nunca se haya ingresado nada de ese nombre
    todavía (pedido de Bruno, 2026-09-15) — pisa el catálogo vacío de
    _ConRutaTemporal con uno de prueba propio."""

    def setUp(self):
        super().setUp()
        self._catalogo = mock.patch.multiple(
            "core.repositorio",
            ESTRUCTURAS_LEGADO=["Base auto", "Cinta doble contacto"],
            ESTRUCTURAS_LEGADO_VALORES={
                "Base auto": {"valorUNIT": 11000.0},
                "Cinta doble contacto": {"valorML": 500.0},
            },
        )
        self._catalogo.start()
        self.addCleanup(self._catalogo.stop)

    def test_lista_materiales_del_catalogo_en_cero(self):
        materiales = repo_mat.listar_materiales()
        nombres = {m["nombre"] for m in materiales}
        self.assertEqual(nombres, {"Base auto", "Cinta doble contacto"})
        for m in materiales:
            self.assertEqual(m["cantidad"], 0.0)
            self.assertIsNone(m["valor"])
            self.assertEqual(m["proveedor"], "")
            self.assertEqual(m["historial"], [])

    def test_tipo_se_deriva_del_catalogo(self):
        por_nombre = {m["nombre"]: m for m in repo_mat.listar_materiales()}
        self.assertEqual(por_nombre["Base auto"]["tipo"], "unidad")
        self.assertEqual(por_nombre["Cinta doble contacto"]["tipo"], "metro")

    def test_sembrado_no_pisa_ni_duplica_material_ya_existente(self):
        ingresado = repo_mat.ingresar_material("Base auto", 5, costo_unitario=20000)
        materiales = repo_mat.listar_materiales()
        self.assertEqual(len([m for m in materiales if m["nombre"] == "Base auto"]), 1)
        base_auto = next(m for m in materiales if m["nombre"] == "Base auto")
        self.assertEqual(base_auto["id"], ingresado["id"])
        self.assertEqual(base_auto["cantidad"], 5.0)
        self.assertEqual(base_auto["valor"], 20000.0)  # el del ingreso real, no el del catálogo

    def test_sembrado_no_cambia_el_precio_efectivo(self):
        # valor=None en el sembrado -> estructuras_legado_valores_efectivos
        # sigue resolviendo contra el catálogo estático, sin cambios.
        repo_mat.listar_materiales()
        efectivos = repo_mat.estructuras_legado_valores_efectivos()
        self.assertEqual(efectivos["Base auto"], {"valorUNIT": 11000.0})
        self.assertEqual(efectivos["Cinta doble contacto"], {"valorML": 500.0})

    def test_segunda_llamada_no_duplica_ni_reescribe(self):
        primera = repo_mat.listar_materiales()
        archivos_primera = sorted((self._base / "Materiales").glob("*.json"))
        segunda = repo_mat.listar_materiales()
        archivos_segunda = sorted((self._base / "Materiales").glob("*.json"))
        self.assertEqual(len(primera), len(segunda))
        self.assertEqual(archivos_primera, archivos_segunda)

    def test_primera_compra_real_siembra_valor_del_material_sembrado(self):
        # El material ya existe (sembrado en cero, valor=None) antes de
        # este ingreso — la primera compra real igual tiene que fijarle un
        # valor inicial, no solo cuando el registro se crea en el mismo
        # llamado (ver docstring de ingresar_material).
        repo_mat.listar_materiales()  # fuerza la siembra
        m = repo_mat.ingresar_material("Base auto", 3, costo_unitario=25000)
        self.assertEqual(m["valor"], 25000.0)


if __name__ == "__main__":
    unittest.main()
