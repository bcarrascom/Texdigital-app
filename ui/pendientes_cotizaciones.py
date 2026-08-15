"""
ui/pendientes_cotizaciones.py
Ventana que lista las cotizaciones pendientes — progreso guardado a medio
hacer desde cualquier pantalla de producto (botón "💾 Guardar progreso" o
Ctrl+S/Cmd+S, ver ui/cotizacion.py / ui/cotizador_backlight.py y
core/repositorio_pendientes.py). Todavía no tienen N° de cotización ni
cliente, así que se identifican por nombre del trabajo y cantidad de
productos. Doble clic retoma la cotización justo donde quedó.
"""

import sys
import subprocess
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

from core import escala as _esc
from core.repositorio_pendientes import (
    carpeta_pendientes, listar_pendientes, cargar_pendiente, eliminar_pendiente,
)

# Mismo look que ui/revisar_cotizaciones.py (ventana hermana, abierta desde
# ahí) — cada ventana de este estilo define su propia paleta local, mismo
# criterio que el resto del proyecto (ver ui/formulario_cliente.py).
COLORES = {
    "fondo":        "#F5F3EE",
    "acento":       "#1A3A5C",
    "acento_hover": "#245480",
    "texto":        "#1C1C1C",
    "texto_suave":  "#6B6B6B",
    "borde":        "#D8D4CC",
    "lista_sel":    "#C8D4FF",
    "fila_par":     "#FFFFFF",
    "fila_impar":   "#F0F4FA",
    "error":        "#C0392B",
    "error_hover":  "#E74C3C",
}

if sys.platform == "darwin":
    FUENTE_TITULO = ("Helvetica Neue", 14, "bold")
    FUENTE_LABEL  = ("Helvetica Neue", 11)
    FUENTE_LISTA  = ("Helvetica Neue", 12)
    FUENTE_HEAD   = ("Helvetica Neue", 11, "bold")
    FUENTE_BTN    = ("Helvetica Neue", 11, "bold")
else:
    FUENTE_TITULO = ("Georgia", 13, "bold")
    FUENTE_LABEL  = ("Segoe UI", 10)
    FUENTE_LISTA  = ("Segoe UI", 11)
    FUENTE_HEAD   = ("Segoe UI", 10, "bold")
    FUENTE_BTN    = ("Segoe UI", 10, "bold")

_NOMBRES_TIPO = {"normal": "Normal", "backlight": "Backlight"}


def _texto_productos(p: dict) -> str:
    """"2/5" (completos/total, ver core/repositorio_pendientes.py — la
    lista "productos" guarda huecos = null en su posición real para los
    que faltan) + una nota si además hay un producto a medio llenar."""
    productos = p.get("productos", [])
    completos = sum(1 for x in productos if x is not None)
    texto = f"{completos}/{len(productos)}"
    if p.get("producto_parcial"):
        texto += " (+1 a medias)"
    return texto


def _abrir_carpeta(ruta):
    ruta = str(ruta)
    if sys.platform == "win32":
        import os
        os.startfile(ruta)
    elif sys.platform == "darwin":
        subprocess.run(["open", ruta])
    else:
        subprocess.run(["xdg-open", ruta])


