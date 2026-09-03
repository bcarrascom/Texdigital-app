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

── Arquitectura de ventanas/procesos (importante) ───────────────────────────
Desde que se retiró Tkinter, la app entera corre sobre pywebview, sin
ningún otro toolkit de por medio — y desde que la ventana principal
(menú + las 4 pantallas a las que se navega desde ahí, ver
ui/api_app.py::ApiApp) pasó a ser UNA sola ventana persistente que navega
con load_url() en vez de crear una ventana nueva por pantalla, este panel
es la ÚNICA razón por la que sigue existiendo el modelo de "ventana
aparte"/"proceso aparte": es una segunda ventana CONCURRENTE de verdad
(coexiste con la ventana principal, no la reemplaza), a diferencia de
las 4 pantallas de ApiApp, que ya no necesitan serlo.

En Windows/Linux es simplemente UNA VENTANA MÁS del mismo proceso
pywebview: main.py la crea oculta al arrancar (preparar_panel_oculto,
llamado ANTES de webview.start() junto con la ventana principal — ver
ui.api_app.ApiApp.crear_ventana). mostrar_panel()/ocultar_panel() solo la
muestran/ocultan (nunca la destruyen) cuando el usuario aprieta
"Revisar OPs" (siempre arrancando en el listado).

En **macOS**, en cambio, el panel corre como **proceso aparte** — porque
Cocoa/AppKit exige que cada ventana pywebview se cree y controle desde el
hilo principal real de SU PROPIO proceso, y ese hilo ya lo ocupa la
ventana principal de la app. Esa restricción es sobre CREAR una ventana
nueva, no sobre navegar una ya creada (por eso las 4 pantallas de
ApiApp, que solo navegan la ventana principal ya existente, no necesitan
esto) — pero el panel es una ventana genuinamente NUEVA y CONCURRENTE, así
que sigue haciendo falta. Al apretar "Revisar OPs" en macOS se lanza el
mismo ejecutable de nuevo con el flag `--panel-produccion` (ver main.py),
que hace que ese nuevo proceso corra ÚNICAMENTE
ejecutar_panel_standalone(). Se comunican solo a través de los JSON de
Dropbox (igual que con el resto de la app), no hace falta nada más.
- mostrar_panel()/ocultar_panel()/preparar_panel_oculto() son la versión
  Windows/Linux (un solo proceso); mostrar_panel_mac()/
  ejecutar_panel_standalone() son la versión macOS (proceso aparte). Cuál
  se usa lo decide ui/api_app.py::ApiApp.ir() según sys.platform; en
  Windows/Linux la ventana oculta ya existe siempre (preparada al
  arrancar, ver arriba), en macOS mostrar_panel_mac() lanza el proceso
  recién al primer click.
