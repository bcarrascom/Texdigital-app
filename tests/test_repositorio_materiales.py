"""
tests/test_repositorio_materiales.py
Verifica core/repositorio_materiales.py: ingresar_material crea o suma a un
material existente (buscado por nombre, no por ID — no hay ID visible),
costo_total/costo_unitario se autocompletan entre sí, editar_material
cambia tipo/valor/proveedor sin tocar cantidad, ajustar_cantidad/
eliminar_ultimo_historial (deshacer solo la entrada más reciente), gasto_del_mes, y el archivado anual del historial (mismo
mecanismo que Decomisionados/AAAA/MM de rollos, pero acá vacía+archiva el
array completo apenas se detecta un año vencido).

Usa una carpeta temporal (mock de _ruta_base) — no toca Dropbox/AppData
reales.

Correr con:  python -m unittest tests.test_repositorio_materiales -v
"""

import json
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

    def test_material_nuevo_con_costo_no_siembra_precio_de_venta(self):
        # Antes (2026-09) el costo de la 1a compra se copiaba a "valor" como
        # "mejor estimación disponible"; desde el modelo económico de
        # 2026-10-01 eso sería cobrar exactamente lo que costó (ganancia 0).
        m = repo_mat.ingresar_material("Estaca", 10, costo_unitario=10000)
        self.assertIsNone(m["valor"])
        self.assertEqual(m["gasto_unitario"], 10000.0)

    def test_material_nuevo_sin_costo_queda_sin_valor(self):
        m = repo_mat.ingresar_material("Estaca", 10)
        self.assertIsNone(m["valor"])

    def test_ingreso_a_material_existente_no_pisa_valor(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_unitario=10000)
        repo_mat.ajustar_valor(creado["id"], 18000)
        m = repo_mat.ingresar_material("Estaca", 5, costo_unitario=99999)
        self.assertEqual(m["valor"], 18000.0)  # el precio de venta es decisión aparte

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

    def test_entrada_de_historial_queda_tipo_restock(self):
        m = repo_mat.ingresar_material("Estaca", 10)
        self.assertEqual(m["historial"][-1]["tipo"], "restock")
        self.assertEqual(m["historial"][-1]["cantidad_anterior"], 0.0)
        self.assertEqual(m["historial"][-1]["cantidad_nueva"], 10.0)

    def test_sin_fecha_usa_hoy(self):
        m = repo_mat.ingresar_material("Estaca", 10)
        self.assertEqual(m["historial"][-1]["fecha"], datetime.now().strftime("%d/%m/%Y"))

    def test_fecha_explicita_se_respeta(self):
        m = repo_mat.ingresar_material("Estaca", 10, fecha="05/03/2026")
        self.assertEqual(m["historial"][-1]["fecha"], "05/03/2026")


