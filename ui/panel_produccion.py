"""
ui/panel_produccion.py
Panel de TV/producción: una sola ventana pywebview con dos vistas HTML que
se alternan navegando dentro de la misma ventana (location.href, del lado
JS — ver panel_lista.html/display_op.html), no dos ventanas separadas:
  - panel_lista.html  → listado + calendario de OPs activas (vista inicial,
    la que abre "Revisar OPs"). Pensada para la estación de impresión.
  - display_op.html   → detalle de una OP (tarjetas por producto, marcar
    listos, completar). Se llega haciendo doble clic en una fila del
    listado; Escape o el botón "← Volver" regresan al listado.
Ambas le piden los datos a esta API vía window.pywebview.api.

Es una ventana normal, movible y redimensionable, como cualquier otra
ventana de Windows: el usuario la arrastra al monitor/TV que quiera y la
maximiza él mismo. Pensada para quedar abierta por horas mientras en la
pantalla principal se sigue usando el programa normalmente (cotizar,
aprobar OPs, etc.). El botón "Recargar" de cada vista vuelve a leer las
carpetas de OPs, por lo que recoge los cambios hechos desde la pantalla
principal mientras tanto.

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
cuando el usuario aprieta "Revisar OPs" (siempre arrancando en el
listado). Cerrarla (la X de la ventana, o Escape en el listado) no la
destruye, solo la oculta — así sigue existiendo la misma ventana maestra
y el hilo principal no se libera hasta que se cierra la app por completo
(ver salir_app).
"""

import json
import os

import webview

from core.repositorio_ops import (
    carpeta_json,
    carpeta_completadas,
    carpeta_pendiente,
    carpeta_historial,
    mover_a_completadas,
    mover_a_pendiente,
    reactivar_desde_pendiente,
    actualizar_fecha_entrega,
    actualizar_listos,
    envejecer_completadas,
)
from core.repositorio import TEXTILES_ANCHOS
from core.rutas import RECURSOS

RUTA_LISTA   = RECURSOS / "panel_tv" / "panel_lista.html"
RUTA_DETALLE = RECURSOS / "panel_tv" / "display_op.html"

_ventana = None
_visible = False
_en_detalle = False
_op_objetivo = {"numero": None}


def _leer_carpeta(carpeta):
    ops = []
    for archivo in sorted(carpeta.glob("*.json")):
        try:
            ops.append(json.loads(archivo.read_text(encoding="utf-8")))
        except Exception:
            pass
    return ops


class _ApiPanelProduccion:

    def obtener_ops(self):
        """OPs activas (Dropbox/SGTD/OPs/JSON/)."""
        return _leer_carpeta(carpeta_json())

    def obtener_ops_completadas(self):
        """OPs completadas recientes (Dropbox/SGTD/OPs/Completadas/).
        Antes de leer, envejece a Historial/ las de más de 14 días."""
        envejecer_completadas()
        return _leer_carpeta(carpeta_completadas())

    def obtener_ops_pendientes(self):
        """OPs a la espera de fecha de entrega definitiva (.../Pendiente/)."""
        return _leer_carpeta(carpeta_pendiente())

    def obtener_op_por_numero(self, numero):
        """Busca una OP por número en cualquier carpeta (para abrir el
        detalle de una OP completada desde el listado)."""
        numero = int(numero)
        for carpeta in (carpeta_json(), carpeta_completadas(),
                         carpeta_pendiente(), carpeta_historial()):
            ruta = carpeta / f"{numero}.json"
            if ruta.exists():
                try:
                    return json.loads(ruta.read_text(encoding="utf-8"))
                except Exception:
                    return None
        return None

    def obtener_anchos_tela(self):
        """Mapeo tela → ancho máximo de rollo (recursos/textiles.json)."""
        return TEXTILES_ANCHOS

    def completar_op(self, numero):
        """Mueve el JSON de la OP de OPs/JSON/ a OPs/Completadas/."""
        mover_a_completadas(int(numero))

    def marcar_pendiente(self, numero):
        """Mueve el JSON de la OP de OPs/JSON/ a OPs/Pendiente/."""
        mover_a_pendiente(int(numero))

    def reactivar_op(self, numero, fecha_entrega):
        """Mueve el JSON de OPs/Pendiente/ a OPs/JSON/ con la nueva fecha."""
        reactivar_desde_pendiente(int(numero), fecha_entrega)

    def cambiar_entrega(self, numero, fecha_entrega):
        """Actualiza Fecha_entrega de una OP activa."""
        actualizar_fecha_entrega(int(numero), fecha_entrega)

    def guardar_listos(self, numero, indices):
        """Guarda en el JSON de la OP qué productos están marcados listos."""
        actualizar_listos(int(numero), list(indices))

    def ir_a_detalle(self, numero):
        """Guarda qué OP eligió el listado. La navegación al HTML de
        detalle la hace el propio JS (ir_a_detalle en panel_lista.html)
        después de recibir esta respuesta, para no pisar la página antes
        de que pywebview le entregue el valor de retorno."""
        global _en_detalle
        _op_objetivo["numero"] = int(numero)
        _en_detalle = True

    def confirmar_en_lista(self):
        """panel_lista.html avisa que ya terminó de cargar, para que
        mostrar_panel() sepa que, si el panel se vuelve a abrir más
        adelante, no hace falta forzar una recarga a RUTA_LISTA (ya
        estamos ahí)."""
        global _en_detalle
        _en_detalle = False

    def obtener_op_objetivo(self):
        """La vista de detalle la llama una vez al cargar, para saber con
        qué OP abrir (la que se eligió con doble clic en el listado)."""
        numero = _op_objetivo["numero"]
        _op_objetivo["numero"] = None
        return numero

    def cerrar(self):
        ocultar_panel()


def _on_closing():
    # Se ejecuta al apretar la X de la ventana del panel. Devolver False
    # cancela el cierre nativo: solo la ocultamos, no se destruye.
    ocultar_panel()
    return False


def iniciar_panel(func_app_escritorio):
    """
    Crea (oculta) la ventana del panel, arrancando en el listado, y arranca
    el bucle de pywebview en el hilo principal. `func_app_escritorio` (la
    app Tkinter completa, con su propio mainloop) corre en el hilo
    secundario que pywebview arranca por nosotros. Esta llamada bloquea
    hasta que se cierra la app entera (ver salir_app) — debe ser lo último
    que haga main().
    """
    global _ventana
    _ventana = webview.create_window(
        "Panel de Producción",
        url=str(RUTA_LISTA),
        js_api=_ApiPanelProduccion(),
        width=1280,
        height=800,
        hidden=True,
    )
    _ventana.events.closing += _on_closing
    webview.start(func_app_escritorio)


def mostrar_panel():
    """"Revisar OPs": muestra el panel, siempre arrancando en el listado
    (sin importar en qué vista se haya quedado la última vez).

    Si quedó en el detalle (ventana oculta con display_op.html cargado),
    hay que forzar la recarga a RUTA_LISTA. Esa recarga se hace DESPUÉS de
    mostrar la ventana, no antes: pedirle a pywebview que navegue una
    ventana todavía oculta es lo que dejaba _en_detalle sin recuperarse
    nunca (el evento "loaded" no vuelve a dispararse), rompiendo cualquier
    llamada a la API por el resto de la sesión ("Main window failed to
    start" en evaluate_js). Si ya estamos en el listado, no hace falta
    recargar nada."""
    global _visible
    if _ventana is None:
        return
    if not _visible:
        _ventana.show()
        if _en_detalle:
            _ventana.load_url(str(RUTA_LISTA))
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
