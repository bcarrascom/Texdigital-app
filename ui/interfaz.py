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

from core import escala as _esc

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

from core.rutas import RECURSOS as _RECURSOS, DOCS as _DOCS
ASSETS = _RECURSOS / "assets"


def _abrir_manual_usuario():
    """Abre el manual de usuario (docs/Manual_de_Uso.pdf) con el visor de
    PDF por defecto del SO — mismo mecanismo que "abrir carpeta" en
    ui/revisar_cotizaciones.py (Explorador/Finder/xdg-open también abren
    un archivo con su aplicación asociada, no solo carpetas)."""
    ruta = _DOCS / "Manual_de_Uso.pdf"
    if not ruta.exists():
        return
    ruta = str(ruta)
    if sys.platform == "win32":
        import os
        os.startfile(ruta)
    elif sys.platform == "darwin":
        import subprocess
        subprocess.run(["open", ruta])
    else:
        import subprocess
        subprocess.run(["xdg-open", ruta])

# Títulos (cabecera + títulos de botón) — misma tipografía en las tres
# plataformas, a diferencia del resto de las fuentes de acá abajo.
FUENTE_CABECERA  = ("DejaVu Sans", 17, "bold")
FUENTE_BTN       = ("DejaVu Sans", 13, "bold")

if sys.platform == "darwin":
    FUENTE_DESC      = ("Helvetica Neue", 10)
    FUENTE_FLECHA    = ("Helvetica Neue", 17)
    FUENTE_FECHA     = ("Helvetica Neue", 10)
    FUENTE_ICONO     = ("Apple Color Emoji", 26)
    FUENTE_PH_TITULO = ("Helvetica Neue", 13)
    FUENTE_PH_SUB    = ("Helvetica Neue", 10)
