"""
tests/test_main_desbloqueo.py
Verifica main.py::_desbloquear_instalacion() — confirmado a mano en
v1.4.0-beta.1 que un .zip descargado por el navegador deja los archivos
extraídos marcados como "de Internet" (Mark of the Web, stream NTFS
":Zone.Identifier"), y que eso hace fallar la carga de Python.Runtime.dll
(pythonnet/clr_loader) en silencio. Esta función debe borrar ese stream de
cada archivo de la carpeta de instalación, solo en Windows y solo en el
build empaquetado (sys.frozen).

El test que de verdad crea y borra un stream ":Zone.Identifier" solo corre
en Windows (es una característica de NTFS) — en otras plataformas se
saltea. Correr con:  python -m unittest tests.test_main_desbloqueo -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main


class TestDesbloquearInstalacion(unittest.TestCase):

    def test_no_hace_nada_si_no_esta_frozen(self):
        with mock.patch.object(sys, "platform", "win32"), \
             mock.patch.object(sys, "frozen", False, create=True), \
             mock.patch("main.Path") as PathMock:
            main._desbloquear_instalacion()
            PathMock.assert_not_called()

    def test_no_hace_nada_fuera_de_windows(self):
        with mock.patch.object(sys, "platform", "darwin"), \
             mock.patch.object(sys, "frozen", True, create=True), \
             mock.patch("main.Path") as PathMock:
            main._desbloquear_instalacion()
            PathMock.assert_not_called()

    @unittest.skipUnless(sys.platform == "win32", "Zone.Identifier es de NTFS/Windows")
    def test_borra_el_stream_zone_identifier_de_verdad(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            archivo = base / "Python.Runtime.dll"
            archivo.write_bytes(b"contenido de prueba")
            # Simula el "Mark of the Web" que deja un .zip descargado por
            # el navegador al extraerse.
            with open(f"{archivo}:Zone.Identifier", "w") as f:
                f.write("[ZoneTransfer]\r\nZoneId=3\r\n")
            self.assertTrue(Path(f"{archivo}:Zone.Identifier").exists())

            falso_exe = base / "SistemaGestion.exe"
            falso_exe.write_bytes(b"")
            with mock.patch.object(sys, "platform", "win32"), \
                 mock.patch.object(sys, "frozen", True, create=True), \
                 mock.patch.object(sys, "executable", str(falso_exe)):
                main._desbloquear_instalacion()

            self.assertFalse(Path(f"{archivo}:Zone.Identifier").exists())
            # El archivo real, sin el stream, sigue intacto.
            self.assertEqual(archivo.read_bytes(), b"contenido de prueba")

    @unittest.skipUnless(sys.platform == "win32", "Zone.Identifier es de NTFS/Windows")
    def test_no_falla_con_archivos_sin_bloquear(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "sin_bloquear.txt").write_text("hola")
            falso_exe = base / "SistemaGestion.exe"
            falso_exe.write_bytes(b"")
            with mock.patch.object(sys, "platform", "win32"), \
                 mock.patch.object(sys, "frozen", True, create=True), \
                 mock.patch.object(sys, "executable", str(falso_exe)):
                main._desbloquear_instalacion()  # no debe lanzar excepción


if __name__ == "__main__":
    unittest.main()
