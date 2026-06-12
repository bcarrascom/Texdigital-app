"""
ui/interfaz.py
Ventana principal de la aplicación.
"""

import sys
import tkinter as tk
from pathlib import Path
from datetime import datetime

# ── Fix DPI para Windows ───────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

fecha_actual = datetime.now().strftime("%Y/%m/%d")

COLORES = {
    "fondo":            "#F5F3EE",
    "panel":            "#FFFFFF",
    "acento":           "#1A3A5C",
    "acento_hover":     "#245480",
    "secundario":       "#E8A020",
    "secundario_hover": "#C8881A",
    "texto":            "#1C1C1C",
    "texto_suave":      "#6B6B6B",
    "borde":            "#D8D4CC",
    "placeholder_bg":   "#ECEAE5",
    "placeholder_txt":  "#BBBBBB",
}

from core.rutas import RECURSOS as _RECURSOS
ASSETS = _RECURSOS / "assets"

if sys.platform == "darwin":
    FUENTE_CABECERA  = ("Helvetica Neue", 17, "bold")
    FUENTE_BTN       = ("Helvetica Neue", 13, "bold")
    FUENTE_DESC      = ("Helvetica Neue", 10)
    FUENTE_FLECHA    = ("Helvetica Neue", 17)
    FUENTE_FECHA     = ("Helvetica Neue", 10)
    FUENTE_ICONO     = ("Apple Color Emoji", 26)
    FUENTE_PH_TITULO = ("Helvetica Neue", 13)
    FUENTE_PH_SUB    = ("Helvetica Neue", 10)
else:
    FUENTE_CABECERA  = ("Georgia", 17, "bold")
    FUENTE_BTN       = ("Georgia", 13, "bold")
    FUENTE_DESC      = ("Segoe UI", 9)
    FUENTE_FLECHA    = ("Segoe UI", 17)
    FUENTE_FECHA     = ("Segoe UI", 10)
    FUENTE_ICONO     = ("Segoe UI Emoji", 26)
    FUENTE_PH_TITULO = ("Segoe UI", 13)
    FUENTE_PH_SUB    = ("Segoe UI", 9)


# ── Botón azul ─────────────────────────────────────────────────────────────────
class BotonPrincipal(tk.Frame):

    def __init__(self, parent, icono, titulo, descripcion,
                 color_base, color_hover, comando=None, **kwargs):
        super().__init__(parent, bg=COLORES["fondo"], **kwargs)

        self._color_base  = color_base
        self._color_hover = color_hover
        self._comando     = comando

        self._inner = tk.Frame(self, bg=color_base, cursor="hand2", padx=20, pady=18)
        self._inner.pack(fill="both", expand=True)

        lbl_icono = tk.Label(self._inner, text=icono, font=FUENTE_ICONO,
                             bg=color_base, fg="#FFFFFF")
        lbl_icono.pack(anchor="w")

        lbl_titulo = tk.Label(self._inner, text=titulo, font=FUENTE_BTN,
                              bg=color_base, fg="#FFFFFF", justify="left")
        lbl_titulo.pack(anchor="w", pady=(6, 2))

        lbl_desc = tk.Label(self._inner, text=descripcion, font=FUENTE_DESC,
                            bg=color_base, fg="#C8D8E8", justify="left", wraplength=160)
        lbl_desc.pack(anchor="w")

        lbl_flecha = tk.Label(self._inner, text="→", font=FUENTE_FLECHA,
                              bg=color_base, fg="#8AAFC8")
        lbl_flecha.pack(anchor="e", pady=(10, 0))

        for w in [self._inner, lbl_icono, lbl_titulo, lbl_desc, lbl_flecha]:
            w.bind("<Enter>",    self._on_enter)
            w.bind("<Leave>",    self._on_leave)
            w.bind("<Button-1>", self._on_click)

    def _cambiar_color(self, color):
        self._inner.config(bg=color)
        for child in self._inner.winfo_children():
            try:
                child.config(bg=color)
            except tk.TclError:
                pass

    def _on_enter(self, _): self._cambiar_color(self._color_hover)
    def _on_leave(self, _): self._cambiar_color(self._color_base)
    def _on_click(self, _):
        if self._comando:
            self._comando()


