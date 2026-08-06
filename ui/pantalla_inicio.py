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
        self._var_despacho    = tk.BooleanVar(value=False)
        self._var_instalacion = tk.BooleanVar(value=False)
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

        # Cantidad de productos + Despacho van en la misma fila (el
        # checkbox a la derecha, para no gastar una fila entera de alto).
        fila_cantidad = tk.Frame(cuerpo, bg=COLORES["fondo"])
        fila_cantidad.pack(anchor="w")

        col_cantidad = tk.Frame(fila_cantidad, bg=COLORES["fondo"])
        col_cantidad.pack(side="left")
        tk.Label(col_cantidad, text="Cantidad de productos",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        vcmd = (self.register(self._validar), "%P")
        tk.Entry(col_cantidad, textvariable=self._var_cantidad,
                 validate="key", validatecommand=vcmd,
                 font=FUENTE_MEDIDA, width=8,
                 relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                 insertbackground=COLORES["texto"],
                 highlightthickness=1, highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"]).pack(anchor="w", ipady=8, ipadx=8)

        # Despacho / Instalación: todavía no se generan guías de despacho
        # ni se detalla la instalación, pero igual hay que poder
        # cobrarlas — si se marca alguna, después de cargar todos los
        # productos se pide su valor (una sola ventana para ambas, ver
        # ui/pantalla_extras.py) antes del resumen.
        # Checkbox custom (no tk.Checkbutton nativo — el indicador nativo
        # queda minúsculo sin importar la fuente): un Frame de tamaño fijo
        # en píxeles como "caja", con una ✓ que se muestra/oculta encima.
        col_despacho = tk.Frame(fila_cantidad, bg=COLORES["fondo"])
        col_despacho.pack(side="left", padx=(16, 0))
        # Label vacía de la misma fuente que "Cantidad de productos", para
        # que el checkbox quede alineado con el campo, no con su etiqueta.
        tk.Label(col_despacho, text="", font=FUENTE_LABEL,
                 bg=COLORES["fondo"]).pack(anchor="w")
        self._construir_checkbox(col_despacho, self._var_despacho, "Despacho")

        col_instalacion = tk.Frame(fila_cantidad, bg=COLORES["fondo"])
        col_instalacion.pack(side="left", padx=(12, 0))
        tk.Label(col_instalacion, text="", font=FUENTE_LABEL,
                 bg=COLORES["fondo"]).pack(anchor="w")
        self._construir_checkbox(col_instalacion, self._var_instalacion, "Instalación")

        self._btn = _btn_label(cuerpo, "Comenzar →")
        self._btn.pack(anchor="e", pady=(20, 0))

        tk.Frame(self, bg=COLORES["fondo"]).pack(fill="both", expand=True)

        self.winfo_toplevel().bind("<Return>", lambda _: self._confirmar())

    def _construir_checkbox(self, parent, variable, texto_label):
        fila = tk.Frame(parent, bg=COLORES["fondo"])
        fila.pack(anchor="w")

        caja = tk.Frame(fila, width=28, height=28, bg="#FFFFFF",
                         highlightthickness=2, highlightbackground=COLORES["borde"],
                         cursor="hand2")
        caja.pack_propagate(False)
        caja.pack(side="left")
        marca = tk.Label(caja, text="✓", font=(FUENTE_LABEL[0], 15, "bold"),
                          bg="#FFFFFF", fg="#FFFFFF", cursor="hand2")
        marca.place(relx=0.5, rely=0.5, anchor="center")

        texto = tk.Label(fila, text=texto_label, font=FUENTE_LABEL,
                          bg=COLORES["fondo"], fg=COLORES["texto"], cursor="hand2")
        texto.pack(side="left", padx=(10, 0))

        def _refrescar(*_):
            if variable.get():
                caja.config(bg=COLORES["acento"], highlightbackground=COLORES["acento"])
                marca.config(bg=COLORES["acento"], fg="#FFFFFF")
            else:
                caja.config(bg="#FFFFFF", highlightbackground=COLORES["borde"])
                marca.config(bg="#FFFFFF", fg="#FFFFFF")

        def _toggle(_e=None):
            variable.set(not variable.get())

        for w in (caja, marca, texto):
            w.bind("<Button-1>", _toggle)

        variable.trace_add("write", _refrescar)
        _refrescar()

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
                self._on_confirmar(cantidad, nombre,
                                    self._var_despacho.get(), self._var_instalacion.get())
        except ValueError:
            pass
