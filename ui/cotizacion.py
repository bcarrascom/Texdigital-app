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

# Paleta, fuentes y helpers compartidos
from ui.estilos import (
    COLORES,
    FUENTE_SUBTITULO,
    FUENTE_TITULO,
    FUENTE_LABEL,
    FUENTE_MEDIDA,
    MAX_LADO,
    MARGEN,
    MARGEN_SUP,
    _construir_cabecera,
    _centrar,
)

# Pantallas compartidas
from ui.pantalla_inicio import PantallaInicio
from ui.pantalla_medidas_base import PantallaMedidasBase

# Widget de autocompletado ya existente
from ui.formulario_cliente import EntradaAutocompletado

# Listas de sugerencias
from core import escala as _esc
from core.repositorio import PRODUCTOS, TEXTILES, TEXTILES_ANCHOS, ESTRUCTURAS, TERMINACIONES

SIN_ESTRUCTURA    = "Sin estructura"
SIN_TERMINACIONES = "Sin terminaciones"
CARA_UNICA        = "Cara única"
TIRO_Y_RETIRO     = "Tiro y retiro"

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
        si Tiro y retiro: ml *= 2 (se imprimen las dos caras, mismo cálculo
        que Cara única pero el doble de tela)
    Devuelve (None, None) si el textil no tiene ancho máximo registrado.
    """
    ancho_tela = TEXTILES_ANCHOS.get(d.get("textil", ""))
    if ancho_tela is None:
        return None, None
    uxa   = max(1, int(ancho_tela / d["ancho"]))
    ratio = d["cantidad"] / uxa
    ml    = round(ratio * d["alto"], 2)
    if d.get("impresion") == TIRO_Y_RETIRO:
        ml *= 2
    return ratio, ml


# ══════════════════════════════════════════════════════════════════════════════
# Pantalla de medidas por producto
# ══════════════════════════════════════════════════════════════════════════════

class _PantallaMedidas(PantallaMedidasBase):

    def __init__(self, parent, ventana_raiz, indice, total,
                 datos_previos, datos_todos, on_siguiente, on_nav):
        super().__init__(parent, ventana_raiz, indice, total,
                          datos_previos, datos_todos, on_siguiente, on_nav)

        if datos_previos:
            producto_ini    = datos_previos.get("producto", "")
            textil_ini      = datos_previos.get("textil", "")
            estructura_ini  = datos_previos.get("estructura", SIN_ESTRUCTURA)
            terminacion_ini = datos_previos.get("terminacion", SIN_TERMINACIONES)
            impresion_ini   = datos_previos.get("impresion", CARA_UNICA)
        else:
            producto_ini    = textil_ini = ""
            estructura_ini  = SIN_ESTRUCTURA
            terminacion_ini = SIN_TERMINACIONES
            impresion_ini   = CARA_UNICA

        self._var_producto    = tk.StringVar(value=producto_ini)
        self._var_textil      = tk.StringVar(value=textil_ini)
        self._var_estructura  = tk.StringVar(value=estructura_ini)
        self._var_terminacion = tk.StringVar(value=terminacion_ini)
        self._var_impresion   = tk.StringVar(value=impresion_ini)

        self._construir_ui()

        self._var_producto.trace_add("write", self._actualizar)
        self._var_textil.trace_add("write",   self._actualizar_textil)
        self._var_alto.trace_add("write",     self._actualizar)
        self._var_ancho.trace_add("write",    self._actualizar)
        self._var_cant.trace_add("write",     self._actualizar)
        self._var_impresion.trace_add("write", self._actualizar_switch_impresion)

        self._actualizar()
        self._actualizar_switch_impresion()
        ventana_raiz.bind("<Return>", lambda _: self._enter_sig())

    # ── Sección superior: selección de producto y textil ──────────────────────
    def _construir_seccion_superior(self, sup):
        tk.Label(sup,
                 text=f"Nuevo producto  ·  Producto {self._indice + 1} de {self._total}",
                 font=FUENTE_SUBTITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Label(sup, text="Selección de Producto",
                 font=FUENTE_TITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto"]).pack(anchor="w", pady=(2, 6))

        fila_sel = tk.Frame(sup, bg=COLORES["fondo"])
        fila_sel.pack(anchor="w")

        # Producto y Textil van uno al lado del otro (antes apilados) —
        # Producto a la mitad de ancho para que Textil quepa a su derecha.
        fila_prod_tex = tk.Frame(fila_sel, bg=COLORES["fondo"])
        fila_prod_tex.pack(anchor="w")

        grp_prod = tk.Frame(fila_prod_tex, bg=COLORES["fondo"])
        grp_prod.pack(side="left")
        tk.Label(grp_prod, text="Producto", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        EntradaAutocompletado(
            grp_prod,
            variable=self._var_producto,
            opciones=PRODUCTOS,
            width=30,
        ).pack(anchor="w")

        grp_tex = tk.Frame(fila_prod_tex, bg=COLORES["fondo"])
        grp_tex.pack(side="left", padx=(16, 0))
        tk.Label(grp_tex, text="Textil", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        EntradaAutocompletado(
            grp_tex,
            variable=self._var_textil,
            opciones=TEXTILES,
            width=28,
        ).pack(anchor="w")

        grp_est = tk.Frame(fila_sel, bg=COLORES["fondo"])
        grp_est.pack(anchor="w", pady=(6, 0))
        tk.Label(grp_est, text="Estructura", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        EntradaAutocompletado(
            grp_est,
            variable=self._var_estructura,
            opciones=ESTRUCTURAS,
            width=40,
        ).pack(anchor="w")

        grp_term = tk.Frame(fila_sel, bg=COLORES["fondo"])
        grp_term.pack(anchor="w", pady=(6, 0))
        tk.Label(grp_term, text="Terminación", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        EntradaAutocompletado(
            grp_term,
            variable=self._var_terminacion,
            opciones=TERMINACIONES,
            width=40,
        ).pack(anchor="w")

        grp_impr = tk.Frame(fila_sel, bg=COLORES["fondo"])
        grp_impr.pack(anchor="w", pady=(6, 0))
        tk.Label(grp_impr, text="Impresión", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._construir_switch_impresion(grp_impr).pack(anchor="w")

        self._crear_lbl_ancho_tela(sup)

    def _construir_switch_impresion(self, parent):
        """Switch de 2 estados Cara única / Tiro y retiro. Tiro y retiro usa
        el doble de tela (mismo cálculo de ML, ×2 — ver _calc_ml)."""
        cont = tk.Frame(parent, bg=COLORES["fondo"])
        self._lbl_cara_unica = tk.Label(
            cont, text=CARA_UNICA, font=FUENTE_LABEL, cursor="hand2", padx=14, pady=6)
        self._lbl_tiro_retiro = tk.Label(
            cont, text=TIRO_Y_RETIRO, font=FUENTE_LABEL, cursor="hand2", padx=14, pady=6)
        self._lbl_cara_unica.pack(side="left")
        self._lbl_tiro_retiro.pack(side="left", padx=(4, 0))
        self._lbl_cara_unica.bind("<Button-1>", lambda _: self._var_impresion.set(CARA_UNICA))
        self._lbl_tiro_retiro.bind("<Button-1>", lambda _: self._var_impresion.set(TIRO_Y_RETIRO))
        return cont

    def _actualizar_switch_impresion(self, *_):
        activo = self._var_impresion.get()
        for lbl, valor in ((self._lbl_cara_unica, CARA_UNICA), (self._lbl_tiro_retiro, TIRO_Y_RETIRO)):
            if valor == activo:
                lbl.config(bg=COLORES["acento"], fg="#FFFFFF")
            else:
                lbl.config(bg=COLORES["borde"], fg=COLORES["texto_suave"])

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

    def _dibujar_rect(self, alto, ancho, color=None):
        self._canvas.delete("all")
        if color is None:
            color = COLORES["rect_relleno"]
        # Orientar el lado largo como alto del rectángulo
        ad = max(alto, ancho)
        aw = min(alto, ancho)

        rh, rw = (MAX_LADO, MAX_LADO * (aw / ad)) if ad >= aw else (MAX_LADO * (ad / aw), MAX_LADO)

        x1, y1 = MARGEN, MARGEN_SUP
        x2, y2 = x1 + rw, y1 + rh

        self._canvas.create_rectangle(x1, y1, x2, y2,
                                      fill=color,
                                      outline=COLORES["rect_borde"], width=2)
        self._canvas.create_text((x1 + x2) / 2, y1 - 6, text=f"{aw} m",
                                 font=FUENTE_MEDIDA, fill=COLORES["texto"], anchor="s")
        self._canvas.create_text(x1 - 8, (y1 + y2) / 2, text=f"{ad} m",
                                 font=FUENTE_MEDIDA, fill=COLORES["texto"],
                                 anchor="e", angle=90)

    def _siguiente(self):
        self._on_siguiente({
            "producto":    self._var_producto.get().strip(),
            "textil":      self._var_textil.get().strip(),
            "estructura":  self._var_estructura.get().strip() or SIN_ESTRUCTURA,
            "terminacion": self._var_terminacion.get().strip() or SIN_TERMINACIONES,
            "impresion":   self._var_impresion.get(),
            "alto":        float(self._var_alto.get().replace(",", ".")),
            "ancho":       float(self._var_ancho.get().replace(",", ".")),
            "cantidad":    int(self._var_cant.get()),
            "tema":        self._var_tema.get().strip(),
            "obs":         self._var_obs.get().strip(),
        })


# ══════════════════════════════════════════════════════════════════════════════
# Ventana principal — gestiona el flujo completo
# ══════════════════════════════════════════════════════════════════════════════

class CotizacionNueva(tk.Tk):

    # TAM_MEDIDAS crecida para dar espacio a Estructura/Terminación/Impresión
    # (antes 960/1250 de alto).
    TAM_INICIO  = (800, 560)
    TAM_MEDIDAS = (960, 1160)

    def __init__(self, edicion: dict | None = None):
        super().__init__()
        if sys.platform == "darwin":
            self.TAM_INICIO  = (_esc.px(800), _esc.px(730))
            self.TAM_MEDIDAS = (_esc.px(1100), _esc.px(1450))
        else:
            self.TAM_INICIO  = (_esc.px(800), _esc.px(560))
            self.TAM_MEDIDAS = (_esc.px(960), _esc.px(1160))
        self.title("Ingresar Cotización")
        self.configure(bg=COLORES["fondo"])
        # En macOS las fuentes nativas a veces desbordan el alto fijo
        # calculado; se deja redimensionar a mano para asegurar que todo
        # quepa. En Windows/Linux el tamaño fijo ya está afinado.
        self.resizable(sys.platform == "darwin", sys.platform == "darwin")
        _centrar(self, *self.TAM_INICIO)

        from ui.panel_produccion import salir_app
        self.protocol("WM_DELETE_WINDOW", lambda: salir_app())
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

        self._total_productos  = 0
        self._iteracion_actual = 0
        self._desde_resumen    = False
        self._datos: list[dict] = []
        self._nombre_trabajo   = ""
        # edicion = {"json": <dict completo de la cotización>, "productos": [<dict interno>, ...]}
        # No None ⇒ se está editando una cotización ya guardada (viene de Revisar Cotizaciones).
        self._edicion           = edicion

        _construir_cabecera(self, self._volver)

        self._area = tk.Frame(self, bg=COLORES["fondo"])
        self._area.pack(fill="both", expand=True)

        if edicion:
            self._datos            = edicion["productos"]
            self._nombre_trabajo   = edicion["json"].get("Nombre", "")
            self._total_productos  = len(self._datos)
            self._abrir_resumen()
        else:
            PantallaInicio(self._area, subtitulo="Cotizacion nueva",
                           on_confirmar=self._on_inicio_confirmado)

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
        if self._edicion:
            self._guardar_edicion_y_volver()
            return
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

    # ── Modo edición (cotización ya guardada, viene de Revisar Cotizaciones) ──

    def _guardar_edicion_y_volver(self):
        from ui.formulario_cliente import _mapear_producto
        from core.repositorio_cotizaciones import guardar_cotizacion

        json_actualizado = dict(self._edicion["json"])
        json_actualizado["productos"] = [_mapear_producto(d) for d in self._datos]
        guardar_cotizacion(json_actualizado)

        self._volver_a_revisar()

    def _volver_a_revisar(self):
        from ui.interfaz import VentanaPrincipal
        self.destroy()
        root = VentanaPrincipal()
        root.after(0, root._abrir_revisar_cotizaciones)
        root.mainloop()

    def _volver(self, _=None):
        if self._edicion:
            self._volver_a_revisar()
            return
        from ui.interfaz import VentanaPrincipal
        self.destroy()
        VentanaPrincipal().mainloop()
