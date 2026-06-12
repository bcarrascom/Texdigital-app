"""
ui/estilos.py
Paleta de colores, fuentes y helpers de UI compartidos por las pantallas
del cotizador estándar y del cotizador backlight.
"""

import sys
import tkinter as tk

from core.rutas import RECURSOS as _RECURSOS
from core import escala as _esc

ASSETS = _RECURSOS / "assets"

COLORES = {
    "fondo":         "#E1E1E1",
    "acento":        "#1A3A5C",
    "acento_hover":  "#245480",
    "secundario":    "#E8A020",
    "texto":         "#1C1C1C",
    "texto_suave":   "#6B6B6B",
    "borde":         "#D8D4CC",
    "rect_relleno":  "#858585",
    "rect_borde":    "#FFFFFF",
    "error":         "#C0392B",
    "btn_disabled":  "#AAAAAA",
    "btn_enabled":   "#1A3A5C",
    "btn_en_hover":  "#245480",
    "nav_inactivo":  "#AAAAAA",
    "nav_activo":    "#1A3A5C",
    "nav_completo":  "#245480",
    "tabla_cab":     "#1A3A5C",
    "tabla_fila1":   "#F5F5F5",
    "tabla_fila2":   "#E8E8E8",
    "tabla_total":   "#D0D8E4",
    "hover_fila":    "#C8D4FF",
}

if sys.platform == "darwin":
    FUENTE_CABECERA  = ("Helvetica Neue", _esc.pt(22), "bold")
    FUENTE_SUBTITULO = ("Helvetica Neue", _esc.pt(14))
    FUENTE_TITULO    = ("Helvetica Neue", _esc.pt(23), "bold")
    FUENTE_LABEL     = ("Helvetica Neue", _esc.pt(13))
    FUENTE_MEDIDA    = ("Helvetica Neue", _esc.pt(14), "bold")
    FUENTE_AVISO     = ("Helvetica Neue", _esc.pt(13))
    FUENTE_BTN       = ("Helvetica Neue", _esc.pt(14), "bold")
    FUENTE_TABLA_CAB = ("Helvetica Neue", _esc.pt(13), "bold")
    FUENTE_TABLA     = ("Helvetica Neue", _esc.pt(13))
    FUENTE_TOTAL     = ("Helvetica Neue", _esc.pt(13), "bold")
    FUENTE_NAV       = ("Helvetica Neue", _esc.pt(12), "bold")
else:
    FUENTE_CABECERA  = ("Georgia", _esc.pt(17), "bold")
    FUENTE_SUBTITULO = ("Segoe UI", _esc.pt(11))
    FUENTE_TITULO    = ("Georgia", _esc.pt(18), "bold")
    FUENTE_LABEL     = ("Segoe UI", _esc.pt(10))
    FUENTE_MEDIDA    = ("Segoe UI", _esc.pt(11), "bold")
    FUENTE_AVISO     = ("Segoe UI", _esc.pt(10))
    FUENTE_BTN       = ("Segoe UI", _esc.pt(11), "bold")
    FUENTE_TABLA_CAB = ("Segoe UI", _esc.pt(10), "bold")
    FUENTE_TABLA     = ("Segoe UI", _esc.pt(10))
    FUENTE_TOTAL     = ("Segoe UI", _esc.pt(10), "bold")
    FUENTE_NAV       = ("Segoe UI", _esc.pt(9), "bold")

MAX_LADO = _esc.px(220)
MARGEN   = _esc.px(48)
CANVAS_W = MAX_LADO + MARGEN + _esc.px(30)
CANVAS_H = MAX_LADO + MARGEN + _esc.px(30)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers reutilizables
# ══════════════════════════════════════════════════════════════════════════════

def _construir_cabecera(ventana, on_volver):
    """Cabecera azul común para todas las ventanas principales."""
    cabecera = tk.Frame(ventana, bg=COLORES["acento"])
    cabecera.pack(fill="x")

    contenido = tk.Frame(cabecera, bg=COLORES["acento"], padx=24, pady=14)
    contenido.pack(fill="x")

    btn_v = tk.Label(contenido, text="← Volver",
                     font=FUENTE_LABEL, bg=COLORES["acento"],
                     fg="#FFFFFF", cursor="hand2")
    btn_v.pack(side="left", padx=(0, 20))
    btn_v.bind("<Button-1>", on_volver)
    btn_v.bind("<Enter>", lambda _: btn_v.config(fg=COLORES["secundario"]))
    btn_v.bind("<Leave>", lambda _: btn_v.config(fg="#FFFFFF"))

    logo_path = ASSETS / "logo.png"
    if logo_path.exists():
        try:
            from PIL import Image, ImageTk
            img = Image.open(logo_path).resize((34, 34))
            ventana._logo_img = ImageTk.PhotoImage(img)
            tk.Label(contenido, image=ventana._logo_img,
                     bg=COLORES["acento"]).pack(side="left", padx=(0, 10))
        except ImportError:
            pass

    tk.Label(contenido, text="Sistema de Gestión",
             font=FUENTE_CABECERA, bg=COLORES["acento"], fg="#FFFFFF").pack(side="left")


def _centrar(ventana, ancho, alto):
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth()  - ancho) // 2
    y = (ventana.winfo_screenheight() - alto)  // 2
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")


def _btn_label(parent, texto, habilitado=False):
    """Crea un Label que actúa como botón, devuelve el widget."""
    color = COLORES["btn_enabled"] if habilitado else COLORES["btn_disabled"]
    cursor = "hand2" if habilitado else "arrow"
    return tk.Label(parent, text=texto, font=FUENTE_BTN,
                    bg=color, fg="#FFFFFF", padx=20, pady=10, cursor=cursor)
