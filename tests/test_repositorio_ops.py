"""
tests/test_repositorio_ops.py
Verifica la estructura de carpetas AAAA/MM de core/repositorio_ops.py
(un cambio de ui/op-historial: antes las OPs vivían planas en cada
carpeta — JSON/Completadas/Pendiente/Historial —, ahora cada una guarda
sus JSON en subcarpetas AAAA/MM según Fecha_ingreso, para que el
historial pueda listar un mes puntual sin abrir el resto de los
archivos). Usa una carpeta temporal (mock de _ruta_base) — no toca
Dropbox ni AppData reales.

Correr con:  python -m unittest tests.test_repositorio_ops -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_ops as repo_ops


def _op(numero, fecha_ingreso, fecha_entrega="01/01/2026"):
    return {
        "Cotizacion": numero,
        "Empresa": f"Empresa {numero}",
        "Fecha_ingreso": fecha_ingreso,
        "Fecha_entrega": fecha_entrega,
        "productos": [],
    }


class _ConRutaTemporal(unittest.TestCase):
    """Cada test corre contra su propia carpeta temporal — _ruta_base()
    mockeada, y _migradas limpiado para que la migración no quede "ya
    hecha" de un test anterior con otra ruta pero el mismo nombre."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._base = Path(self._tmp.name)
        self._parche = mock.patch.object(repo_ops, "_ruta_base", lambda: self._base)
        self._parche.start()
        self.addCleanup(self._parche.stop)
        repo_ops._migradas.clear()


class TestGuardarYCargar(_ConRutaTemporal):

    def test_guardar_op_la_deja_en_subcarpeta_anio_mes_de_ingreso(self):
        repo_ops.guardar_op(_op(1001, "15/08/2026"))
        ruta = self._base / "JSON" / "2026" / "08" / "1001.json"
        self.assertTrue(ruta.exists())

    def test_cargar_op_la_encuentra_sin_saber_el_mes(self):
        repo_ops.guardar_op(_op(1002, "03/01/2025"))
        datos = repo_ops.cargar_op(1002)
        self.assertIsNotNone(datos)
        self.assertEqual(datos["Empresa"], "Empresa 1002")

    def test_cargar_op_inexistente_da_none(self):
        self.assertIsNone(repo_ops.cargar_op(9999))

    def test_guardar_op_sobreescribe_el_mismo_numero(self):
        repo_ops.guardar_op(_op(1003, "15/08/2026"))
        datos = _op(1003, "15/08/2026")
        datos["Empresa"] = "Empresa nueva"
        repo_ops.guardar_op(datos)
        self.assertEqual(repo_ops.cargar_op(1003)["Empresa"], "Empresa nueva")
        # No debe quedar un archivo duplicado
        self.assertEqual(len(list((self._base / "JSON").rglob("1003.json"))), 1)


class TestMoverEntreCarpetas(_ConRutaTemporal):

    def test_mover_a_completadas_mantiene_la_subcarpeta_anio_mes(self):
        repo_ops.guardar_op(_op(2001, "20/03/2024"))
        repo_ops.mover_a_completadas(2001)
        self.assertTrue((self._base / "Completadas" / "2024" / "03" / "2001.json").exists())
        self.assertFalse((self._base / "JSON" / "2024" / "03" / "2001.json").exists())

    def test_mover_a_pendiente_mantiene_la_subcarpeta_anio_mes(self):
        repo_ops.guardar_op(_op(2002, "05/11/2023"))
        repo_ops.mover_a_pendiente(2002)
        self.assertTrue((self._base / "Pendiente" / "2023" / "11" / "2002.json").exists())

    def test_reactivar_desde_pendiente_vuelve_a_json_mismo_mes(self):
        repo_ops.guardar_op(_op(2003, "05/11/2023"))
        repo_ops.mover_a_pendiente(2003)
        repo_ops.reactivar_desde_pendiente(2003, "20/12/2023")
        self.assertTrue((self._base / "JSON" / "2023" / "11" / "2003.json").exists())
        self.assertFalse((self._base / "Pendiente" / "2023" / "11" / "2003.json").exists())
        self.assertEqual(repo_ops.cargar_op(2003)["Fecha_entrega"], "20/12/2023")

    def test_mover_op_inexistente_no_revienta(self):
        repo_ops.mover_a_completadas(424242)  # no existe en ninguna carpeta

    def test_eliminar_op_activa(self):
        repo_ops.guardar_op(_op(2010, "10/05/2026"))
        self.assertTrue(repo_ops.eliminar_op(2010))
        self.assertIsNone(repo_ops.cargar_op(2010))

    def test_eliminar_op_la_encuentra_en_cualquier_carpeta_de_ciclo_de_vida(self):
        repo_ops.guardar_op(_op(2011, "10/05/2026"))
        repo_ops.mover_a_completadas(2011)
        self.assertTrue(repo_ops.eliminar_op(2011))
        self.assertIsNone(repo_ops.cargar_op(2011))

    def test_eliminar_op_inexistente_da_false(self):
        self.assertFalse(repo_ops.eliminar_op(999999))

    def test_envejecer_completadas_mueve_a_historial_mismo_mes(self):
        op = _op(2004, "01/01/2020", fecha_entrega="01/01/2020")  # bien vieja
        repo_ops.guardar_op(op)
        repo_ops.mover_a_completadas(2004)
        repo_ops.envejecer_completadas(dias=14)
        self.assertTrue((self._base / "Historial" / "2020" / "01" / "2004.json").exists())
        self.assertFalse((self._base / "Completadas" / "2020" / "01" / "2004.json").exists())

    def test_envejecer_completadas_no_mueve_las_recientes(self):
        from datetime import datetime
        hoy = datetime.now().strftime("%d/%m/%Y")
        op = _op(2005, "01/01/2026", fecha_entrega=hoy)
        repo_ops.guardar_op(op)
        repo_ops.mover_a_completadas(2005)
        repo_ops.envejecer_completadas(dias=14)
        self.assertTrue((self._base / "Completadas" / "2026" / "01" / "2005.json").exists())


