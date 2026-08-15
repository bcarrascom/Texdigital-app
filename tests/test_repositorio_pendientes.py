"""
tests/test_repositorio_pendientes.py
Verifica core/repositorio_pendientes.py (carpeta dedicada plana, sin
estructura AAAA/MM — ver docstring del módulo). Usa una carpeta temporal
(mock de _detectar_dropbox) — no toca Dropbox ni AppData reales, mismo
criterio que tests/test_repositorio_cotizaciones.py.

Correr con:  python -m unittest tests.test_repositorio_pendientes -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio_pendientes as repo_pend


def _pendiente(id_, nombre="Trabajo X", n_productos=1):
    return {
        "id": id_,
        "tipo": "normal",
        "nombre_trabajo": nombre,
        "productos": [{"producto": "Lona"} for _ in range(n_productos)],
        "despacho": None,
        "instalacion": None,
        "guardado_en": "15/08/2026 10:00",
    }


class _ConRutaTemporal(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._base = Path(self._tmp.name)
        self._parche = mock.patch.object(repo_pend, "_detectar_dropbox", lambda: None)
        self._parche.start()
        self.addCleanup(self._parche.stop)
        self._parche_datos = mock.patch.object(repo_pend, "DATOS", self._base)
        self._parche_datos.start()
        self.addCleanup(self._parche_datos.stop)


class TestNuevoId(unittest.TestCase):

    def test_nuevo_id_es_unico(self):
        self.assertNotEqual(repo_pend.nuevo_id(), repo_pend.nuevo_id())


class TestGuardarYCargar(_ConRutaTemporal):

    def test_guardar_pendiente_la_deja_en_carpeta_pendientes(self):
        id_ = repo_pend.nuevo_id()
        repo_pend.guardar_pendiente(_pendiente(id_))
        self.assertTrue((self._base / "Cotizaciones" / "Pendientes" / f"{id_}.json").exists())

    def test_cargar_pendiente_la_encuentra_por_id(self):
        id_ = repo_pend.nuevo_id()
        repo_pend.guardar_pendiente(_pendiente(id_, nombre="Cubre alarma"))
        datos = repo_pend.cargar_pendiente(id_)
        self.assertIsNotNone(datos)
        self.assertEqual(datos["nombre_trabajo"], "Cubre alarma")

    def test_cargar_pendiente_inexistente_da_none(self):
        self.assertIsNone(repo_pend.cargar_pendiente("no-existe"))

    def test_reguardar_el_mismo_id_sobreescribe_no_duplica(self):
        id_ = repo_pend.nuevo_id()
        repo_pend.guardar_pendiente(_pendiente(id_, n_productos=1))
        repo_pend.guardar_pendiente(_pendiente(id_, n_productos=3))
        self.assertEqual(len(repo_pend.cargar_pendiente(id_)["productos"]), 3)
        self.assertEqual(len(list(repo_pend.carpeta_pendientes().glob("*.json"))), 1)

    def test_listar_pendientes_devuelve_todas_las_guardadas(self):
        repo_pend.guardar_pendiente(_pendiente(repo_pend.nuevo_id(), nombre="A"))
        repo_pend.guardar_pendiente(_pendiente(repo_pend.nuevo_id(), nombre="B"))
        nombres = {p["nombre_trabajo"] for p in repo_pend.listar_pendientes()}
        self.assertEqual(nombres, {"A", "B"})


class TestEliminar(_ConRutaTemporal):

    def test_eliminar_pendiente_existente(self):
        id_ = repo_pend.nuevo_id()
        repo_pend.guardar_pendiente(_pendiente(id_))
        self.assertTrue(repo_pend.eliminar_pendiente(id_))
        self.assertIsNone(repo_pend.cargar_pendiente(id_))

    def test_eliminar_pendiente_inexistente_da_false(self):
        self.assertFalse(repo_pend.eliminar_pendiente("no-existe"))


if __name__ == "__main__":
    unittest.main()
