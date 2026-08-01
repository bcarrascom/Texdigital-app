"""
core/escala.py
Escalado adaptativo de la interfaz según la resolución de pantalla.

Calcula un factor de escala para que las ventanas más grandes siempre
quepan en la pantalla actual, en cualquier SO y resolución.
"""

import tkinter as _tk

# Dimensiones de las ventanas más grandes que NO tienen scroll — deben
# coincidir con el TAM_MEDIDAS/ancho_ventana más grande de la app (ver
# ui/cotizacion.py y ui/ventana_resumen.py). Si se agranda alguna de esas
# ventanas, ACTUALIZAR ACÁ TAMBIÉN: si no, el factor de escala se calcula
# para un diseño más chico del que realmente hay que hacer entrar en
# pantalla, y en una pantalla más chica que la de referencia la ventana
# puede terminar sin entrar completa.
#   · VentanaResumen (cotizacion)      → 1850 px de ancho  ← la más ancha
#   · PantallaMedidas (cotizacion.py)  → 1480 px de alto   ← la más alta
_MAX_W = 1850
_MAX_H = 1480


def _calcular() -> float:
    """
    Calcula el factor de escala midiendo la pantalla con una ventana Tk temporal.
    Funciona en Windows, macOS y Linux.  Nunca supera 1.0 (solo escala hacia abajo).
    """
    tmp = _tk.Tk()
    tmp.withdraw()
    sw = tmp.winfo_screenwidth()
    sh = tmp.winfo_screenheight()
    tmp.destroy()
    # 95 % del ancho y 90 % del alto disponibles (el resto lo ocupa la barra del SO)
    f = min(sw * 0.95 / _MAX_W, sh * 0.90 / _MAX_H, 1.0)
    return max(round(f, 3), 0.60)   # mínimo 0.60 para no encoger demasiado


F: float = _calcular()


def px(v: int) -> int:
    """Escala un valor en píxeles (geometría de ventanas, canvas, paddings)."""
    return max(1, round(v * F))


def pt(v: int) -> int:
    """Escala un tamaño de fuente en puntos."""
    return max(7, round(v * F))
