"""
ui/formulario_cliente.py
Ventana de datos del cliente + exportación a Excel.
Se abre después del resumen del cotizador backlight.
"""

import sys
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
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

# ── Rutas base ─────────────────────────────────────────────────────────────────
from core import escala as _esc
from core.repositorio import (
    formatear_rut,
    cargar_clientes,
    guardar_cliente,
    cargar_contactos,
    guardar_contacto,
    TEXTILES_ANCHOS,
)
from core.repositorio_cotizaciones import (
    siguiente_numero,
    guardar_cotizacion,
    carpeta_excel,
)

COLORES = {
    "fondo":        "#E1E1E1",
    "acento":       "#1A3A5C",
    "acento_hover": "#245480",
    "secundario":   "#E8A020",
    "texto":        "#1C1C1C",
    "texto_suave":  "#6B6B6B",
    "borde":        "#D8D4CC",
    "error":        "#C0392B",
    "ok":           "#27AE60",
    "btn_disabled": "#AAAAAA",
    "btn_enabled":  "#1A3A5C",
    "btn_en_hover": "#245480",
    "dropdown_bg":  "#FFFFFF",
    "dropdown_sel": "#C8D4FF",
}

if sys.platform == "darwin":
    FUENTE_CABECERA  = ("Helvetica Neue", _esc.pt(22), "bold")
    FUENTE_TITULO    = ("Helvetica Neue", _esc.pt(23), "bold")
    FUENTE_SUBTITULO = ("Helvetica Neue", _esc.pt(14))
    FUENTE_LABEL     = ("Helvetica Neue", _esc.pt(13))
    FUENTE_MEDIDA    = ("Helvetica Neue", _esc.pt(14), "bold")
    FUENTE_BTN       = ("Helvetica Neue", _esc.pt(14), "bold")
    FUENTE_DROP      = ("Helvetica Neue", _esc.pt(13))
else:
    FUENTE_CABECERA  = ("Georgia", _esc.pt(17), "bold")
    FUENTE_TITULO    = ("Georgia", _esc.pt(18), "bold")
    FUENTE_SUBTITULO = ("Segoe UI", _esc.pt(11))
    FUENTE_LABEL     = ("Segoe UI", _esc.pt(10))
    FUENTE_MEDIDA    = ("Segoe UI", _esc.pt(11), "bold")
    FUENTE_BTN       = ("Segoe UI", _esc.pt(11), "bold")
    FUENTE_DROP      = ("Segoe UI", _esc.pt(10))


# ══════════════════════════════════════════════════════════════════════════════
# Widget de autocompletado
# ══════════════════════════════════════════════════════════════════════════════

