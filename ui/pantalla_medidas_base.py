"""
ui/pantalla_medidas_base.py
Base compartida para las pantallas de "Medidas" del cotizador estándar y del
cotizador backlight: barra de navegación, sección "Medidas" (inputs + canvas +
botón) y validaciones comunes.

Cada cotizador implementa su propia sección de selección de producto
(`_construir_seccion_superior`) y su lógica de validación, dibujo y avance
(`_actualizar`, `_dibujar_rect`, `_siguiente`), ya que las reglas de negocio
difieren entre flujos.
"""

import tkinter as tk

from ui.estilos import (
    COLORES,
    FUENTE_LABEL,
    FUENTE_MEDIDA,
    FUENTE_AVISO,
    FUENTE_NAV,
    FUENTE_TITULO,
    CANVAS_W,
    CANVAS_H,
    _btn_label,
)


class PantallaMedidasBase(tk.Frame):

    def __init__(self, parent, ventana_raiz, indice, total,
                 datos_previos, datos_todos, on_siguiente, on_nav,
                 con_extras=False, extras_texto="", extras_completo=False):
        super().__init__(parent, bg=COLORES["fondo"])
        self.pack(fill="both", expand=True)

        self._ventana_raiz   = ventana_raiz
        self._indice         = indice
        self._total          = total
        self._datos_todos    = datos_todos
        self._on_siguiente   = on_siguiente
        self._on_nav         = on_nav
        self._btn_habilitado = False
        # "Forzar": checkbox junto al botón Confirmar/Siguiente para
        # permitir medidas que exceden el ancho de la tela (ver _set_btn y
        # el _actualizar de cada cotizador). Reemplaza al viejo botón
        # "Omitir restricción ⚠" que solo aparecía condicionalmente.
        self._var_forzar = tk.BooleanVar(value=False)
        # Despacho/Instalación (opcionales, ver ui/pantalla_extras.py): se
        # representan como UN cuadrado más en la barra de navegación (con
        # índice `total`, uno más allá del último producto real — así
        # on_nav(total) es un valor centinela inequívoco para "ir a
        # despacho/instalación" sin necesitar un callback aparte), visible
        # si al menos uno de los dos está activo. `extras_texto` es lo que
        # muestra el cuadrado ("D", "I" o "D/I" según cuál esté activo —
        # decidido por el cotizador, no acá).
        self._con_extras      = con_extras
        self._extras_texto    = extras_texto
        self._extras_completo = extras_completo
        self._nav_cuadro_extras = None

        if datos_previos:
            alto_ini  = str(datos_previos["alto"])
            ancho_ini = str(datos_previos["ancho"])
            cant_ini  = str(datos_previos["cantidad"])
            tema_ini  = datos_previos.get("tema", "")
            obs_ini   = datos_previos.get("obs", "")
        else:
            alto_ini = ancho_ini = cant_ini = tema_ini = obs_ini = ""

        self._var_alto  = tk.StringVar(value=alto_ini)
        self._var_ancho = tk.StringVar(value=ancho_ini)
        self._var_cant  = tk.StringVar(value=cant_ini)
        self._var_tema  = tk.StringVar(value=tema_ini)
        self._var_obs   = tk.StringVar(value=obs_ini)

    def _enter_sig(self):
        if self._btn_habilitado:
            self._siguiente()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _construir_ui(self):
        # ── Barra de navegación ───────────────────────────────────────────────
        nav = tk.Frame(self, bg=COLORES["fondo"], pady=8)
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

        if self._con_extras:
            ce = tk.Label(nav, text=self._extras_texto, font=FUENTE_NAV,
                          width=3, pady=4, relief="flat", cursor="hand2")
            ce.pack(side="left", padx=(10, 3))
            ce.bind("<Button-1>", lambda _: self._on_nav(self._total))
            self._nav_cuadro_extras = ce

        self._actualizar_nav()

        tk.Frame(self, bg=COLORES["borde"], height=1).pack(fill="x", padx=30)

        # ── Sección superior: específica de cada flujo ────────────────────────
        sup = tk.Frame(self, bg=COLORES["fondo"], padx=40, pady=10)
        sup.pack(fill="x")
        self._construir_seccion_superior(sup)

        # ── Sección inferior: medidas + canvas ────────────────────────────────
        inf = tk.Frame(self, bg=COLORES["fondo"], padx=40, pady=10)
        inf.pack(fill="both", expand=True)

        tk.Label(inf, text="Medidas", font=FUENTE_TITULO,
                 bg=COLORES["fondo"], fg=COLORES["texto"]).pack(anchor="w", pady=(0, 8))

        col_izq = tk.Frame(inf, bg=COLORES["fondo"])
        col_izq.pack(side="left", anchor="n")

        fila_inp = tk.Frame(col_izq, bg=COLORES["fondo"])
        fila_inp.pack(anchor="w")
        self._crear_input(fila_inp, "Ancho (m)", self._var_ancho).pack(side="left", padx=(0, 16))
        self._crear_input(fila_inp, "Alto (m)",  self._var_alto).pack(side="left", padx=(0, 16))
        self._crear_input(fila_inp, "Cantidad",  self._var_cant).pack(side="left")

        fila_tema = tk.Frame(col_izq, bg=COLORES["fondo"])
        fila_tema.pack(anchor="w", pady=(8, 0))
        tk.Label(fila_tema, text="Tema", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Entry(fila_tema, textvariable=self._var_tema,
                 font=FUENTE_MEDIDA, width=28,
                 relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                 insertbackground=COLORES["texto"], highlightthickness=1,
                 highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"]).pack(anchor="w", ipady=6, ipadx=6)

        fila_obs = tk.Frame(col_izq, bg=COLORES["fondo"])
        fila_obs.pack(anchor="w", pady=(8, 0))
        tk.Label(fila_obs, text="Obs", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Entry(fila_obs, textvariable=self._var_obs,
                 font=FUENTE_MEDIDA, width=28,
                 relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                 insertbackground=COLORES["texto"], highlightthickness=1,
                 highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"]).pack(anchor="w", ipady=6, ipadx=6)

        self._lbl_rotacion = tk.Label(col_izq, text="", font=FUENTE_AVISO,
                                      bg=COLORES["fondo"], fg=COLORES["texto_suave"])
        self._lbl_rotacion.pack(anchor="w", pady=(6, 0))

        self._lbl_error = tk.Label(col_izq, text="", font=FUENTE_AVISO,
                                   bg=COLORES["fondo"], fg=COLORES["error"],
                                   wraplength=500, justify="left")
        self._lbl_error.pack(anchor="w", pady=(4, 0))

        # Canvas a la derecha — anclado arriba (como col_izq), no centrado
        # verticalmente en "inf": con "inf" alto (pantallas con muchos
        # campos arriba), centrarlo lo empujaba hacia abajo y quedaba
        # tapado por el botón de Confirmar/Siguiente, que está anclado al
        # borde inferior de la ventana entera.
        self._canvas = tk.Canvas(inf, width=CANVAS_W, height=CANVAS_H,
                                 bg=COLORES["fondo"], highlightthickness=0)
        self._canvas.pack(side="right", anchor="n", padx=(0, 10))

        # Botón siguiente — sobre self (este Frame), no sobre ventana_raiz:
        # este Frame ya ocupa toda la ventana (fill="both", expand=True,
        # sin nada más compitiendo por espacio), así que el resultado visual
        # es idéntico, pero al destruirse este Frame (_limpiar() en el
        # cotizador, al cambiar de pantalla) el botón se destruye con él.
        # Puesto directo en ventana_raiz, quedaba huérfano en cada cambio de
        # pantalla — invisible mientras la siguiente pantalla lo tapaba en
        # el mismo píxel, pero visible si el tamaño de ventana cambiaba (ej.
        # al pasar a la pantalla de Despacho/Instalación, más chica). El checkbox
        # "Forzar" y el botón van juntos en un mismo contenedor (en vez de
        # cada uno con su propio .place()) para que "a la izquierda del
        # botón" se mantenga sin importar el ancho del texto del botón
        # ("Confirmar ✓" vs "Siguiente →").
        barra_inferior = tk.Frame(self, bg=COLORES["fondo"])
        barra_inferior.place(relx=1.0, rely=1.0, anchor="se", x=-30, y=-20)

        self._construir_checkbox_forzar(barra_inferior)

        es_ultimo = (self._indice == self._total - 1)
        self._btn_sig = _btn_label(
            barra_inferior,
            "Confirmar ✓" if es_ultimo else "Siguiente →"
        )
        self._btn_sig.pack(side="left", padx=(16, 0))

    def _construir_checkbox_forzar(self, parent):
        """Checkbox custom "Forzar" — permite confirmar un producto con
        medidas que exceden el ancho de la tela (ver _set_btn y el
        _actualizar de cada cotizador). Mismo patrón visual que el
        checkbox de despacho en ui/pantalla_inicio.py."""
        fila = tk.Frame(parent, bg=COLORES["fondo"])
        fila.pack(side="left")

        caja = tk.Frame(fila, width=24, height=24, bg="#FFFFFF",
                         highlightthickness=2, highlightbackground=COLORES["borde"],
                         cursor="hand2")
        caja.pack_propagate(False)
        caja.pack(side="left")
        marca = tk.Label(caja, text="✓", font=(FUENTE_LABEL[0], 13, "bold"),
                          bg="#FFFFFF", fg="#FFFFFF", cursor="hand2")
        marca.place(relx=0.5, rely=0.5, anchor="center")

        texto = tk.Label(fila, text="Forzar", font=FUENTE_LABEL,
                          bg=COLORES["fondo"], fg=COLORES["texto"], cursor="hand2")
        texto.pack(side="left", padx=(6, 0))

        def _refrescar(*_):
            if self._var_forzar.get():
                caja.config(bg=COLORES["secundario"], highlightbackground=COLORES["secundario"])
                marca.config(bg=COLORES["secundario"], fg="#FFFFFF")
            else:
                caja.config(bg="#FFFFFF", highlightbackground=COLORES["borde"])
                marca.config(bg="#FFFFFF", fg="#FFFFFF")

        def _toggle(_e=None):
            self._var_forzar.set(not self._var_forzar.get())

        for w in (caja, marca, texto):
            w.bind("<Button-1>", _toggle)

        self._var_forzar.trace_add("write", _refrescar)
        _refrescar()

    def _crear_lbl_ancho_tela(self, sup):
        """Label de aviso del ancho máximo de impresión, común a ambos flujos."""
        self._lbl_ancho_tela = tk.Label(sup, text="", font=FUENTE_AVISO,
                                        bg=COLORES["fondo"], fg=COLORES["texto_suave"])
        self._lbl_ancho_tela.pack(anchor="w", pady=(6, 0))

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
        if self._nav_cuadro_extras:
            color = COLORES["nav_completo"] if self._extras_completo else COLORES["nav_inactivo"]
            self._nav_cuadro_extras.config(bg=color, fg="#FFFFFF")

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

    def _dibujar_vacio(self):
        self._canvas.delete("all")
        self._canvas.create_text(CANVAS_W // 2, CANVAS_H // 2,
                                 text="Ingresa medidas para\nver la proporción",
                                 font=FUENTE_LABEL, fill=COLORES["borde"],
                                 justify="center")

    # ── Botón ─────────────────────────────────────────────────────────────────
    def _set_btn(self, habilitado: bool, forzado: bool = False):
        """`forzado`=True (medidas excedentes + checkbox "Forzar" marcado)
        pinta el botón amarillo en vez del azul normal, para que quede
        claro que se está confirmando algo fuera de lo normal."""
        self._btn_habilitado = habilitado
        if habilitado and forzado:
            color_base, color_hover = COLORES["secundario"], "#C8881A"
            self._btn_sig.config(bg=color_base, cursor="hand2")
            self._btn_sig.bind("<Button-1>", lambda _: self._siguiente())
            self._btn_sig.bind("<Enter>", lambda _: self._btn_sig.config(bg=color_hover))
            self._btn_sig.bind("<Leave>", lambda _: self._btn_sig.config(bg=color_base))
        elif habilitado:
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
