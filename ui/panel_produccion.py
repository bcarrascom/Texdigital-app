"""
ui/panel_produccion.py
Panel de TV de producción: ventana pywebview que muestra las Órdenes de
Producción (OP) activas, leídas en vivo desde Dropbox/SGTD/OPs/JSON/. El
HTML/JS vive en recursos/panel_tv/display_op.html y le pide los datos a
esta API vía window.pywebview.api.

Es una ventana normal, movible y redimensionable, como cualquier otra
ventana de Windows: el usuario la arrastra al monitor/TV que quiera y la
maximiza él mismo. Pensada para quedar abierta por horas mientras en la
pantalla principal se sigue usando el programa normalmente (cotizar,
aprobar OPs, etc.). El botón "Recargar" del panel vuelve a leer la carpeta
de OPs, por lo que recoge ahí las que se aprueben mientras tanto desde la
pantalla principal.

── Arquitectura de hilos (importante) ──────────────────────────────────────
En Windows, pywebview exige que su ventana "maestra" (la primera que se
crea en el proceso) se cree y arranque desde el hilo principal — registra
un manejador de SIGINT ahí, lo que sólo es legal en ese hilo — y bloquea
ese hilo hasta que esa ventana se destruye. Por eso la app se invierte
respecto a un programa Tkinter normal: el hilo principal lo ocupa
pywebview (ver iniciar_panel) y el resto del programa (toda la app
Tkinter) corre en un hilo secundario, que pywebview arranca por nosotros
vía el parámetro `func` de webview.start().

La ventana del panel se crea oculta al iniciar la app y solo se muestra
cuando el usuario aprieta "Abrir panel TV". Cerrarla (la X de la ventana,
o Escape dentro del panel) no la destruye, solo la oculta — así sigue
existiendo la misma ventana maestra y el hilo principal no se libera hasta
que se cierra la app por completo (ver salir_app).
"""

import json
import os

import webview

from core.repositorio_ops import carpeta_json, mover_a_historial, actualizar_listos
from core.repositorio import TEXTILES_ANCHOS
from core.rutas import RECURSOS

RUTA_HTML = RECURSOS / "panel_tv" / "display_op.html"

_ventana = None
_visible = False


class _ApiPanelProduccion:

    def obtener_ops(self):
        """Lee todas las OPs activas desde Dropbox/SGTD/OPs/JSON/."""
        ops = []
        for archivo in sorted(carpeta_json().glob("*.json")):
            try:
                ops.append(json.loads(archivo.read_text(encoding="utf-8")))
            except Exception:
                pass
        return ops

    def obtener_anchos_tela(self):
        """Mapeo tela → ancho máximo de rollo (recursos/textiles.txt)."""
        return TEXTILES_ANCHOS

    def completar_op(self, numero):
        """Mueve el JSON de la OP de OPs/JSON/ a OPs/Historial/."""
        mover_a_historial(int(numero))

    def guardar_listos(self, numero, indices):
        """Guarda en el JSON de la OP qué productos están marcados listos."""
        actualizar_listos(int(numero), list(indices))

    def cerrar(self):
        ocultar_panel()


def _on_closing():
    # Se ejecuta al apretar la X de la ventana del panel. Devolver False
    # cancela el cierre nativo: solo la ocultamos, no se destruye.
    ocultar_panel()
    return False


def iniciar_panel(func_app_escritorio):
    """
    Crea (oculta) la ventana del panel y arranca el bucle de pywebview en
    el hilo principal. `func_app_escritorio` (la app Tkinter completa, con
    su propio mainloop) corre en el hilo secundario que pywebview arranca
    por nosotros. Esta llamada bloquea hasta que se cierra la app entera
    (ver salir_app) — debe ser lo último que haga main().
    """
    global _ventana
    _ventana = webview.create_window(
        "Panel de Producción",
        url=str(RUTA_HTML),
        js_api=_ApiPanelProduccion(),
        width=1280,
        height=800,
        hidden=True,
    )
    _ventana.events.closing += _on_closing
    webview.start(func_app_escritorio)


def mostrar_panel():
    global _visible
    if _ventana is None or _visible:
        return
    _ventana.show()
    _visible = True


def ocultar_panel():
    global _visible
    if _ventana is None or not _visible:
        return
    _ventana.hide()
    _visible = False


def panel_esta_abierto() -> bool:
    return _visible


def salir_app():
    """
    Termina la app por completo. Reemplaza a sys.exit(0) en los cierres de
    ventana: ahora el hilo principal lo ocupa pywebview, así que un
    sys.exit normal desde el hilo de Tkinter solo terminaría ese hilo y
    dejaría el proceso colgado.
    """
    os._exit(0)