class EntradaAutocompletado(tk.Frame):
    """
    Entry con dropdown de sugerencias basado en una lista de opciones.
    on_select(opcion_str) se llama cuando el usuario elige una sugerencia.
    Navegación: flechas ↑↓ para moverse, Enter para seleccionar, Escape para cerrar.
    """

    MAX_SUGERENCIAS = 6

    def __init__(self, parent, variable: tk.StringVar,
                 opciones: list[str], on_select=None,
                 width=28, **kwargs):
        super().__init__(parent, bg=COLORES["fondo"])
        self._var              = variable
        self._opciones         = opciones
        self._on_select        = on_select
        self._dropdown         = None
        self._labels           = []
        self._idx_sel          = -1
        self._opciones_actuales = []

        self._entry = tk.Entry(
            self, textvariable=variable,
            font=FUENTE_MEDIDA, width=width,
            relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
            insertbackground=COLORES["texto"],
            highlightthickness=1,
            highlightbackground=COLORES["borde"],
            highlightcolor=COLORES["acento"],
            **kwargs
        )
        self._entry.pack(ipady=7, ipadx=6, fill="x")

        variable.trace_add("write", self._on_cambio)
        self._entry.bind("<FocusOut>", self._cerrar_dropdown)
        self._entry.bind("<Escape>",   lambda _: self._cerrar_dropdown())
        self._entry.bind("<Down>",     self._navegar_abajo)
        self._entry.bind("<Up>",       self._navegar_arriba)
        self._entry.bind("<Return>",   self._seleccionar_actual)

    def _on_cambio(self, *_):
        texto = self._var.get().strip().lower()
        if not texto:
            self._cerrar_dropdown()
            return
        coincidencias = [o for o in self._opciones
                         if texto in o.lower()][:self.MAX_SUGERENCIAS]
        if coincidencias:
            self._mostrar_dropdown(coincidencias)
        else:
            self._cerrar_dropdown()

    def _mostrar_dropdown(self, opciones):
        self._cerrar_dropdown()
        self._opciones_actuales = opciones
        self._idx_sel = -1
        self._labels = []

        top = tk.Toplevel(self)
        top.wm_overrideredirect(True)
        top.configure(bg=COLORES["borde"])

        # Posicionar debajo del entry
        self.update_idletasks()
        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height()
        w = self._entry.winfo_width()
        top.geometry(f"{w}x{len(opciones)*28}+{x}+{y}")

        for i, opcion in enumerate(opciones):
            lbl = tk.Label(top, text=opcion, font=FUENTE_DROP,
                           bg=COLORES["dropdown_bg"], fg=COLORES["texto"],
                           anchor="w", padx=8, pady=4)
            lbl.pack(fill="x")
            lbl.bind("<Enter>",    lambda _, idx=i: self._hover(idx))
            lbl.bind("<Leave>",    lambda _, idx=i: self._unhover(idx))
            lbl.bind("<Button-1>", lambda _, o=opcion: self._seleccionar(o))
            self._labels.append(lbl)

        self._dropdown = top

    def _hover(self, idx):
        self._idx_sel = idx
        self._actualizar_highlight()

    def _unhover(self, idx):
        if self._idx_sel == idx:
            self._idx_sel = -1
            self._actualizar_highlight()

    def _actualizar_highlight(self):
        for i, lbl in enumerate(self._labels):
            color = COLORES["dropdown_sel"] if i == self._idx_sel else COLORES["dropdown_bg"]
            lbl.config(bg=color)

    def _navegar_abajo(self, _):
        if not self._dropdown:
            return
        if self._idx_sel < len(self._opciones_actuales) - 1:
            self._idx_sel += 1
            self._actualizar_highlight()
        return "break"

    def _navegar_arriba(self, _):
        if not self._dropdown:
            return
        if self._idx_sel > 0:
            self._idx_sel -= 1
            self._actualizar_highlight()
        elif self._idx_sel == 0:
            self._idx_sel = -1
            self._actualizar_highlight()
        return "break"

    def _seleccionar_actual(self, _):
        if self._dropdown and self._idx_sel >= 0:
            opcion = self._opciones_actuales[self._idx_sel]
            self._seleccionar(opcion)
            return "break"

    def _seleccionar(self, opcion):
        self._var.set(opcion)
        self._cerrar_dropdown()
        if self._on_select:
            self._on_select(opcion)

    def _cerrar_dropdown(self, *_):
        if self._dropdown:
            try:
                self._dropdown.destroy()
            except Exception:
                pass
            self._dropdown = None
        self._labels = []
        self._idx_sel = -1
        self._opciones_actuales = []

    def get(self):
        return self._entry.get()

    def set_opciones(self, opciones: list[str]):
        self._opciones = opciones


def _mapear_producto(d: dict) -> dict:
    """Convierte un dict interno de producto al esquema JSON de cotización/OP."""
    if "tela" in d:
        return {
            "Tela":     d.get("tela", ""),
            "Caja":     d.get("caja", ""),
            "Ancho":    float(d.get("ancho", 0.0)),
            "Alto":     float(d.get("alto", 0.0)),
            "Cantidad": int(d.get("cantidad", 0)),
            "Tema":     d.get("tema", ""),
            "Obs":      d.get("obs", ""),
        }
    return {
        "producto": d.get("producto", ""),
        "Tela":     d.get("textil", ""),
        "Ancho":    float(d.get("ancho", 0.0)),
        "Alto":     float(d.get("alto", 0.0)),
        "Cantidad": int(d.get("cantidad", 0)),
        "Tema":     d.get("tema", ""),
        "Obs":      d.get("obs", ""),
    }


