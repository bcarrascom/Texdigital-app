"""
tests/test_api_actualizacion.py
El estado que ve la pantalla al buscar e instalar una versión nueva
(ui/api_actualizacion.py). core.actualizador va mockeado: no hay red ni se
toca ninguna carpeta.

Correr con:  python -m unittest tests.test_api_actualizacion -v
"""

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.api_actualizacion as api_act
from ui.panel_produccion import salir_app

RELEASE = {"tag": "v2.1.1", "url": "u", "nombre": "SistemaGestion-windows.zip"}


class TestApiActualizacion(unittest.TestCase):

    def setUp(self):
        frozen = mock.patch.object(sys, "frozen", True, create=True)
        frozen.start()
        self.addCleanup(frozen.stop)
        # Los hilos corren en el momento, para no tener que esperarlos.
        hilo = mock.patch.object(api_act.threading, "Thread",
                                 side_effect=lambda target, args=(), daemon=None: mock.Mock(start=lambda: target(*args)))
        hilo.start()
        self.addCleanup(hilo.stop)
        self.api = api_act.ApiActualizacion()

    def test_sin_frozen_no_busca(self):
        with mock.patch.object(sys, "frozen", False, create=True):
            api = api_act.ApiActualizacion()
        with mock.patch.object(api_act.actualizador, "buscar_actualizacion") as buscar:
            self.assertEqual(api.buscar()["fase"], "no_disponible")
        buscar.assert_not_called()

    def test_encuentra_una_version_nueva(self):
        with mock.patch.object(api_act.actualizador, "buscar_actualizacion", return_value=RELEASE):
            self.api.buscar()
        estado = self.api.estado()
        self.assertEqual((estado["fase"], estado["nueva"]), ("disponible", "v2.1.1"))

    def test_al_dia(self):
        with mock.patch.object(api_act.actualizador, "buscar_actualizacion", return_value=None):
            self.api.buscar()
        self.assertEqual(self.api.estado()["fase"], "al_dia")

    def test_sin_internet_lo_dice_claro(self):
        with mock.patch.object(api_act.actualizador, "buscar_actualizacion",
                               side_effect=urllib.error.URLError("x")):
            self.api.buscar()
        estado = self.api.estado()
        self.assertEqual(estado["fase"], "error")
        self.assertIn("conexión a internet", estado["error"])

    def test_instalar_deja_listo_y_cierra_la_app(self):
        with mock.patch.object(api_act.actualizador, "buscar_actualizacion", return_value=RELEASE):
            self.api.buscar()
        with mock.patch.object(api_act.actualizador, "aplicar_actualizacion") as aplicar, \
             mock.patch.object(api_act.threading, "Timer") as timer:
            self.api.instalar()
        aplicar.assert_called_once()
        self.assertEqual(self.api.estado()["fase"], "listo")
        timer.assert_called_once_with(api_act.ESPERA_ANTES_DE_CERRAR, salir_app)

    def test_si_falla_la_instalacion_se_puede_volver_a_buscar(self):
        with mock.patch.object(api_act.actualizador, "buscar_actualizacion", return_value=RELEASE):
            self.api.buscar()
            with mock.patch.object(api_act.actualizador, "aplicar_actualizacion",
                                   side_effect=PermissionError("x")):
                self.api.instalar()
            self.assertEqual(self.api.estado()["fase"], "error")
            self.assertEqual(self.api.buscar()["fase"], "disponible")

    def test_no_instala_sin_una_version_encontrada(self):
        with mock.patch.object(api_act.actualizador, "aplicar_actualizacion") as aplicar:
            self.api.instalar()
        aplicar.assert_not_called()

    def test_recien_actualizado_se_dice_una_vez(self):
        api = api_act.ApiActualizacion(recien_actualizado=True)
        self.assertTrue(api.estado()["recien_actualizado"])
        self.assertFalse(api.estado()["recien_actualizado"])


if __name__ == "__main__":
    unittest.main()
