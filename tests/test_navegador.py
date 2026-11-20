"""Tests de core/navegador.py: en el Mac, una pestaña nueva por AppleScript
en Safari o un Chromium; en cualquier otro caso, webbrowser.open."""

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from core import navegador


def _resultado(salida="", codigo=0):
    return subprocess.CompletedProcess(args=[], returncode=codigo, stdout=salida, stderr="")


class AbrirTest(unittest.TestCase):
    URL = "file:///tmp/OP%201005.html"

    def _abrir_en_mac(self, respuestas):
        """Corre navegador._abrir como en el Mac; `respuestas` son las
        salidas de cada osascript, en orden."""
        with mock.patch.object(navegador.sys, "platform", "darwin"), \
             mock.patch.object(navegador.subprocess, "run", side_effect=respuestas) as run, \
             mock.patch.object(navegador.webbrowser, "open") as abrir:
            navegador._abrir(self.URL)
        return run, abrir

    def test_chrome_abre_una_pestana_y_no_llama_a_webbrowser(self):
        run, abrir = self._abrir_en_mac([_resultado("com.google.Chrome\n"), _resultado("ok\n")])
        abrir.assert_not_called()
        args, kwargs = run.call_args_list[1]
        self.assertEqual(args[0], ["osascript", "-", self.URL])
        self.assertIn('application id "com.google.Chrome"', kwargs["input"])
        self.assertIn("make new tab", kwargs["input"])
        # La URL va como argumento, nunca dentro del script.
        self.assertNotIn(self.URL, kwargs["input"])

    def test_safari_abre_una_pestana(self):
        run, abrir = self._abrir_en_mac([_resultado("com.apple.Safari"), _resultado("ok")])
        abrir.assert_not_called()
        self.assertIn("set current tab to", run.call_args_list[1].kwargs["input"])

    def test_navegador_cerrado_abre_como_siempre(self):
        _, abrir = self._abrir_en_mac([_resultado("com.google.Chrome"), _resultado("cerrado")])
        abrir.assert_called_once_with(self.URL)

    def test_permiso_negado_abre_como_siempre(self):
        _, abrir = self._abrir_en_mac([_resultado("com.apple.Safari"), _resultado("", codigo=1)])
        abrir.assert_called_once_with(self.URL)

    def test_otro_navegador_abre_como_siempre(self):
        run, abrir = self._abrir_en_mac([_resultado("org.mozilla.firefox")])
        abrir.assert_called_once_with(self.URL)
        self.assertEqual(run.call_count, 1)

    def test_sin_navegador_por_defecto_abre_como_siempre(self):
        _, abrir = self._abrir_en_mac([_resultado("")])
        abrir.assert_called_once_with(self.URL)

    def test_sin_osascript_abre_como_siempre(self):
        _, abrir = self._abrir_en_mac(OSError("no está"))
        abrir.assert_called_once_with(self.URL)

    def test_en_windows_no_usa_osascript(self):
        with mock.patch.object(navegador.sys, "platform", "win32"), \
             mock.patch.object(navegador.subprocess, "run") as run, \
             mock.patch.object(navegador.webbrowser, "open") as abrir:
            navegador._abrir(self.URL)
        run.assert_not_called()
        abrir.assert_called_once_with(self.URL)

    def test_abrir_html_pasa_la_ruta_como_file_uri(self):
        with mock.patch.object(navegador, "_abrir") as abrir, \
             mock.patch.object(navegador.threading, "Thread") as hilo:
            hilo.side_effect = lambda target, args, daemon: mock.Mock(start=lambda: target(*args))
            navegador.abrir_html(Path("OP 1005.html"))
        url = abrir.call_args.args[0]
        self.assertTrue(url.startswith("file:///"))
        self.assertTrue(url.endswith("/OP%201005.html"))


if __name__ == "__main__":
    unittest.main()
