"""
tests/test_reportes_inventario.py
Verifica core/reportes_inventario.py: cuánto se usó y cuánto quedó de cada
textil y material en un mes, reconstruido desde los historiales (solo los
consumos de OP cuentan como uso; los ajustes cambian lo restante), el valor
de cada cosa, y los archivos: reportes/<año>/<mes>-<año>.json, el del mes en
curso se recalcula y los de meses terminados se cierran una vez y no se
tocan más.

Usa una carpeta temporal (mock de _ruta_base en los tres módulos) — no toca
Dropbox/AppData reales.

Correr con:  python -m unittest tests.test_reportes_inventario -v
"""

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_inventario as repo_inv
import core.repositorio_materiales as repo_mat
import core.reportes_inventario as reportes

HOY = date(2026, 10, 24)


def _uso(fecha, anterior, nuevo, tipo="consumo"):
    return {"id": f"{fecha}-{anterior}", "fecha": fecha, "tipo": tipo,
            "metros_restantes_anterior": anterior, "metros_restantes_nuevo": nuevo, "descripcion": ""}


def _entrada(fecha, anterior, nuevo, tipo="consumo", **extra):
    return {"id": f"{fecha}-{anterior}-{tipo}", "fecha": fecha, "tipo": tipo,
            "cantidad_anterior": anterior, "cantidad_nueva": nuevo, "descripcion": "", **extra}


