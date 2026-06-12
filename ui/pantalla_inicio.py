"""
ui/pantalla_inicio.py
Pantalla inicial compartida por el cotizador estándar y el cotizador
backlight: nombre del trabajo y cantidad de productos.
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


class PantallaInicio(tk.Frame):

    def __init__(self, parent, subtitulo, on_confirmar):
        super().__init__(parent, bg=COLORES["fondo"])
        self.pack(fill="both", expand=True)
        self._subtitulo     = subtitulo
        self._on_confirmar  = on_confirmar
        self._btn_habilitado = False
        self._var_nombre   = tk.StringVar()
        self._var_cantidad = tk.StringVar()
        self._var_nombre.trace_add("write",   self._actualizar_btn)
        self._var_cantidad.trace_add("write", self._actualizar_btn)
        self._construir_ui()

    def _construir_ui(self):
        tk.Frame(self, bg=COLORES["fondo"]).pack(fill="both", expand=True)

        cuerpo = tk.Frame(self, bg=COLORES["fondo"], padx=80)
        cuerpo.pack(fill="x")

        tk.Label(cuerpo, text=self._subtitulo,
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