class VentanaPendientes(tk.Toplevel):

    ANCHO = _esc.px(720)
    ALTO  = _esc.px(560)

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Cotizaciones Pendientes")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        self._centrar()
        self.lift()
        self.focus_force()

        self._entradas = []  # [(id, nombre, tipo, n_productos, guardado_en), ...]
        self._cargar_pendientes()
        self._aplicar_estilo()
        self._construir_ui()

    # ── Carga ──────────────────────────────────────────────────────────────────

    def _cargar_pendientes(self):
        # Más reciente primero — "guardado_en" es "%d/%m/%Y %H:%M", el orden
        # de texto no coincide con el cronológico, así que se ordena a
        # partir de la fecha ya parseada.
        from datetime import datetime

        def _clave(p):
            try:
                return datetime.strptime(p.get("guardado_en", ""), "%d/%m/%Y %H:%M")
            except ValueError:
                return datetime.min

        pendientes = sorted(listar_pendientes(), key=_clave, reverse=True)
        self._entradas = [
            (
                p.get("id", ""),
                p.get("nombre_trabajo", "—"),
                _NOMBRES_TIPO.get(p.get("tipo", ""), p.get("tipo", "—")),
                _texto_productos(p),
                p.get("guardado_en", "—"),
            )
            for p in pendientes
        ]

    # ── Estilo ttk ─────────────────────────────────────────────────────────────

    def _aplicar_estilo(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Pend.Treeview",
            background=COLORES["fila_par"],
            foreground=COLORES["texto"],
            fieldbackground=COLORES["fila_par"],
            rowheight=_esc.px(32),
            font=FUENTE_LISTA,
            borderwidth=0,
        )
        s.configure("Pend.Treeview.Heading",
            background=COLORES["acento"],
            foreground="#FFFFFF",
            font=FUENTE_HEAD,
            relief="flat",
            padding=(_esc.px(8), _esc.px(6)),
        )
        s.map("Pend.Treeview",
            background=[("selected", COLORES["lista_sel"])],
            foreground=[("selected", COLORES["texto"])],
        )
        s.map("Pend.Treeview.Heading",
            background=[("active", COLORES["acento_hover"])],
            relief=[("active", "flat")],
        )

    def _centrar(self):
        pantalla_w = self.winfo_screenwidth()
        pantalla_h = self.winfo_screenheight()
        x = (pantalla_w - self.ANCHO) // 2
        y = (pantalla_h - self.ALTO) // 2
        self.geometry(f"{self.ANCHO}x{self.ALTO}+{x}+{y}")

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        cab = tk.Frame(self, bg=COLORES["acento"], padx=20, pady=12)
        cab.pack(fill="x")
        tk.Label(cab, text="Cotizaciones pendientes",
                 font=FUENTE_TITULO, bg=COLORES["acento"],
                 fg="#FFFFFF").pack(side="left", anchor="w")

        btn_carpeta = tk.Label(
            cab, text="📁", font=FUENTE_TITULO,
            bg=COLORES["acento_hover"], fg="#FFFFFF",
            width=2, height=1, cursor="hand2",
        )
        btn_carpeta.pack(side="right")
        btn_carpeta.bind("<Button-1>", lambda _: _abrir_carpeta(carpeta_pendientes()))
        btn_carpeta.bind("<Enter>", lambda _: btn_carpeta.config(bg=COLORES["acento"]))
        btn_carpeta.bind("<Leave>", lambda _: btn_carpeta.config(bg=COLORES["acento_hover"]))

        tk.Label(self,
                 text="Doble clic sobre una fila para continuarla. "
                      "Se identifican por nombre y cantidad de productos "
                      "(todavía no tienen N° de cotización ni cliente).",
                 font=FUENTE_LABEL, bg=COLORES["fondo"], fg=COLORES["texto_suave"],
                 wraplength=_esc.px(660), justify="left"
                 ).pack(anchor="w", padx=20, pady=(12, 6))

        # ── Footer (empacado antes del árbol para que expand=True no lo tape) ──
        frame_botones = tk.Frame(self, bg=COLORES["fondo"])
        frame_botones.pack(side="bottom", fill="x", padx=20, pady=(8, 16))

        self._btn_eliminar = tk.Label(
            frame_botones, text="Eliminar", font=FUENTE_BTN,
            bg="#9E9E9E", fg="#FFFFFF", padx=16, pady=8, cursor="arrow",
        )
        self._btn_eliminar.pack(side="left")
        self._btn_eliminar.bind("<Button-1>", self._on_eliminar)

        self._lbl_estado = tk.Label(
            self, text="", font=FUENTE_LABEL,
            bg=COLORES["fondo"], fg=COLORES["error"],
            wraplength=_esc.px(660), justify="left",
        )
        self._lbl_estado.pack(side="bottom", anchor="w", padx=20, pady=(0, 4))

        # ── Tabla ─────────────────────────────────────────────────────────────
        frame_tree = tk.Frame(self, bg=COLORES["fondo"])
        frame_tree.pack(fill="both", expand=True, padx=20)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self._tree = ttk.Treeview(
            frame_tree,
            columns=("nombre", "tipo", "productos", "guardado"),
            show="headings",
            style="Pend.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="browse",
        )
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._tree.yview)

        self._tree.heading("nombre",    text="Nombre",     anchor="w")
        self._tree.heading("tipo",      text="Tipo",       anchor="w")
        self._tree.heading("productos", text="Productos",  anchor="w")
        self._tree.heading("guardado",  text="Guardado",   anchor="w")
        self._tree.column("nombre",    width=_esc.px(260), anchor="w")
        self._tree.column("tipo",      width=_esc.px(110), anchor="w")
        self._tree.column("productos", width=_esc.px(90),  anchor="w")
        self._tree.column("guardado",  width=_esc.px(140), anchor="w")

        for i, (id_, nombre, tipo, n_prod, guardado) in enumerate(self._entradas):
            tag = "par" if i % 2 == 0 else "impar"
            self._tree.insert("", "end", iid=id_,
                               values=(nombre, tipo, n_prod, guardado), tags=(tag,))
        self._tree.tag_configure("par",   background=COLORES["fila_par"])
        self._tree.tag_configure("impar", background=COLORES["fila_impar"])

        if not self._entradas:
            self._lbl_estado.config(
                text="No hay cotizaciones pendientes.", fg=COLORES["texto_suave"])

        self._tree.bind("<Double-Button-1>", self._on_doble_clic)
        self._tree.bind("<Return>", self._on_doble_clic)

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _on_doble_clic(self, _e=None):
        iid = self._tree.focus()
        if not iid:
            return
        pendiente = cargar_pendiente(iid)
        if pendiente is None:
            self._lbl_estado.config(
                text="⚠ No se pudo leer el archivo de esa cotización pendiente.",
                fg=COLORES["error"])
            return

        # self.master es VentanaCotizaciones (quien abrió esta ventana);
        # su propio master es la ventana raíz (VentanaPrincipal) — se
        # destruye desde ahí para cerrar toda la cadena de una vez, mismo
        # patrón que ui/revisar_cotizaciones.py::_editar_cotizacion.
        raiz = self.master.master
        raiz.destroy()
        if pendiente.get("tipo") == "backlight":
            from ui.cotizador_backlight import CotizadorBacklight
            CotizadorBacklight(pendiente=pendiente).mainloop()
        else:
            from ui.cotizacion import CotizacionNueva
            CotizacionNueva(pendiente=pendiente).mainloop()

    def _on_eliminar(self, _e=None):
        iid = self._tree.focus()
        if not iid:
            return
        nombre = self._tree.set(iid, "nombre")
        if not messagebox.askyesno(
                "Eliminar pendiente",
                f"¿Eliminar el progreso guardado de \"{nombre}\"?\n\n"
                "Esta acción no se puede deshacer."):
            return
        eliminar_pendiente(iid)
        self._tree.delete(iid)
        self._entradas = [e for e in self._entradas if e[0] != iid]
        if not self._entradas:
            self._lbl_estado.config(
                text="No hay cotizaciones pendientes.", fg=COLORES["texto_suave"])