class _ConRutaTemporal(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / "Inventario"
        for modulo in (repo_inv, repo_mat, reportes):
            parche = mock.patch.object(modulo, "_ruta_base", lambda: self.base)
            parche.start()
            self.addCleanup(parche.stop)
        parche = mock.patch("core.catalogo.nombre_textil", lambda n: n)
        parche.start()
        self.addCleanup(parche.stop)

    def rollo(self, id_, textil="Lona", fecha="01/09/2026", restantes=0.0, valor=1000.0, usos=(), decomiso=None):
        r = {"id": id_, "nombre_textil": textil, "ancho": 3.0, "metros_iniciales": 50.0,
             "metros_restantes": restantes, "fecha": fecha, "precio_compra": 0.0, "valor": valor,
             "proveedor": "", "estado": "activo", "usos": list(usos)}
        if decomiso:
            r["fecha_decomiso"] = decomiso
            carpeta = repo_inv.carpeta_decomisionados() / "2026" / decomiso[3:5]
            carpeta.mkdir(parents=True, exist_ok=True)
        else:
            carpeta = repo_inv.carpeta_activos()
        (carpeta / f"{id_}.json").write_text(json.dumps(r), encoding="utf-8")

    def material(self, id_, nombre="Ojal", cantidad=0.0, valor=100.0, historial=(), tipo="unidad"):
        m = {"id": id_, "nombre": nombre, "tipo": tipo, "cantidad": cantidad, "valor": valor,
             "anio_historial": 2026, "historial": list(historial)}
        (repo_mat.carpeta_materiales() / f"{id_}.json").write_text(json.dumps(m), encoding="utf-8")


class TestTextiles(_ConRutaTemporal):

    def test_usado_son_los_consumos_del_mes_y_restante_lo_que_quedo_al_cerrarlo(self):
        self.rollo("0001", restantes=20.0, usos=[
            _uso("15/09/2026", 50.0, 45.0),
            _uso("03/10/2026", 45.0, 40.0),
            _uso("20/10/2026", 40.0, 30.0),
            _uso("02/11/2026", 30.0, 20.0),
        ])
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual(fila["usado"], 15.0)
        self.assertEqual(fila["restante"], 30.0)
        self.assertEqual(fila["valor_vendido"], 15000.0)
        self.assertEqual(fila["valor_restante"], 30000.0)

    def test_inicial_es_lo_que_habia_al_empezar_el_mes(self):
        self.rollo("0001", restantes=30.0, usos=[
            _uso("15/09/2026", 50.0, 45.0),
            _uso("01/10/2026", 45.0, 30.0),
        ])
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual(fila["inicial"], 45.0)
        self.assertEqual(fila["ingresado"], 0.0)

    def test_rollo_cargado_en_el_mes_es_ingresado_y_no_inicial(self):
        self.rollo("0001", fecha="05/10/2026", restantes=40.0, usos=[_uso("05/10/2026", 50.0, 40.0)])
        self.rollo("0002", fecha="20/10/2026", restantes=30.0)
        reporte = reportes.generar_reporte(2026, 10, HOY)
        fila = reporte["textiles"][0]
        self.assertEqual(fila["inicial"], 0.0)
        self.assertEqual(fila["ingresado"], 80.0)
        self.assertEqual(fila["usado"], 10.0)
        self.assertEqual(fila["restante"], 70.0)
        self.assertEqual(reporte["totales"]["textiles"]["ingresado"], 80.0)

    def test_rollo_cargado_el_mes_anterior_no_es_ingresado(self):
        self.rollo("0001", fecha="28/09/2026", restantes=50.0)
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual((fila["inicial"], fila["ingresado"]), (50.0, 0.0))

    def test_lo_que_le_quedaba_a_un_rollo_decomisionado_es_uso_sin_venta(self):
        self.rollo("0001", restantes=3.0, decomiso="10/10/2026")
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual((fila["inicial"], fila["usado"], fila["restante"]), (3.0, 3.0, 0.0))
        self.assertEqual(fila["valor_vendido"], 0.0)

    def test_un_ajuste_que_resta_es_uso_pero_no_venta(self):
        self.rollo("0001", restantes=38.0, usos=[_uso("05/10/2026", 50.0, 38.0, tipo="ajuste")])
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual(fila["usado"], 12.0)
        self.assertEqual(fila["valor_vendido"], 0.0)
        self.assertEqual(fila["restante"], 38.0)

    def test_un_ajuste_que_suma_es_ingreso(self):
        self.rollo("0001", restantes=55.0, usos=[_uso("05/10/2026", 50.0, 55.0, tipo="ajuste")])
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual((fila["ingresado"], fila["usado"]), (5.0, 0.0))

    def test_inicial_mas_ingresado_menos_usado_da_el_restante(self):
        self.rollo("0001", restantes=20.0, usos=[
            _uso("15/09/2026", 50.0, 45.0),
            _uso("05/10/2026", 45.0, 30.0),
            _uso("08/10/2026", 30.0, 33.0, tipo="ajuste"),
            _uso("12/10/2026", 33.0, 20.0, tipo="ajuste"),
        ])
        self.rollo("0002", fecha="10/10/2026", restantes=8.0, decomiso="20/10/2026", usos=[_uso("11/10/2026", 30.0, 8.0)])
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertAlmostEqual(fila["inicial"] + fila["ingresado"] - fila["usado"], fila["restante"])

    def test_sin_movimientos_antes_de_fin_de_mes_queda_lo_que_habia_antes_del_primero(self):
        self.rollo("0001", fecha="01/09/2026", restantes=10.0, usos=[_uso("05/11/2026", 50.0, 10.0)])
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual(fila["restante"], 50.0)

    def test_suma_los_rollos_del_mismo_textil(self):
        self.rollo("0001", restantes=10.0)
        self.rollo("0002", restantes=5.0)
        reporte = reportes.generar_reporte(2026, 10, HOY)
        self.assertEqual(len(reporte["textiles"]), 1)
        self.assertEqual(reporte["textiles"][0]["rollos"], 2)
        self.assertEqual(reporte["textiles"][0]["restante"], 15.0)
        self.assertEqual(reporte["totales"]["textiles"]["restante"], 15.0)

    def test_rollo_que_entro_despues_del_mes_no_aparece(self):
        self.rollo("0001", fecha="02/11/2026", restantes=50.0)
        self.assertEqual(reportes.generar_reporte(2026, 10, HOY)["textiles"], [])

    def test_decomisionado_en_el_mes_cuenta_lo_usado_y_no_deja_restante(self):
        self.rollo("0001", restantes=2.0, decomiso="25/10/2026", usos=[_uso("10/10/2026", 12.0, 2.0)])
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual(fila["usado"], 10.0 + 2.0)
        self.assertEqual(fila["valor_vendido"], 10 * 1000.0)
        self.assertEqual(fila["restante"], 0.0)

    def test_decomisionado_antes_del_mes_no_aparece(self):
        self.rollo("0001", restantes=2.0, decomiso="20/09/2026")
        self.assertEqual(reportes.generar_reporte(2026, 10, HOY)["textiles"], [])

    def test_valor_vendido_con_el_de_cada_venta_y_restante_con_el_del_cierre(self):
        self.rollo("0001", restantes=20.0, valor=3000.0, usos=[
            dict(_uso("05/10/2026", 50.0, 40.0), valor_venta=1000.0),
            {**_uso("10/10/2026", 40.0, 40.0, tipo="precio"), "valor_anterior": 1000.0, "valor_nuevo": 2000.0},
            dict(_uso("15/10/2026", 40.0, 30.0), valor_venta=2000.0),
            {**_uso("03/11/2026", 30.0, 30.0, tipo="precio"), "valor_anterior": 2000.0, "valor_nuevo": 3000.0},
            dict(_uso("04/11/2026", 30.0, 20.0), valor_venta=3000.0),
        ])
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual(fila["valor_vendido"], 10 * 1000.0 + 10 * 2000.0)
        self.assertEqual(fila["valor_restante"], 30 * 2000.0)

    def test_consumo_viejo_sin_valor_guardado_usa_el_que_regia_ese_dia(self):
        self.rollo("0001", restantes=30.0, valor=2000.0, usos=[
            _uso("05/10/2026", 50.0, 40.0),
            {**_uso("10/10/2026", 40.0, 40.0, tipo="precio"), "valor_anterior": 1000.0, "valor_nuevo": 2000.0},
            _uso("15/10/2026", 40.0, 30.0),
        ])
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual(fila["valor_vendido"], 10 * 1000.0 + 10 * 2000.0)

    def test_rollo_sin_valor_queda_contado_aparte(self):
        self.rollo("0001", restantes=10.0, valor=None)
        fila = reportes.generar_reporte(2026, 10, HOY)["textiles"][0]
        self.assertEqual(fila["sin_valor"], 1)
        self.assertEqual(fila["valor_restante"], 0.0)


class TestMateriales(_ConRutaTemporal):

    def test_valor_vendido_con_el_precio_de_cada_op_y_restante_con_el_del_cierre(self):
        self.material("m1", cantidad=60.0, valor=300.0, historial=[
            _entrada("01/10/2026", 0.0, 100.0, tipo="restock"),
            _entrada("10/10/2026", 100.0, 90.0, valor_venta=100.0),
            _entrada("20/10/2026", 90.0, 80.0, valor_venta=200.0),
            _entrada("05/11/2026", 80.0, 80.0, tipo="precio", valor_anterior=200.0, valor_nuevo=300.0),
            _entrada("06/11/2026", 80.0, 60.0, valor_venta=300.0),
        ])
        fila = reportes.generar_reporte(2026, 10, HOY)["materiales"][0]
        self.assertEqual(fila["usado"], 20.0)
        self.assertEqual(fila["restante"], 80.0)
        self.assertEqual(fila["valor_vendido"], 1000.0 + 2000.0)
        self.assertEqual(fila["valor_restante"], 80.0 * 200.0)
        self.assertEqual(fila["unidad"], "un.")

    def test_inicial_e_ingresado_salen_del_stock_previo_y_los_restocks_del_mes(self):
        self.material("m1", cantidad=95.0, historial=[
            _entrada("01/09/2026", 0.0, 40.0, tipo="restock"),
            _entrada("03/10/2026", 40.0, 70.0, tipo="restock"),
            _entrada("10/10/2026", 70.0, 65.0, tipo="ajuste"),
            _entrada("12/10/2026", 65.0, 95.0, tipo="restock"),
            _entrada("02/11/2026", 95.0, 120.0, tipo="restock"),
        ])
        fila = reportes.generar_reporte(2026, 10, HOY)["materiales"][0]
        self.assertEqual(fila["inicial"], 40.0)
        self.assertEqual(fila["ingresado"], 60.0)
        self.assertEqual(fila["usado"], 5.0)   # el ajuste que restó
        self.assertEqual(fila["valor_vendido"], 0.0)
        self.assertEqual(fila["restante"], 95.0)

    def test_material_creado_en_el_mes_arranca_en_cero(self):
        self.material("m1", cantidad=25.0, historial=[_entrada("05/10/2026", 0.0, 25.0, tipo="restock")])
        fila = reportes.generar_reporte(2026, 10, HOY)["materiales"][0]
        self.assertEqual((fila["inicial"], fila["ingresado"]), (0.0, 25.0))

    def test_material_que_todavia_no_existia_no_aparece(self):
        self.material("m1", cantidad=10.0, historial=[_entrada("03/11/2026", 0.0, 10.0, tipo="restock")])
        self.assertEqual(reportes.generar_reporte(2026, 10, HOY)["materiales"], [])

    def test_lee_el_historial_archivado_de_anos_anteriores(self):
        archivo = self.base / "Historial" / "2025" / "Materiales" / "m1.json"
        archivo.parent.mkdir(parents=True)
        archivo.write_text(json.dumps([
            _entrada("01/12/2025", 0.0, 50.0, tipo="restock"),
            _entrada("15/12/2025", 50.0, 42.0, valor_venta=100.0),
        ]), encoding="utf-8")
        self.material("m1", cantidad=42.0, historial=[])
        fila = reportes.generar_reporte(2025, 12, HOY)["materiales"][0]
        self.assertEqual(fila["usado"], 8.0)
        self.assertEqual(fila["restante"], 42.0)


class TestArchivos(_ConRutaTemporal):

    def test_guarda_el_mes_en_curso_en_su_carpeta_de_ano(self):
        self.rollo("0001", restantes=10.0)
        reportes.actualizar_reportes(HOY)
        ruta = self.base / "reportes" / "2026" / "octubre-2026.json"
        self.assertTrue(ruta.exists())
        self.assertFalse(json.loads(ruta.read_text(encoding="utf-8"))["cerrado"])

    def test_cierra_los_meses_terminados_desde_el_primero_con_datos(self):
        self.rollo("0001", fecha="10/08/2026", restantes=10.0)
        reportes.actualizar_reportes(HOY)
        meses = reportes.listar_reportes()
        self.assertEqual([(m["anio"], m["mes"], m["cerrado"]) for m in meses],
                         [(2026, 10, False), (2026, 9, True), (2026, 8, True)])

    def test_un_reporte_cerrado_no_se_vuelve_a_calcular(self):
        self.rollo("0001", fecha="10/09/2026", restantes=10.0)
        ruta = self.base / "reportes" / "2026" / "septiembre-2026.json"
        ruta.parent.mkdir(parents=True)
        ruta.write_text(json.dumps({"anio": 2026, "mes": 9, "cerrado": True, "textiles": [], "materiales": []}),
                        encoding="utf-8")
        reportes.actualizar_reportes(HOY)
        self.assertEqual(json.loads(ruta.read_text(encoding="utf-8"))["textiles"], [])

    def test_un_reporte_de_un_mes_terminado_sin_cerrar_se_cierra(self):
        self.rollo("0001", fecha="10/09/2026", restantes=10.0)
        reportes.actualizar_reportes(date(2026, 9, 15))
        reportes.actualizar_reportes(HOY)
        self.assertTrue(reportes.obtener_reporte(2026, 9)["cerrado"])

    def test_no_reescribe_un_reporte_que_no_cambio(self):
        self.rollo("0001", restantes=10.0)
        reportes.actualizar_reportes(HOY)
        ruta = self.base / "reportes" / "2026" / "octubre-2026.json"
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["generado"] = "marca"
        ruta.write_text(json.dumps(datos), encoding="utf-8")
        reportes.actualizar_reportes(HOY)
        self.assertEqual(reportes.obtener_reporte(2026, 10)["generado"], "marca")

    def test_recalcular_desde_reescribe_tambien_los_cerrados(self):
        self.rollo("0001", fecha="10/09/2026", restantes=10.0)
        ruta = self.base / "reportes" / "2026" / "septiembre-2026.json"
        ruta.parent.mkdir(parents=True)
        ruta.write_text(json.dumps({"anio": 2026, "mes": 9, "cerrado": True, "textiles": [], "materiales": []}),
                        encoding="utf-8")
        reportes.recalcular_desde(["15/09/2026"], HOY)
        septiembre = reportes.obtener_reporte(2026, 9)
        self.assertTrue(septiembre["cerrado"])
        self.assertEqual(len(septiembre["textiles"]), 1)
        self.assertIsNotNone(reportes.obtener_reporte(2026, 10))

    def test_recalcular_sin_fechas_no_hace_nada(self):
        reportes.recalcular_desde([], HOY)
        self.assertEqual(reportes.listar_reportes(), [])

    def test_listar_ignora_archivos_con_otro_nombre(self):
        carpeta = self.base / "reportes" / "2026"
        carpeta.mkdir(parents=True)
        (carpeta / "octubre-2026 (copia en conflicto).json").write_text("{}", encoding="utf-8")
        self.assertEqual(reportes.listar_reportes(), [])

    def test_obtener_un_mes_invalido_da_none(self):
        self.assertIsNone(reportes.obtener_reporte(2026, 0))
        self.assertIsNone(reportes.obtener_reporte(2026, 13))


if __name__ == "__main__":
    unittest.main()
