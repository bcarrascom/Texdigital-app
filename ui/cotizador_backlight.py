"""
ui/cotizador_backlight.py
Ventana principal del Cotizador Backlight.
Flujo: pantalla-cantidad → iteraciones de medidas → ventana-resumen separada.
"""

import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

if sys.platform == "win32":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

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

from core.rutas import RECURSOS as _RECURSOS
from core import escala as _esc
ASSETS = _RECURSOS / "assets"

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

TELAS = [
    ("Popelina 155",  1.53),
    ("Popelina 310",  3.08),
    ("Pearl 155",     1.53),
    ("Pearl 310",     3.08),
    ("Pearl 160 HP",  1.60),
]

# Editar esta lista para agregar/quitar opciones de cajas y perfiles
LISTA_CAJAS = [
    "PERFIL 60 MM",
    "PERFIL 80 MM",
    "PERFIL 100 MM SIMPLE",
    "PERFIL 100 MM DOBLE",
    "PERFIL 120 MM DOBLE"
]

MAX_LADO = _esc.px(220)
MARGEN   = _esc.px(48)
CANVAS_W = MAX_LADO + MARGEN + _esc.px(30)
CANVAS_H = MAX_LADO + MARGEN + _esc.px(30)

# Ancho de columnas del resumen — ajustar aquí si la tabla queda angosta/ancha
# Orden: #, Textil, Tema, Cantidad, Alto, Ancho, Área
RESUMEN_COL_W = [_esc.px(v) for v in [35, 130, 130, 90, 90, 90, 100]]


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


# ══════════════════════════════════════════════════════════════════════════════
# Ventana principal — gestiona el flujo completo
# ══════════════════════════════════════════════════════════════════════════════