"""

import json
import os
import sys
import webbrowser

import webview

from core.repositorio_ops import (
    carpeta_json,
    carpeta_completadas,
    carpeta_pendiente,
    cargar_op,
    completar_op as _completar_op,
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
_modo_standalone_mac = False   # True solo en el proceso aparte del panel (macOS)
_proceso_panel_mac = None      # Popen del proceso del panel, si está corriendo (macOS)


def _leer_carpeta(carpeta):
    ops = []
    # JSON/Completadas/Pendiente son planas (ver core/repositorio_ops.py —
    # solo Historial/ se organiza en subcarpetas AAAA/MM, y esta función
    # nunca lee Historial/).
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
        return cargar_op(int(numero))

    def generar_html_op(self, numero):
        """Genera el HTML imprimible de la OP (sin precios, para los
        trabajadores de planta — ver core/presentar_op.py) y lo abre en el
        navegador. Devuelve True si pudo, False si la OP no existe o algo
        falló (el JS solo necesita saber si mostrar un error)."""
        datos = cargar_op(int(numero))
        if datos is None:
            return False
        try:
            from core.presentar_op import generar_html
            ruta_html = generar_html(datos)
            webbrowser.open(ruta_html.as_uri())
            return True
        except Exception as e:
            print("No se pudo generar el HTML de la OP:", e)
            return False

    def obtener_anchos_tela(self):
        """Mapeo tela → ancho máximo de rollo (recursos/textiles.json)."""
        return TEXTILES_ANCHOS

    def completar_op(self, numero):
        """Completa la OP — ver core.repositorio_ops.completar_op (decide
        sola entre Completadas/ y Despachos/ según si tiene Despacho/
        Instalacion). Mismo punto de entrada que usa ahora también el
        botón "Completar" de ver-op.html, en la ventana principal."""
        _completar_op(numero)

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
        # En modo proceso aparte (macOS) este proceso ES el panel — no
        # tiene sentido "ocultarlo", hay que cerrarlo de verdad y listo
        # (la próxima vez que se apriete "Revisar OPs" se lanza uno nuevo).
        if _modo_standalone_mac:
            _ventana.destroy()
        else:
            ocultar_panel()


def _on_closing():
    # Se ejecuta al apretar la X de la ventana del panel. Devolver False
    # cancela el cierre nativo: solo la ocultamos, no se destruye.
    ocultar_panel()
    return False


def preparar_panel_oculto() -> None:
    """
    Crea (oculta) la ventana del panel, arrancando en el listado — SOLO
    Windows/Linux (modo un solo proceso). Debe llamarse ANTES de
    webview.start() (ver main.py), junto con la creación de la ventana
    principal (ui.api_app.ApiApp.crear_ventana) — main.py es quien arranca
    el bucle de pywebview (webview.start()) recién después de crear todas
    las ventanas iniciales, no esta función.
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


# ══════════════════════════════════════════════════════════════════════════════
# Modo macOS: panel como proceso aparte (ver docstring del módulo)
# ══════════════════════════════════════════════════════════════════════════════

def ejecutar_panel_standalone():
    """
    Punto de entrada del proceso hijo en macOS (lanzado por main.py con el
    flag --panel-produccion). Este proceso ES el panel, nada más — corre
    en su propio hilo principal real, sin Tkinter compitiendo por él.
    Bloquea hasta que se cierra la ventana (o el proceso padre lo mata al
    salir, ver salir_app), y ahí termina el proceso solo.
    """
    global _ventana, _modo_standalone_mac
    _modo_standalone_mac = True
    _ventana = webview.create_window(
        "Panel de Producción",
        url=str(RUTA_LISTA),
        js_api=_ApiPanelProduccion(),
        width=1280,
        height=800,
    )
    webview.start()


def _comando_relanzar_panel() -> list[str]:
    """Comando para lanzar este mismo programa en modo panel-standalone.
    Empaquetado (PyInstaller): sys.executable ES el ejecutable ya armado,
    re-invocarlo con el flag alcanza. Corriendo desde código fuente: hay
    que decirle al intérprete qué script correr."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--panel-produccion"]
    from pathlib import Path
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    return [sys.executable, str(main_py), "--panel-produccion"]


def mostrar_panel_mac():
    """"Revisar OPs" en macOS: lanza el panel como proceso aparte si no
    hay uno corriendo ya. Si el usuario lo cerró, el siguiente click lanza
    uno nuevo — arranca siempre en el listado, igual que en Windows/Linux."""
    global _proceso_panel_mac
    if _proceso_panel_mac is not None and _proceso_panel_mac.poll() is None:
        return  # ya hay un panel abierto en su propio proceso
    import subprocess
    _proceso_panel_mac = subprocess.Popen(_comando_relanzar_panel())


def salir_app():
    """
    Termina la app por completo. Reemplaza a un cierre de ventana normal:
    en Windows/Linux la ventana oculta del panel (ver
    preparar_panel_oculto) mantiene vivo el proceso durante toda la
    sesión, así que hace falta un os._exit explícito para terminarlo de
    verdad. También mata el proceso del panel en macOS si quedó abierto,
    para no dejarlo huérfano.
    """
    if _proceso_panel_mac is not None and _proceso_panel_mac.poll() is None:
        try:
            _proceso_panel_mac.terminate()
        except Exception:
            pass
    os._exit(0)
