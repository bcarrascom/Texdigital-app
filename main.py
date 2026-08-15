"""
main.py  –  Punto de entrada de la aplicación.
"""

import os
import sys
import atexit
import subprocess
from pathlib import Path

from ui.interfaz import VentanaPrincipal

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


def _iniciar_app_escritorio():
    _recordar_y_ocultar_terminal()
    app = VentanaPrincipal()
    app.mainloop()


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


def main():
    _desbloquear_instalacion()

    if "--panel-produccion" in sys.argv:
        # Proceso hijo lanzado por mostrar_panel_mac() — SOLO en macOS.
        # Este proceso completo es el panel de producción, nada de
        # Tkinter acá (ver el docstring de ui/panel_produccion.py sobre
        # por qué macOS necesita esto en un proceso aparte).
        from ui.panel_produccion import ejecutar_panel_standalone
        ejecutar_panel_standalone()
        return

    atexit.register(_cerrar_terminal_mac)

    if sys.platform == "darwin":
        # macOS: Tkinter (Cocoa) y pywebview exigen CADA UNO el hilo
        # principal real del proceso - no se puede repartir como en
        # Windows/Linux. Acá la app de escritorio corre directo en este
        # hilo; el panel de producción se abre como proceso aparte (ver
        # ui/panel_produccion.py) cuando se aprieta "Revisar OPs".
        _iniciar_app_escritorio()
    else:
        # Windows/Linux: pywebview necesita el hilo principal del proceso;
        # la app de escritorio Tkinter corre en el hilo secundario que
        # iniciar_panel() arranca por nosotros. Ver ui/panel_produccion.py.
        from ui.panel_produccion import iniciar_panel
        iniciar_panel(_iniciar_app_escritorio)


if __name__ == "__main__":
    main()
