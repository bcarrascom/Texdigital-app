"""
main.py  –  Punto de entrada de la aplicación.
"""

import os
import sys
import atexit
import subprocess
from pathlib import Path

# ID de la ventana de Terminal que abrió la app (se guarda al inicio).
_terminal_win_id = None


def _recordar_y_ocultar_terminal():
    """
    Al iniciar, guarda el ID de la ventana de Terminal activa (si existe)
    y la minimiza para que no moleste mientras se usa la app.
    Reintenta brevemente por si la ventana todavía no está registrada.
    """
    global _terminal_win_id
    if sys.platform != "darwin":
        return

    import time

    script_id = (
        'tell application "Terminal"\n'
        '  if (count of windows) > 0 then\n'
        '    return id of front window\n'
        '  end if\n'
        'end tell'
    )

    for _ in range(3):          # hasta 3 intentos con 0.2 s entre cada uno
        try:
            result = subprocess.run(
                ["osascript", "-e", script_id],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip().isdigit():
                _terminal_win_id = result.stdout.strip()
                # Minimizar la ventana de Terminal de inmediato
                script_min = (
                    'tell application "Terminal"\n'
                    '  set miniaturized of front window to true\n'
                    'end tell'
                )
                subprocess.run(
                    ["osascript", "-e", script_min],
                    capture_output=True, timeout=3
                )
                break
        except Exception:
            pass
        time.sleep(0.2)


def _cerrar_terminal_mac():
    """Al salir de Python, cierra la ventana de Terminal que abrió la app."""
    if sys.platform != "darwin":
        return
    try:
        if _terminal_win_id:
            script = (
                f'tell application "Terminal"\n'
                f'  close (every window whose id is {_terminal_win_id})\n'
                f'end tell'
            )
        else:
            script = (
                'tell application "Terminal"\n'
                '  if (count of windows) > 0 then\n'
                '    close front window\n'
                '  end if\n'
                'end tell'
            )
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, timeout=5
        )
    except Exception:
        pass


def _desbloquear_instalacion():
    """
    Confirmado a mano (v1.4.0-beta.1): los releases se distribuyen como
    .zip, y Windows marca cada archivo extraído de un .zip descargado por
    el navegador como "de Internet" (Mark of the Web, un stream NTFS
    ":Zone.Identifier" aparte). El loader de .NET Framework que usa
    pythonnet/clr_loader para pywebview en Windows se niega en silencio a
    cargar un ensamblado marcado así — Python.Runtime.dll no carga, y el
    error que tira ("Failed to resolve Python.Runtime.Loader.Initialize")
    no menciona el bloqueo para nada. Desbloqueando el .zip a mano antes
    de extraerlo (clic derecho → Propiedades → Desbloquear) el mismo build
    corre bien — esto hace lo mismo por código, apenas arranca, para que
    quien instala la app no tenga que enterarse nunca de este detalle:
    borra el stream ":Zone.Identifier" de cada archivo de la carpeta de
    instalación (si un archivo no está bloqueado, borrarlo falla y se
    ignora — no hay nada que hacer ahí).
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    base = Path(sys.executable).resolve().parent
    for archivo in base.rglob("*"):
        if archivo.is_file():
            try:
                os.remove(f"{archivo}:Zone.Identifier")
            except OSError:
                pass


def _silenciar_ruido_navegacion():
    """
    Filtra del log un efecto colateral inofensivo de tener una sola
    ventana persistente que navega con load_url() (ver ui/api_app.py):
    cada TD.api.xxx() llamado desde JS se procesa en un hilo de fondo de
    pywebview que, al terminar, siempre intenta devolver el resultado a un
    callback registrado en la página que hizo la llamada
    (window.pywebview._returnValuesCallbacks, ver webview/util.py::
    js_bridge_call) — sin importar si ese resultado se usa o no. Si esa
    llamada todavía estaba en camino cuando OTRA (p.ej. una navegación)
    reemplazó la página, el callback ya no existe y pywebview tira una
    JavascriptException en ese hilo de fondo. No se pierde nada (la página
    vieja ya no está, nadie seguía esperando ese resultado) pero ensucia
    la consola en cada navegación. Cualquier otra excepción de hilo se
    deja pasar igual que siempre — esto NO es un manejador general de
    errores, solo descarta esta forma de ruido puntual y ya identificada.
    """
    import threading
    from webview.errors import JavascriptException

    anterior = threading.excepthook

    def _filtro(args):
        exc = args.exc_value
        if isinstance(exc, JavascriptException):
            detalle = exc.args[0] if exc.args else None
            mensaje = detalle.get("message", "") if isinstance(detalle, dict) else str(detalle)
            if "_returnValuesCallbacks" in mensaje and "is not a function" in mensaje:
                return
        anterior(args)

    threading.excepthook = _filtro


def _iniciar_app():
    """
    Crea las ventanas iniciales (la ventana única de la app — menú + las
    4 pantallas a las que se navega desde ahí, ver ui.api_app.ApiApp — más
    la oculta del panel de producción, ver
    ui.panel_produccion.preparar_panel_oculto) y arranca el loop de
    pywebview en el hilo principal — sin `func`, ya no hay ningún otro
    toolkit (Tkinter) que arrancar en un hilo aparte. Bloquea hasta que se
    cierra la app entera (ver ui.panel_produccion.salir_app) — debe ser lo
    último que haga main().

    Igual en las 3 plataformas: ya no hace falta relanzar el proceso para
    abrir una pantalla (ver ui.api_app — antes, en macOS, cada pantalla se
    abría como proceso aparte; con una sola ventana persistente que solo
    navega vía load_url(), esa restricción de Cocoa/AppKit no aplica más,
    ver el docstring de ui/api_app.py). El panel de producción SÍ sigue
    necesitando su propio manejo por plataforma (es una segunda ventana
    concurrente de verdad, no una navegación de la principal) — ver
    ui/panel_produccion.py.
    """
    _recordar_y_ocultar_terminal()
    _silenciar_ruido_navegacion()

    import webview
    from ui.panel_produccion import preparar_panel_oculto
    from ui.api_app import ApiApp

    preparar_panel_oculto()
    ApiApp().crear_ventana()
    webview.start()


def main():
    _desbloquear_instalacion()

    if "--panel-produccion" in sys.argv:
        # Proceso hijo lanzado por mostrar_panel_mac() — SOLO en macOS.
        from ui.panel_produccion import ejecutar_panel_standalone
        ejecutar_panel_standalone()
        return

    atexit.register(_cerrar_terminal_mac)
    _iniciar_app()


if __name__ == "__main__":
    main()