else:
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
        from ui.panel_produccion import salir_app
        self.protocol("WM_DELETE_WINDOW", lambda: salir_app())
        self._centrar_ventana(_esc.px(1080), _esc.px(820))
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

        from core.version import VERSION
        tk.Label(contenido_cab, text=f"v{VERSION}",
                 font=FUENTE_FECHA, bg=COLORES["acento"], fg="#8AAFC8").pack(side="right")

        # Botón "Actualizar" — abre ui/actualizador.py::VentanaActualizar.
        # Empacado DESPUÉS de la versión (mismo side="right") para quedar
        # justo a su izquierda; el botón "?" (más abajo) queda más a la
        # izquierda todavía.
        btn_actualizar = tk.Label(
            contenido_cab, text="⟳", font=FUENTE_BTN,
            bg=COLORES["acento"], fg="#FFFFFF", cursor="hand2",
            highlightthickness=1, highlightbackground="#FFFFFF", highlightcolor="#FFFFFF",
            padx=8, pady=4,
        )
        btn_actualizar.pack(side="right", padx=(0, 10))
        btn_actualizar.bind("<Button-1>", lambda _: self._abrir_actualizador())
        btn_actualizar.bind("<Enter>", lambda _: btn_actualizar.config(bg=COLORES["acento_hover"]))
        btn_actualizar.bind("<Leave>", lambda _: btn_actualizar.config(bg=COLORES["acento"]))

        # Botón "?" — abre el manual de usuario (ver _abrir_manual_usuario).
        # Empacado DESPUÉS de la versión (mismo side="right") para quedar
        # justo a su izquierda.
        btn_ayuda = tk.Label(
            contenido_cab, text="?", font=FUENTE_BTN,
            bg=COLORES["acento"], fg="#FFFFFF",
            width=2, height=1, cursor="hand2",
            highlightthickness=1, highlightbackground="#FFFFFF", highlightcolor="#FFFFFF",
        )
        btn_ayuda.pack(side="right", padx=(0, 10))
        btn_ayuda.bind("<Button-1>", lambda _: _abrir_manual_usuario())
        btn_ayuda.bind("<Enter>", lambda _: btn_ayuda.config(bg=COLORES["acento_hover"]))
        btn_ayuda.bind("<Leave>", lambda _: btn_ayuda.config(bg=COLORES["acento"]))

        # ── 4 columnas ────────────────────────────────────────────────────────
        grid = tk.Frame(self, bg=COLORES["fondo"])
        grid.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # Las 4 columnas tienen el mismo peso
        for i in range(4):
            grid.columnconfigure(i, weight=1, uniform="col")
        # Fila 0 (pendientes + fecha) no se estira — su alto es fijo (ver
        # _ALTO_FILA_PENDIENTES más abajo), las otras dos sí.
        grid.rowconfigure(1, weight=3)
        grid.rowconfigure(2, weight=1)

        # ── Fila 0: botón "Cotizaciones incompletas" (si hay alguna
        # pendiente) + fecha. El espacio vertical arriba/abajo de esta fila
        # (pady) es el mismo que el que separa la fila de botones grandes
        # de la fila de "Revisar Cotizaciones"/"Historial OPs" (10px, ver
        # pady=(10,0) más abajo) — mismo ritmo vertical en las tres filas.
        _ALTO_FILA_PENDIENTES = 80  # 2 líneas de FUENTE_BTN (13pt bold) + margen
        fila_pendientes = tk.Frame(grid, bg=COLORES["fondo"], height=_ALTO_FILA_PENDIENTES)
        fila_pendientes.grid(row=0, column=0, columnspan=4, sticky="nsew", pady=(10, 10))
        fila_pendientes.grid_propagate(False)

        from core.repositorio_pendientes import listar_pendientes
        if listar_pendientes():
            # relx/relwidth como fracción del ANCHO TOTAL de las 4 columnas
            # (fila_pendientes ocupa las 4, columnspan=4): la columna 0 va
            # de 0 a 0.25 (medio = 0.125), la columna 1 de 0.25 a 0.5 (medio
            # = 0.375) — el botón arranca en 0.125 y mide 0.25 (0.375-0.125),
            # o sea de la mitad de la columna 0 a la mitad de la columna 1.
            btn_pendientes = tk.Frame(fila_pendientes, bg=COLORES["acento"], cursor="hand2")
            btn_pendientes.place(relx=0.125, rely=0, relwidth=0.25, relheight=1.0)

            # Dos líneas, no una — el ancho del botón está fijo (exactamente
            # una columna, ver relwidth arriba) y en una sola línea el
            # texto no entra en pantallas más chicas/escaladas (ver
            # core/escala.py: las fuentes de este archivo no se escalan
            # con la ventana, así que a bajo factor de escala el texto se
            # sale del botón).
            lbl_pendientes = tk.Label(btn_pendientes, text="Cotizaciones\nincompletas",
                                      font=("DejaVu Sans", 10, "bold"), bg=COLORES["acento"], fg="#FFFFFF",
                                      justify="center")
            lbl_pendientes.pack(expand=True)

            def _pend_enter(_):
                btn_pendientes.config(bg=COLORES["acento_hover"])
                lbl_pendientes.config(bg=COLORES["acento_hover"])

            def _pend_leave(_):
                btn_pendientes.config(bg=COLORES["acento"])
                lbl_pendientes.config(bg=COLORES["acento"])

            for w in (btn_pendientes, lbl_pendientes):
                w.bind("<Enter>",    _pend_enter)
                w.bind("<Leave>",    _pend_leave)
                w.bind("<Button-1>", lambda _: self._abrir_pendientes())

        tk.Label(fila_pendientes, text=fecha_actual, font=FUENTE_FECHA,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]
                 ).place(relx=0.5, rely=0.5, anchor="center")

        # ── Columna 0: Cotizador Backlight ──
        col0 = tk.Frame(grid, bg=COLORES["fondo"])
        col0.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

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
        col1.grid(row=1, column=1, sticky="nsew", padx=(6, 12))

        BotonPrincipal(
            col1,
            icono="📋",
            titulo="Ingresar\nCotización",
            descripcion="Crea y registra una\nnueva cotización.",
            color_base=COLORES["acento"],
            color_hover=COLORES["acento_hover"],
            comando=self._abrir_cotizacion,
        ).pack(fill="both", expand=True)

        # ── Columna 2: Revisar OPs ──
        col2 = tk.Frame(grid, bg=COLORES["fondo"])
        col2.grid(row=1, column=2, sticky="nsew", padx=(0, 0))

        BotonPrincipal(
            col2,
            icono="🏭",
            titulo="Revisar\nOPs",
            descripcion="Lista las órdenes\nde producción activas.",
            color_base=COLORES["acento"],
            color_hover=COLORES["acento_hover"],
            comando=self._abrir_revisar_ops,
        ).pack(fill="both", expand=True)

        # ── Columna 3: placeholder ──
        ColumnaPlaceholder(
            grid,
            titulo="Próximamente",
            subtitulo="Esta sección\nestá por definir.",
        ).grid(row=1, column=3, sticky="nsew")

        # ── Fila 2: botón Revisar Cotizaciones (ancho = col0+col1, alto = 1/3 de fila 1) ──
        btn_revisar = tk.Frame(grid, bg=COLORES["acento"], cursor="hand2")
        btn_revisar.grid(row=2, column=0, columnspan=2,
                         sticky="nsew", padx=(0, 12), pady=(10, 0))

        lbl_revisar = tk.Label(btn_revisar, text="Revisar Cotizaciones",
                               font=FUENTE_BTN, bg=COLORES["acento"],
                               fg="#FFFFFF")
        lbl_revisar.pack(expand=True)

        def _revisar_enter(_):
            btn_revisar.config(bg=COLORES["acento_hover"])
            lbl_revisar.config(bg=COLORES["acento_hover"])

        def _revisar_leave(_):
            btn_revisar.config(bg=COLORES["acento"])
            lbl_revisar.config(bg=COLORES["acento"])

        for w in (btn_revisar, lbl_revisar):
            w.bind("<Enter>",    _revisar_enter)
            w.bind("<Leave>",    _revisar_leave)
            w.bind("<Button-1>", lambda _: self._abrir_revisar_cotizaciones())

        # ── Fila 2, columna 2: botón Historial OPs (mismo ancho que
        # "Revisar OPs" arriba — misma columna del grid — y mismo alto que
        # "Revisar Cotizaciones" a su izquierda — misma fila del grid) ──
        btn_historial = tk.Frame(grid, bg=COLORES["acento"], cursor="hand2")
        btn_historial.grid(row=2, column=2, sticky="nsew", pady=(10, 0))

        lbl_historial = tk.Label(btn_historial, text="Historial OPs",
                                 font=FUENTE_BTN, bg=COLORES["acento"],
                                 fg="#FFFFFF")
        lbl_historial.pack(expand=True)

        def _historial_enter(_):
            btn_historial.config(bg=COLORES["acento_hover"])
            lbl_historial.config(bg=COLORES["acento_hover"])

        def _historial_leave(_):
            btn_historial.config(bg=COLORES["acento"])
            lbl_historial.config(bg=COLORES["acento"])

        for w in (btn_historial, lbl_historial):
            w.bind("<Enter>",    _historial_enter)
            w.bind("<Leave>",    _historial_leave)
            w.bind("<Button-1>", lambda _: self._abrir_historial_ops())

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _abrir_cotizador_backlight(self):
        from ui.cotizador_backlight import CotizadorBacklight
        self.destroy()
        CotizadorBacklight().mainloop()

    def _abrir_cotizacion(self):
        from ui.cotizacion import CotizacionNueva
        self.destroy()
        CotizacionNueva().mainloop()

    def _abrir_actualizador(self):
        from ui.actualizador import VentanaActualizar
        VentanaActualizar(self)

    def _abrir_revisar_cotizaciones(self):
        from ui.revisar_cotizaciones import VentanaCotizaciones
        VentanaCotizaciones(self)

    def _abrir_pendientes(self):
        from ui.pendientes_cotizaciones import VentanaPendientes
        VentanaPendientes(self)

    def _abrir_historial_ops(self):
        from ui.historial_ops import VentanaHistorialOps
        VentanaHistorialOps(self)

    def _abrir_revisar_ops(self):
        import sys
        if sys.platform == "darwin":
            from ui.panel_produccion import mostrar_panel_mac
            mostrar_panel_mac()
        else:
            from ui.panel_produccion import mostrar_panel
            mostrar_panel()

    def _centrar_ventana(self, ancho, alto):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - ancho) // 2
        y = (self.winfo_screenheight() - alto)  // 2
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
