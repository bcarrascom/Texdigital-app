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


def main():
    _recordar_y_ocultar_terminal()
    atexit.register(_cerrar_terminal_mac)
    app = VentanaPrincipal()
    app.mainloop()


if __name__ == "__main__":
    main()
