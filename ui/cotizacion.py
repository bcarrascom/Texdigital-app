"""
ui/cotizacion.py
Ventana de ingreso de cotización nueva (flujo no-backlight).
Flujo: pantalla-inicio → iteraciones de medidas → ventana-resumen.
"""

import sys
import tkinter as tk

if sys.platform == "win32":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Reutilizar paleta, fuentes y helpers del cotizador backlight
from ui.cotizador_backlight import (
    COLORES,
    FUENTE_CABECERA,
    FUENTE_SUBTITULO,
    FUENTE_TITULO,
    FUENTE_LABEL,
    FUENTE_MEDIDA,
    FUENTE_BTN,
    FUENTE_AVISO,
    FUENTE_NAV,
    FUENTE_TABLA_CAB,
    FUENTE_TABLA,
    FUENTE_TOTAL,
    MAX_LADO,
    MARGEN,
    CANVAS_W,
    CANVAS_H,
    _construir_cabecera,
    _centrar,
    _btn_label,
)

# Widget de autocompletado ya existente
from ui.formulario_cliente import EntradaAutocompletado

# Listas de sugerencias
from core import escala as _esc
from core.repositorio import PRODUCTOS, TEXTILES, TEXTILES_ANCHOS

# Anchos de columna del resumen
# Orden: #, Producto, Textil, Tema, Cantidad, Ancho (m), Alto (m), Ratio, ML imp.
RESUMEN_COL_W = [35, 140, 120, 120, 75, 75, 75, 90]


def _calc_ml(d: dict) -> tuple[float | None, float | None]:
    """
    Calcula Ratio y ML impresos para un producto.
    Fórmula:
        UxA   = int(ancho_tela / ancho_producto)  ← floor, mínimo 1
        ratio = cantidad / UxA
        ml    = round(ratio * alto, 2)
    Devuelve (None, None) si el textil no tiene ancho máximo registrado.
    """
    ancho_tela = TEXTILES_ANCHOS.get(d.get("textil", ""))
    if ancho_tela is None:
        return None, None
    uxa   = max(1, int(ancho_tela / d["ancho"]))
    ratio = d["cantidad"] / uxa
    ml    = round(ratio * d["alto"], 2)
    return ratio, ml


# ══════════════════════════════════════════════════════════════════════════════
# Pantalla inicial — nombre del trabajo y cantidad de productos
# ══════════════════════════════════════════════════════════════════════════════

