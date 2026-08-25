"""
tests/test_repositorio_cotizaciones.py
Verifica la estructura de carpetas AAAA/MM de core/repositorio_cotizaciones.py
(mismo mecanismo que las OPs, ver tests/test_repositorio_ops.py, pero
bucketeado por el campo "Fecha" en vez de "Fecha_ingreso") y
buscar_en_ultimos_meses — usada por "Buscar cotización" en el historial
de OPs. Usa una carpeta temporal (mock de _ruta_base) — no toca Dropbox
ni AppData reales.

Correr con:  python -m unittest tests.test_repositorio_cotizaciones -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_cotizaciones as repo_cot


def _cotizacion(numero, fecha):
    return {
        "Cotizacion": numero,
        "Empresa": f"Empresa {numero}",
        "Fecha": fecha,
        "productos": [],
    }


class _ConRutaTemporal(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._base = Path(self._tmp.name)
        self._parche = mock.patch.object(repo_cot, "_ruta_base", lambda: self._base)
        self._parche.start()
        self.addCleanup(self._parche.stop)
        repo_cot._migradas.clear()


class TestGuardarYCargar(_ConRutaTemporal):

    def test_guardar_cotizacion_la_deja_en_subcarpeta_anio_mes_de_fecha(self):
        repo_cot.guardar_cotizacion(_cotizacion(1001, "15/08/2026"))
        self.assertTrue((self._base / "JSON" / "2026" / "08" / "1001.json").exists())

    def test_cargar_cotizacion_la_encuentra_sin_saber_el_mes(self):
        repo_cot.guardar_cotizacion(_cotizacion(1002, "03/01/2025"))
        datos = repo_cot.cargar_cotizacion(1002)
        self.assertIsNotNone(datos)
        self.assertEqual(datos["Empresa"], "Empresa 1002")

    def test_cargar_cotizacion_inexistente_da_none(self):
        self.assertIsNone(repo_cot.cargar_cotizacion(9999))

    def test_editar_y_reguardar_no_duplica_ni_cambia_de_mes(self):
        repo_cot.guardar_cotizacion(_cotizacion(1003, "15/08/2026"))
        datos = _cotizacion(1003, "15/08/2026")
        datos["Empresa"] = "Empresa editada"
        repo_cot.guardar_cotizacion(datos)
        self.assertEqual(repo_cot.cargar_cotizacion(1003)["Empresa"], "Empresa editada")
        self.assertEqual(len(list((self._base / "JSON").rglob("1003.json"))), 1)


class TestListarCotizaciones(_ConRutaTemporal):

    def test_lista_solo_activas_mas_nuevas_primero(self):
        repo_cot.guardar_cotizacion(_cotizacion(1001, "15/08/2026"))
        repo_cot.guardar_cotizacion(_cotizacion(1003, "03/01/2025"))
        repo_cot.guardar_cotizacion(_cotizacion(1002, "20/12/2025"))
        lista = repo_cot.listar_cotizaciones()
        self.assertEqual([e["numero"] for e in lista], [1003, 1002, 1001])
        self.assertEqual(lista[0]["empresa"], "Empresa 1003")
        self.assertEqual(lista[0]["fecha"], "03/01/2025")

    def test_no_incluye_las_movidas_a_historial(self):
        repo_cot.guardar_cotizacion(_cotizacion(1001, "15/08/2026"))
        repo_cot.mover_a_historial(1001)
        self.assertEqual(repo_cot.listar_cotizaciones(), [])

    def test_sin_cotizaciones_da_lista_vacia(self):
        self.assertEqual(repo_cot.listar_cotizaciones(), [])


class TestMoverYEliminar(_ConRutaTemporal):

    def test_mover_a_historial_mantiene_la_subcarpeta_anio_mes(self):
        repo_cot.guardar_cotizacion(_cotizacion(2001, "20/03/2024"))
        repo_cot.mover_a_historial(2001)
        self.assertTrue((self._base / "Historial" / "2024" / "03" / "2001.json").exists())
        self.assertFalse((self._base / "JSON" / "2024" / "03" / "2001.json").exists())

    def test_eliminar_cotizacion_activa(self):
        repo_cot.guardar_cotizacion(_cotizacion(2002, "10/05/2026"))
        self.assertTrue(repo_cot.eliminar_cotizacion(2002))
        self.assertIsNone(repo_cot.cargar_cotizacion(2002))

    def test_eliminar_cotizacion_en_historial(self):
        repo_cot.guardar_cotizacion(_cotizacion(2003, "10/05/2026"))
        repo_cot.mover_a_historial(2003)
        self.assertTrue(repo_cot.eliminar_cotizacion(2003))
        self.assertIsNone(repo_cot.cargar_cotizacion(2003))

    def test_eliminar_cotizacion_inexistente_da_false(self):
        self.assertFalse(repo_cot.eliminar_cotizacion(999999))


class TestMigracionArchivosPlanos(_ConRutaTemporal):

    def test_archivo_plano_viejo_se_migra_a_su_subcarpeta(self):
        carpeta = self._base / "JSON"
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "3001.json").write_text(
            json.dumps(_cotizacion(3001, "09/09/2022")), encoding="utf-8")

        repo_cot.carpeta_json()  # dispara la migración

        self.assertFalse((carpeta / "3001.json").exists())
        self.assertTrue((carpeta / "2022" / "09" / "3001.json").exists())


class TestRecalcularDescuentos(_ConRutaTemporal):
    # Sin productos (Despacho es el único monto, no depende de catálogos de
    # textiles/estructuras/terminaciones) para que el resultado sea
    # determinístico sin importar los catálogos reales de la máquina donde
    # corre el test — mismo criterio que el resto de este archivo.

    def _cotizacion_con_totales_desactualizados(self, numero):
        datos = _cotizacion(numero, "15/08/2026")
        datos["Descuento"] = 10
        datos["Despacho"] = 10000
        # Simula una cotización guardada antes de un cambio a la fórmula de
        # precios: estos montos ya no coinciden con lo que costo_cotizacion
        # calcularía hoy para los mismos productos/Descuento/Despacho.
        datos["Neto"] = 0
        datos["NetoTotal"] = 0
        datos["IVA"] = 0
        datos["Total"] = 0
        return datos

    def test_recalcula_neto_y_total_a_partir_de_descuento_y_despacho(self):
        datos = self._cotizacion_con_totales_desactualizados(5001)
        resultado = repo_cot.recalcular_descuentos(datos, guardar=False)
        # neto = 10000 (despacho, sin productos); descuento 10% = 1000;
        # neto_total = 9000; iva = 9000*0.19 = 1710; total = 10710.
        self.assertAlmostEqual(resultado["Neto"], 10000)
        self.assertAlmostEqual(resultado["NetoTotal"], 9000)
        self.assertAlmostEqual(resultado["IVA"], 1710)
        self.assertAlmostEqual(resultado["Total"], 10710)

    def test_guardar_true_persiste_la_correccion_en_disco(self):
        numero = 5002
        repo_cot.guardar_cotizacion(self._cotizacion_con_totales_desactualizados(numero))
        datos = repo_cot.cargar_cotizacion(numero)
        repo_cot.recalcular_descuentos(datos)  # guardar=True por default
        self.assertAlmostEqual(repo_cot.cargar_cotizacion(numero)["Total"], 10710)

    def test_guardar_false_no_toca_el_archivo(self):
        numero = 5003
        repo_cot.guardar_cotizacion(self._cotizacion_con_totales_desactualizados(numero))
        datos = repo_cot.cargar_cotizacion(numero)
        repo_cot.recalcular_descuentos(datos, guardar=False)
        # El dict en memoria se actualizó, pero el archivo en disco sigue
        # con el Total desactualizado (0) porque guardar=False.
        self.assertEqual(repo_cot.cargar_cotizacion(numero)["Total"], 0)


class TestBuscarEnUltimosMeses(_ConRutaTemporal):

    def test_encuentra_en_el_mismo_mes_de_referencia(self):
        repo_cot.guardar_cotizacion(_cotizacion(4001, "20/08/2026"))
        datos = repo_cot.buscar_en_ultimos_meses(4001, 2026, 8, cantidad_meses=3)
        self.assertIsNotNone(datos)
        self.assertEqual(datos["Cotizacion"], 4001)

    def test_encuentra_dos_meses_antes_del_mes_de_referencia(self):
        repo_cot.guardar_cotizacion(_cotizacion(4002, "05/06/2026"))
        # OP con Fecha_ingreso en agosto — la cotización es de junio,
        # 2 meses antes, todavía dentro de la ventana de 3 meses.
        datos = repo_cot.buscar_en_ultimos_meses(4002, 2026, 8, cantidad_meses=3)
        self.assertIsNotNone(datos)

    def test_no_encuentra_fuera_de_la_ventana_de_meses(self):
        repo_cot.guardar_cotizacion(_cotizacion(4003, "05/04/2026"))  # 4 meses antes
        datos = repo_cot.buscar_en_ultimos_meses(4003, 2026, 8, cantidad_meses=3)
        self.assertIsNone(datos)

    def test_busca_tanto_en_json_activa_como_en_historial(self):
        repo_cot.guardar_cotizacion(_cotizacion(4004, "20/08/2026"))
        repo_cot.mover_a_historial(4004)
        datos = repo_cot.buscar_en_ultimos_meses(4004, 2026, 8, cantidad_meses=3)
        self.assertIsNotNone(datos)

    def test_ventana_de_meses_cruza_el_cambio_de_anio(self):
        repo_cot.guardar_cotizacion(_cotizacion(4005, "10/12/2025"))
        # Referencia enero 2026 -> revisa enero, diciembre y noviembre 2025.
        datos = repo_cot.buscar_en_ultimos_meses(4005, 2026, 1, cantidad_meses=3)
        self.assertIsNotNone(datos)

    def test_no_encontrada_da_none(self):
        self.assertIsNone(repo_cot.buscar_en_ultimos_meses(424242, 2026, 8))


if __name__ == "__main__":
    unittest.main()