class TestActualizaciones(_ConRutaTemporal):

    def test_actualizar_fecha_entrega_encuentra_el_archivo_anidado(self):
        repo_ops.guardar_op(_op(3001, "12/06/2026"))
        repo_ops.actualizar_fecha_entrega(3001, "01/07/2026")
        self.assertEqual(repo_ops.cargar_op(3001)["Fecha_entrega"], "01/07/2026")

    def test_actualizar_listos_encuentra_el_archivo_anidado(self):
        repo_ops.guardar_op(_op(3002, "12/06/2026"))
        repo_ops.actualizar_listos(3002, [0, 2])
        self.assertEqual(repo_ops.cargar_op(3002)["ProductosListos"], [0, 2])


class TestMigracionArchivosPlanos(_ConRutaTemporal):

    def test_archivo_plano_viejo_se_migra_a_su_subcarpeta(self):
        carpeta = self._base / "JSON"
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "4001.json").write_text(
            json.dumps(_op(4001, "09/09/2022")), encoding="utf-8")

        repo_ops.carpeta_json()  # dispara la migración

        self.assertFalse((carpeta / "4001.json").exists())
        self.assertTrue((carpeta / "2022" / "09" / "4001.json").exists())

    def test_archivo_plano_sin_fecha_ingreso_no_revienta_la_migracion(self):
        carpeta = self._base / "JSON"
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "4002.json").write_text(
            json.dumps({"Cotizacion": 4002}), encoding="utf-8")  # sin Fecha_ingreso

        repo_ops.carpeta_json()  # no debe lanzar excepción

        self.assertFalse((carpeta / "4002.json").exists())  # se migró (con fecha de hoy)

    def test_migracion_no_repite_en_llamadas_siguientes(self):
        carpeta = self._base / "JSON"
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "4003.json").write_text(
            json.dumps(_op(4003, "09/09/2022")), encoding="utf-8")
        repo_ops.carpeta_json()
        # Un archivo plano nuevo, agregado DESPUÉS de la primera migración:
        # como ya se marcó esta carpeta como migrada en esta sesión, no se
        # mueve solo (comportamiento esperado: la migración es de arranque,
        # no un vigilante corriendo todo el tiempo).
        (carpeta / "4004.json").write_text(
            json.dumps(_op(4004, "09/09/2022")), encoding="utf-8")
        repo_ops.carpeta_json()
        self.assertTrue((carpeta / "4004.json").exists())


class TestListadoPorMes(_ConRutaTemporal):

    def test_listar_meses_disponibles_junta_las_4_carpetas(self):
        repo_ops.guardar_op(_op(5001, "15/08/2026"))
        repo_ops.guardar_op(_op(5002, "20/01/2025"))
        repo_ops.mover_a_completadas(5002)
        repo_ops.guardar_op(_op(5003, "03/03/2024"))
        repo_ops.mover_a_pendiente(5003)

        meses = repo_ops.listar_meses_disponibles()

        self.assertEqual(meses, sorted([(2024, 3), (2025, 1), (2026, 8)]))

    def test_listar_meses_disponibles_vacio_sin_ops(self):
        self.assertEqual(repo_ops.listar_meses_disponibles(), [])

    def test_listar_ops_del_mes_solo_trae_ese_mes(self):
        repo_ops.guardar_op(_op(6001, "15/08/2026"))
        repo_ops.guardar_op(_op(6002, "20/08/2026"))
        repo_ops.guardar_op(_op(6003, "01/09/2026"))  # otro mes, no debe salir

        resultado = repo_ops.listar_ops_del_mes(2026, 8)

        numeros = sorted(d["Cotizacion"] for d, _ in resultado)
        self.assertEqual(numeros, [6001, 6002])

    def test_listar_ops_del_mes_incluye_activas_y_marca_origen(self):
        repo_ops.guardar_op(_op(6004, "15/08/2026"))   # queda activa (JSON/)
        repo_ops.guardar_op(_op(6005, "18/08/2026"))
        repo_ops.mover_a_completadas(6005)
        repo_ops.guardar_op(_op(6006, "22/08/2026"))
        repo_ops.mover_a_pendiente(6006)

        resultado = repo_ops.listar_ops_del_mes(2026, 8)
        origenes = {d["Cotizacion"]: origen for d, origen in resultado}

        self.assertEqual(origenes[6004], "JSON")
        self.assertEqual(origenes[6005], "Completadas")
        self.assertEqual(origenes[6006], "Pendiente")

    def test_listar_ops_del_mes_sin_datos_da_lista_vacia(self):
        self.assertEqual(repo_ops.listar_ops_del_mes(1999, 1), [])


if __name__ == "__main__":
    unittest.main()