class TestEditarMaterial(_ConRutaTemporal):

    def test_edita_nombre_tipo_valor_proveedor(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        editado = repo_mat.editar_material(creado["id"], "Estaca grande", "metro", valor=5000, proveedor="Prov X")
        self.assertEqual(editado["nombre"], "Estaca grande")
        self.assertEqual(editado["tipo"], "metro")
        self.assertEqual(editado["valor"], 5000.0)
        self.assertEqual(editado["proveedor"], "Prov X")

    def test_editar_no_toca_cantidad(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        editado = repo_mat.editar_material(creado["id"], "Estaca", "unidad", valor=1000)
        self.assertEqual(editado["cantidad"], 10.0)

    def test_editar_registra_el_cambio_de_precio_en_el_historial(self):
        # Pedido explícito de Bruno (2026-10-01): un cambio de precio de
        # venta nunca pasa sin dejar rastro, por qué formulario entró no
        # cambia eso.
        creado = repo_mat.ingresar_material("Estaca", 10)
        editado = repo_mat.editar_material(creado["id"], "Estaca", "unidad", valor=1000)
        self.assertEqual(len(editado["historial"]), 2)
        entrada = editado["historial"][-1]
        self.assertEqual(entrada["tipo"], "precio")
        self.assertIsNone(entrada["valor_anterior"])
        self.assertEqual(entrada["valor_nuevo"], 1000.0)
        # No mueve stock: la cantidad de antes y la de después son la misma.
        self.assertEqual(entrada["cantidad_anterior"], entrada["cantidad_nueva"])

    def test_editar_sin_cambiar_el_precio_no_registra_nada(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        repo_mat.editar_material(creado["id"], "Estaca", "unidad", valor=1000)
        editado = repo_mat.editar_material(creado["id"], "Estaca 2", "unidad", valor=1000)
        self.assertEqual(len(editado["historial"]), 2)  # sigue siendo compra + 1 precio

    def test_valor_none_limpia_el_valor(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_unitario=5000)
        editado = repo_mat.editar_material(creado["id"], "Estaca", "unidad", valor=None)
        self.assertIsNone(editado["valor"])

    def test_material_inexistente_da_none(self):
        self.assertIsNone(repo_mat.editar_material("no-existe", "X", "unidad"))


class TestEliminarMaterial(_ConRutaTemporal):

    def test_elimina_para_siempre(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        self.assertTrue(repo_mat.eliminar_material(creado["id"]))
        self.assertIsNone(repo_mat.obtener_material(creado["id"]))
        self.assertNotIn("Estaca", [m["nombre"] for m in repo_mat.listar_materiales()])

    def test_inexistente_da_false(self):
        self.assertFalse(repo_mat.eliminar_material("no-existe"))

    def test_limpia_sus_asociaciones_del_indice(self):
        creado = repo_mat.ingresar_material(
            "Ojal", 10, tipo_consumo="fijo_por_producto",
            consumo_parametros={"n": 1}, productos_asociados=["Pendón"],
        )
        repo_mat.eliminar_material(creado["id"])
        self.assertEqual(repo_mat.materiales_para_producto("Pendón"), [])


class TestAjustarCantidad(_ConRutaTemporal):
    """ajustar_cantidad es el único movimiento de stock manual que queda — el
    tipo "uso" se eliminó (decisión de Bruno, 2026-10-01: "dejémoslo como
    ajuste"), así que una merma o una rotura entra por acá."""

    def test_es_absoluto_no_delta(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        m = repo_mat.ajustar_cantidad(creado["id"], 25, descripcion="Recuento físico")
        self.assertEqual(m["cantidad"], 25.0)
        self.assertEqual(m["historial"][-1]["tipo"], "ajuste")

    def test_ajuste_a_la_baja_sirve_de_merma(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        m = repo_mat.ajustar_cantidad(creado["id"], 7, descripcion="3 estacas dobladas")
        self.assertEqual(m["cantidad"], 7.0)
        entrada = m["historial"][-1]
        self.assertEqual(entrada["tipo"], "ajuste")
        # La entrada guarda las DOS cantidades, así que el delta (-3) se deriva
        # sin tener que guardarlo aparte — es lo que muestra la UI.
        self.assertEqual(entrada["cantidad_anterior"] - entrada["cantidad_nueva"], 3.0)

    def test_eliminar_ultimo_historial_deshace_el_ajuste(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        ajustado = repo_mat.ajustar_cantidad(creado["id"], 7)
        id_entrada = ajustado["historial"][-1]["id"]
        m = repo_mat.eliminar_ultimo_historial(creado["id"], id_entrada)
        self.assertEqual(m["cantidad"], 10.0)
        self.assertEqual(len(m["historial"]), 1)  # solo queda el restock original

    def test_eliminar_no_ultimo_no_hace_nada(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        primera_id = creado["historial"][-1]["id"]
        repo_mat.ajustar_cantidad(creado["id"], 7)
        self.assertIsNone(repo_mat.eliminar_ultimo_historial(creado["id"], primera_id))

    def test_material_inexistente_da_none(self):
        self.assertIsNone(repo_mat.ajustar_cantidad("no-existe", 1))


class TestTiposRenombrados(_ConRutaTemporal):
    """Los dos tipos de entrada que ya no se escriben se convierten al LEER
    (ver _TIPOS_RENOMBRADOS) — un material guardado por una versión anterior
    tiene que verse igual que uno nuevo, sin migración a mano."""

    def test_compra_vieja_se_lee_como_restock(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_total=50000)
        ruta = repo_mat.carpeta_materiales() / f"{creado['id']}.json"
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["historial"][0]["tipo"] = "compra"  # como lo guardaba la versión vieja
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        m = repo_mat.obtener_material(creado["id"])
        self.assertEqual(m["historial"][0]["tipo"], "restock")
        # Y sigue contando como gasto del mes, que es lo que filtra por el tipo
        self.assertEqual(repo_mat.gasto_del_mes(m), 50000.0)

    def test_uso_viejo_se_lee_como_ajuste(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        ruta = repo_mat.carpeta_materiales() / f"{creado['id']}.json"
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["historial"].append({
            "id": "viejo", "fecha": "01/09/2026", "tipo": "uso",
            "cantidad_anterior": 10.0, "cantidad_nueva": 7.0, "descripcion": "merma",
        })
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        m = repo_mat.obtener_material(creado["id"])
        self.assertEqual(m["historial"][-1]["tipo"], "ajuste")

    def test_el_tipo_nuevo_queda_en_disco_al_escribir(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_total=50000)
        ruta = repo_mat.carpeta_materiales() / f"{creado['id']}.json"
        self.assertEqual(json.loads(ruta.read_text(encoding="utf-8"))["historial"][0]["tipo"],
                          "restock")


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

    def test_los_ajustes_no_cuentan_como_gasto(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_total=50000)
        repo_mat.ajustar_cantidad(creado["id"], 8)
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
        creado = repo_mat.ingresar_material("Estaca", 10)
        repo_mat.ajustar_valor(creado["id"], 5000)
        self.assertEqual(repo_mat.valores_legado_materiales(), {"Estaca": {"valorUNIT": 5000.0}})

    def test_tipo_metro_da_valorML(self):
        creado = repo_mat.ingresar_material("Cinta", 10, tipo="metro")
        repo_mat.ajustar_valor(creado["id"], 200)
        self.assertEqual(repo_mat.valores_legado_materiales(), {"Cinta": {"valorML": 200.0}})

    def test_efectivos_mezcla_catalogo_estatico_con_materiales(self):
        base = repo_mat.ingresar_material("Base auto", 5)
        repo_mat.ajustar_valor(base["id"], 15000)
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


class TestInventarioApagado(_ConRutaTemporal):
    """Con core.config.MODULOS_HABILITADOS["inventario"] en False (pedido
    de Bruno, 2026-09-16 — sacar un release con Inventario todavía
    pausado), los materiales NO deben pisar el precio de ninguna
    cotización: estructuras_legado_valores_efectivos tiene que devolver el
    catálogo estático tal cual."""

    def setUp(self):
        super().setUp()
        self._parche_modulo = mock.patch.dict(
            "core.config.MODULOS_HABILITADOS", {"inventario": False},
        )
        self._parche_modulo.start()
        self.addCleanup(self._parche_modulo.stop)

    def test_no_pisa_el_catalogo_estatico(self):
        repo_mat.ingresar_material("Base auto", 5, costo_unitario=99999)  # valor editado
        catalogo_mock = {"Base auto": {"valorUNIT": 11000.0}}
        with mock.patch("core.repositorio.ESTRUCTURAS_LEGADO_VALORES", catalogo_mock):
            efectivos = repo_mat.estructuras_legado_valores_efectivos()
        self.assertEqual(efectivos, catalogo_mock)  # el 99999 del material NO aparece


class TestCalcularConsumo(unittest.TestCase):
    """calcular_consumo — las 3 fórmulas con parámetros (pedido de Bruno,
    2026-09-27). Función pura, no toca disco."""

    def test_fijo_por_producto(self):
        material = {"tipo_consumo": "fijo_por_producto", "consumo_parametros": {"n": 2}}
        self.assertEqual(repo_mat.calcular_consumo(material, medida=0.0, cantidad_producto=3), 6.0)

    def test_fijo_por_producto_ignora_la_medida(self):
        material = {"tipo_consumo": "fijo_por_producto", "consumo_parametros": {"n": 1}}
        self.assertEqual(
            repo_mat.calcular_consumo(material, medida=999.0, cantidad_producto=1),
            repo_mat.calcular_consumo(material, medida=0.1, cantidad_producto=1),
        )

    def test_metro_lineal_directo(self):
        material = {"tipo_consumo": "metro_lineal_directo", "consumo_parametros": {}}
        self.assertEqual(repo_mat.calcular_consumo(material, medida=4.5, cantidad_producto=2), 9.0)

    def test_metro_lineal_salto_redondea_para_arriba(self):
        # paso=2, medida=5 -> 3 bloques (no 2.5) -> 3 * n * cantidad
        material = {"tipo_consumo": "metro_lineal_salto", "consumo_parametros": {"paso": 2, "n": 1}}
        self.assertEqual(repo_mat.calcular_consumo(material, medida=5.0, cantidad_producto=1), 3.0)

    def test_metro_lineal_salto_bloque_exacto_no_redondea_de_mas(self):
        material = {"tipo_consumo": "metro_lineal_salto", "consumo_parametros": {"paso": 2, "n": 1}}
        self.assertEqual(repo_mat.calcular_consumo(material, medida=4.0, cantidad_producto=1), 2.0)

    def test_metro_lineal_salto_multiplica_por_n_y_cantidad(self):
        material = {"tipo_consumo": "metro_lineal_salto", "consumo_parametros": {"paso": 2, "n": 3}}
        # 5m -> 3 bloques * n=3 * cantidad=2 productos = 18
        self.assertEqual(repo_mat.calcular_consumo(material, medida=5.0, cantidad_producto=2), 18.0)

    def test_metro_lineal_salto_sin_paso_da_cero(self):
        material = {"tipo_consumo": "metro_lineal_salto", "consumo_parametros": {"paso": 0, "n": 3}}
        self.assertEqual(repo_mat.calcular_consumo(material, medida=5.0, cantidad_producto=1), 0.0)

    def test_manual_da_cero_aca(self):
        # "manual" se resuelve en consumir_para_op vía consumos_manuales,
        # no en calcular_consumo.
        material = {"tipo_consumo": "manual", "consumo_parametros": {}}
        self.assertEqual(repo_mat.calcular_consumo(material, medida=5.0, cantidad_producto=1), 0.0)

    def test_sin_tipo_consumo_da_cero(self):
        material = {"tipo_consumo": None, "consumo_parametros": {}}
        self.assertEqual(repo_mat.calcular_consumo(material, medida=5.0, cantidad_producto=1), 0.0)


class TestIndiceConsumo(_ConRutaTemporal):
    """El índice invertido (productos_asociados/estructuras_asociadas de
    cada material -> indice_consumo.json) se reconstruye solo al editar,
    y materiales_para_producto lo resuelve sin escanear todos los
    materiales — pedido de Bruno (2026-09-27)."""

    def test_se_reconstruye_al_editar_asociaciones(self):
        m = repo_mat.ingresar_material("Adhesivo", 10)
        repo_mat.editar_material(
            m["id"], "Adhesivo", "unidad",
            productos_asociados=["Bandera"], estructuras_asociadas=["Base auto"],
        )
        por_producto = repo_mat.materiales_para_producto("Bandera", [])
        por_estructura = repo_mat.materiales_para_producto("Otro producto", ["Base auto"])
        self.assertEqual([x["id"] for x in por_producto], [m["id"]])
        self.assertEqual([x["id"] for x in por_estructura], [m["id"]])

    def test_producto_sin_asociacion_no_devuelve_nada(self):
        repo_mat.ingresar_material("Adhesivo", 10)
        self.assertEqual(repo_mat.materiales_para_producto("Nada que ver", []), [])

    def test_deduplica_si_matchea_por_producto_y_estructura_a_la_vez(self):
        m = repo_mat.ingresar_material("Adhesivo", 10)
        repo_mat.editar_material(
            m["id"], "Adhesivo", "unidad",
            productos_asociados=["Bandera"], estructuras_asociadas=["Base auto"],
        )
        resultado = repo_mat.materiales_para_producto("Bandera", ["Base auto"])
        self.assertEqual(len(resultado), 1)

    def test_editar_reemplaza_las_asociaciones_no_las_suma(self):
        m = repo_mat.ingresar_material("Adhesivo", 10)
        repo_mat.editar_material(m["id"], "Adhesivo", "unidad", productos_asociados=["Bandera"])
        repo_mat.editar_material(m["id"], "Adhesivo", "unidad", productos_asociados=["Estandarte"])
        self.assertEqual(repo_mat.materiales_para_producto("Bandera", []), [])
        self.assertEqual([x["id"] for x in repo_mat.materiales_para_producto("Estandarte", [])], [m["id"]])

    def test_sobrevive_a_un_rename_del_material(self):
        # El índice guarda IDs, no nombres — renombrar el material no lo
        # deja huérfano.
        m = repo_mat.ingresar_material("Adhesivo", 10)
        repo_mat.editar_material(m["id"], "Adhesivo", "unidad", productos_asociados=["Bandera"])
        repo_mat.editar_material(m["id"], "Adhesivo doble contacto", "unidad", productos_asociados=["Bandera"])
        resultado = repo_mat.materiales_para_producto("Bandera", [])
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["nombre"], "Adhesivo doble contacto")

    def test_ingresar_material_nuevo_con_asociaciones_ya_queda_indexado(self):
        m = repo_mat.ingresar_material(
            "Ojal", 5, productos_asociados=["Bandera"], estructuras_asociadas=[],
        )
        self.assertEqual([x["id"] for x in repo_mat.materiales_para_producto("Bandera", [])], [m["id"]])

    def test_ingresar_a_material_existente_no_toca_sus_asociaciones(self):
        m = repo_mat.ingresar_material("Ojal", 5, productos_asociados=["Bandera"])
        # Un segundo ingreso al mismo material (por nombre) pasa
        # productos_asociados=None (como haría el diálogo "+", que no
        # vuelve a mandar asociaciones para un material existente) — no
        # debe borrar lo que ya tenía.
        repo_mat.ingresar_material("Ojal", 3)
        self.assertEqual([x["id"] for x in repo_mat.materiales_para_producto("Bandera", [])], [m["id"]])


def _producto_interno(producto="", textil="TelaTest", ancho=1.0, alto=1.0, cantidad=1, estructuras=None):
    return {
        "producto": producto, "textil": textil,
        "estructuras": estructuras or [], "terminaciones": [],
        "impresion": "Cara única", "ancho": ancho, "alto": alto, "cantidad": cantidad,
        "tema": "", "obs": "",
    }


class TestConsumirParaOpMateriales(_ConRutaTemporal):
    """consumir_para_op — el auto-descuento al aprobar una cotización
    (pedido de Bruno, 2026-09-27). Mockea TEXTILES_ANCHOS (igual que
    tests/test_repositorio_inventario.py) para que el ML del producto no
    dependa de recursos/textiles.json real."""

    def setUp(self):
        super().setUp()
        self._parche_anchos = mock.patch.dict(
            "core.repositorio.TEXTILES_ANCHOS", {"TelaTest": 1.5}, clear=True,
        )
        self._parche_anchos.start()
        self.addCleanup(self._parche_anchos.stop)

    def test_fijo_por_producto_se_descuenta_solo(self):
        m = repo_mat.ingresar_material("Bastidor", 10, tipo_consumo="fijo_por_producto",
                                        consumo_parametros={"n": 1}, productos_asociados=["Bandera"])
        p = _producto_interno(producto="Bandera", cantidad=2)

        repo_mat.consumir_para_op([p], 4210, "Cliente ABC")

        actualizado = repo_mat.obtener_material(m["id"])
        self.assertEqual(actualizado["cantidad"], 8.0)  # 10 - (1 * 2)
        entrada = actualizado["historial"][-1]
        self.assertEqual(entrada["tipo"], "consumo")
        self.assertEqual(entrada["numero_op"], 4210)
        self.assertEqual(entrada["cliente"], "Cliente ABC")

    def test_via_estructura_asociada(self):
        m = repo_mat.ingresar_material("Tornillo", 100, tipo_consumo="fijo_por_producto",
                                        consumo_parametros={"n": 4}, estructuras_asociadas=["Base auto"])
        p = _producto_interno(producto="Otro", estructuras=["Base auto"], cantidad=1)

        repo_mat.consumir_para_op([p], 4211)

        self.assertEqual(repo_mat.obtener_material(m["id"])["cantidad"], 96.0)

    def test_dos_productos_al_mismo_material_un_solo_registro(self):
        m = repo_mat.ingresar_material("Bastidor", 100, tipo_consumo="fijo_por_producto",
                                        consumo_parametros={"n": 1}, productos_asociados=["Bandera"])
        p1 = _producto_interno(producto="Bandera", cantidad=2)
        p2 = _producto_interno(producto="Bandera", cantidad=3)

        repo_mat.consumir_para_op([p1, p2], 4212)

        actualizado = repo_mat.obtener_material(m["id"])
        self.assertEqual(actualizado["cantidad"], 95.0)  # 100 - 2 - 3
        # historial: la "compra" del ingresar_material inicial + UN solo
        # "consumo" (no dos, aunque le tocó a los dos productos).
        consumos = [h for h in actualizado["historial"] if h["tipo"] == "consumo"]
        self.assertEqual(len(consumos), 1)
        self.assertEqual(consumos[0]["cantidad_anterior"], 100.0)
        self.assertEqual(consumos[0]["cantidad_nueva"], 95.0)

    def test_material_sin_tipo_consumo_no_se_toca(self):
        m = repo_mat.ingresar_material("Adhesivo", 10, productos_asociados=["Bandera"])
        p = _producto_interno(producto="Bandera", cantidad=1)
        repo_mat.consumir_para_op([p], 4213)
        self.assertEqual(repo_mat.obtener_material(m["id"])["cantidad"], 10.0)

    def test_manual_usa_el_monto_de_consumos_manuales(self):
        m = repo_mat.ingresar_material("Cinta", 50, tipo_consumo="manual", productos_asociados=["Bandera"])
        p = _producto_interno(producto="Bandera", cantidad=1)

        repo_mat.consumir_para_op([p], 4214, consumos_manuales={m["id"]: 12.5})

        self.assertEqual(repo_mat.obtener_material(m["id"])["cantidad"], 37.5)

    def test_manual_sin_monto_no_se_toca(self):
        m = repo_mat.ingresar_material("Cinta", 50, tipo_consumo="manual", productos_asociados=["Bandera"])
        p = _producto_interno(producto="Bandera", cantidad=1)
        repo_mat.consumir_para_op([p], 4215)
        self.assertEqual(repo_mat.obtener_material(m["id"])["cantidad"], 50.0)

    def test_manual_no_se_cuenta_dos_veces_por_op(self):
        m = repo_mat.ingresar_material("Cinta", 50, tipo_consumo="manual", productos_asociados=["Bandera"])
        p1 = _producto_interno(producto="Bandera", cantidad=1)
        p2 = _producto_interno(producto="Bandera", cantidad=5)

        repo_mat.consumir_para_op([p1, p2], 4216, consumos_manuales={m["id"]: 10.0})

        # 10 es el monto TOTAL para la OP, no por producto -> 50-10, no 50-20.
        self.assertEqual(repo_mat.obtener_material(m["id"])["cantidad"], 40.0)

    def test_no_bloquea_con_stock_negativo(self):
        m = repo_mat.ingresar_material("Bastidor", 1, tipo_consumo="fijo_por_producto",
                                        consumo_parametros={"n": 5}, productos_asociados=["Bandera"])
        p = _producto_interno(producto="Bandera", cantidad=1)
        repo_mat.consumir_para_op([p], 4217)
        self.assertEqual(repo_mat.obtener_material(m["id"])["cantidad"], -4.0)

    def test_metro_lineal_directo_usa_ml_sin_margen_de_tension(self):
        # Producto de 1.5x10 con TelaTest a 1.5 de ancho -> 10 ML reales.
        # Si usara el margen de rollos (+1) daría 11 — confirma que NO lo usa.
        m = repo_mat.ingresar_material("Cinta metro", 100, tipo_consumo="metro_lineal_directo",
                                        productos_asociados=["Bandera"])
        p = _producto_interno(producto="Bandera", ancho=1.5, alto=10.0, cantidad=1)
        repo_mat.consumir_para_op([p], 4218)
        self.assertEqual(repo_mat.obtener_material(m["id"])["cantidad"], 90.0)  # 100 - 10, no 100 - 11


# ══════════════════════════════════════════════════════════════════════════════
# Modelo económico (pedido de Bruno, 2026-10-01 — "reinventar la forma de
# cobrar por estructuras"): costo promedio ponderado que sale solo de los
# restocks, precio de venta manual que queda registrado, ganancias como margen
# de lo vendido, y el cobro de una OP por los materiales que de verdad gasta.
# Ver el docstring de core/repositorio_materiales.py.
# ══════════════════════════════════════════════════════════════════════════════

class TestGastoUnitarioPromedioPonderado(_ConRutaTemporal):
    """El costo unitario es un promedio móvil que sale de los restocks, no el
    último precio pagado ni un campo de formulario — pedido de Bruno: "los
    gastos no se ingresan manualmente, sino que se cuentan al restockear"."""

    def test_primera_compra_fija_el_costo(self):
        m = repo_mat.ingresar_material("Estaca", 10, costo_total=10000)
        self.assertEqual(m["gasto_unitario"], 1000.0)
        self.assertEqual(m["gasto_acumulado"], 10000.0)

    def test_segunda_compra_mas_cara_promedia_ponderado(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_unitario=1000)
        m = repo_mat.ingresar_material("Estaca", 10, costo_unitario=1400)
        # (10 × 1000 + 10 × 1400) / 20 = 1200 — no 1400, que es el último precio
        self.assertEqual(m["gasto_unitario"], 1200.0)
        self.assertEqual(m["gasto_acumulado"], 24000.0)
        self.assertEqual(m["id"], creado["id"])

    def test_promedio_pondera_por_cantidad_no_por_compra(self):
        repo_mat.ingresar_material("Estaca", 90, costo_unitario=1000)
        m = repo_mat.ingresar_material("Estaca", 10, costo_unitario=2000)
        # (90 × 1000 + 10 × 2000) / 100 = 1100 — no 1500, el promedio simple
        self.assertEqual(m["gasto_unitario"], 1100.0)

    def test_compra_sin_costo_no_mueve_el_promedio(self):
        repo_mat.ingresar_material("Estaca", 10, costo_unitario=1000)
        m = repo_mat.ingresar_material("Estaca", 10)
        self.assertEqual(m["gasto_unitario"], 1000.0)
        self.assertEqual(m["gasto_acumulado"], 10000.0)

    def test_stock_negativo_no_baja_el_promedio(self):
        # Un consumo de OP puede dejar el stock en negativo (acá no se bloquea):
        # ese negativo no debe restar valor y dar un promedio más bajo que
        # cualquier precio realmente pagado.
        creado = repo_mat.ingresar_material("Estaca", 5, costo_unitario=1000)
        repo_mat.ajustar_cantidad(creado["id"], -15)  # un consumo lo dejó negativo
        m = repo_mat.ingresar_material("Estaca", 10, costo_unitario=2000)
        self.assertEqual(m["gasto_unitario"], 2000.0)


class TestAjustarValor(_ConRutaTemporal):
    """El precio de VENTA es el único precio manual, y cambiarlo SIEMPRE queda
    en el historial (pedido explícito de Bruno, 2026-10-01)."""

    def test_registra_entrada_de_tipo_precio(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        m = repo_mat.ajustar_valor(creado["id"], 7000, "subio el proveedor")
        self.assertEqual(m["valor"], 7000.0)
        entrada = m["historial"][-1]
        self.assertEqual(entrada["tipo"], "precio")
        self.assertIsNone(entrada["valor_anterior"])
        self.assertEqual(entrada["valor_nuevo"], 7000.0)
        self.assertEqual(entrada["descripcion"], "subio el proveedor")

    def test_guarda_el_precio_anterior(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        repo_mat.ajustar_valor(creado["id"], 7000)
        m = repo_mat.ajustar_valor(creado["id"], 9000)
        self.assertEqual(m["historial"][-1]["valor_anterior"], 7000.0)
        self.assertEqual(m["historial"][-1]["valor_nuevo"], 9000.0)

    def test_no_toca_el_stock(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        m = repo_mat.ajustar_valor(creado["id"], 7000)
        self.assertEqual(m["cantidad"], 10.0)
        entrada = m["historial"][-1]
        self.assertEqual(entrada["cantidad_anterior"], entrada["cantidad_nueva"])

    def test_poner_el_mismo_precio_no_registra_nada(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        repo_mat.ajustar_valor(creado["id"], 7000)
        m = repo_mat.ajustar_valor(creado["id"], 7000)
        self.assertEqual(len([h for h in m["historial"] if h["tipo"] == "precio"]), 1)

    def test_borrar_el_precio_tambien_se_registra(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        repo_mat.ajustar_valor(creado["id"], 7000)
        m = repo_mat.ajustar_valor(creado["id"], None)
        self.assertIsNone(m["valor"])
        self.assertEqual(m["historial"][-1]["valor_anterior"], 7000.0)
        self.assertIsNone(m["historial"][-1]["valor_nuevo"])

    def test_material_inexistente_da_none(self):
        self.assertIsNone(repo_mat.ajustar_valor("no-existe", 100))


def _material_con_formula(nombre, cantidad, costo_unitario, valor, **kwargs):
    """Material listo para consumir/cobrar: stock con costo, precio de venta y
    una fórmula de consumo (por default, 1 fijo por producto) asociada a la
    estructura "Base auto"."""
    creado = repo_mat.ingresar_material(nombre, cantidad, costo_unitario=costo_unitario)
    repo_mat.editar_material(
        creado["id"], nombre, "unidad", valor=valor,
        tipo_consumo=kwargs.get("tipo_consumo", "fijo_por_producto"),
        consumo_parametros=kwargs.get("consumo_parametros", {"n": 1}),
        productos_asociados=kwargs.get("productos_asociados"),
        estructuras_asociadas=kwargs.get("estructuras_asociadas", ["Base auto"]),
    )
    return repo_mat.obtener_material(creado["id"])


def _producto(cantidad=10, alto=2.0, estructuras=("Base auto",), nombre="Bandera"):
    return {"producto": nombre, "estructuras": list(estructuras),
            "ancho": 1.0, "alto": alto, "cantidad": cantidad}


class TestDeshacerConModeloEconomico(_ConRutaTemporal):
    """Deshacer una entrada deshace también lo que le hizo al modelo económico
    — si no, una compra cargada por error deja el costo promedio y el gasto
    total contando plata que nunca se pagó."""

    def test_deshacer_compra_vuelve_al_costo_anterior(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_unitario=1000)
        segunda = repo_mat.ingresar_material("Estaca", 10, costo_unitario=1400)
        self.assertEqual(segunda["gasto_unitario"], 1200.0)
        m = repo_mat.eliminar_ultimo_historial(creado["id"], segunda["historial"][-1]["id"])
        self.assertEqual(m["gasto_unitario"], 1000.0)
        self.assertEqual(m["gasto_acumulado"], 10000.0)
        self.assertEqual(m["cantidad"], 10.0)

    def test_deshacer_cambio_de_precio_vuelve_al_precio_anterior(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        repo_mat.ajustar_valor(creado["id"], 7000)
        segundo = repo_mat.ajustar_valor(creado["id"], 9000)
        m = repo_mat.eliminar_ultimo_historial(creado["id"], segundo["historial"][-1]["id"])
        self.assertEqual(m["valor"], 7000.0)

    def test_deshacer_consumo_descuenta_lo_vendido_y_la_ganancia(self):
        mat = _material_con_formula("Estaca", 100, 1000, 3000)
        repo_mat.consumir_para_op([_producto()], 500, "Cliente")
        m = repo_mat.obtener_material(mat["id"])
        self.assertEqual(m["vendido_acumulado"], 30000.0)
        self.assertEqual(m["ganancia_acumulada"], 20000.0)  # 10 × (3000 − 1000)
        m = repo_mat.eliminar_ultimo_historial(mat["id"], m["historial"][-1]["id"])
        self.assertEqual(m["vendido_acumulado"], 0.0)
        self.assertEqual(m["ganancia_acumulada"], 0.0)
        self.assertEqual(m["cantidad"], 100.0)


class TestMedidaUnitaria(unittest.TestCase):
    """La medida que gasta material es el ALTO FÍSICO de UNA pieza (decisión de
    Bruno, 2026-10-01) — antes se pasaba el ML de rollo de TODA la línea, y las
    fórmulas por metro lineal contaban la cantidad dos veces."""

    def test_es_el_alto_del_producto(self):
        self.assertEqual(repo_mat.medida_unitaria({"ancho": 1.0, "alto": 3.0, "cantidad": 10}), 3.0)

    def test_no_depende_de_la_cantidad(self):
        uno = repo_mat.medida_unitaria({"ancho": 1.0, "alto": 3.0, "cantidad": 1})
        cien = repo_mat.medida_unitaria({"ancho": 1.0, "alto": 3.0, "cantidad": 100})
        self.assertEqual(uno, cien)

    def test_sin_alto_da_cero(self):
        self.assertEqual(repo_mat.medida_unitaria({"cantidad": 5}), 0.0)

    def test_alto_invalido_no_revienta(self):
        self.assertEqual(repo_mat.medida_unitaria({"alto": "", "cantidad": 5}), 0.0)


class TestConsumirParaOpNoDuplicaLaCantidad(_ConRutaTemporal):
    """El bug que arrastraba el consumo automático: con una fórmula por metro
    lineal la cantidad se contaba dos veces (una en el ML de toda la línea y
    otra en el × cantidad_producto de la fórmula)."""

    def test_metro_lineal_directo_usa_el_alto_por_pieza(self):
        mat = _material_con_formula(
            "Cinta", 1000, 100, 300,
            tipo_consumo="metro_lineal_directo", consumo_parametros={},
        )
        repo_mat.consumir_para_op([_producto(cantidad=10, alto=3.0)], 600, "Cliente")
        m = repo_mat.obtener_material(mat["id"])
        self.assertEqual(m["cantidad"], 970.0)  # 3 m × 10 piezas = 30

    def test_metro_lineal_salto_cuenta_bloques_por_pieza(self):
        mat = _material_con_formula(
            "Asta", 1000, 100, 300,
            tipo_consumo="metro_lineal_salto", consumo_parametros={"paso": 1.5, "n": 1},
        )
        # Pieza de 3 m con paso 1,5 → 2 astas por pieza × 10 piezas = 20
        repo_mat.consumir_para_op([_producto(cantidad=10, alto=3.0)], 601, "Cliente")
        m = repo_mat.obtener_material(mat["id"])
        self.assertEqual(m["cantidad"], 980.0)


class TestMetricasMaterial(_ConRutaTemporal):

    def test_las_nueve_cifras(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_unitario=1000)
        repo_mat.ajustar_valor(creado["id"], 2500)
        met = repo_mat.metricas_material(repo_mat.obtener_material(creado["id"]))
        self.assertEqual(met["gasto_unitario"], 1000.0)
        self.assertEqual(met["gasto_mes"], 10000.0)
        self.assertEqual(met["gasto_total"], 10000.0)
        self.assertEqual(met["valor_unitario"], 2500.0)
        self.assertEqual(met["valor_restante"], 25000.0)
        self.assertEqual(met["valor_vendido"], 0.0)
        self.assertEqual(met["ganancia_unitaria"], 1500.0)
        self.assertEqual(met["ganancia_mes"], 0.0)
        self.assertEqual(met["ganancia_total"], 0.0)

    def test_sin_precio_de_venta_las_unitarias_son_none_no_cero(self):
        creado = repo_mat.ingresar_material("Estaca", 10, costo_unitario=1000)
        met = repo_mat.metricas_material(repo_mat.obtener_material(creado["id"]))
        self.assertIsNone(met["valor_unitario"])
        self.assertIsNone(met["valor_restante"])
        self.assertIsNone(met["ganancia_unitaria"])

    def test_sin_costo_la_ganancia_unitaria_es_none(self):
        creado = repo_mat.ingresar_material("Estaca", 10)
        repo_mat.ajustar_valor(creado["id"], 2500)
        met = repo_mat.metricas_material(repo_mat.obtener_material(creado["id"]))
        self.assertIsNone(met["ganancia_unitaria"])
        self.assertEqual(met["valor_restante"], 25000.0)

    def test_ganancia_del_mes_es_margen_de_lo_vendido_no_flujo_de_caja(self):
        # Mes con un restock caro y una venta chica: el margen de lo vendido es
        # positivo aunque la caja del mes esté en rojo (decisión de Bruno).
        mat = _material_con_formula("Estaca", 100, 1000, 3000)
        repo_mat.consumir_para_op([_producto()], 501, "Cliente")
        met = repo_mat.metricas_material(repo_mat.obtener_material(mat["id"]))
        self.assertEqual(met["gasto_mes"], 100000.0)     # el restock
        self.assertEqual(met["valor_vendido"], 30000.0)
        self.assertEqual(met["ganancia_mes"], 20000.0)   # 10 × (3000 − 1000)

    def test_lo_vendido_queda_al_precio_de_esa_op_no_al_de_hoy(self):
        mat = _material_con_formula("Estaca", 100, 1000, 3000)
        repo_mat.consumir_para_op([_producto()], 502, "Cliente")
        repo_mat.ajustar_valor(mat["id"], 99000)  # sube el precio DESPUÉS
        met = repo_mat.metricas_material(repo_mat.obtener_material(mat["id"]))
        self.assertEqual(met["valor_vendido"], 30000.0)
        self.assertEqual(met["ganancia_mes"], 20000.0)


class TestCobroMaterialesProducto(_ConRutaTemporal):
    """La nueva forma de cobrar estructuras: el monto sale de los materiales
    que la estructura de verdad gasta, y REEMPLAZA al valor de catálogo
    (decisión de Bruno, 2026-10-01)."""

    def test_estructura_con_material_cobra_consumo_por_precio_de_venta(self):
        _material_con_formula("Estaca", 100, 1000, 3000)
        cobro = repo_mat.cobro_materiales_producto(_producto(cantidad=10))
        self.assertEqual(cobro["estructuras"], {"Base auto": 30000.0})
        self.assertEqual(cobro["incompletas"], [])

    def test_estructura_sin_materiales_no_aparece_y_queda_el_catalogo(self):
        cobro = repo_mat.cobro_materiales_producto(_producto(estructuras=["Tubo"]))
        self.assertEqual(cobro["estructuras"], {})
        self.assertEqual(cobro["incompletas"], [])

    def test_estructura_suma_todos_sus_materiales(self):
        _material_con_formula("Estaca", 100, 1000, 3000)
        _material_con_formula("Remache", 100, 100, 500)
        cobro = repo_mat.cobro_materiales_producto(_producto(cantidad=10))
        self.assertEqual(cobro["estructuras"], {"Base auto": 35000.0})

    def test_material_sin_precio_de_venta_devuelve_la_estructura_al_catalogo(self):
        _material_con_formula("Estaca", 100, 1000, 3000)
        _material_con_formula("Remache", 100, 100, None)
        cobro = repo_mat.cobro_materiales_producto(_producto(cantidad=10))
        self.assertEqual(cobro["estructuras"], {})          # ni siquiera parcial
        self.assertEqual(cobro["incompletas"], ["Base auto"])

    def test_material_manual_devuelve_la_estructura_al_catalogo(self):
        _material_con_formula("Estaca", 100, 1000, 3000,
                              tipo_consumo="manual", consumo_parametros={})
        cobro = repo_mat.cobro_materiales_producto(_producto(cantidad=10))
        self.assertEqual(cobro["estructuras"], {})
        self.assertEqual(cobro["incompletas"], ["Base auto"])

    def test_material_del_producto_se_cobra_aparte(self):
        _material_con_formula("Ojalillo", 100, 50, 200,
                              productos_asociados=["Bandera"], estructuras_asociadas=[])
        cobro = repo_mat.cobro_materiales_producto(_producto(cantidad=10, estructuras=[]))
        self.assertEqual(cobro["materiales_producto"], {"Ojalillo": 2000.0})

    def test_material_del_producto_y_de_la_estructura_se_cobra_una_sola_vez(self):
        _material_con_formula("Estaca", 100, 1000, 3000,
                              productos_asociados=["Bandera"], estructuras_asociadas=["Base auto"])
        cobro = repo_mat.cobro_materiales_producto(_producto(cantidad=10))
        self.assertEqual(cobro["estructuras"], {"Base auto": 30000.0})
        self.assertEqual(cobro["materiales_producto"], {})

    def test_producto_sin_estructuras_ni_nombre_no_consulta_nada(self):
        _material_con_formula("Estaca", 100, 1000, 3000)
        cobro = repo_mat.cobro_materiales_producto({"ancho": 1.0, "alto": 2.0, "cantidad": 5})
        self.assertEqual(cobro["estructuras"], {})
        self.assertEqual(cobro["materiales_producto"], {})

    def test_con_el_modulo_inventario_apagado_no_cobra_nada(self):
        _material_con_formula("Estaca", 100, 1000, 3000)
        from core import config as _config
        with mock.patch.dict(_config.MODULOS_HABILITADOS, {"inventario": False}):
            cobro = repo_mat.cobro_materiales_producto(_producto(cantidad=10))
        self.assertEqual(cobro["estructuras"], {})
        self.assertEqual(cobro["materiales_producto"], {})


if __name__ == "__main__":
    unittest.main()