class CotizadorBacklight(tk.Tk):

    if sys.platform == "darwin":
        TAM_CANTIDAD = (_esc.px(800), _esc.px(730))
        TAM_MEDIDAS  = (_esc.px(1100), _esc.px(1250))
    else:
        TAM_CANTIDAD = (_esc.px(800), _esc.px(560))
        TAM_MEDIDAS  = (_esc.px(960), _esc.px(960))

    def __init__(self):
        super().__init__()
        self.title("Cotizador Backlight")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        _centrar(self, *self.TAM_CANTIDAD)

        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

        self._total_productos  = 0
        self._iteracion_actual = 0
        self._desde_resumen    = False
        self._datos: list[dict] = []
        self._tela_defecto   = TELAS[0][0]
        self._nombre_trabajo = ""

        _construir_cabecera(self, self._volver)

        self._area = tk.Frame(self, bg=COLORES["fondo"])
        self._area.pack(fill="both", expand=True)

        self._mostrar_pantalla_cantidad()

    # ── Navegación entre pantallas ─────────────────────────────────────────────
    def _limpiar(self):
        for w in self._area.winfo_children():
            w.destroy()
        # Limpiar bindings de Enter que pudiera haber dejado la pantalla anterior
        self.unbind("<Return>")

    def _mostrar_pantalla_cantidad(self):
        self._limpiar()
        _centrar(self, *self.TAM_CANTIDAD)
        PantallaCantidad(self._area, on_confirmar=self._on_cantidad_confirmada)

    def _on_cantidad_confirmada(self, y: int, nombre: str):
        self._total_productos  = y
        self._nombre_trabajo   = nombre
        self._datos            = [None] * y
        self._iteracion_actual = 0
        self._mostrar_medidas()

    def _mostrar_medidas(self, desde_resumen=False):
        self._desde_resumen = desde_resumen
        self._limpiar()
        _centrar(self, *self.TAM_MEDIDAS)
        PantallaMedidas(
            self._area,
            ventana_raiz=self,
            indice=self._iteracion_actual,
            total=self._total_productos,
            datos_previos=self._datos[self._iteracion_actual],
            datos_todos=self._datos,
            tela_defecto=self._tela_defecto,
            on_siguiente=self._on_medidas_confirmadas,
            on_nav=self._on_nav,
        )

    def _on_medidas_confirmadas(self, datos: dict):
        self._datos[self._iteracion_actual] = datos
        if self._iteracion_actual == 0:
            self._tela_defecto = datos["tela"]

        if self._desde_resumen:
            self._abrir_resumen()
            return

        sig = self._iteracion_actual + 1
        if sig < self._total_productos:
            self._iteracion_actual = sig
            self._mostrar_medidas()
        else:
            self._abrir_resumen()

    def _on_nav(self, indice: int):
        if self._datos[indice] is not None or indice == self._iteracion_actual:
            self._iteracion_actual = indice
            self._mostrar_medidas(desde_resumen=self._desde_resumen)

    def _abrir_resumen(self):
        from ui.ventana_resumen import VentanaResumen

        COLS = ["#", "Textil", "Tema", "Cantidad", "Ancho (m)", "Alto (m)", "ML imp."]

        filas      = []
        total_cant = 0
        total_ml   = 0.0

        for i, d in enumerate(self._datos):
            uxa   = d["ancho_max"] / d["ancho"]
            ratio = d["cantidad"]  / uxa
            ml    = d["alto"] * d["cantidad"] * ratio
            total_cant += d["cantidad"]
            total_ml   += ml
            filas.append([
                str(i + 1),
                d["tela"],
                d.get("tema", ""),
                str(d["cantidad"]),
                str(d["ancho"]),
                str(d["alto"]),
                f"{ml:.4f}",
            ])

        total_ml = round(total_ml, 4)
        totales  = ["", "TOTAL", "", str(total_cant), "", "", f"{total_ml:.4f}"]

        self.withdraw()
        VentanaResumen(
            ancho_ventana=_esc.px(1600),
            columnas=COLS,
            col_w=RESUMEN_COL_W,
            filas=filas,
            totales=totales,
            titulo="Resumen — Cotizador Backlight",
            subtitulo="Cotizador Backlight",
            nombre_trabajo=self._nombre_trabajo,
            on_editar=self._on_editar_desde_resumen,
            on_confirmar=self._on_confirmar_resumen,
            on_cerrar=self._on_cerrar_resumen,
        )

    def _on_editar_desde_resumen(self, indice: int):
        # La ventana resumen se destruye sola antes de llamar esto
        self.deiconify()
        self.lift()
        self.focus_force()
        self._iteracion_actual = indice
        self._mostrar_medidas(desde_resumen=True)

    def _on_confirmar_resumen(self):
        # Abre el formulario de cliente
        from ui.formulario_cliente import FormularioCliente
        FormularioCliente(
            self,
            datos_productos=self._datos,
            nombre_trabajo=self._nombre_trabajo,
            on_cerrar=None,
        )

    def _on_cerrar_resumen(self):
        # El usuario cerró el resumen sin confirmar → volver a medidas
        self.deiconify()
        self.lift()
        self.focus_force()
        self._mostrar_medidas(desde_resumen=True)

    def _volver(self, _=None):
        from ui.interfaz import VentanaPrincipal
        self.destroy()
        VentanaPrincipal().mainloop()


# ══════════════════════════════════════════════════════════════════════════════
# Pantalla de cantidad (reemplaza al popup)
# ══════════════════════════════════════════════════════════════════════════════

