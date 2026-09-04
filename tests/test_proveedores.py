"""
tests/test_proveedores.py
Verifica core/repositorio.py::cargar_proveedores/guardar_proveedor —
proveedores.json vive en Conf (crece a medida que el operador carga
rollos nuevos en Inventario, ver core/repositorio_inventario.py), no es
un catálogo de referencia como textiles.json. Monkeypatch de
PROVEEDORES_PATH a un archivo temporal — no toca Dropbox ni AppData reales.

Correr con:  python -m unittest tests.test_proveedores -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio as repo


class _ConArchivoTemporal(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        ruta = Path(self._tmp.name) / "proveedores.json"
        self._parche = mock.patch.object(repo, "PROVEEDORES_PATH", ruta)
        self._parche.start()
        self.addCleanup(self._parche.stop)


class TestProveedores(_ConArchivoTemporal):

    def test_cargar_proveedores_vacio_sin_archivo(self):
        self.assertEqual(repo.cargar_proveedores(), [])

    def test_guardar_proveedor_lo_deja_disponible(self):
        repo.guardar_proveedor("Textiles del Sur")
        self.assertEqual(repo.cargar_proveedores(), ["Textiles del Sur"])

    def test_guardar_proveedor_no_duplica_por_nombre(self):
        repo.guardar_proveedor("Textiles del Sur")
        repo.guardar_proveedor("textiles del sur")  # mismo nombre, otra capitalización
        self.assertEqual(len(repo.cargar_proveedores()), 1)

    def test_guardar_proveedor_vacio_no_hace_nada(self):
        repo.guardar_proveedor("   ")
        self.assertEqual(repo.cargar_proveedores(), [])

    def test_varios_proveedores_se_acumulan(self):
        repo.guardar_proveedor("Proveedor A")
        repo.guardar_proveedor("Proveedor B")
        self.assertEqual(repo.cargar_proveedores(), ["Proveedor A", "Proveedor B"])


if __name__ == "__main__":
    unittest.main()
