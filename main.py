"""
main.py  –  Punto de entrada de la aplicación.
"""

import sys
import atexit
import subprocess

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


def _revisar_actualizacion() -> bool:
    """
    Si hay una versión más nueva publicada en GitHub, la descarga y deja
    lista, mostrando un aviso mínimo mientras tanto. Devuelve True si la
    actualización quedó lista para relanzarse (el proceso actual debe
    cerrarse enseguida); False si no había nada nuevo, o si algo falló
    (sin internet, etc.) y hay que seguir abriendo la versión actual.
    """
    from core.actualizador import buscar_actualizacion, aplicar_actualizacion

    release = buscar_actualizacion()
    if release is None:
        return False

    import tkinter as tk
    import threading

    resultado = {"ok": False}
    aviso = tk.Tk()
    aviso.title("Actualizando")
    aviso.resizable(False, False)
    ancho, alto = 380, 110
    x = (aviso.winfo_screenwidth() - ancho) // 2
    y = (aviso.winfo_screenheight() - alto) // 2
    aviso.geometry(f"{ancho}x{alto}+{x}+{y}")
    tk.Label(
        aviso, text=f"Descargando la versión {release['tag']}...",
        font=("Segoe UI", 11), pady=25,
    ).pack(expand=True)

    def _hacer():
        resultado["ok"] = aplicar_actualizacion(release)
        aviso.after(0, aviso.destroy)

    threading.Thread(target=_hacer, daemon=True).start()
    aviso.mainloop()
    return resultado["ok"]


def main():
    if "--panel-produccion" in sys.argv:
        # Proceso hijo lanzado por mostrar_panel_mac() — SOLO en macOS.
        # Este proceso completo es el panel de producción, nada de
        # Tkinter acá (ver el docstring de ui/panel_produccion.py sobre
        # por qué macOS necesita esto en un proceso aparte).
        from ui.panel_produccion import ejecutar_panel_standalone
        ejecutar_panel_standalone()
        return

    if _revisar_actualizacion():
        return  # la nueva versión se relanza sola; este proceso termina acá

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
