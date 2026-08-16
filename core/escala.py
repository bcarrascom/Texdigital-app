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

    OJO en macOS: winfo_screenwidth()/winfo_screenheight() devuelven la
    resolución LÓGICA (en puntos), no los píxeles físicos — Retina ya está
    manejado de forma transparente por macOS/Tk. Un Mac con pantalla Retina
    puede perfectamente reportar una resolución lógica MÁS CHICA que un
    monitor Windows 1080p corriente (ej. MacBook 13" Retina: 1440×900
    puntos), aunque la pantalla en sí sea de mayor densidad/calidad — no
    es una pantalla chica de verdad, y no debería tratarse como una.
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
# Piso más alto que el de F, solo para texto (ver pt()): F=0.60 shrinkea un
# FUENTE_LABEL de 13pt a 7-8pt, ilegible — confirmado en un Mac con
# resolución lógica chica (ver docstring de _calcular arriba), a pesar de
# ser una pantalla de alta densidad. La geometría de ventanas/canvas sigue
# shrinkeando hasta F para entrar en pantallas chicas de verdad, pero el
# texto nunca baja de este piso, más conservador.
F_FUENTE: float = max(F, 0.85)


def px(v: int) -> int:
    """Escala un valor en píxeles (geometría de ventanas, canvas, paddings)."""
    return max(1, round(v * F))


def pt(v: int) -> int:
    """Escala un tamaño de fuente en puntos — con un piso más alto que px()
    (ver F_FUENTE) para que el texto se mantenga legible incluso en
    pantallas con resolución lógica chica (típico en Mac con Retina)."""
    return max(7, round(v * F_FUENTE))
