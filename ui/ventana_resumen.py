"""
ui/ventana_resumen.py
Ventana de resumen compartida por el cotizador estándar y el cotizador backlight.

Uso:
    VentanaResumen(
        ancho_ventana = <int px>,
        columnas      = ["#", "Producto", ...],
        col_w         = [35, 140, ...],
        filas         = [["1", "Lona", ...], ...],   # datos ya formateados
        totales       = ["", "TOTAL", "", "5", ...],
        titulo        = "Resumen — Cotizacion nueva",
        subtitulo     = "Cotizacion nueva",
        nombre_trabajo= "Trabajo XYZ",
        on_editar     = lambda idx: ...,
        on_confirmar  = lambda: ...,
        on_cerrar     = lambda: ...,
        on_agregar    = lambda: ...,       # opcional — si se pasa, aparece "+ Agregar producto"
        on_eliminar   = lambda idx: ...,   # opcional — si se pasa, aparece un ✕ por fila (con confirmación)
    )
"""

import tkinter as tk

from ui.estilos import (
    COLORES,
    FUENTE_CABECERA,
    FUENTE_SUBTITULO,
    FUENTE_LABEL,
    FUENTE_TABLA_CAB,
    FUENTE_TABLA,
    FUENTE_TOTAL,
    _construir_cabecera,
    _centrar,
    _btn_label,
)
from core import escala as _esc


