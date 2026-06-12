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
    )
"""

import tkinter as tk

from ui.cotizador_backlight import (
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
                 on_cerrar):
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

        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        _construir_cabecera(self, lambda _: self._cerrar())

        filas_extra = max(0, len(filas) - 2)
        alto = self._ALTO_BASE + filas_extra * self._ALTO_POR_FILA
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

        # Fila de totales — fila N+1
        tot_row = len(self._filas) + 1
        for col, val in enumerate(self._totales):
            tk.Label(tabla, text=val, font=FUENTE_TOTAL,
                     bg=COLORES["tabla_total"], fg=COLORES["acento"],
                     anchor="w", padx=8, pady=8
                     ).grid(row=tot_row, column=col, sticky="ew")

        # ── Botón confirmar ───────────────────────────────────────────────────
        btn_conf = _btn_label(self, "Confirmar ✓", habilitado=True)
        btn_conf.place(relx=1.0, rely=1.0, anchor="se", x=-30, y=-20)
        btn_conf.bind("<Button-1>", lambda _: self._confirmar())
        btn_conf.bind("<Enter>", lambda _: btn_conf.config(bg=COLORES["btn_en_hover"]))
        btn_conf.bind("<Leave>", lambda _: btn_conf.config(bg=COLORES["btn_enabled"]))

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _confirmar(self):
        self.destroy()
        self._on_confirmar()

    def _cerrar(self):
        self.destroy()
        self._on_cerrar()
