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


class TestEditarProveedor(_ConArchivoTemporal):

    def test_renombra(self):
        repo.guardar_proveedor("Textiles del Sur")
        self.assertTrue(repo.editar_proveedor("Textiles del Sur", "Textiles del Norte"))
        self.assertEqual(repo.cargar_proveedores(), ["Textiles del Norte"])

    def test_mantiene_la_posicion_en_la_lista(self):
        repo.guardar_proveedor("A")
        repo.guardar_proveedor("B")
        repo.guardar_proveedor("C")
        repo.editar_proveedor("B", "B renombrado")
        self.assertEqual(repo.cargar_proveedores(), ["A", "B renombrado", "C"])

    def test_nombre_actual_inexistente_da_false(self):
        self.assertFalse(repo.editar_proveedor("No existe", "Nuevo"))
        self.assertEqual(repo.cargar_proveedores(), [])

    def test_no_permite_colisionar_con_otro_proveedor(self):
        repo.guardar_proveedor("A")
        repo.guardar_proveedor("B")
        self.assertFalse(repo.editar_proveedor("A", "b"))  # ya es "B", sin importar mayúsculas
        self.assertEqual(repo.cargar_proveedores(), ["A", "B"])

    def test_renombrar_a_si_mismo_con_otra_capitalizacion_funciona(self):
        repo.guardar_proveedor("Textiles del Sur")
        self.assertTrue(repo.editar_proveedor("Textiles del Sur", "textiles del sur"))
        self.assertEqual(repo.cargar_proveedores(), ["textiles del sur"])

    def test_nombre_nuevo_vacio_no_hace_nada(self):
        repo.guardar_proveedor("A")
        self.assertFalse(repo.editar_proveedor("A", "   "))
        self.assertEqual(repo.cargar_proveedores(), ["A"])


class TestEliminarProveedor(_ConArchivoTemporal):

    def test_elimina(self):
        repo.guardar_proveedor("A")
        repo.guardar_proveedor("B")
        self.assertTrue(repo.eliminar_proveedor("A"))
        self.assertEqual(repo.cargar_proveedores(), ["B"])

    def test_es_insensible_a_mayusculas(self):
        repo.guardar_proveedor("Textiles del Sur")
        self.assertTrue(repo.eliminar_proveedor("textiles DEL sur"))
        self.assertEqual(repo.cargar_proveedores(), [])

    def test_inexistente_da_false(self):
        self.assertFalse(repo.eliminar_proveedor("No existe"))


if __name__ == "__main__":
    unittest.main()