class VentanaResumen(tk.Toplevel):
    """
    Ventana de resumen genérica para cualquier cotizador.

    Parámetros
    ----------
    ancho_ventana   Ancho de la ventana en píxeles.
    columnas        Lista de encabezados de columna.
    col_w           Lista de anchos de columna en píxeles (misma longitud que columnas).
    filas           Lista de filas de datos; cada fila es una lista[str] con el
                    mismo número de elementos que columnas.
    totales         Fila de totales: lista[str] con el mismo largo que columnas.
    titulo          Título de la ventana (barra de título del SO).
    subtitulo       Texto pequeño que aparece sobre el nombre del trabajo.
    nombre_trabajo  Nombre del trabajo a mostrar en grande.
    on_editar       Callback(idx: int) — se llama al hacer clic en una fila de datos.
    on_confirmar    Callback() — se llama al presionar "Confirmar".
    on_cerrar       Callback() — se llama al cerrar sin confirmar.
    on_agregar      Callback() opcional — si se pasa, aparece el botón
                    "+ Agregar producto". Se llama tras destruir esta ventana
                    (mismo patrón que on_editar).
    on_eliminar     Callback(idx: int) opcional — si se pasa, cada fila
                    muestra un ✕ que pide confirmación antes de llamar a
                    esto (también tras destruir esta ventana). No se puede
                    eliminar si solo queda 1 producto.
    filas_extra     list[list[str]] opcional (cada una del mismo largo que
                    columnas) — filas extra de solo lectura entre los datos
                    y el total (ej. "Despacho" y/o "Instalación" + su
                    monto). No son clickeables ni tienen ✕ — para editarlas
                    hay que entrar por cualquier producto y usar el
                    cuadrado de la barra de navegación (ver
                    ui/pantalla_medidas_base.py).
    """

    _ALTO_BASE     = _esc.px(600)
    _ALTO_POR_FILA = _esc.px(36)

    def __init__(self,
                 ancho_ventana: int,
                 columnas: list,
                 col_w: list,
                 filas: list,
                 totales: list,
                 titulo: str,
                 subtitulo: str,
                 nombre_trabajo: str,
                 on_editar,
                 on_confirmar,
                 on_cerrar,
                 on_agregar=None,
                 on_eliminar=None,
                 filas_extra=None):
        super().__init__()
        self.title(titulo)
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)

        self._columnas       = columnas
        self._col_w          = col_w
        self._filas          = filas
        self._totales        = totales
        self._subtitulo      = subtitulo
        self._nombre_trabajo = nombre_trabajo
        self._on_editar      = on_editar
        self._on_confirmar   = on_confirmar
        self._on_cerrar      = on_cerrar
        self._on_agregar     = on_agregar
        self._on_eliminar    = on_eliminar
        self._filas_extra    = filas_extra or []

        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        _construir_cabecera(self, lambda _: self._cerrar())

        n_filas_extra = max(0, len(filas) - 2) + len(self._filas_extra)
        alto = self._ALTO_BASE + n_filas_extra * self._ALTO_POR_FILA
        _centrar(self, ancho_ventana, alto)

        self.lift()
        self.focus_force()
        self._construir_ui()
        self.bind("<Return>", lambda _: self._confirmar())

    # ── UI ────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        cuerpo = tk.Frame(self, bg=COLORES["fondo"], padx=40, pady=24)
        cuerpo.pack(fill="both", expand=True)

        tk.Label(cuerpo, text=self._subtitulo,
                 font=FUENTE_SUBTITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")

        tk.Label(cuerpo, text=self._nombre_trabajo,
                 font=FUENTE_CABECERA, bg=COLORES["fondo"],
                 fg=COLORES["acento"]).pack(anchor="w", pady=(0, 10))

        tk.Label(cuerpo, text="Haz clic en una fila para editarla.",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w", pady=(0, 12))

        # ── Tabla ─────────────────────────────────────────────────────────────
        # Un único frame con grid compartido garantiza que todas las filas
        # (cabecera, datos, totales) usen exactamente los mismos anchos de columna.
        tabla = tk.Frame(cuerpo, bg=COLORES["fondo"])
        tabla.pack(fill="x")

        col_w = self._col_w
        for col, w in enumerate(col_w):
            tabla.columnconfigure(col, minsize=w, weight=w)
        # Columna extra para el ✕ de eliminar — no forma parte del esquema
        # que pasa cada cotizador (columnas/col_w/filas/totales), así no
        # hay que tocar ui/cotizacion.py ni ui/cotizador_backlight.py más
        # que para pasar el callback.
        col_elim = len(col_w)
        if self._on_eliminar:
            tabla.columnconfigure(col_elim, minsize=_esc.px(52), weight=0)

        # Cabecera — fila 0
        for col, (txt, w) in enumerate(zip(self._columnas, col_w)):
            tk.Label(tabla, text=txt, font=FUENTE_TABLA_CAB,
                     bg=COLORES["tabla_cab"], fg="#FFFFFF",
                     anchor="w", padx=8, pady=6
                     ).grid(row=0, column=col, sticky="ew")

        # Filas de datos — filas 1..N
        for i, fila in enumerate(self._filas):
            bg  = COLORES["tabla_fila1"] if i % 2 == 0 else COLORES["tabla_fila2"]
            row = i + 1
            labels = []

            for col, val in enumerate(fila):
                lbl = tk.Label(tabla, text=val, font=FUENTE_TABLA,
                               bg=bg, fg=COLORES["texto"],
                               anchor="w", padx=8, pady=6)
                lbl.grid(row=row, column=col, sticky="ew")
                labels.append(lbl)

            def _on_enter(_, ls=labels):
                for l in ls: l.config(bg=COLORES["hover_fila"])

            def _on_leave(_, ls=labels, b=bg):
                for l in ls: l.config(bg=b)

            def _on_click(_, idx=i):
                self.destroy()
                self._on_editar(idx)

            for lbl in labels:
                lbl.bind("<Enter>",    _on_enter)
                lbl.bind("<Leave>",    _on_leave)
                lbl.bind("<Button-1>", _on_click)

            # ✕ de eliminar — widget aparte, no entra en `labels` (que
            # editan la fila), así el click no se confunde con "editar".
            # Cuadrado relleno rojo con la X blanca en negrita — no intenta
            # calzar con el color de la fila (par/impar), así siempre se ve
            # clarito incluso en un espacio angosto.
            if self._on_eliminar:
                btn_x = tk.Label(tabla, text="✕",
                                 font=(FUENTE_TABLA[0], FUENTE_TABLA[1], "bold"),
                                 bg=COLORES["error"], fg="#FFFFFF", cursor="hand2",
                                 anchor="center", width=2, pady=6)
                # Sin pady acá en el grid — el pady=6 ya está en el Label;
                # duplicarlo hacía esta fila más alta que el resto (el
                # "espaciado irregular" entre filas con ✕ y sin él).
                btn_x.grid(row=row, column=col_elim, padx=6)
                btn_x.bind("<Enter>", lambda _, w=btn_x: w.config(bg="#E74C3C"))
                btn_x.bind("<Leave>", lambda _, w=btn_x: w.config(bg=COLORES["error"]))
                btn_x.bind("<Button-1>", lambda _, idx=i: self._confirmar_eliminar(idx))

        # Filas extra (Despacho / Instalación, opcionales) — entre los
        # datos y el total, de solo lectura: no tienen hover, no son
        # clickeables, no tienen ✕.
        siguiente_fila = len(self._filas) + 1
        for fila_extra in self._filas_extra:
            for col, val in enumerate(fila_extra):
                tk.Label(tabla, text=val, font=FUENTE_TABLA_CAB,
                         bg=COLORES["tabla_fila2"], fg=COLORES["texto"],
                         anchor="w", padx=8, pady=6
                         ).grid(row=siguiente_fila, column=col, sticky="ew")
            siguiente_fila += 1

        # Fila de totales
        tot_row = siguiente_fila
        for col, val in enumerate(self._totales):
            tk.Label(tabla, text=val, font=FUENTE_TOTAL,
                     bg=COLORES["tabla_total"], fg=COLORES["acento"],
                     anchor="w", padx=8, pady=8
                     ).grid(row=tot_row, column=col, sticky="ew")

        # ── Botón "+ Agregar producto" (abajo a la izquierda) ─────────────────
        if self._on_agregar:
            btn_agregar = tk.Label(
                self, text="+ Agregar producto", font=FUENTE_LABEL,
                bg=COLORES["borde"], fg=COLORES["texto"],
                padx=16, pady=10, cursor="hand2",
            )
            btn_agregar.place(relx=0.0, rely=1.0, anchor="sw", x=40, y=-20)
            btn_agregar.bind("<Button-1>", lambda _: self._agregar())
            btn_agregar.bind("<Enter>", lambda _: btn_agregar.config(bg="#C0BCBA"))
            btn_agregar.bind("<Leave>", lambda _: btn_agregar.config(bg=COLORES["borde"]))

        # ── Botón confirmar ───────────────────────────────────────────────────
        btn_conf = _btn_label(self, "Confirmar ✓", habilitado=True)
        btn_conf.place(relx=1.0, rely=1.0, anchor="se", x=-30, y=-20)
        btn_conf.bind("<Button-1>", lambda _: self._confirmar())
        btn_conf.bind("<Enter>", lambda _: btn_conf.config(bg=COLORES["btn_en_hover"]))
        btn_conf.bind("<Leave>", lambda _: btn_conf.config(bg=COLORES["btn_enabled"]))

    # ── Eliminar (con confirmación) ─────────────────────────────────────────────

    def _confirmar_eliminar(self, idx: int):
        if len(self._filas) <= 1:
            self._mostrar_aviso("La cotización debe tener al menos un producto.")
            return

        fila = self._filas[idx]
        nombre_prod = fila[1] if len(fila) > 1 else ""

        dlg = tk.Toplevel(self)
        dlg.title("Confirmar eliminación")
        dlg.configure(bg=COLORES["fondo"])
        dlg.resizable(False, False)
        dlg.transient(self)

        ancho, alto = _esc.px(624), _esc.px(350)
        ox = self.winfo_x() + (self.winfo_width()  - ancho) // 2
        oy = self.winfo_y() + (self.winfo_height() - alto)  // 2
        dlg.geometry(f"{ancho}x{alto}+{ox}+{oy}")
        dlg.grab_set()

        frame_btns = tk.Frame(dlg, bg=COLORES["fondo"])
        frame_btns.pack(side="bottom", fill="x", padx=24, pady=(0, 18))

        frame_msg = tk.Frame(dlg, bg=COLORES["fondo"], padx=24, pady=18)
        frame_msg.pack(fill="both", expand=True)

        tk.Label(frame_msg, text=f"¿Eliminar el producto {idx + 1}?",
                 font=FUENTE_CABECERA, bg=COLORES["fondo"], fg=COLORES["texto"],
                 wraplength=_esc.px(408), justify="center").pack()
        if nombre_prod:
            tk.Label(frame_msg, text=nombre_prod,
                     font=FUENTE_LABEL, bg=COLORES["fondo"], fg=COLORES["texto_suave"],
                     wraplength=_esc.px(408), justify="center").pack(pady=(4, 0))
        tk.Label(frame_msg, text="Esta acción no se puede deshacer.",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(pady=(10, 0))

        def _cancelar(_e=None):
            dlg.grab_release()
            dlg.destroy()

        def _confirmar(_e=None):
            dlg.grab_release()
            dlg.destroy()
            self.destroy()
            self._on_eliminar(idx)

        btn_cancelar = tk.Label(
            frame_btns, text="Cancelar", font=FUENTE_LABEL,
            bg=COLORES["borde"], fg=COLORES["texto"],
            padx=19, pady=10, cursor="hand2",
        )
        btn_cancelar.pack(side="left")
        btn_cancelar.bind("<Button-1>", _cancelar)
        btn_cancelar.bind("<Enter>", lambda _: btn_cancelar.config(bg="#C0BCBA"))
        btn_cancelar.bind("<Leave>", lambda _: btn_cancelar.config(bg=COLORES["borde"]))

        btn_confirmar = tk.Label(
            frame_btns, text="Eliminar", font=FUENTE_LABEL,
            bg=COLORES["error"], fg="#FFFFFF",
            padx=19, pady=10, cursor="hand2",
        )
        btn_confirmar.pack(side="right")
        btn_confirmar.bind("<Button-1>", _confirmar)
        btn_confirmar.bind("<Enter>", lambda _: btn_confirmar.config(bg="#E74C3C"))
        btn_confirmar.bind("<Leave>", lambda _: btn_confirmar.config(bg=COLORES["error"]))

        dlg.bind("<Return>", _confirmar)
        dlg.bind("<Escape>", _cancelar)
        dlg.focus_force()
        dlg.wait_window()

    def _mostrar_aviso(self, texto: str):
        dlg = tk.Toplevel(self)
        dlg.title("Aviso")
        dlg.configure(bg=COLORES["fondo"])
        dlg.resizable(False, False)
        dlg.transient(self)

        ancho, alto = _esc.px(420), _esc.px(160)
        ox = self.winfo_x() + (self.winfo_width()  - ancho) // 2
        oy = self.winfo_y() + (self.winfo_height() - alto)  // 2
        dlg.geometry(f"{ancho}x{alto}+{ox}+{oy}")
        dlg.grab_set()

        tk.Label(dlg, text=texto, font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto"], wraplength=_esc.px(360),
                 justify="center").pack(expand=True, padx=24, pady=(24, 8))

        btn_ok = tk.Label(dlg, text="Entendido", font=FUENTE_LABEL,
                           bg=COLORES["borde"], fg=COLORES["texto"],
                           padx=19, pady=8, cursor="hand2")
        btn_ok.pack(pady=(0, 18))
        btn_ok.bind("<Button-1>", lambda _: (dlg.grab_release(), dlg.destroy()))

        dlg.bind("<Return>", lambda _: (dlg.grab_release(), dlg.destroy()))
        dlg.focus_force()
        dlg.wait_window()

    def _agregar(self):
        self.destroy()
        self._on_agregar()

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _confirmar(self):
        self.destroy()
        self._on_confirmar()

    def _cerrar(self):
        self.destroy()
        self._on_cerrar()