class _PantallaInicio(tk.Frame):

    def __init__(self, parent, on_confirmar):
        super().__init__(parent, bg=COLORES["fondo"])
        self.pack(fill="both", expand=True)
        self._on_confirmar   = on_confirmar
        self._btn_habilitado = False
        self._var_nombre     = tk.StringVar()
        self._var_cantidad   = tk.StringVar()
        self._var_nombre.trace_add("write",   self._actualizar_btn)
        self._var_cantidad.trace_add("write", self._actualizar_btn)
        self._construir_ui()

    def _construir_ui(self):
        tk.Frame(self, bg=COLORES["fondo"]).pack(fill="both", expand=True)

        cuerpo = tk.Frame(self, bg=COLORES["fondo"], padx=80)
        cuerpo.pack(fill="x")

        tk.Label(cuerpo, text="Cotizacion nueva",
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
        tk.Entry(cuerpo, textvariable=self._var_cantidad,
                 validate="key", validatecommand=vcmd,
                 font=FUENTE_MEDIDA, width=8,
                 relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                 insertbackground=COLORES["texto"],
                 highlightthickness=1, highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"]).pack(anchor="w", ipady=8, ipadx=8)

        self._btn = _btn_label(cuerpo, "Comenzar →")
        self._btn.pack(anchor="e", pady=(20, 0))

        tk.Frame(self, bg=COLORES["fondo"]).pack(fill="both", expand=True)

        self.winfo_toplevel().bind("<Return>", lambda _: self._confirmar())

    def _validar(self, valor):
        return valor == "" or valor.isdigit()

    def _actualizar_btn(self, *_):
        try:
            ok = int(self._var_cantidad.get()) >= 1 and self._var_nombre.get().strip() != ""
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
            cantidad = int(self._var_cantidad.get())
            nombre   = self._var_nombre.get().strip()
            if cantidad >= 1 and nombre:
                self.winfo_toplevel().unbind("<Return>")
                self._on_confirmar(cantidad, nombre)
        except ValueError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# Pantalla de medidas por producto
# ══════════════════════════════════════════════════════════════════════════════

class _PantallaMedidas(tk.Frame):

    def __init__(self, parent, ventana_raiz, indice, total,
                 datos_previos, datos_todos, on_siguiente, on_nav):
        super().__init__(parent, bg=COLORES["fondo"])
        self.pack(fill="both", expand=True)

        self._ventana_raiz   = ventana_raiz
        self._indice         = indice
        self._total          = total
        self._datos_todos    = datos_todos
        self._on_siguiente   = on_siguiente
        self._on_nav         = on_nav
        self._btn_habilitado = False
        self._omitir_activo  = False

        if datos_previos:
            producto_ini = datos_previos.get("producto", "")
            textil_ini   = datos_previos.get("textil", "")
            alto_ini     = str(datos_previos["alto"])
            ancho_ini    = str(datos_previos["ancho"])
            cant_ini     = str(datos_previos["cantidad"])
            tema_ini     = datos_previos.get("tema", "")
        else:
            producto_ini = textil_ini = alto_ini = ancho_ini = cant_ini = tema_ini = ""

        self._var_producto = tk.StringVar(value=producto_ini)
        self._var_textil   = tk.StringVar(value=textil_ini)
        self._var_alto     = tk.StringVar(value=alto_ini)
        self._var_ancho    = tk.StringVar(value=ancho_ini)
        self._var_cant     = tk.StringVar(value=cant_ini)
        self._var_tema     = tk.StringVar(value=tema_ini)

        self._construir_ui()

        self._var_producto.trace_add("write", self._actualizar)
        self._var_textil.trace_add("write",   self._actualizar_textil)
        self._var_alto.trace_add("write",     self._actualizar)
        self._var_ancho.trace_add("write",    self._actualizar)
        self._var_cant.trace_add("write",     self._actualizar)

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
            c = tk.Label(nav, text=str(i + 1), font=FUENTE_NAV,
                         width=3, pady=4, relief="flat", cursor="hand2")
            c.pack(side="left", padx=3)
            c.bind("<Button-1>", lambda _, idx=i: self._on_nav(idx))
            self._nav_cuadros.append(c)
        self._actualizar_nav()

        tk.Frame(self, bg=COLORES["borde"], height=1).pack(fill="x", padx=30)

        # ── Sección superior: selección de producto y textil ──────────────────
        sup = tk.Frame(self, bg=COLORES["fondo"], padx=40, pady=18)
        sup.pack(fill="x")

        tk.Label(sup,
                 text=f"Nuevo producto  ·  Producto {self._indice + 1} de {self._total}",
                 font=FUENTE_SUBTITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Label(sup, text="Selección de Producto",
                 font=FUENTE_TITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto"]).pack(anchor="w", pady=(4, 10))

        fila_sel = tk.Frame(sup, bg=COLORES["fondo"])
        fila_sel.pack(anchor="w")

        grp_prod = tk.Frame(fila_sel, bg=COLORES["fondo"])
        grp_prod.pack(side="left")
        tk.Label(grp_prod, text="Producto", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        EntradaAutocompletado(
            grp_prod,
            variable=self._var_producto,
            opciones=PRODUCTOS,
            width=28,
        ).pack(anchor="w")

        grp_tex = tk.Frame(fila_sel, bg=COLORES["fondo"])
        grp_tex.pack(side="left", padx=(16, 0))
        tk.Label(grp_tex, text="Textil", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        EntradaAutocompletado(
            grp_tex,
            variable=self._var_textil,
            opciones=TEXTILES,
            width=28,
        ).pack(anchor="w")

        self._lbl_ancho_tela = tk.Label(sup, text="", font=FUENTE_AVISO,
                                        bg=COLORES["fondo"], fg=COLORES["texto_suave"])
        self._lbl_ancho_tela.pack(anchor="w", pady=(6, 0))

        # ── Sección inferior: medidas + canvas ────────────────────────────────
        inf = tk.Frame(self, bg=COLORES["fondo"], padx=40, pady=18)
        inf.pack(fill="both", expand=True)

        tk.Label(inf, text="Medidas", font=FUENTE_TITULO,
                 bg=COLORES["fondo"], fg=COLORES["texto"]).pack(anchor="w", pady=(0, 12))

        col_izq = tk.Frame(inf, bg=COLORES["fondo"])
        col_izq.pack(side="left", anchor="n")

        fila_inp = tk.Frame(col_izq, bg=COLORES["fondo"])
        fila_inp.pack(anchor="w")
        self._crear_input(fila_inp, "Ancho (m)", self._var_ancho).pack(side="left", padx=(0, 16))
        self._crear_input(fila_inp, "Alto (m)",  self._var_alto).pack(side="left", padx=(0, 16))
        self._crear_input(fila_inp, "Cantidad",  self._var_cant).pack(side="left")

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

        # Canvas a la derecha
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

    # ── Lógica ────────────────────────────────────────────────────────────────
    def _ancho_max_textil(self) -> float | None:
        """Devuelve el ancho máximo del textil seleccionado, o None si no está en la lista."""
        return TEXTILES_ANCHOS.get(self._var_textil.get().strip())

    def _actualizar_textil(self, *_):
        """Actualiza el label de ancho de tela al cambiar el textil y re-evalúa."""
        ancho_max = self._ancho_max_textil()
        if ancho_max is not None:
            self._lbl_ancho_tela.config(
                text=f"Ancho máximo de impresión: {ancho_max:.2f} m")
        else:
            self._lbl_ancho_tela.config(text="")
        self._actualizar()

    def _actualizar(self, *_):
        alto    = self._parse_float(self._var_alto)
        ancho   = self._parse_float(self._var_ancho)
        cant    = self._parse_int(self._var_cant)
        prod_ok = self._var_producto.get().strip() != ""
        tex_ok  = self._var_textil.get().strip() != ""

        if not (alto and ancho and alto > 0 and ancho > 0):
            self._lbl_rotacion.config(text="")
            self._lbl_error.config(text="")
            self._btn_omitir.pack_forget()
            self._dibujar_vacio()
            self._set_btn(False)
            return

        ancho_max = self._ancho_max_textil()
        lado_corto = min(alto, ancho)
        error = False

        if ancho_max is not None and lado_corto > ancho_max:
            error = True
            self._lbl_rotacion.config(text="")
            self._lbl_error.config(
                text=f"⚠ El lado corto ({lado_corto:.2f} m) excede el ancho "
                     f"máximo del textil ({ancho_max:.2f} m).")
            if not self._omitir_activo:
                self._btn_omitir.pack(anchor="w", pady=(8, 0))
            else:
                self._btn_omitir.pack_forget()
        else:
            self._omitir_activo = False
            self._btn_omitir.pack_forget()
            self._lbl_error.config(text="")
            if ancho_max is not None and alto != ancho:
                rotado = lado_corto == ancho
                self._lbl_rotacion.config(
                    text="↺ La impresión será rotada para ajustarse al textil."
                    if rotado else "")
            else:
                self._lbl_rotacion.config(text="")

        if error and self._omitir_activo:
            self._dibujar_rect(alto, ancho, "#F0C040")
            self._set_btn(prod_ok and tex_ok and cant is not None)
        elif error:
            self._dibujar_rect(alto, ancho, COLORES["error"])
            self._set_btn(False)
        else:
            self._dibujar_rect(alto, ancho, COLORES["rect_relleno"])
            self._set_btn(prod_ok and tex_ok and cant is not None)

    def _omitir_restriccion(self):
        self._omitir_activo = True
        self._actualizar()

    def _dibujar_vacio(self):
        self._canvas.delete("all")
        self._canvas.create_text(CANVAS_W // 2, CANVAS_H // 2,
                                 text="Ingresa medidas para\nver la proporción",
                                 font=FUENTE_LABEL, fill=COLORES["borde"],
                                 justify="center")

    def _dibujar_rect(self, alto, ancho, color=None):
        self._canvas.delete("all")
        if color is None:
            color = COLORES["rect_relleno"]
        # Orientar el lado largo como alto del rectángulo
        ad = max(alto, ancho)
        aw = min(alto, ancho)

        rh, rw = (MAX_LADO, MAX_LADO * (aw / ad)) if ad >= aw else (MAX_LADO * (ad / aw), MAX_LADO)

        x1, y1 = MARGEN, MARGEN
        x2, y2 = x1 + rw, y1 + rh

        self._canvas.create_rectangle(x1, y1, x2, y2,
                                      fill=color,
                                      outline=COLORES["rect_borde"], width=2)
        self._canvas.create_text((x1 + x2) / 2, y1 - 6, text=f"{aw} m",
                                 font=FUENTE_MEDIDA, fill=COLORES["texto"], anchor="s")
        self._canvas.create_text(x1 - 8, (y1 + y2) / 2, text=f"{ad} m",
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
        self._on_siguiente({
            "producto": self._var_producto.get().strip(),
            "textil":   self._var_textil.get().strip(),
            "alto":     float(self._var_alto.get().replace(",", ".")),
            "ancho":    float(self._var_ancho.get().replace(",", ".")),
            "cantidad": int(self._var_cant.get()),
            "tema":     self._var_tema.get().strip(),
        })


# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# Ventana principal — gestiona el flujo completo
# ══════════════════════════════════════════════════════════════════════════════

class CotizacionNueva(tk.Tk):

    TAM_INICIO  = (800, 560)
    TAM_MEDIDAS = (960, 960)

    def __init__(self):
        super().__init__()
        if sys.platform == "darwin":
            self.TAM_INICIO  = (_esc.px(800), _esc.px(730))
            self.TAM_MEDIDAS = (_esc.px(1100), _esc.px(1250))
        else:
            self.TAM_INICIO  = (800, 560)
            self.TAM_MEDIDAS = (960, 960)
        self.title("Ingresar Cotización")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        _centrar(self, *self.TAM_INICIO)

        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

        self._total_productos  = 0
        self._iteracion_actual = 0
        self._desde_resumen    = False
        self._datos: list[dict] = []
        self._nombre_trabajo   = ""

        _construir_cabecera(self, self._volver)

        self._area = tk.Frame(self, bg=COLORES["fondo"])
        self._area.pack(fill="both", expand=True)

        _PantallaInicio(self._area, on_confirmar=self._on_inicio_confirmado)

    # ── Navegación ────────────────────────────────────────────────────────────
    def _limpiar(self):
        for w in self._area.winfo_children():
            w.destroy()
        self.unbind("<Return>")

    def _on_inicio_confirmado(self, cantidad: int, nombre: str):
        self._total_productos  = cantidad
        self._nombre_trabajo   = nombre
        self._datos            = [None] * cantidad
        self._iteracion_actual = 0
        self._mostrar_medidas()

    def _mostrar_medidas(self, desde_resumen=False):
        self._desde_resumen = desde_resumen
        self._limpiar()
        _centrar(self, *self.TAM_MEDIDAS)
        _PantallaMedidas(
            self._area,
            ventana_raiz=self,
            indice=self._iteracion_actual,
            total=self._total_productos,
            datos_previos=self._datos[self._iteracion_actual],
            datos_todos=self._datos,
            on_siguiente=self._on_medidas_confirmadas,
            on_nav=self._on_nav,
        )

    def _on_medidas_confirmadas(self, datos: dict):
        self._datos[self._iteracion_actual] = datos

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

        COLS = ["#", "Producto", "Textil", "Tema", "Cantidad", "Ancho (m)", "Alto (m)", "ML imp."]

        filas = []
        total_cant    = 0
        total_ml      = 0.0
        alguno_con_ml = False

        for i, d in enumerate(self._datos):
            total_cant += d["cantidad"]
            ratio, ml = _calc_ml(d)
            if ml is not None:
                total_ml      += ml
                alguno_con_ml  = True
            filas.append([
                str(i + 1),
                d.get("producto", ""),
                d.get("textil", ""),
                d.get("tema", ""),
                str(d["cantidad"]),
                str(d["ancho"]),
                str(d["alto"]),
                f"{ml:.2f}" if ml is not None else "—",
            ])

        total_ml_str = f"{round(total_ml, 2):.2f}" if alguno_con_ml else "—"
        totales = ["", "TOTAL", "", "", str(total_cant), "", "", total_ml_str]

        self.withdraw()
        VentanaResumen(
            ancho_ventana=_esc.px(1850),
            columnas=COLS,
            col_w=RESUMEN_COL_W,
            filas=filas,
            totales=totales,
            titulo="Resumen — Cotizacion nueva",
            subtitulo="Cotizacion nueva",
            nombre_trabajo=self._nombre_trabajo,
            on_editar=self._on_editar_desde_resumen,
            on_confirmar=self._on_confirmar_resumen,
            on_cerrar=self._on_cerrar_resumen,
        )

    def _on_editar_desde_resumen(self, indice: int):
        self.deiconify()
        self.lift()
        self.focus_force()
        self._iteracion_actual = indice
        self._mostrar_medidas(desde_resumen=True)

    def _on_confirmar_resumen(self):
        from ui.formulario_cliente import FormularioCliente
        FormularioCliente(
            self,
            datos_productos=self._datos,
            nombre_trabajo=self._nombre_trabajo,
            on_cerrar=None,
            subtitulo="Cotizacion nueva",
            incluir_terminaciones=False,
        )

    def _on_cerrar_resumen(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self._mostrar_medidas(desde_resumen=True)

    def _volver(self, _=None):
        from ui.interfaz import VentanaPrincipal
        self.destroy()
        VentanaPrincipal().mainloop()
