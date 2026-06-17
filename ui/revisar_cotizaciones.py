"""
ui/revisar_cotizaciones.py
Ventana que lista las cotizaciones guardadas en JSON y permite abrir
el Excel correspondiente con doble clic.
"""

import json
import os
import subprocess
import sys
import tkinter as tk
import tkinter.ttk as ttk

from core import escala as _esc
from core.repositorio_cotizaciones import carpeta_json, carpeta_excel

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
    "hover":        "#E0E5EC",
    "ok":           "#27AE60",
    "error":        "#C0392B",
}

if sys.platform == "darwin":
    FUENTE_TITULO = ("Helvetica Neue", 14, "bold")
    FUENTE_LABEL  = ("Helvetica Neue", 11)
    FUENTE_LISTA  = ("Helvetica Neue", 12)
    FUENTE_HEAD   = ("Helvetica Neue", 11, "bold")
    FUENTE_BTN    = ("Helvetica Neue", 12, "bold")
else:
    FUENTE_TITULO = ("Georgia", 13, "bold")
    FUENTE_LABEL  = ("Segoe UI", 10)
    FUENTE_LISTA  = ("Segoe UI", 11)
    FUENTE_HEAD   = ("Segoe UI", 10, "bold")
    FUENTE_BTN    = ("Segoe UI", 10, "bold")


def _abrir_archivo(path: str):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


class VentanaCotizaciones(tk.Toplevel):

    ANCHO = _esc.px(880)
    ALTO  = _esc.px(720)

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Revisar Cotizaciones")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        self._centrar()
        self.lift()
        self.focus_force()

        self._entradas    = []
        self._iid_tags    = {}   # iid → tag original ("par"/"impar")
        self._hover_iid   = None
        self._cargar_cotizaciones()
        self._aplicar_estilo()
        self._construir_ui()

    # ── Carga ──────────────────────────────────────────────────────────────────

    def _cargar_cotizaciones(self):
        carpeta = carpeta_json()
        entradas = []
        for archivo in sorted(carpeta.glob("*.json")):
            try:
                datos   = json.loads(archivo.read_text(encoding="utf-8"))
                num     = int(datos.get("Cotizacion", archivo.stem))
                empresa = datos.get("Empresa", "—")
                fecha   = datos.get("Fecha", "—")
                entradas.append((num, empresa, fecha, archivo))
            except Exception:
                pass
        self._entradas = sorted(entradas, key=lambda e: e[0], reverse=True)

    # ── Estilo ttk ─────────────────────────────────────────────────────────────

    def _aplicar_estilo(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Cotiz.Treeview",
            background=COLORES["fila_par"],
            foreground=COLORES["texto"],
            fieldbackground=COLORES["fila_par"],
            rowheight=_esc.px(28),
            font=FUENTE_LISTA,
            borderwidth=0,
        )
        s.configure("Cotiz.Treeview.Heading",
            background=COLORES["acento"],
            foreground="#FFFFFF",
            font=FUENTE_HEAD,
            relief="flat",
            padding=(_esc.px(8), _esc.px(6)),
        )
        s.map("Cotiz.Treeview",
            background=[("selected", COLORES["lista_sel"])],
            foreground=[("selected", COLORES["texto"])],
        )
        s.map("Cotiz.Treeview.Heading",
            background=[("active", COLORES["acento_hover"])],
            relief=[("active", "flat")],
        )

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        # Cabecera
        cab = tk.Frame(self, bg=COLORES["acento"], padx=20, pady=12)
        cab.pack(fill="x")
        tk.Label(cab, text="Cotizaciones guardadas",
                 font=FUENTE_TITULO, bg=COLORES["acento"],
                 fg="#FFFFFF").pack(anchor="w")

        # Instrucción
        tk.Label(self,
                 text="Doble clic sobre una fila para abrir el Excel correspondiente.",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w", padx=20, pady=(12, 6))

        # Tabla
        frame_tree = tk.Frame(self, bg=COLORES["fondo"])
        frame_tree.pack(fill="both", expand=True, padx=20)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self._tree = ttk.Treeview(
            frame_tree,
            columns=("num", "empresa", "fecha"),
            show="headings",
            style="Cotiz.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="browse",
        )
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._tree.yview)

        # Encabezados
        self._tree.heading("num",     text="N°",      anchor="w")
        self._tree.heading("empresa", text="Empresa", anchor="w")
        self._tree.heading("fecha",   text="Fecha",   anchor="w")

        # Anchos de columna
        self._tree.column("num",     width=_esc.px(80),  minwidth=60,  anchor="w", stretch=False)
        self._tree.column("empresa", width=_esc.px(530), minwidth=200, anchor="w", stretch=True)
        self._tree.column("fecha",   width=_esc.px(210), minwidth=100, anchor="w", stretch=False)

        # Colores por fila
        self._tree.tag_configure("par",   background=COLORES["fila_par"])
        self._tree.tag_configure("impar", background=COLORES["fila_impar"])
        self._tree.tag_configure("hover", background=COLORES["hover"])

        if self._entradas:
            for i, (num, empresa, fecha, _) in enumerate(self._entradas):
                tag = "par" if i % 2 == 0 else "impar"
                iid = str(num)
                self._iid_tags[iid] = tag
                self._tree.insert("", tk.END, iid=iid,
                                  values=(f"{num:04d}", empresa, fecha),
                                  tags=(tag,))
        else:
            self._tree.insert("", tk.END,
                              values=("—", "No hay cotizaciones guardadas.", "—"))

        self._tree.bind("<Double-Button-1>", self._on_doble_clic)
        self._tree.bind("<Motion>",          self._on_hover_motion)
        self._tree.bind("<Leave>",           self._on_hover_leave)

        # Mensaje de estado
        self._lbl_estado = tk.Label(
            self, text="", font=FUENTE_LABEL,
            bg=COLORES["fondo"], fg=COLORES["error"],
            wraplength=_esc.px(830), justify="left",
        )
        self._lbl_estado.pack(anchor="w", padx=20, pady=(6, 0))

        # Botón cerrar
        btn_cerrar = tk.Label(
            self, text="Cerrar",
            font=FUENTE_BTN, bg=COLORES["acento"],
            fg="#FFFFFF", padx=18, pady=8, cursor="hand2",
        )
        btn_cerrar.pack(anchor="e", padx=20, pady=(8, 16))
        btn_cerrar.bind("<Button-1>", lambda _: self.destroy())
        btn_cerrar.bind("<Enter>", lambda _: btn_cerrar.config(bg=COLORES["acento_hover"]))
        btn_cerrar.bind("<Leave>", lambda _: btn_cerrar.config(bg=COLORES["acento"]))

    # ── Acción doble clic ──────────────────────────────────────────────────────

    def _on_doble_clic(self, _):
        sel = self._tree.selection()
        if not sel or not self._entradas:
            return
        try:
            num = int(sel[0])
        except ValueError:
            return

        ruta_excel = carpeta_excel() / f"Cotización {num:04d}.xlsx"
        if not ruta_excel.exists():
            ruta_excel = carpeta_excel() / f"Cotización {num}.xlsx"

        if ruta_excel.exists():
            self._lbl_estado.config(text="")
            _abrir_archivo(str(ruta_excel))
        else:
            self._lbl_estado.config(
                text=f"⚠ No se encontró el Excel para la cotización N° {num:04d}.\n"
                     f"Buscado en: {carpeta_excel()}",
                fg=COLORES["error"],
            )

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
