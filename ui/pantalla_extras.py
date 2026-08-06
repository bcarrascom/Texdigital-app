"""
ui/pantalla_extras.py
Pantalla para ingresar el valor del despacho y/o la instalación —
compartida por el cotizador estándar y el cotizador backlight. Se
muestra después de cargar todos los productos (y desde el cuadrado de la
barra de navegación, o al reabrir desde el resumen) solo si el usuario
marcó "Tiene despacho" y/o "Tiene instalación" en la pantalla inicial —
muestra solo el/los campo(s) que corresponda, en una sola ventana.
Todavía no se generan guías de despacho ni se detalla la instalación,
pero ambas se cobran igual — estos valores se suman al total de la
cotización.
"""

import tkinter as tk

from ui.estilos import (
    COLORES,
    FUENTE_SUBTITULO,
    FUENTE_TITULO,
    FUENTE_LABEL,
    FUENTE_MEDIDA,
    _btn_label,
)
from core.precios import parsear_valor_manual, formatear_clp


class PantallaExtras(tk.Frame):

    def __init__(self, parent, subtitulo,
                 mostrar_despacho, valor_despacho_inicial,
                 mostrar_instalacion, valor_instalacion_inicial,
                 on_confirmar):
        super().__init__(parent, bg=COLORES["fondo"])
        self.pack(fill="both", expand=True)
        self._subtitulo           = subtitulo
        self._mostrar_despacho    = mostrar_despacho
        self._mostrar_instalacion = mostrar_instalacion
        self._on_confirmar        = on_confirmar
        self._btn_habilitado      = False

        self._var_despacho = tk.StringVar(
            value=formatear_clp(valor_despacho_inicial) if valor_despacho_inicial is not None else "")
        self._var_instalacion = tk.StringVar(
            value=formatear_clp(valor_instalacion_inicial) if valor_instalacion_inicial is not None else "")
        self._var_despacho.trace_add("write",    self._actualizar_btn)
        self._var_instalacion.trace_add("write", self._actualizar_btn)
        self._construir_ui()

    def _titulo(self):
        if self._mostrar_despacho and self._mostrar_instalacion:
            return "Despacho e instalación"
        return "Despacho" if self._mostrar_despacho else "Instalación"

    def _construir_ui(self):
        tk.Frame(self, bg=COLORES["fondo"]).pack(fill="both", expand=True)

        cuerpo = tk.Frame(self, bg=COLORES["fondo"], padx=80)
        cuerpo.pack(fill="x")

        tk.Label(cuerpo, text=self._subtitulo,
                 font=FUENTE_SUBTITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Label(cuerpo, text=self._titulo(),
                 font=FUENTE_TITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto"], justify="left").pack(anchor="w", pady=(6, 16))

        if self._mostrar_despacho:
            self._crear_campo(cuerpo, "Valor del despacho", self._var_despacho)
        if self._mostrar_instalacion:
            self._crear_campo(cuerpo, "Valor de la instalación", self._var_instalacion)

        self._btn = _btn_label(cuerpo, "Confirmar ✓")
        self._btn.pack(anchor="e", pady=(20, 0))

        tk.Frame(self, bg=COLORES["fondo"]).pack(fill="both", expand=True)

        self.winfo_toplevel().bind("<Return>", lambda _: self._confirmar())
        self._actualizar_btn()

    def _crear_campo(self, parent, etiqueta, variable):
        tk.Label(parent, text=etiqueta, font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Entry(parent, textvariable=variable,
                 font=FUENTE_MEDIDA, width=18,
                 relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                 insertbackground=COLORES["texto"],
                 highlightthickness=1, highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"],
                 ).pack(anchor="w", ipady=8, ipadx=8, pady=(0, 12))

    def _valor(self, variable):
        return parsear_valor_manual(variable.get())

    def _actualizar_btn(self, *_):
        ok = True
        if self._mostrar_despacho and self._valor(self._var_despacho) is None:
            ok = False
        if self._mostrar_instalacion and self._valor(self._var_instalacion) is None:
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
        if not self._btn_habilitado:
            return
        valor_despacho    = self._valor(self._var_despacho) if self._mostrar_despacho else None
        valor_instalacion = self._valor(self._var_instalacion) if self._mostrar_instalacion else None
        self.winfo_toplevel().unbind("<Return>")
        self._on_confirmar(valor_despacho, valor_instalacion)
