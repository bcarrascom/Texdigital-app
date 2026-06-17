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
from tkinter import messagebox

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

    # Colores del botón Eliminar
    _C_ELIM_OFF    = "#9E9E9E"
    _C_ELIM_OFF_HV = "#BDBDBD"
    _C_ELIM_ON     = COLORES["error"]
    _C_ELIM_ON_HV  = COLORES["error_hover"]

    # Colores del botón Seleccionar múltiples
    _C_MULTI_OFF    = "#D8D8D8"
    _C_MULTI_OFF_HV = "#BEBEBE"
    _C_MULTI_ON     = COLORES["acento"]
    _C_MULTI_ON_HV  = COLORES["acento_hover"]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Revisar Cotizaciones")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        self._centrar()
        self.lift()
        self.focus_force()

        self._entradas     = []
        self._iid_tags     = {}    # iid → "par" | "impar"
        self._selected     = set() # iids actualmente seleccionados
        self._hover_iid    = None
        self._multi_select = False
        self._drag_anchor  = None
        self._elim_on      = False

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
            rowheight=_esc.px(56),
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
        # La selección se maneja quitando tags (sin tag = color de selección)
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
            selectmode="extended",
        )
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._tree.yview)

        self._tree.heading("num",     text="N°",      anchor="w")
        self._tree.heading("empresa", text="Empresa", anchor="w")
        self._tree.heading("fecha",   text="Fecha",   anchor="w")

        self._tree.column("num",     width=_esc.px(80),  minwidth=60,  anchor="w", stretch=False)
        self._tree.column("empresa", width=_esc.px(530), minwidth=200, anchor="w", stretch=True)
        self._tree.column("fecha",   width=_esc.px(210), minwidth=100, anchor="w", stretch=False)

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

        self._tree.bind("<Double-Button-1>",  self._on_doble_clic)
        self._tree.bind("<ButtonPress-1>",    self._on_tree_click)
        self._tree.bind("<B1-Motion>",        self._on_tree_drag)
        self._tree.bind("<Motion>",           self._on_hover_motion)
        self._tree.bind("<Leave>",            self._on_hover_leave)
        self._tree.bind("<<TreeviewSelect>>", lambda _: self._on_selection_change())

        # Mensaje de estado
        self._lbl_estado = tk.Label(
            self, text="", font=FUENTE_LABEL,
            bg=COLORES["fondo"], fg=COLORES["error"],
            wraplength=_esc.px(830), justify="left",
        )
        self._lbl_estado.pack(anchor="w", padx=20, pady=(6, 0))

        # Barra de botones
        frame_botones = tk.Frame(self, bg=COLORES["fondo"])
        frame_botones.pack(fill="x", padx=20, pady=(8, 16))

        frame_izq = tk.Frame(frame_botones, bg=COLORES["fondo"])
        frame_izq.pack(side="left")

        self._btn_eliminar = tk.Label(
            frame_izq, text="Eliminar",
            font=FUENTE_BTN, bg=self._C_ELIM_OFF,
            fg="#FFFFFF", padx=16, pady=8, cursor="arrow",
        )
        self._btn_eliminar.pack(side="left", padx=(0, 8))

        self._btn_multi = tk.Label(
            frame_izq, text="Seleccionar múltiples",
            font=FUENTE_BTN, bg=self._C_MULTI_OFF,
            fg=COLORES["texto"], padx=16, pady=8, cursor="hand2",
        )
        self._btn_multi.pack(side="left")

        btn_cerrar = tk.Label(
            frame_botones, text="Cerrar",
            font=FUENTE_BTN, bg=COLORES["acento"],
            fg="#FFFFFF", padx=18, pady=8, cursor="hand2",
        )
        btn_cerrar.pack(side="right")

        self._btn_eliminar.bind("<Enter>",    self._on_elim_enter)
        self._btn_eliminar.bind("<Leave>",    self._on_elim_leave)
        self._btn_eliminar.bind("<Button-1>", self._on_eliminar)

        self._btn_multi.bind("<Enter>",    self._on_multi_enter)
        self._btn_multi.bind("<Leave>",    self._on_multi_leave)
        self._btn_multi.bind("<Button-1>", self._toggle_multi_select)

        btn_cerrar.bind("<Button-1>", lambda _: self.destroy())
        btn_cerrar.bind("<Enter>", lambda _: btn_cerrar.config(bg=COLORES["acento_hover"]))
        btn_cerrar.bind("<Leave>", lambda _: btn_cerrar.config(bg=COLORES["acento"]))

        # Click fuera de árbol y botones → deseleccionar
        self._safe_widgets = {self._tree, self._btn_eliminar, self._btn_multi, btn_cerrar}
        self.bind("<ButtonPress-1>", self._on_window_click, add="+")

    # ── Selección ──────────────────────────────────────────────────────────────

    def _on_tree_click(self, event):
        iid = self._tree.identify_row(event.y)

        if not iid:
            # Click en área vacía del árbol
            self._tree.selection_set([])
            return "break"

        self._drag_anchor = iid

        if self._multi_select:
            # Toggle sin limpiar otras filas
            current = list(self._tree.selection())
            if iid in current:
                current.remove(iid)
            else:
                current.append(iid)
            self._tree.selection_set(current)
            self._tree.focus(iid)
            return "break"
        # Modo normal: el selectmode="extended" maneja Shift/Ctrl+click y flechas

    def _on_tree_drag(self, event):
        if not self._multi_select or not self._drag_anchor:
            return
        iid = self._tree.identify_row(event.y)
        if not iid or iid == self._drag_anchor:
            return
        all_iids = list(self._iid_tags.keys())
        if self._drag_anchor in all_iids and iid in all_iids:
            i1 = all_iids.index(self._drag_anchor)
            i2 = all_iids.index(iid)
            self._tree.selection_set(all_iids[min(i1, i2) : max(i1, i2) + 1])
        return "break"

    def _on_selection_change(self):
        """Sincroniza tags de fila con el estado de selección actual.

        Tags de ttk.Treeview sobrescriben el color de selección del estilo,
        por eso las filas seleccionadas quedan sin tag (muestra el azul del estilo).
        """
        new_sel = set(self._tree.selection())

        for iid in (self._selected - new_sel):
            # Deseleccionada: restaurar hover u original
            if iid == self._hover_iid:
                self._tree.item(iid, tags=("hover",))
            else:
                self._tree.item(iid, tags=(self._iid_tags.get(iid, "par"),))

        for iid in (new_sel - self._selected):
            # Recién seleccionada: sin tag → el estilo muestra el azul de selección
            self._tree.item(iid, tags=())

        self._selected = new_sel
        self._actualizar_btn_eliminar()

    def _on_window_click(self, event):
        """Deselecciona al hacer click fuera del árbol y los botones."""
        w = event.widget
        while w is not None and w is not self:
            if w in self._safe_widgets:
                return
            w = getattr(w, "master", None)
        self._tree.selection_set([])

    # ── Botón Eliminar ─────────────────────────────────────────────────────────

    def _actualizar_btn_eliminar(self):
        hay_sel = bool(self._selected)
        if hay_sel == self._elim_on:
            return
        self._elim_on = hay_sel
        if hay_sel:
            self._btn_eliminar.config(bg=self._C_ELIM_ON, fg="#FFFFFF", cursor="hand2")
        else:
            self._btn_eliminar.config(bg=self._C_ELIM_OFF, fg="#FFFFFF", cursor="arrow")

    def _on_elim_enter(self, _):
        self._btn_eliminar.config(
            bg=self._C_ELIM_ON_HV if self._elim_on else self._C_ELIM_OFF_HV)

    def _on_elim_leave(self, _):
        self._btn_eliminar.config(
            bg=self._C_ELIM_ON if self._elim_on else self._C_ELIM_OFF)

    def _on_eliminar(self, _):
        if not self._elim_on:
            return
        sel = list(self._selected)
        if not sel:
            return
        n = len(sel)
        plural = "es" if n > 1 else ""
        if not messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar {n} cotización{plural}?\nEsta acción no se puede deshacer.",
            parent=self,
        ):
            return

        for iid in sel:
            try:
                num = int(iid)
            except ValueError:
                continue
            for nombre in (f"{num}.json", f"{num:04d}.json"):
                p = carpeta_json() / nombre
                if p.exists():
                    p.unlink()
                    break
            for nombre in (f"Cotización {num:04d}.xlsx", f"Cotización {num}.xlsx"):
                p = carpeta_excel() / nombre
                if p.exists():
                    p.unlink()
                    break
            self._tree.delete(iid)
            self._entradas = [(n, e, f, p) for n, e, f, p in self._entradas
                              if str(n) != iid]
            self._iid_tags.pop(iid, None)

        self._selected.clear()

        # Reaplicar colores alternados tras la eliminación
        for i, iid in enumerate(self._tree.get_children()):
            tag = "par" if i % 2 == 0 else "impar"
            self._iid_tags[iid] = tag
            self._tree.item(iid, tags=(tag,))

        self._actualizar_btn_eliminar()

    # ── Botón Seleccionar múltiples ────────────────────────────────────────────

    def _toggle_multi_select(self, _):
        self._multi_select = not self._multi_select
        if self._multi_select:
            self._btn_multi.config(bg=self._C_MULTI_ON, fg="#FFFFFF")
        else:
            self._btn_multi.config(bg=self._C_MULTI_OFF, fg=COLORES["texto"])
            # Al salir del modo multi, conservar solo la primera seleccionada
            if len(self._selected) > 1:
                self._tree.selection_set([next(iter(self._selected))])

    def _on_multi_enter(self, _):
        self._btn_multi.config(
            bg=self._C_MULTI_ON_HV if self._multi_select else self._C_MULTI_OFF_HV)

    def _on_multi_leave(self, _):
        self._btn_multi.config(
            bg=self._C_MULTI_ON if self._multi_select else self._C_MULTI_OFF)

    # ── Hover ──────────────────────────────────────────────────────────────────

    def _on_hover_motion(self, event):
        iid = self._tree.identify_row(event.y)
        if iid == self._hover_iid:
            return
        if self._hover_iid:
            if self._hover_iid in self._selected:
                self._tree.item(self._hover_iid, tags=())
            else:
                self._tree.item(self._hover_iid,
                                tags=(self._iid_tags.get(self._hover_iid, "par"),))
        self._hover_iid = iid
        if iid and iid not in self._selected:
            self._tree.item(iid, tags=("hover",))

    def _on_hover_leave(self, _):
        if self._hover_iid:
            if self._hover_iid in self._selected:
                self._tree.item(self._hover_iid, tags=())
            else:
                self._tree.item(self._hover_iid,
                                tags=(self._iid_tags.get(self._hover_iid, "par"),))
            self._hover_iid = None

    # ── Doble clic ─────────────────────────────────────────────────────────────

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

    # ── Utilidades ─────────────────────────────────────────────────────────────

    def _centrar(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - self.ANCHO) // 2
        y = (self.winfo_screenheight() - self.ALTO)  // 2
        self.geometry(f"{self.ANCHO}x{self.ALTO}+{x}+{y}")