def producto_desde_json(d: dict) -> dict:
    """Inversa de `_mapear_producto`: convierte un producto en esquema JSON
    de vuelta al esquema interno que usan las pantallas de edición."""
    if "Caja" in d:
        return {
            "tela":      d.get("Tela", ""),
            "caja":      d.get("Caja", ""),
            "ancho_max": TEXTILES_ANCHOS.get(d.get("Tela", ""), 0.0),
            "ancho":     d.get("Ancho", 0.0),
            "alto":      d.get("Alto", 0.0),
            "cantidad":  d.get("Cantidad", 0),
            "tema":      d.get("Tema", ""),
            "obs":       d.get("Obs", ""),
            "rotado":    False,
        }
    return {
        "producto": d.get("producto", ""),
        "textil":   d.get("Tela", ""),
        "ancho":    d.get("Ancho", 0.0),
        "alto":     d.get("Alto", 0.0),
        "cantidad": d.get("Cantidad", 0),
        "tema":     d.get("Tema", ""),
        "obs":      d.get("Obs", ""),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Ventana del formulario de cliente
# ══════════════════════════════════════════════════════════════════════════════

class FormularioCliente(tk.Toplevel):
    """
    Ventana de datos del cliente.
    Recibe datos_productos (lista de dicts del cotizador) y nombre_trabajo.
    Al exportar llama a exportar_excel() del módulo excel/.
    """

    ANCHO = _esc.px(1200)
    ALTO  = _esc.px(1265)

    def __init__(self, parent, datos_productos: list[dict],
                 nombre_trabajo: str, on_cerrar=None,
                 subtitulo="Cotizador Backlight",
                 incluir_terminaciones=True):
        super().__init__(parent)
        self.title("Datos del cliente")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)

        self._datos_productos       = datos_productos
        self._nombre_trabajo        = nombre_trabajo
        self._on_cerrar             = on_cerrar
        self._subtitulo             = subtitulo
        self._incluir_terminaciones = incluir_terminaciones
        self._clientes          = cargar_clientes()
        self._nombres_empresas  = [c["empresa"] for c in self._clientes]
        self._contactos         = cargar_contactos()
        self._nombres_contactos = [c["contacto"] for c in self._contactos]
        self._datos_guardados   = False
        self._contacto_guardado = False
        self._formateando_rut   = False
        self._exportado         = False
        self._num_cotizacion_defecto = str(siguiente_numero()).zfill(4)

        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self._centrar(self.ANCHO, self.ALTO)
        if sys.platform == "darwin":
            self.resizable(True, True)
        self.lift()
        self.focus_force()

        self._construir_ui()

    # ── Construcción UI ────────────────────────────────────────────────────────

    def _construir_ui(self):
        # Cabecera
        cab = tk.Frame(self, bg=COLORES["acento"])
        cab.pack(fill="x")
        tk.Frame(cab, bg=COLORES["secundario"], height=3).pack(fill="x")
        contenido_cab = tk.Frame(cab, bg=COLORES["acento"], padx=24, pady=14)
        contenido_cab.pack(fill="x")
        tk.Label(contenido_cab, text="Sistema de Gestión",
                 font=FUENTE_CABECERA, bg=COLORES["acento"], fg="#FFFFFF").pack(side="left")

        # Cuerpo — en macOS con scroll vertical, en otros sistemas sin scroll
        if sys.platform == "darwin":
            _outer = tk.Frame(self, bg=COLORES["fondo"])
            _outer.pack(fill="both", expand=True)

            _scrollbar = tk.Scrollbar(_outer, orient="vertical")
            _scrollbar.pack(side="right", fill="y")

            _canvas = tk.Canvas(_outer, bg=COLORES["fondo"],
                                yscrollcommand=_scrollbar.set,
                                highlightthickness=0)
            _canvas.pack(side="left", fill="both", expand=True)
            _scrollbar.config(command=_canvas.yview)

            cuerpo = tk.Frame(_canvas, bg=COLORES["fondo"], padx=40, pady=24)
            _win_id = _canvas.create_window((0, 0), window=cuerpo, anchor="nw")

            def _on_frame_configure(_e):
                _canvas.configure(scrollregion=_canvas.bbox("all"))

            def _on_canvas_configure(e):
                _canvas.itemconfig(_win_id, width=e.width)

            def _on_mousewheel(e):
                _canvas.yview_scroll(-1 * (e.delta // 120), "units")

            cuerpo.bind("<Configure>", _on_frame_configure)
            _canvas.bind("<Configure>", _on_canvas_configure)
            _canvas.bind_all("<MouseWheel>", _on_mousewheel)
        else:
            cuerpo = tk.Frame(self, bg=COLORES["fondo"], padx=40, pady=24)
            cuerpo.pack(fill="both", expand=True)

        tk.Label(cuerpo, text=self._subtitulo,
                 font=FUENTE_SUBTITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Label(cuerpo, text="Datos del cliente",
                 font=FUENTE_TITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto"]).pack(anchor="w", pady=(4, 4))
        tk.Label(cuerpo, text=self._nombre_trabajo,
                 font=FUENTE_CABECERA, bg=COLORES["fondo"],
                 fg=COLORES["acento"]).pack(anchor="w", pady=(0, 16))

        # ── Grupo 1: Empresa / Rut / Razón Social (con autocompletado) ────────
        self._var_empresa      = tk.StringVar()
        self._var_rut          = tk.StringVar()
        self._var_razon_social = tk.StringVar()

        tk.Label(cuerpo, text="Empresa", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._ac_empresa = EntradaAutocompletado(
            cuerpo, self._var_empresa,
            opciones=self._nombres_empresas,
            on_select=self._autocompletar_cliente,
            width=36,
        )
        self._ac_empresa.pack(anchor="w", fill="x", pady=(0, 10))

        fila_rut = tk.Frame(cuerpo, bg=COLORES["fondo"])
        fila_rut.pack(fill="x", pady=(0, 10))

        col_rut = tk.Frame(fila_rut, bg=COLORES["fondo"])
        col_rut.pack(side="left", padx=(0, 20))
        tk.Label(col_rut, text="RUT", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._e_rut = self._crear_entry(col_rut, self._var_rut, width=16)
        self._e_rut.pack(anchor="w", ipady=7, ipadx=6)
        self._var_rut.trace_add("write", self._on_rut_cambio)

        col_rs = tk.Frame(fila_rut, bg=COLORES["fondo"])
        col_rs.pack(side="left", padx=(0, 16))
        tk.Label(col_rs, text="Razón Social", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._e_razon = self._crear_entry(col_rs, self._var_razon_social, width=28)
        self._e_razon.pack(anchor="w", ipady=7, ipadx=6)

        # Botón "Guardar Datos" alineado verticalmente con el entry de Razón Social
        col_btn_guardar = tk.Frame(fila_rut, bg=COLORES["fondo"])
        col_btn_guardar.pack(side="left")
        # Espacio vacío para alinear con el label de arriba
        tk.Label(col_btn_guardar, text="", font=FUENTE_LABEL,
                 bg=COLORES["fondo"]).pack(anchor="w")
        self._btn_guardar = tk.Button(
            col_btn_guardar, text="Guardar Datos",
            font=FUENTE_BTN,
            bg=COLORES["btn_enabled"], fg="#FFFFFF",
            activebackground=COLORES["btn_en_hover"], activeforeground="#FFFFFF",
            relief="flat", cursor="hand2",
            padx=12, pady=7,
            command=self._guardar_datos,
        )
        self._btn_guardar.pack(anchor="w")
        self._btn_guardar.bind("<Return>", lambda _: self._guardar_datos())

        tk.Frame(cuerpo, bg=COLORES["borde"], height=1).pack(fill="x", pady=(8, 14))

        # ── Grupo 2: Contacto / Email / Fuente / Condición ───────────────────
        self._var_contacto  = tk.StringVar()
        self._var_email     = tk.StringVar()
        self._var_fuente    = tk.StringVar()
        self._var_condicion = tk.StringVar()

        fila2 = tk.Frame(cuerpo, bg=COLORES["fondo"])
        fila2.pack(fill="x", pady=(0, 10))

        # Contacto con autocompletado
        col_contacto = tk.Frame(fila2, bg=COLORES["fondo"])
        col_contacto.pack(side="left", padx=(0, 16))
        tk.Label(col_contacto, text="Contacto", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._ac_contacto = EntradaAutocompletado(
            col_contacto, self._var_contacto,
            opciones=self._nombres_contactos,
            on_select=self._autocompletar_contacto,
            width=20,
        )
        self._ac_contacto.pack(anchor="w")

        col_email = tk.Frame(fila2, bg=COLORES["fondo"])
        col_email.pack(side="left", padx=(0, 16))
        tk.Label(col_email, text="Email", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._crear_entry(col_email, self._var_email, width=26).pack(anchor="w", ipady=7, ipadx=6)

        col_fuente = tk.Frame(fila2, bg=COLORES["fondo"])
        col_fuente.pack(side="left")
        tk.Label(col_fuente, text="Fuente", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        _frame_fuente = tk.Frame(col_fuente, bg=COLORES["fondo"])
        _frame_fuente.pack(anchor="w")
        self._crear_entry(_frame_fuente, self._var_fuente, width=10).pack(side="left", ipady=7, ipadx=6)
        tk.Label(_frame_fuente, text="%", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto"]).pack(side="left", padx=(2, 0))

        # Fila: Condición de pago + botón Guardar Contacto
        fila_condicion = tk.Frame(cuerpo, bg=COLORES["fondo"])
        fila_condicion.pack(fill="x", pady=(0, 10))

        col_cond = tk.Frame(fila_condicion, bg=COLORES["fondo"])
        col_cond.pack(side="left", padx=(0, 16))
        tk.Label(col_cond, text="Condición de pago", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._crear_entry(col_cond, self._var_condicion, width=20).pack(anchor="w", ipady=7, ipadx=6)

        col_btn_contacto = tk.Frame(fila_condicion, bg=COLORES["fondo"])
        col_btn_contacto.pack(side="left")
        tk.Label(col_btn_contacto, text="", font=FUENTE_LABEL,
                 bg=COLORES["fondo"]).pack(anchor="w")
        self._btn_guardar_contacto = tk.Button(
            col_btn_contacto, text="Guardar Contacto",
            font=FUENTE_BTN,
            bg=COLORES["btn_enabled"], fg="#FFFFFF",
            activebackground=COLORES["btn_en_hover"], activeforeground="#FFFFFF",
            relief="flat", cursor="hand2",
            padx=12, pady=7,
            command=self._guardar_contacto_datos,
        )
        self._btn_guardar_contacto.pack(anchor="w")

        tk.Frame(cuerpo, bg=COLORES["borde"], height=1).pack(fill="x", pady=(8, 14))

        # ── Grupo 3: Fecha / Cotización / Terminaciones Caja ─────────────────
        self._var_fecha         = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self._var_cotizacion    = tk.StringVar(value=self._num_cotizacion_defecto)
        self._var_terminaciones = tk.StringVar(value="CAJA TERMINADA")

        fila3 = tk.Frame(cuerpo, bg=COLORES["fondo"])
        fila3.pack(fill="x", pady=(0, 10))

        col_f = tk.Frame(fila3, bg=COLORES["fondo"])
        col_f.pack(side="left", padx=(0, 20))
        tk.Label(col_f, text="Fecha", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._crear_entry(col_f, self._var_fecha, width=14).pack(anchor="w", ipady=7, ipadx=6)

        col_c = tk.Frame(fila3, bg=COLORES["fondo"])
        col_c.pack(side="left")
        tk.Label(col_c, text="N° Cotización (4 dígitos)", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        vcmd = (self.register(self._validar_cotizacion), "%P")
        self._e_cotizacion = tk.Entry(
            col_c, textvariable=self._var_cotizacion,
            validate="key", validatecommand=vcmd,
            font=FUENTE_MEDIDA, width=8,
            relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
            insertbackground=COLORES["texto"],
            highlightthickness=1,
            highlightbackground=COLORES["borde"],
            highlightcolor=COLORES["acento"],
        )
        self._e_cotizacion.pack(anchor="w", ipady=7, ipadx=6)

        # Switch TERMINACIONES CAJA (solo backlight)
        if self._incluir_terminaciones:
            col_term = tk.Frame(fila3, bg=COLORES["fondo"])
            col_term.pack(side="left", padx=(20, 0))
            tk.Label(col_term, text="TERMINACIONES CAJA", font=FUENTE_LABEL,
                     bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
            switch_frame = tk.Frame(col_term, bg=COLORES["borde"], padx=1, pady=1)
            switch_frame.pack(anchor="w")
            self._btn_term_caja = tk.Label(
                switch_frame, text="CAJA TERMINADA",
                font=FUENTE_LABEL,
                bg=COLORES["acento"], fg="#FFFFFF",
                padx=8, pady=7, cursor="hand2",
            )
            self._btn_term_caja.pack(side="left")
            self._btn_term_visual = tk.Label(
                switch_frame, text="AREA VISUAL",
                font=FUENTE_LABEL,
                bg="#FFFFFF", fg=COLORES["texto"],
                padx=8, pady=7, cursor="hand2",
            )
            self._btn_term_visual.pack(side="left")
            self._btn_term_caja.bind("<Button-1>",   lambda _: self._sel_terminacion("CAJA TERMINADA"))
            self._btn_term_visual.bind("<Button-1>", lambda _: self._sel_terminacion("AREA VISUAL"))

        tk.Frame(cuerpo, bg=COLORES["borde"], height=1).pack(fill="x", pady=(8, 14))

        # ── Grupo 4: Descripción ──────────────────────────────────────────────
        self._var_descripcion = tk.StringVar()

        tk.Label(cuerpo, text="Descripción (C19)", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._crear_entry(cuerpo, self._var_descripcion, width=60).pack(
            anchor="w", ipady=7, ipadx=6, pady=(0, 10))

        # ── Label de estado ───────────────────────────────────────────────────
        self._lbl_estado = tk.Label(cuerpo, text="", font=FUENTE_LABEL,
                                    bg=COLORES["fondo"], fg=COLORES["ok"],
                                    justify="left")
        self._lbl_estado.pack(anchor="w")

        # ── Botones exportar / nueva cotización ───────────────────────────────
        if sys.platform == "darwin":
            # En macOS los botones van dentro del cuerpo scrollable usando pack
            _fila_btn = tk.Frame(cuerpo, bg=COLORES["fondo"])
            _fila_btn.pack(fill="x", pady=(16, 4))

            self._btn_nueva = tk.Label(
                _fila_btn, text="← Cancelar",
                font=FUENTE_BTN, bg=COLORES["error"],
                fg="#FFFFFF", padx=20, pady=10, cursor="hand2",
            )
            self._btn_nueva.pack(side="left")
            self._btn_nueva.bind("<Button-1>", lambda _: self._nueva_cotizacion())
            self._btn_nueva.bind("<Enter>",
                lambda _: self._btn_nueva.config(bg="#A93226"))
            self._btn_nueva.bind("<Leave>",
                lambda _: self._btn_nueva.config(bg=COLORES["error"]))

            self._lbl_export_estado = tk.Label(
                _fila_btn, text="", font=FUENTE_LABEL,
                bg=COLORES["fondo"], fg=COLORES["ok"],
                justify="center", wraplength=400,
            )
            self._lbl_export_estado.pack(side="left", expand=True)

            self._btn_exportar = tk.Label(
                _fila_btn, text="Guardar y Exportar →",
                font=FUENTE_BTN, bg=COLORES["btn_enabled"],
                fg="#FFFFFF", padx=20, pady=10, cursor="hand2",
            )
            self._btn_exportar.pack(side="right")
            self._btn_exportar.bind("<Button-1>", lambda _: self._exportar())
            self._btn_exportar.bind("<Enter>",
                lambda _: self._btn_exportar.config(bg=COLORES["btn_en_hover"]))
            self._btn_exportar.bind("<Leave>",
                lambda _: self._btn_exportar.config(bg=COLORES["btn_enabled"]))
        else:
            # En Windows los botones flotan sobre la ventana usando place
            self._btn_exportar = tk.Label(
                self, text="Guardar y Exportar →",
                font=FUENTE_BTN, bg=COLORES["btn_enabled"],
                fg="#FFFFFF", padx=20, pady=10, cursor="hand2",
            )
            self._btn_exportar.place(relx=1.0, rely=1.0, anchor="se", x=-30, y=-20)
            self._btn_exportar.bind("<Button-1>", lambda _: self._exportar())
            self._btn_exportar.bind("<Enter>",
                lambda _: self._btn_exportar.config(bg=COLORES["btn_en_hover"]))
            self._btn_exportar.bind("<Leave>",
                lambda _: self._btn_exportar.config(bg=COLORES["btn_enabled"]))

            self._btn_nueva = tk.Label(
                self, text="← Cancelar",
                font=FUENTE_BTN, bg=COLORES["error"],
                fg="#FFFFFF", padx=20, pady=10, cursor="hand2",
            )
            self._btn_nueva.place(relx=0.0, rely=1.0, anchor="sw", x=30, y=-20)
            self._btn_nueva.bind("<Button-1>", lambda _: self._nueva_cotizacion())
            self._btn_nueva.bind("<Enter>",
                lambda _: self._btn_nueva.config(bg="#A93226"))
            self._btn_nueva.bind("<Leave>",
                lambda _: self._btn_nueva.config(bg=COLORES["error"]))

            self._lbl_export_estado = tk.Label(
                self, text="", font=FUENTE_LABEL,
                bg=COLORES["fondo"], fg=COLORES["ok"],
                justify="center", wraplength=500,
            )
            self._lbl_export_estado.place(relx=0.5, rely=1.0, anchor="s", y=-26)

    def _crear_entry(self, parent, variable, width=20):
        return tk.Entry(
            parent, textvariable=variable,
            font=FUENTE_MEDIDA, width=width,
            relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
            insertbackground=COLORES["texto"],
            highlightthickness=1,
            highlightbackground=COLORES["borde"],
            highlightcolor=COLORES["acento"],
        )

    # ── Autocompletado de cliente ──────────────────────────────────────────────

    def _on_rut_cambio(self, *_):
        """Formatea el RUT automáticamente mientras el usuario escribe."""
        if self._formateando_rut:
            return
        self._formateando_rut = True
        raw = self._var_rut.get()
        formateado = formatear_rut(raw)
        self._var_rut.set(formateado)
        # Mover cursor al final
        self._e_rut.after_idle(lambda: self._e_rut.icursor("end"))
        self._formateando_rut = False

    def _autocompletar_cliente(self, nombre_empresa: str):
        """Busca la empresa en clientes y rellena Rut + Razón Social."""
        for c in self._clientes:
            if c["empresa"].lower() == nombre_empresa.lower():
                self._var_rut.set(c["rut"])
                self._var_razon_social.set(c["razon_social"])
                return

    # ── Guardar datos del cliente ──────────────────────────────────────────────

    def _guardar_datos(self):
        """Guarda empresa/rut/razón social en clientes.txt. Solo funciona una vez."""
        if self._datos_guardados:
            return
        empresa = self._var_empresa.get().strip()
        if not empresa:
            self._lbl_estado.config(
                text="⚠ El campo Empresa es obligatorio para guardar.",
                fg=COLORES["error"],
            )
            return
        rut          = self._var_rut.get().strip()
        razon_social = self._var_razon_social.get().strip()
        guardar_cliente(empresa, rut, razon_social)
        # Recargar para que el autocompletado incluya la nueva entrada
        self._clientes        = cargar_clientes()
        self._nombres_empresas = [c["empresa"] for c in self._clientes]
        self._ac_empresa.set_opciones(self._nombres_empresas)
        self._datos_guardados = True
        self._btn_guardar.config(
            state="disabled",
            bg=COLORES["btn_disabled"],
            cursor="",
        )
        self._lbl_estado.config(text="✓ Datos guardados correctamente.", fg=COLORES["ok"])

    # ── Autocompletado de contacto ────────────────────────────────────────────

    def _autocompletar_contacto(self, nombre_contacto: str):
        """Busca el contacto y rellena Email, Fuente y Condición."""
        for c in self._contactos:
            if c["contacto"].lower() == nombre_contacto.lower():
                self._var_email.set(c["email"])
                self._var_fuente.set(c["fuente"])
                self._var_condicion.set(c["condicion"])
                return

    # ── Guardar datos del contacto ────────────────────────────────────────────

    def _guardar_contacto_datos(self):
        """Guarda contacto/email/fuente/condicion en contactos.txt. Solo funciona una vez."""
        if self._contacto_guardado:
            return
        contacto = self._var_contacto.get().strip()
        if not contacto:
            self._lbl_estado.config(
                text="⚠ El campo Contacto es obligatorio para guardar.",
                fg=COLORES["error"],
            )
            return
        email     = self._var_email.get().strip()
        fuente    = self._var_fuente.get().strip()
        condicion = self._var_condicion.get().strip()
        guardar_contacto(contacto, email, fuente, condicion)
        self._contactos         = cargar_contactos()
        self._nombres_contactos = [c["contacto"] for c in self._contactos]
        self._ac_contacto.set_opciones(self._nombres_contactos)
        self._contacto_guardado = True
        self._btn_guardar_contacto.config(
            state="disabled",
            bg=COLORES["btn_disabled"],
            cursor="",
        )
        self._lbl_estado.config(text="✓ Contacto guardado correctamente.", fg=COLORES["ok"])

    # ── Validación ─────────────────────────────────────────────────────────────

    def _sel_terminacion(self, opcion: str):
        self._var_terminaciones.set(opcion)
        if opcion == "CAJA TERMINADA":
            self._btn_term_caja.config(bg=COLORES["acento"], fg="#FFFFFF")
            self._btn_term_visual.config(bg="#FFFFFF", fg=COLORES["texto"])
        else:
            self._btn_term_caja.config(bg="#FFFFFF", fg=COLORES["texto"])
            self._btn_term_visual.config(bg=COLORES["acento"], fg="#FFFFFF")

    def _validar_cotizacion(self, valor):
        return valor == "" or (valor.isdigit() and len(valor) <= 4)

    def _campos_ok(self) -> tuple[bool, str]:
        """Devuelve (ok, mensaje_error)."""
        if not self._var_empresa.get().strip():
            return False, "El campo Empresa es obligatorio."
        cot = self._var_cotizacion.get().strip()
        if not cot or len(cot) != 4:
            return False, "El N° de Cotización debe tener exactamente 4 dígitos."
        return True, ""

    # ── Estado del botón Cancelar / Nueva Cotización ─────────────────────────

    def _modo_cancelar(self):
        self._btn_nueva.config(text="← Cancelar", bg=COLORES["error"])
        self._btn_nueva.bind("<Enter>", lambda _: self._btn_nueva.config(bg="#A93226"))
        self._btn_nueva.bind("<Leave>", lambda _: self._btn_nueva.config(bg=COLORES["error"]))

    def _modo_nueva_cot(self):
        self._btn_nueva.config(text="← Nueva Cotización", bg=COLORES["secundario"])
        self._btn_nueva.bind("<Enter>", lambda _: self._btn_nueva.config(bg="#C8881A"))
        self._btn_nueva.bind("<Leave>", lambda _: self._btn_nueva.config(bg=COLORES["secundario"]))

    # ── Exportar + Guardar ────────────────────────────────────────────────────

    def _exportar(self):
        ok, msg = self._campos_ok()
        if not ok:
            self._lbl_export_estado.config(text=f"⚠ {msg}", fg=COLORES["error"])
            return

        datos_cliente = {
            "nombre_trabajo": self._nombre_trabajo,
            "empresa":        self._var_empresa.get().strip(),
            "rut":            self._var_rut.get().strip(),
            "razon_social":   self._var_razon_social.get().strip(),
            "contacto":       self._var_contacto.get().strip(),
            "email":          self._var_email.get().strip(),
            "fuente":         self._var_fuente.get().strip(),
            "condicion":      self._var_condicion.get().strip(),
            "fecha":          self._var_fecha.get().strip(),
            "cotizacion":     self._var_cotizacion.get().strip(),
            "descripcion":    self._var_descripcion.get().strip(),
        }
        if self._incluir_terminaciones:
            datos_cliente["terminaciones_caja"] = self._var_terminaciones.get()

        try:
            # ── Excel ─────────────────────────────────────────────────────────
            carpeta_xls = carpeta_excel()
            if self._incluir_terminaciones:
                from excel.generador_documentos import exportar_cotizacion_backlight
                ruta_xls = exportar_cotizacion_backlight(
                    datos_cliente=datos_cliente,
                    datos_productos=self._datos_productos,
                    destino_dir=carpeta_xls,
                )
            else:
                from excel.generador_documentos import exportar_cotizacion_nueva
                ruta_xls = exportar_cotizacion_nueva(
                    datos_cliente=datos_cliente,
                    datos_productos=self._datos_productos,
                    destino_dir=carpeta_xls,
                )

            # ── JSON ──────────────────────────────────────────────────────────
            fuente_raw = datos_cliente.get("fuente", "")
            try:
                fuente_val = float(fuente_raw)
            except (ValueError, TypeError):
                fuente_val = 0.0

            json_dict = {
                "Cotizacion":       int(datos_cliente["cotizacion"]),
                "Nombre":           datos_cliente["nombre_trabajo"],
                "Fecha":            datos_cliente["fecha"],
                "Empresa":          datos_cliente["empresa"],
                "RUT":              datos_cliente["rut"],
                "Razon Social":     datos_cliente["razon_social"],
                "Contacto":         datos_cliente["contacto"],
                "Email":            datos_cliente["email"],
                "Fuente":           fuente_val,
                "Condicion de pago": datos_cliente["condicion"],
                "Descripcion":      datos_cliente["descripcion"],
                "productos":        [_mapear_producto(d) for d in self._datos_productos],
            }
            ruta_json = guardar_cotizacion(json_dict)

            self._lbl_export_estado.config(
                text=f"✓ Guardado correctamente:\n{ruta_xls}\n{ruta_json}",
                fg=COLORES["ok"],
            )
            self._modo_nueva_cot()

        except Exception as e:
            self._lbl_export_estado.config(
                text=f"⚠ Error al guardar: {e}",
                fg=COLORES["error"],
            )

    def _nueva_cotizacion(self):
        """Cierra esta ventana y regresa al menú inicial."""
        from ui.interfaz import VentanaPrincipal
        # Destruir la ventana raíz tk.Tk (padre del Toplevel) para que su
        # mainloop() termine limpiamente antes de crear la nueva VentanaPrincipal.
        self.master.destroy()
        VentanaPrincipal().mainloop()

    # ── Utilidades ─────────────────────────────────────────────────────────────

    def _cerrar(self):
        if self._on_cerrar:
            self._on_cerrar()
        self.destroy()
        sys.exit(0)

    def _centrar(self, ancho, alto):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - ancho) // 2
        y = (self.winfo_screenheight() - alto)  // 2
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
