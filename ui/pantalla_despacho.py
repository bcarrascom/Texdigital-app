"""
ui/pantalla_despacho.py
Pantalla para ingresar el valor del despacho — compartida por el cotizador
estándar y el cotizador backlight. Se muestra después de cargar todos los
productos (y desde el cuadrado "D" de la barra de navegación, o desde la
fila "Despacho" del resumen) solo si el usuario marcó "Tiene despacho" en
la pantalla inicial. Todavía no se generan guías de despacho, pero el
despacho igual se cobra — este valor se suma al total de la cotización.
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


class PantallaDespacho(tk.Frame):

    def __init__(self, parent, subtitulo, valor_inicial, on_confirmar):
        super().__init__(parent, bg=COLORES["fondo"])
        self.pack(fill="both", expand=True)
        self._subtitulo    = subtitulo
        self._on_confirmar = on_confirmar
        self._btn_habilitado = False
        self._var_valor = tk.StringVar(
            value=formatear_clp(valor_inicial) if valor_inicial is not None else "")
        self._var_valor.trace_add("write", self._actualizar_btn)
        self._construir_ui()

    def _construir_ui(self):
        tk.Frame(self, bg=COLORES["fondo"]).pack(fill="both", expand=True)

        cuerpo = tk.Frame(self, bg=COLORES["fondo"], padx=80)
        cuerpo.pack(fill="x")

        tk.Label(cuerpo, text=self._subtitulo,
                 font=FUENTE_SUBTITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Label(cuerpo, text="Despacho",
                 font=FUENTE_TITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto"], justify="left").pack(anchor="w", pady=(6, 16))

        tk.Label(cuerpo, text="Valor del despacho",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Entry(cuerpo, textvariable=self._var_valor,
                 font=FUENTE_MEDIDA, width=18,
                 relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                 insertbackground=COLORES["texto"],
                 highlightthickness=1, highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"],
                 ).pack(anchor="w", ipady=8, ipadx=8)

        self._btn = _btn_label(cuerpo, "Confirmar ✓")
        self._btn.pack(anchor="e", pady=(20, 0))

        tk.Frame(self, bg=COLORES["fondo"]).pack(fill="both", expand=True)

        self.winfo_toplevel().bind("<Return>", lambda _: self._confirmar())
        self._actualizar_btn()

    def _valor_parseado(self):
        return parsear_valor_manual(self._var_valor.get())

    def _actualizar_btn(self, *_):
        ok = self._valor_parseado() is not None
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
        valor = self._valor_parseado()
        if valor is not None:
            self.winfo_toplevel().unbind("<Return>")
            self._on_confirmar(valor)