# ── Columna placeholder ────────────────────────────────────────────────────────
class ColumnaPlaceholder(tk.Frame):

    def __init__(self, parent, titulo, subtitulo, **kwargs):
        super().__init__(parent, bg=COLORES["placeholder_bg"], **kwargs)

        # Borde izquierdo sutil
        tk.Frame(self, bg=COLORES["borde"], width=1).pack(side="left", fill="y")

        contenido = tk.Frame(self, bg=COLORES["placeholder_bg"])
        contenido.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(contenido, text=titulo, font=FUENTE_PH_TITULO,
                 bg=COLORES["placeholder_bg"], fg=COLORES["placeholder_txt"],
                 justify="left").pack(anchor="w")

        tk.Label(contenido, text=subtitulo, font=FUENTE_PH_SUB,
                 bg=COLORES["placeholder_bg"], fg=COLORES["placeholder_txt"],
                 justify="left", wraplength=160).pack(anchor="w", pady=(4, 0))


# ── Ventana principal ──────────────────────────────────────────────────────────
class VentanaPrincipal(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Sistema de Gestión")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
        self._centrar_ventana(1080, 640)
        self._construir_ui()

    def _construir_ui(self):
        # ── Cabecera ──
        cabecera = tk.Frame(self, bg=COLORES["acento"])
        cabecera.pack(fill="x")
        tk.Frame(cabecera, bg=COLORES["secundario"], height=3).pack(fill="x")

        contenido_cab = tk.Frame(cabecera, bg=COLORES["acento"], padx=24, pady=14)
        contenido_cab.pack(fill="x")

        logo_path = ASSETS / "logo.png"
        if logo_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(logo_path).resize((34, 34))
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(contenido_cab, image=self._logo_img,
                         bg=COLORES["acento"]).pack(side="left", padx=(0, 10))
            except ImportError:
                pass

        tk.Label(contenido_cab, text="Sistema de Gestión",
                 font=FUENTE_CABECERA, bg=COLORES["acento"], fg="#FFFFFF").pack(side="left")

        # ── Fecha ──
        tk.Label(self, text=fecha_actual, font=FUENTE_FECHA,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(pady=(20, 10))

        # ── 4 columnas ────────────────────────────────────────────────────────
        grid = tk.Frame(self, bg=COLORES["fondo"])
        grid.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # Las 4 columnas tienen el mismo peso
        for i in range(4):
            grid.columnconfigure(i, weight=1, uniform="col")
        grid.rowconfigure(0, weight=1)

        # ── Columna 0: Cotizador Backlight ──
        col0 = tk.Frame(grid, bg=COLORES["fondo"])
        col0.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        BotonPrincipal(
            col0,
            icono="🔳",
            titulo="Cotizador\nBacklight",
            descripcion="Calcula medidas y\ncostos con backlight.",
            color_base=COLORES["acento"],
            color_hover=COLORES["acento_hover"],
            comando=self._abrir_cotizador_backlight,
        ).pack(fill="both", expand=True)

        # ── Columna 1: segundo botón azul ──
        col1 = tk.Frame(grid, bg=COLORES["fondo"])
        col1.grid(row=0, column=1, sticky="nsew", padx=(6, 12))

        BotonPrincipal(
            col1,
            icono="📋",
            titulo="Ingresar\nCotización",
            descripcion="Crea y registra una\nnueva cotización.",
            color_base=COLORES["acento"],
            color_hover=COLORES["acento_hover"],
            comando=self._abrir_cotizacion,
        ).pack(fill="both", expand=True)

        # ── Columna 2: placeholder ──
        ColumnaPlaceholder(
            grid,
            titulo="Próximamente",
            subtitulo="Esta sección\nestá por definir.",
        ).grid(row=0, column=2, sticky="nsew", padx=(0, 0))

        # ── Columna 3: placeholder ──
        ColumnaPlaceholder(
            grid,
            titulo="Próximamente",
            subtitulo="Esta sección\nestá por definir.",
        ).grid(row=0, column=3, sticky="nsew")

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _abrir_cotizador_backlight(self):
        from ui.cotizador_backlight import CotizadorBacklight
        self.destroy()
        CotizadorBacklight().mainloop()

    def _abrir_cotizacion(self):
        from ui.cotizacion import CotizacionNueva
        self.destroy()
        CotizacionNueva().mainloop()

    def _centrar_ventana(self, ancho, alto):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - ancho) // 2
        y = (self.winfo_screenheight() - alto)  // 2
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
