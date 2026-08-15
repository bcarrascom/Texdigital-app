"""
tests/test_actualizador.py
Verifica core/actualizador.py: comparación de versiones, selección del
asset para este SO, y buscar_actualizacion() contra la API de GitHub
(mockeada — no se hace ninguna llamada de red real).

Correr con:  python -m unittest tests.test_actualizador -v
"""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.actualizador as act


class TestVersionTupla(unittest.TestCase):

    def test_con_v_y_puntos(self):
        self.assertEqual(act._version_tupla("v1.2.3"), (1, 2, 3))

    def test_sin_v(self):
        self.assertEqual(act._version_tupla("1.2.3"), (1, 2, 3))

    def test_con_sufijo_dev(self):
        self.assertEqual(act._version_tupla("1.2.3-dev"), (1, 2, 3))

    def test_vacio_da_cero(self):
        self.assertEqual(act._version_tupla(""), (0,))

    def test_comparacion_mayor_menor(self):
        self.assertGreater(act._version_tupla("1.10.0"), act._version_tupla("1.9.0"))
        self.assertLess(act._version_tupla("1.2.0"), act._version_tupla("1.2.1"))


class TestAssetParaEsteOS(unittest.TestCase):

    def test_encuentra_el_asset_de_windows(self):
        with mock.patch.object(sys, "platform", "win32"):
            assets = [
                {"name": "SistemaGestion-macos.zip", "browser_download_url": "a"},
                {"name": "SistemaGestion-windows.zip", "browser_download_url": "b"},
            ]
            self.assertEqual(act._asset_para_este_os(assets)["browser_download_url"], "b")

    def test_sin_match_da_none(self):
        with mock.patch.object(sys, "platform", "win32"):
            assets = [{"name": "SistemaGestion-macos.zip", "browser_download_url": "a"}]
            self.assertIsNone(act._asset_para_este_os(assets))


class TestBuscarActualizacion(unittest.TestCase):

    def setUp(self):
        self._frozen_patch = mock.patch.object(sys, "frozen", True, create=True)
        self._frozen_patch.start()
        self.addCleanup(self._frozen_patch.stop)

    def _mock_respuesta(self, data: dict):
        cm = mock.MagicMock()
        cm.__enter__.return_value.read.return_value = json.dumps(data).encode("utf-8")
        cm.__exit__.return_value = False
        return cm

    def test_no_frozen_da_none_sin_llamar_a_la_red(self):
        with mock.patch.object(sys, "frozen", False, create=True):
            with mock.patch("urllib.request.urlopen") as m:
                self.assertIsNone(act.buscar_actualizacion())
                m.assert_not_called()

    def test_version_mas_nueva_devuelve_el_release(self):
        data = {
            "tag_name": "v99.0.0",
            "assets": [{"name": "SistemaGestion-windows.zip",
                        "browser_download_url": "https://example.com/x.zip"}],
        }
        with mock.patch.object(sys, "platform", "win32"), \
             mock.patch("urllib.request.urlopen", return_value=self._mock_respuesta(data)):
            release = act.buscar_actualizacion()
        self.assertEqual(release["tag"], "v99.0.0")
        self.assertEqual(release["url"], "https://example.com/x.zip")

    def test_version_igual_o_menor_da_none(self):
        data = {"tag_name": f"v{act.VERSION.lstrip('v')}", "assets": []}
        with mock.patch("urllib.request.urlopen", return_value=self._mock_respuesta(data)):
            self.assertIsNone(act.buscar_actualizacion())

    def test_release_sin_asset_para_este_os_lanza_excepcion(self):
        data = {
            "tag_name": "v99.0.0",
            "assets": [{"name": "SistemaGestion-macos.zip",
                        "browser_download_url": "https://example.com/x.zip"}],
        }
        with mock.patch.object(sys, "platform", "win32"), \
             mock.patch("urllib.request.urlopen", return_value=self._mock_respuesta(data)):
            with self.assertRaises(RuntimeError):
                act.buscar_actualizacion()

    def test_error_de_red_se_propaga(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("sin internet")):
            with self.assertRaises(OSError):
                act.buscar_actualizacion()

    def test_tag_vacio_lanza_excepcion(self):
        data = {"tag_name": "", "assets": []}
        with mock.patch("urllib.request.urlopen", return_value=self._mock_respuesta(data)):
            with self.assertRaises(RuntimeError):
                act.buscar_actualizacion()


if __name__ == "__main__":
    unittest.main()
