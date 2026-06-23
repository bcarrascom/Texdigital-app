"""
ui/revisar_ops.py
Ventana de solo lectura que lista las Órdenes de Producción (OP) activas,
leídas desde Dropbox/SGTD/OPs/JSON/. Ordenadas por fecha de entrega más
próxima primero.
"""

import json
import sys
import tkinter as tk
import tkinter.ttk as ttk
from datetime import datetime

from core import escala as _esc
from core.repositorio_ops import carpeta_json

COLORES = {
    "fondo":        "#F5F3EE",
    "acento":       "#1A3A5C",
    "acento_hover": "#245480",
    "texto":        "#1C1C1C",
    "texto_suave":  "#6B6B6B",
    "borde":        "#D8D4CC",
    "fila_par":     "#FFFFFF",
    "fila_impar":   "#F0F4FA",
    "hover":        "#E0E5EC",
}

if sys.platform == "darwin":
    FUENTE_TITULO = ("Helvetica Neue", 14, "bold")
    FUENTE_LABEL  = ("Helvetica Neue", 11)
    FUENTE_LISTA  = ("Helvetica Neue", 12)
    FUENTE_HEAD   = ("Helvetica Neue", 11, "bold")
else:
    FUENTE_TITULO = ("Georgia", 13, "bold")
    FUENTE_LABEL  = ("Segoe UI", 10)
    FUENTE_LISTA  = ("Segoe UI", 11)
    FUENTE_HEAD   = ("Segoe UI", 10, "bold")


def _clave_fecha_entrega(texto: str):
    """Fechas válidas (dd/mm/aaaa) ordenan por proximidad; inválidas o
    vacías van al final de la lista."""
    try:
        return (0, datetime.strptime(texto.strip(), "%d/%m/%Y"))
    except (ValueError, AttributeError):
        return (1, datetime.max)


class VentanaOPs(tk.Toplevel):

    ANCHO = _esc.px(1046)
    ALTO  = _esc.px(720)

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Revisar Órdenes de Producción")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        self._centrar()
        self.lift()
        self.focus_force()

        self._iid_tags  = {}
        self._hover_iid = None

        self._cargar_ops()
        self._aplicar_estilo()
        self._construir_ui()

    # ── Carga ──────────────────────────────────────────────────────────────────

    def _cargar_ops(self):
        carpeta = carpeta_json()
        entradas = []
        for archivo in sorted(carpeta.glob("*.json")):
            try:
                datos   = json.loads(archivo.read_text(encoding="utf-8"))
                num     = int(datos.get("Cotizacion", archivo.stem))
                nombre  = datos.get("Nombre", "—")
                empresa = datos.get("Empresa", "—")
                entrega = datos.get("Fecha_entrega", "—")
                entradas.append((num, nombre, empresa, entrega))
            except Exception:
                pass
        self._entradas = sorted(entradas, key=lambda e: _clave_fecha_entrega(e[3]))

    # ── Estilo ttk ─────────────────────────────────────────────────────────────

    def _aplicar_estilo(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Ops.Treeview",
            background=COLORES["fila_par"],
            foreground=COLORES["texto"],
            fieldbackground=COLORES["fila_par"],
            rowheight=_esc.px(56),
            font=FUENTE_LISTA,
            borderwidth=0,
        )
        s.configure("Ops.Treeview.Heading",
            background=COLORES["acento"],
            foreground="#FFFFFF",
            font=FUENTE_HEAD,
            relief="flat",
            padding=(_esc.px(8), _esc.px(6)),
        )
        s.map("Ops.Treeview.Heading",
            background=[("active", COLORES["acento_hover"])],
            relief=[("active", "flat")],
        )

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        cab = tk.Frame(self, bg=COLORES["acento"], padx=20, pady=12)
        cab.pack(fill="x")
        tk.Label(cab, text="Órdenes de Producción activas",
                 font=FUENTE_TITULO, bg=COLORES["acento"],
                 fg="#FFFFFF").pack(anchor="w")

        tk.Label(self,
                 text="Listado de solo lectura, ordenado por fecha de entrega más próxima.",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w", padx=20, pady=(12, 6))

        frame_tree = tk.Frame(self, bg=COLORES["fondo"])
        frame_tree.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self._tree = ttk.Treeview(
            frame_tree,
            columns=("num", "nombre", "empresa", "entrega"),
            show="headings",
            style="Ops.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="none",
        )
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._tree.yview)

        self._tree.heading("num",     text="N° OP",             anchor="w")
        self._tree.heading("nombre",  text="Nombre del trabajo", anchor="w")
        self._tree.heading("empresa", text="Empresa",            anchor="w")
        self._tree.heading("entrega", text="Fecha de entrega",   anchor="w")

        self._tree.column("num",     width=_esc.px(80),  minwidth=60,  anchor="w", stretch=False)
        self._tree.column("nombre",  width=_esc.px(320), minwidth=200, anchor="w", stretch=False)
        self._tree.column("empresa", width=_esc.px(260), minwidth=180, anchor="w", stretch=False)
        self._tree.column("entrega", width=_esc.px(200), minwidth=200, anchor="w", stretch=True)

        self._tree.tag_configure("par",   background=COLORES["fila_par"])
        self._tree.tag_configure("impar", background=COLORES["fila_impar"])
        self._tree.tag_configure("hover", background=COLORES["hover"])

        if self._entradas:
            for i, (num, nombre, empresa, entrega) in enumerate(self._entradas):
                tag = "par" if i % 2 == 0 else "impar"
                iid = str(num)
                self._iid_tags[iid] = tag
                self._tree.insert("", tk.END, iid=iid,
                                  values=(f"{num:04d}", nombre, empresa, entrega),
                                  tags=(tag,))
        else:
            self._tree.insert("", tk.END,
                              values=("—", "No hay Órdenes de Producción activas.", "—", "—"))

        self._tree.bind("<Motion>", self._on_hover_motion)
        self._tree.bind("<Leave>",  self._on_hover_leave)

    # ── Hover ──────────────────────────────────────────────────────────────────

    def _on_hover_motion(self, event):
        iid = self._tree.identify_row(event.y)
        if iid == self._hover_iid:
            return
        if self._hover_iid:
            self._tree.item(self._hover_iid,
                            tags=(self._iid_tags.get(self._hover_iid, "par"),))
        self._hover_iid = iid
        if iid:
            self._tree.item(iid, tags=("hover",))

    def _on_hover_leave(self, _):
        if self._hover_iid:
            self._tree.item(self._hover_iid,
                            tags=(self._iid_tags.get(self._hover_iid, "par"),))
            self._hover_iid = None

    # ── Utilidades ─────────────────────────────────────────────────────────────

    def _centrar(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - self.ANCHO) // 2
        y = (self.winfo_screenheight() - self.ALTO)  // 2
        self.geometry(f"{self.ANCHO}x{self.ALTO}+{x}+{y}")
