"""
tests/test_repositorio_despachos.py
Verifica core/repositorio_despachos.py: una OP recibida desde el panel de
producción (recibir_op) llega a NoAsignadas/ con CantidadDespachada=0 en
cada producto; la dirección se asigna POR PRODUCTO
(asignar_direccion_productos), que mueve sola la OP a Asignadas/ apenas
TODOS los productos tienen una (sin un paso "Completar" aparte, ver
_sincronizar_carpeta); generar_guia() exige
que los productos de una misma guía compartan dirección, y puede
despachar parcialmente (varias guías por OP). Usa una carpeta temporal
(mock de _ruta_base) — no toca Dropbox ni AppData reales.

Correr con:  python -m unittest tests.test_repositorio_despachos -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_despachos as repo_desp


def _op(numero, productos=None):
    return {
        "Cotizacion": numero,
        "Empresa": f"Empresa {numero}",
        "Contacto": "Juan Pérez",
        "Fecha_completada": "20/08/2026",
        "Despacho": 15000,
        "productos": productos if productos is not None else [
            {"producto": "Pendón", "Tema": "Verano", "Cantidad": 10},
        ],
    }


_DIR_A = {
    "rut": "12.345.678-9", "empresa": "Empresa 1", "alias": "Bodega",
    "calle": "Av. Siempre Viva", "numero": "742", "comuna": "Providencia",
    "region": "Región Metropolitana", "codigo_postal": "",
}
_DIR_B = {
    "rut": "12.345.678-9", "empresa": "Empresa 1", "alias": "Sucursal",
    "calle": "Calle Otra", "numero": "100", "comuna": "Ñuñoa",
    "region": "Región Metropolitana", "codigo_postal": "",
}


class _ConRutaTemporal(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._base = Path(self._tmp.name)
        self._parche = mock.patch.object(repo_desp, "_ruta_base", lambda: self._base)
        self._parche.start()
        self.addCleanup(self._parche.stop)


class TestRecibirOp(_ConRutaTemporal):

    def test_recibir_op_queda_pendiente_con_cantidad_despachada_en_cero(self):
        repo_desp.recibir_op(_op(1001))
        datos = repo_desp.cargar_op_despacho(1001)
        self.assertEqual(datos["EstadoDespacho"], repo_desp.ESTADO_DESPACHO_PENDIENTE)
        self.assertEqual(datos["productos"][0]["CantidadDespachada"], 0)

    def test_recibir_op_la_deja_en_no_asignadas(self):
        repo_desp.recibir_op(_op(1002))
        self.assertTrue((self._base / "OPs" / "NoAsignadas" / "1002.json").exists())

    def test_recibir_op_no_pisa_cantidad_despachada_existente(self):
        op = _op(1003)
        op["productos"][0]["CantidadDespachada"] = 4
        repo_desp.recibir_op(op)
        datos = repo_desp.cargar_op_despacho(1003)
        self.assertEqual(datos["productos"][0]["CantidadDespachada"], 4)


class TestAsignacionDeDirecciones(_ConRutaTemporal):

    def test_op_recien_recibida_esta_no_asignada(self):
        repo_desp.recibir_op(_op(1010))
        datos = repo_desp.cargar_op_despacho(1010)
        self.assertEqual(repo_desp.estado_asignacion(datos), repo_desp.ESTADO_ASIGNACION_NO_ASIGNADA)

    def test_asignar_direccion_a_un_producto(self):
        repo_desp.recibir_op(_op(1011, productos=[
            {"producto": "Pendón", "Cantidad": 10},
            {"producto": "Lona", "Cantidad": 5},
        ]))
        repo_desp.asignar_direccion_productos(1011, [0], _DIR_A)
        datos = repo_desp.cargar_op_despacho(1011)
        self.assertEqual(datos["productos"][0]["Direccion"]["comuna"], "Providencia")
        self.assertNotIn("Direccion", datos["productos"][1])
        # todavía no están TODOS asignados
        self.assertEqual(repo_desp.estado_asignacion(datos), repo_desp.ESTADO_ASIGNACION_NO_ASIGNADA)

    def test_asignada_recien_cuando_todos_los_productos_tienen_direccion(self):
        repo_desp.recibir_op(_op(1012, productos=[
            {"producto": "Pendón", "Cantidad": 10},
            {"producto": "Lona", "Cantidad": 5},
        ]))
        repo_desp.asignar_direccion_productos(1012, [0], _DIR_A)
        repo_desp.asignar_direccion_productos(1012, [1], _DIR_B)
        datos = repo_desp.cargar_op_despacho(1012)
        self.assertEqual(repo_desp.estado_asignacion(datos), repo_desp.ESTADO_ASIGNACION_ASIGNADA)

    def test_quitar_direccion_de_un_producto(self):
        repo_desp.recibir_op(_op(1013))
        repo_desp.asignar_direccion_productos(1013, [0], _DIR_A)
        repo_desp.quitar_direccion_productos(1013, [0])
        datos = repo_desp.cargar_op_despacho(1013)
        self.assertNotIn("Direccion", datos["productos"][0])

    def test_asignar_direccion_a_op_inexistente_no_revienta(self):
        repo_desp.asignar_direccion_productos(999999, [0], _DIR_A)


class TestSincronizacionDeCarpeta(_ConRutaTemporal):
    """Ya no hay un botón "Completar" — asignar_direccion_productos/
    quitar_direccion_productos mueven la OP solas entre NoAsignadas/ y
    Asignadas/ apenas cambia su EstadoAsignacion (ver
    core.repositorio_despachos._sincronizar_carpeta)."""

    def test_queda_en_no_asignadas_mientras_falte_algun_producto(self):
        repo_desp.recibir_op(_op(2001, productos=[
            {"producto": "Pendón", "Cantidad": 10},
            {"producto": "Lona", "Cantidad": 5},
        ]))
        repo_desp.asignar_direccion_productos(2001, [0], _DIR_A)
        self.assertTrue((self._base / "OPs" / "NoAsignadas" / "2001.json").exists())
        self.assertFalse((self._base / "OPs" / "Asignadas" / "2001.json").exists())

    def test_pasa_sola_a_asignadas_al_completar_el_ultimo_producto(self):
        repo_desp.recibir_op(_op(2002, productos=[
            {"producto": "Pendón", "Cantidad": 10},
            {"producto": "Lona", "Cantidad": 5},
        ]))
        repo_desp.asignar_direccion_productos(2002, [0], _DIR_A)
        repo_desp.asignar_direccion_productos(2002, [1], _DIR_B)
        self.assertTrue((self._base / "OPs" / "Asignadas" / "2002.json").exists())
        self.assertFalse((self._base / "OPs" / "NoAsignadas" / "2002.json").exists())

    def test_vuelve_a_no_asignadas_si_se_quita_una_direccion(self):
        repo_desp.recibir_op(_op(2003, productos=[
            {"producto": "Pendón", "Cantidad": 10},
            {"producto": "Lona", "Cantidad": 5},
        ]))
        repo_desp.asignar_direccion_productos(2003, [0], _DIR_A)
        repo_desp.asignar_direccion_productos(2003, [1], _DIR_B)
        self.assertTrue((self._base / "OPs" / "Asignadas" / "2003.json").exists())

        repo_desp.quitar_direccion_productos(2003, [0])
        self.assertTrue((self._base / "OPs" / "NoAsignadas" / "2003.json").exists())
        self.assertFalse((self._base / "OPs" / "Asignadas" / "2003.json").exists())

    def test_cargar_op_la_encuentra_despues_de_pasar_a_asignadas(self):
        repo_desp.recibir_op(_op(2004))
        repo_desp.asignar_direccion_productos(2004, [0], _DIR_A)
        self.assertIsNotNone(repo_desp.cargar_op_despacho(2004))


class TestGenerarGuia(_ConRutaTemporal):

    def test_generar_guia_sin_direccion_lanza_valueerror(self):
        repo_desp.recibir_op(_op(3001))
        with self.assertRaises(ValueError):
            repo_desp.generar_guia(3001, [{"indice_producto": 0, "cantidad": 10}])

    def test_generar_guia_con_productos_de_distinta_direccion_lanza_valueerror(self):
        repo_desp.recibir_op(_op(3002, productos=[
            {"producto": "Pendón", "Cantidad": 10},
            {"producto": "Lona", "Cantidad": 5},
        ]))
        repo_desp.asignar_direccion_productos(3002, [0], _DIR_A)
        repo_desp.asignar_direccion_productos(3002, [1], _DIR_B)
        with self.assertRaises(ValueError):
            repo_desp.generar_guia(3002, [
                {"indice_producto": 0, "cantidad": 10},
                {"indice_producto": 1, "cantidad": 5},
            ])

    def test_generar_guia_completa_deja_estado_despachado(self):
        repo_desp.recibir_op(_op(3003))
        repo_desp.asignar_direccion_productos(3003, [0], _DIR_A)
        guia = repo_desp.generar_guia(3003, [{"indice_producto": 0, "cantidad": 10}])
        self.assertEqual(guia["numero_guia"], "3003-1")
        self.assertEqual(guia["direccion"]["comuna"], "Providencia")
        datos = repo_desp.cargar_op_despacho(3003)
        self.assertEqual(datos["EstadoDespacho"], repo_desp.ESTADO_DESPACHO_DESPACHADO)

    def test_dos_guias_parciales_van_de_pendiente_a_parcial_a_despachado(self):
        repo_desp.recibir_op(_op(4001, productos=[
            {"producto": "Pendón", "Tema": "Verano", "Cantidad": 10},
        ]))
        repo_desp.asignar_direccion_productos(4001, [0], _DIR_A)

        guia1 = repo_desp.generar_guia(4001, [{"indice_producto": 0, "cantidad": 4}])
        self.assertEqual(guia1["numero_guia"], "4001-1")
        self.assertEqual(
            repo_desp.cargar_op_despacho(4001)["EstadoDespacho"],
            repo_desp.ESTADO_DESPACHO_PARCIAL,
        )

        guia2 = repo_desp.generar_guia(4001, [{"indice_producto": 0, "cantidad": 6}])
        self.assertEqual(guia2["numero_guia"], "4001-2")
        datos = repo_desp.cargar_op_despacho(4001)
        self.assertEqual(datos["EstadoDespacho"], repo_desp.ESTADO_DESPACHO_DESPACHADO)
        self.assertEqual(datos["productos"][0]["CantidadDespachada"], 10)

    def test_listar_guias_de_op(self):
        repo_desp.recibir_op(_op(5001))
        repo_desp.asignar_direccion_productos(5001, [0], _DIR_A)
        repo_desp.generar_guia(5001, [{"indice_producto": 0, "cantidad": 4}])
        repo_desp.generar_guia(5001, [{"indice_producto": 0, "cantidad": 6}])
        guias = repo_desp.listar_guias_de_op(5001)
        self.assertEqual([g["numero_guia"] for g in guias], ["5001-1", "5001-2"])

    def test_generar_guia_funciona_con_op_ya_en_asignadas(self):
        repo_desp.recibir_op(_op(5002))
        # único producto -> asignar_direccion_productos ya la deja en
        # Asignadas/ sola (ver TestSincronizacionDeCarpeta).
        repo_desp.asignar_direccion_productos(5002, [0], _DIR_A)
        self.assertTrue((self._base / "OPs" / "Asignadas" / "5002.json").exists())
        guia = repo_desp.generar_guia(5002, [{"indice_producto": 0, "cantidad": 10}])
        self.assertEqual(guia["numero_guia"], "5002-1")


class TestEstadoDespacho(unittest.TestCase):

    def test_pendiente_sin_nada_despachado(self):
        datos = {"productos": [{"Cantidad": 10, "CantidadDespachada": 0}]}
        self.assertEqual(repo_desp.estado_despacho(datos), repo_desp.ESTADO_DESPACHO_PENDIENTE)

    def test_parcial_con_algo_despachado(self):
        datos = {"productos": [{"Cantidad": 10, "CantidadDespachada": 4}]}
        self.assertEqual(repo_desp.estado_despacho(datos), repo_desp.ESTADO_DESPACHO_PARCIAL)

    def test_despachado_cuando_todo_esta_cubierto(self):
        datos = {"productos": [{"Cantidad": 10, "CantidadDespachada": 10}]}
        self.assertEqual(repo_desp.estado_despacho(datos), repo_desp.ESTADO_DESPACHO_DESPACHADO)


class TestEstadoAsignacion(unittest.TestCase):

    def test_no_asignada_sin_productos(self):
        self.assertEqual(repo_desp.estado_asignacion({"productos": []}), repo_desp.ESTADO_ASIGNACION_NO_ASIGNADA)

    def test_no_asignada_con_algun_producto_sin_direccion(self):
        datos = {"productos": [{"Direccion": _DIR_A}, {}]}
        self.assertEqual(repo_desp.estado_asignacion(datos), repo_desp.ESTADO_ASIGNACION_NO_ASIGNADA)

    def test_asignada_con_todos_los_productos_con_direccion(self):
        datos = {"productos": [{"Direccion": _DIR_A}, {"Direccion": _DIR_B}]}
        self.assertEqual(repo_desp.estado_asignacion(datos), repo_desp.ESTADO_ASIGNACION_ASIGNADA)


class TestMarcarEntregado(_ConRutaTemporal):

    def test_marcar_entregado_mueve_de_asignadas_a_historial(self):
        repo_desp.recibir_op(_op(6001))
        repo_desp.asignar_direccion_productos(6001, [0], _DIR_A)  # único producto -> Asignadas
        self.assertTrue(repo_desp.marcar_entregado(6001))
        self.assertTrue((self._base / "OPs" / "Historial" / "6001.json").exists())
        self.assertFalse((self._base / "OPs" / "Asignadas" / "6001.json").exists())

    def test_marcar_entregado_graba_fecha(self):
        repo_desp.recibir_op(_op(6002))
        repo_desp.asignar_direccion_productos(6002, [0], _DIR_A)
        repo_desp.marcar_entregado(6002)
        datos = json.loads((self._base / "OPs" / "Historial" / "6002.json").read_text(encoding="utf-8"))
        self.assertIn("Entregado", datos)

    def test_marcar_entregado_de_op_sin_asignar_da_false(self):
        repo_desp.recibir_op(_op(6003, productos=[
            {"producto": "Pendón", "Cantidad": 10},
            {"producto": "Lona", "Cantidad": 5},
        ]))
        repo_desp.asignar_direccion_productos(6003, [0], _DIR_A)  # queda en NoAsignadas
        self.assertFalse(repo_desp.marcar_entregado(6003))
        self.assertTrue((self._base / "OPs" / "NoAsignadas" / "6003.json").exists())

    def test_marcar_entregado_de_op_inexistente_da_false(self):
        self.assertFalse(repo_desp.marcar_entregado(999999))


class TestEliminarDespacho(_ConRutaTemporal):

    def test_eliminar_desde_no_asignadas(self):
        repo_desp.recibir_op(_op(7001))
        self.assertTrue(repo_desp.eliminar_despacho(7001))
        self.assertIsNone(repo_desp.cargar_op_despacho(7001))

    def test_eliminar_desde_asignadas(self):
        repo_desp.recibir_op(_op(7002))
        repo_desp.asignar_direccion_productos(7002, [0], _DIR_A)
        self.assertTrue(repo_desp.eliminar_despacho(7002))
        self.assertIsNone(repo_desp.cargar_op_despacho(7002))

    def test_eliminar_desde_historial(self):
        repo_desp.recibir_op(_op(7003))
        repo_desp.asignar_direccion_productos(7003, [0], _DIR_A)
        repo_desp.marcar_entregado(7003)
        self.assertTrue(repo_desp.eliminar_despacho(7003))
        self.assertFalse((self._base / "OPs" / "Historial" / "7003.json").exists())

    def test_eliminar_inexistente_da_false(self):
        self.assertFalse(repo_desp.eliminar_despacho(999999))

    def test_eliminar_no_toca_las_guias_ya_generadas(self):
        repo_desp.recibir_op(_op(7004))
        repo_desp.asignar_direccion_productos(7004, [0], _DIR_A)
        repo_desp.generar_guia(7004, [{"indice_producto": 0, "cantidad": 10}])
        repo_desp.eliminar_despacho(7004)
        self.assertTrue((self._base / "Guias de despacho" / "JSON" / "7004-1.json").exists())


if __name__ == "__main__":
    unittest.main()