class PantallaCantidad(tk.Frame):

    def __init__(self, parent, on_confirmar):
        super().__init__(parent, bg=COLORES["fondo"])
        self.pack(fill="both", expand=True)
        self._on_confirmar   = on_confirmar
        self._btn_habilitado = False
        self._var_y      = tk.StringVar()
        self._var_nombre = tk.StringVar()
        self._var_y.trace_add("write",      self._actualizar_btn)
        self._var_nombre.trace_add("write", self._actualizar_btn)
        self._construir_ui()

    def _construir_ui(self):
        spacer_top = tk.Frame(self, bg=COLORES["fondo"])
        spacer_top.pack(fill="both", expand=True)

        cuerpo = tk.Frame(self, bg=COLORES["fondo"], padx=80)
        cuerpo.pack(fill="x")

        tk.Label(cuerpo, text="Cotizador Backlight",
                 font=FUENTE_SUBTITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Label(cuerpo, text="Nuevo trabajo",
                 font=FUENTE_TITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto"], justify="left").pack(anchor="w", pady=(6, 16))

        # Campo: Nombre del trabajo
        tk.Label(cuerpo, text="Nombre del trabajo",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Entry(cuerpo, textvariable=self._var_nombre,
                 font=FUENTE_MEDIDA, width=30,
                 relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                 insertbackground=COLORES["texto"],
                 highlightthickness=1, highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"],
                 ).pack(anchor="w", ipady=8, ipadx=8)

        tk.Frame(cuerpo, bg=COLORES["fondo"], height=14).pack()

        # Campo: Cantidad de productos
        tk.Label(cuerpo, text="Cantidad de productos",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        vcmd = (self.register(self._validar), "%P")
        self._entry = tk.Entry(cuerpo, textvariable=self._var_y,
                               validate="key", validatecommand=vcmd,
                               font=FUENTE_MEDIDA, width=8,
                               relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                               insertbackground=COLORES["texto"],
                               highlightthickness=1, highlightbackground=COLORES["borde"],
                               highlightcolor=COLORES["acento"])
        self._entry.pack(anchor="w", ipady=8, ipadx=8)

        self._btn = _btn_label(cuerpo, "Comenzar →")
        self._btn.pack(anchor="e", pady=(20, 0))

        tk.Frame(self, bg=COLORES["fondo"]).pack(fill="both", expand=True)

        self.winfo_toplevel().bind("<Return>", lambda _: self._confirmar())

    def _validar(self, valor):
        return valor == "" or valor.isdigit()

    def _actualizar_btn(self, *_):
        try:
            ok = int(self._var_y.get()) >= 1 and self._var_nombre.get().strip() != ""
        except ValueError:
            ok = False
        self._btn_habilitado = ok
        if ok:
            self._btn.config(bg=COLORES["btn_enabled"], cursor="hand2")
            self._btn.bind("<Button-1>", lambda _: self._confirmar())
            self._btn.bind("<Enter>",
                lambda _: self._btn.config(bg=COLORES["btn_en_hover"]))
            self._btn.bind("<Leave>",
                lambda _: self._btn.config(bg=COLORES["btn_enabled"]))
        else:
            self._btn.config(bg=COLORES["btn_disabled"], cursor="arrow")
            self._btn.unbind("<Button-1>")
            self._btn.unbind("<Enter>")
            self._btn.unbind("<Leave>")

    def _confirmar(self):
        try:
            v      = int(self._var_y.get())
            nombre = self._var_nombre.get().strip()
            if v >= 1 and nombre:
                self.winfo_toplevel().unbind("<Return>")
                self._on_confirmar(v, nombre)
        except ValueError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# Pantalla de medidas
# ══════════════════════════════════════════════════════════════════════════════

class PantallaMedidas(tk.Frame):

    def __init__(self, parent, ventana_raiz, indice, total,
                 datos_previos, datos_todos, tela_defecto,
                 on_siguiente, on_nav):
        super().__init__(parent, bg=COLORES["fondo"])
        self.pack(fill="both", expand=True)

        self._ventana_raiz    = ventana_raiz
        self._indice          = indice
        self._total           = total
        self._datos_todos     = datos_todos
        self._on_siguiente    = on_siguiente
        self._on_nav          = on_nav
        self._rotado          = False
        self._btn_habilitado  = False
        self._omitir_activo   = False

        if datos_previos:
            tela_ini  = datos_previos["tela"]
            caja_ini  = datos_previos.get("caja", "Sin caja")
            alto_ini  = str(datos_previos["alto"])
            ancho_ini = str(datos_previos["ancho"])
            cant_ini  = str(datos_previos["cantidad"])
            tema_ini  = datos_previos.get("tema", "")
        else:
            tela_ini  = tela_defecto
            caja_ini  = "Sin caja"
            alto_ini  = ancho_ini = cant_ini = tema_ini = ""

        self._var_tela  = tk.StringVar(value=tela_ini)
        self._var_caja  = tk.StringVar(value=caja_ini)
        self._var_alto  = tk.StringVar(value=alto_ini)
        self._var_ancho = tk.StringVar(value=ancho_ini)
        self._var_cant  = tk.StringVar(value=cant_ini)
        self._var_tema  = tk.StringVar(value=tema_ini)

        self._construir_ui()

        self._var_tela.trace_add("write",  self._actualizar)
        self._var_alto.trace_add("write",  self._actualizar)
        self._var_ancho.trace_add("write", self._actualizar)
        self._var_cant.trace_add("write",  self._actualizar)
        self._var_tema.trace_add("write",  self._actualizar)

        self._actualizar()
        ventana_raiz.bind("<Return>", lambda _: self._enter_sig())

    def _enter_sig(self):
        if self._btn_habilitado:
            self._siguiente()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _construir_ui(self):
        # ── Barra de navegación ───────────────────────────────────────────────
        nav = tk.Frame(self, bg=COLORES["fondo"], pady=12)
        nav.pack(fill="x", padx=40)
        tk.Label(nav, text="Producto", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(side="left", padx=(0, 10))
        self._nav_cuadros = []
        for i in range(self._total):
            c = tk.Label(nav, text=str(i+1), font=FUENTE_NAV,
                         width=3, pady=4, relief="flat", cursor="hand2")
            c.pack(side="left", padx=3)
            c.bind("<Button-1>", lambda _, idx=i: self._on_nav(idx))
            self._nav_cuadros.append(c)
        self._actualizar_nav()

        tk.Frame(self, bg=COLORES["borde"], height=1).pack(fill="x", padx=30)

        # ── Sección superior: tela ────────────────────────────────────────────
        sup = tk.Frame(self, bg=COLORES["fondo"], padx=40, pady=18)
        sup.pack(fill="x")

        tk.Label(sup,
                 text=f"Cotizador Backlight  ·  Producto {self._indice+1} de {self._total}",
                 font=FUENTE_SUBTITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Label(sup, text="Selección de Tela", font=FUENTE_TITULO,
                 bg=COLORES["fondo"], fg=COLORES["texto"]).pack(anchor="w", pady=(4, 10))
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.TCombobox",
                        fieldbackground="#FFFFFF", background="#FFFFFF",
                        foreground=COLORES["texto"], arrowcolor=COLORES["acento"],
                        bordercolor=COLORES["borde"], relief="flat")

        fila_seleccion = tk.Frame(sup, bg=COLORES["fondo"])
        fila_seleccion.pack(anchor="w")

        grp_tela = tk.Frame(fila_seleccion, bg=COLORES["fondo"])
        grp_tela.pack(side="left")
        tk.Label(grp_tela, text="Tela", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._combo = ttk.Combobox(grp_tela, textvariable=self._var_tela,
                                   values=[n for n, _ in TELAS],
                                   state="readonly", style="Custom.TCombobox",
                                   width=24, font=FUENTE_MEDIDA)
        self._combo.pack(anchor="w", ipady=4)

        grp_caja = tk.Frame(fila_seleccion, bg=COLORES["fondo"])
        grp_caja.pack(side="left", padx=(16, 0))
        tk.Label(grp_caja, text="Caja / Perfil", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._combo_caja = ttk.Combobox(grp_caja, textvariable=self._var_caja,
                                        values=LISTA_CAJAS,
                                        state="readonly", style="Custom.TCombobox",
                                        width=30, font=FUENTE_MEDIDA)
        self._combo_caja.pack(anchor="w", ipady=4)

        self._lbl_ancho_tela = tk.Label(sup, text="", font=FUENTE_AVISO,
                                        bg=COLORES["fondo"], fg=COLORES["texto_suave"])
        self._lbl_ancho_tela.pack(anchor="w", pady=(6, 0))

        # ── Sección inferior: inputs + canvas ─────────────────────────────────
        inf = tk.Frame(self, bg=COLORES["fondo"], padx=40, pady=18)
        inf.pack(fill="both", expand=True)

        tk.Label(inf, text="Medidas", font=FUENTE_TITULO,
                 bg=COLORES["fondo"], fg=COLORES["texto"]).pack(
                     anchor="w", pady=(0, 12))

        # Inputs a la izquierda
        col_izq = tk.Frame(inf, bg=COLORES["fondo"])
        col_izq.pack(side="left", anchor="n")

        fila_inp = tk.Frame(col_izq, bg=COLORES["fondo"])
        fila_inp.pack(anchor="w")
        self._crear_input(fila_inp, "Ancho (m)", self._var_ancho).pack(side="left", padx=(0, 16))
        self._crear_input(fila_inp, "Alto (m)",  self._var_alto).pack(side="left", padx=(0, 16))
        self._crear_input(fila_inp, "Cantidad",  self._var_cant).pack(side="left")

        # Input Tema
        fila_tema = tk.Frame(col_izq, bg=COLORES["fondo"])
        fila_tema.pack(anchor="w", pady=(14, 0))
        tk.Label(fila_tema, text="Tema", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Entry(fila_tema, textvariable=self._var_tema,
                 font=FUENTE_MEDIDA, width=28,
                 relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                 insertbackground=COLORES["texto"], highlightthickness=1,
                 highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"]).pack(anchor="w", ipady=6, ipadx=6)

        self._lbl_rotacion = tk.Label(col_izq, text="", font=FUENTE_AVISO,
                                      bg=COLORES["fondo"], fg=COLORES["texto_suave"])
        self._lbl_rotacion.pack(anchor="w", pady=(10, 0))

        self._lbl_error = tk.Label(col_izq, text="", font=FUENTE_AVISO,
                                   bg=COLORES["fondo"], fg=COLORES["error"],
                                   wraplength=500, justify="left")
        self._lbl_error.pack(anchor="w", pady=(4, 0))

        self._btn_omitir = tk.Label(
            col_izq, text="Omitir restricción ⚠",
            font=FUENTE_BTN, bg=COLORES["secundario"],
            fg="#FFFFFF", padx=16, pady=8, cursor="hand2",
        )
        self._btn_omitir.bind("<Button-1>", lambda _: self._omitir_restriccion())
        self._btn_omitir.bind("<Enter>", lambda _: self._btn_omitir.config(bg="#C8881A"))
        self._btn_omitir.bind("<Leave>", lambda _: self._btn_omitir.config(bg=COLORES["secundario"]))
        # No se empaqueta hasta que haya error

        # Canvas centrado verticalmente a la derecha
        self._canvas = tk.Canvas(inf, width=CANVAS_W, height=CANVAS_H,
                                 bg=COLORES["fondo"], highlightthickness=0)
        self._canvas.place(relx=1.0, rely=0.5, anchor="e")

        # Botón siguiente
        es_ultimo = (self._indice == self._total - 1)
        self._btn_sig = _btn_label(
            self._ventana_raiz,
            "Confirmar ✓" if es_ultimo else "Siguiente →"
        )
        self._btn_sig.place(relx=1.0, rely=1.0, anchor="se", x=-30, y=-20)

    def _crear_input(self, parent, etiqueta, variable):
        c = tk.Frame(parent, bg=COLORES["fondo"])
        tk.Label(c, text=etiqueta, font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        vcmd = (self.register(self._validar_numero), "%P")
        tk.Entry(c, textvariable=variable, validate="key", validatecommand=vcmd,
                 font=FUENTE_MEDIDA, width=8, relief="flat", bd=0,
                 bg="#FFFFFF", fg=COLORES["texto"], insertbackground=COLORES["texto"],
                 highlightthickness=1, highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"]).pack(ipady=6, ipadx=6)
        return c

    def _actualizar_nav(self):
        for i, c in enumerate(self._nav_cuadros):
            if i == self._indice:
                c.config(bg=COLORES["nav_activo"],   fg="#FFFFFF")
            elif self._datos_todos[i] is not None:
                c.config(bg=COLORES["nav_completo"], fg="#FFFFFF")
            else:
                c.config(bg=COLORES["nav_inactivo"], fg="#FFFFFF")

    # ── Validación ─────────────────────────────────────────────────────────────
    def _validar_numero(self, valor):
        if valor == "":
            return True
        v2 = valor.replace(",", ".")
        try:
            float(v2); return True
        except ValueError:
            return v2.endswith(".") and v2.count(".") == 1

    def _parse_float(self, var):
        try:
            return float(var.get().replace(",", "."))
        except ValueError:
            return None

    def _parse_int(self, var):
        try:
            v = int(var.get())
            return v if v > 0 else None
        except ValueError:
            return None

    def _tela_activa(self):
        n = self._var_tela.get()
        for nombre, ancho in TELAS:
            if nombre == n:
                return nombre, ancho
        return None

    # ── Lógica ────────────────────────────────────────────────────────────────
    def _actualizar(self, *_):
        tela  = self._tela_activa()
        alto  = self._parse_float(self._var_alto)
        ancho = self._parse_float(self._var_ancho)
        cant  = self._parse_int(self._var_cant)

        self._lbl_ancho_tela.config(
            text=f"Ancho máximo de impresión: {tela[1]:.2f} m" if tela else "")

        if not (alto and ancho and alto > 0 and ancho > 0):
            self._lbl_rotacion.config(text="")
            self._lbl_error.config(text="")
            self._btn_omitir.pack_forget()
            self._dibujar_vacio()
            self._set_btn(False)
            return

        lado_corto = min(alto, ancho)
        self._rotado = False
        error = False

        if tela and lado_corto > tela[1]:
            self._rotado = True
            error = True

        if error:
            self._lbl_rotacion.config(text="")
            self._lbl_error.config(
                text=f"⚠ El lado corto ({lado_corto:.2f} m) excede el ancho "
                     f"máximo de la tela ({tela[1]:.2f} m).")
            if not self._omitir_activo:
                self._btn_omitir.pack(anchor="w", pady=(8, 0))
            else:
                self._btn_omitir.pack_forget()
        else:
            self._omitir_activo = False
            self._btn_omitir.pack_forget()
            self._lbl_error.config(text="")
            self._lbl_rotacion.config(
                text="↺ La impresión será rotada para ajustarse a la tela."
                if (self._rotado and tela) else "")

        if error and self._omitir_activo:
            self._set_btn(tela is not None and cant is not None)
            self._dibujar_rect(alto, ancho, "#F0C040")
        elif error:
            self._set_btn(False)
            self._dibujar_rect(alto, ancho, COLORES["error"])
        else:
            self._set_btn(tela is not None and cant is not None)
            self._dibujar_rect(alto, ancho, COLORES["rect_relleno"])

    def _omitir_restriccion(self):
        self._omitir_activo = True
        self._actualizar()

    def _dibujar_vacio(self):
        self._canvas.delete("all")
        self._canvas.create_text(CANVAS_W//2, CANVAS_H//2,
                                 text="Ingresa medidas para\nver la proporción",
                                 font=FUENTE_LABEL, fill=COLORES["borde"],
                                 justify="center")

    def _dibujar_rect(self, alto, ancho, color):
        self._canvas.delete("all")
        ad = ancho if self._rotado else alto
        aw = alto  if self._rotado else ancho

        rh, rw = (MAX_LADO, MAX_LADO * (aw/ad)) if ad >= aw else (MAX_LADO * (ad/aw), MAX_LADO)

        x1, y1 = MARGEN, MARGEN
        x2, y2 = x1 + rw, y1 + rh

        self._canvas.create_rectangle(x1, y1, x2, y2,
                                      fill=color, outline=COLORES["rect_borde"], width=2)
        self._canvas.create_text((x1+x2)/2, y1-6, text=f"{aw} m",
                                 font=FUENTE_MEDIDA, fill=COLORES["texto"], anchor="s")
        self._canvas.create_text(x1-8, (y1+y2)/2, text=f"{ad} m",
                                 font=FUENTE_MEDIDA, fill=COLORES["texto"],
                                 anchor="e", angle=90)

    # ── Botón ─────────────────────────────────────────────────────────────────
    def _set_btn(self, habilitado: bool):
        self._btn_habilitado = habilitado
        if habilitado:
            self._btn_sig.config(bg=COLORES["btn_enabled"], cursor="hand2")
            self._btn_sig.bind("<Button-1>", lambda _: self._siguiente())
            self._btn_sig.bind("<Enter>",
                lambda _: self._btn_sig.config(bg=COLORES["btn_en_hover"]))
            self._btn_sig.bind("<Leave>",
                lambda _: self._btn_sig.config(bg=COLORES["btn_enabled"]))
        else:
            self._btn_sig.config(bg=COLORES["btn_disabled"], cursor="arrow")
            self._btn_sig.unbind("<Button-1>")
            self._btn_sig.unbind("<Enter>")
            self._btn_sig.unbind("<Leave>")

    def _siguiente(self):
        tela = self._tela_activa()
        self._on_siguiente({
            "tela":      tela[0],
            "caja":      self._var_caja.get(),
            "ancho_max": tela[1],
            "alto":      float(self._var_alto.get().replace(",", ".")),
            "ancho":     float(self._var_ancho.get().replace(",", ".")),
            "cantidad":  int(self._var_cant.get()),
            "tema":      self._var_tema.get().strip() if hasattr(self, "_var_tema") else "",
            "rotado":    self._rotado,
        })


