"""
tests/test_direcciones.py
Verifica core/repositorio.py::cargar_direcciones/direcciones_de_cliente/
guardar_direccion — direcciones.json es un archivo APARTE de clientes.json:
un cliente (por RUT) puede tener varias. Monkeypatch de DIRECCIONES_PATH a
un archivo temporal — no toca Dropbox ni AppData reales.

Correr con:  python -m unittest tests.test_direcciones -v
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
        ruta = Path(self._tmp.name) / "direcciones.json"
        self._parche = mock.patch.object(repo, "DIRECCIONES_PATH", ruta)
        self._parche.start()
        self.addCleanup(self._parche.stop)


class TestDirecciones(_ConArchivoTemporal):

    def test_cargar_direcciones_vacio_sin_archivo(self):
        self.assertEqual(repo.cargar_direcciones(), [])

    def test_guardar_direccion_la_deja_disponible(self):
        repo.guardar_direccion("12345678-9", "Empresa 1", calle="Av. Providencia", numero="1234")
        direcciones = repo.cargar_direcciones()
        self.assertEqual(len(direcciones), 1)
        self.assertEqual(direcciones[0]["rut"], "12.345.678-9")  # normalizado

    def test_guardar_direccion_sin_ningun_campo_de_direccion_no_revienta(self):
        repo.guardar_direccion("12345678-9", "Empresa 1")
        self.assertEqual(len(repo.cargar_direcciones()), 1)

    def test_un_cliente_puede_tener_varias_direcciones(self):
        repo.guardar_direccion("12345678-9", "Empresa 1", calle="Calle A", numero="100")
        repo.guardar_direccion("12345678-9", "Empresa 1", calle="Calle B", numero="200")
        self.assertEqual(len(repo.direcciones_de_cliente("12345678-9")), 2)

    def test_guardar_direccion_duplicada_no_se_repite(self):
        repo.guardar_direccion("12345678-9", "Empresa 1", calle="Calle A", numero="100")
        repo.guardar_direccion("12.345.678-9", "Empresa 1", calle="calle a", numero="100")
        self.assertEqual(len(repo.cargar_direcciones()), 1)

    def test_direcciones_de_cliente_filtra_por_rut_normalizado(self):
        repo.guardar_direccion("12345678-9", "Empresa 1", calle="Calle A", numero="100")
        repo.guardar_direccion("98765432-1", "Empresa 2", calle="Calle B", numero="200")
        propias = repo.direcciones_de_cliente("12.345.678-9")
        self.assertEqual(len(propias), 1)
        self.assertEqual(propias[0]["calle"], "Calle A")

    def test_direcciones_de_cliente_sin_direcciones_da_lista_vacia(self):
        self.assertEqual(repo.direcciones_de_cliente("11111111-1"), [])


if __name__ == "__main__":
    unittest.main()
