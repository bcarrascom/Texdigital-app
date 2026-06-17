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
from tkinter import messagebox

from core.repositorio_cotizaciones import carpeta_json, carpeta_excel

COLORES = {
    "fondo":       "#F5F3EE",
    "acento":      "#1A3A5C",
    "texto":       "#1C1C1C",
    "texto_suave": "#6B6B6B",
    "borde":       "#D8D4CC",
    "lista_sel":   "#C8D4FF",
    "ok":          "#27AE60",
    "error":       "#C0392B",
}

if sys.platform == "darwin":
    FUENTE_TITULO = ("Helvetica Neue", 14, "bold")
    FUENTE_LABEL  = ("Helvetica Neue", 11)
    FUENTE_LISTA  = ("Helvetica Neue", 12)
    FUENTE_BTN    = ("Helvetica Neue", 12, "bold")
else:
    FUENTE_TITULO = ("Georgia", 13, "bold")
    FUENTE_LABEL  = ("Segoe UI", 10)
    FUENTE_LISTA  = ("Segoe UI", 11)
    FUENTE_BTN    = ("Segoe UI", 10, "bold")


def _abrir_archivo(path: str):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


class VentanaCotizaciones(tk.Toplevel):

    ANCHO = 720
    ALTO  = 720

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Revisar Cotizaciones")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        self._centrar()
        self.lift()
        self.focus_force()

        self._entradas = []  # lista de (numero_int, empresa, fecha, json_path)
        self._cargar_cotizaciones()
        self._construir_ui()

    # ── Carga ──────────────────────────────────────────────────────────────────

    def _cargar_cotizaciones(self):
        carpeta = carpeta_json()
        entradas = []
        for archivo in sorted(carpeta.glob("*.json")):
            try:
                datos = json.loads(archivo.read_text(encoding="utf-8"))
                num    = int(datos.get("Cotizacion", archivo.stem))
                empresa = datos.get("Empresa", "—")
                fecha   = datos.get("Fecha", "—")
                entradas.append((num, empresa, fecha, archivo))
            except Exception:
                pass
        # Más reciente primero (mayor número arriba)
        self._entradas = sorted(entradas, key=lambda e: e[0], reverse=True)

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        # Cabecera
        cab = tk.Frame(self, bg=COLORES["acento"], padx=20, pady=12)
        cab.pack(fill="x")
        tk.Label(cab, text="Cotizaciones guardadas",
                 font=FUENTE_TITULO, bg=COLORES["acento"],
                 fg="#FFFFFF").pack(anchor="w")

        # Instrucción
        tk.Label(self, text="Doble clic sobre una fila para abrir el Excel correspondiente.",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w", padx=20, pady=(12, 6))

        # Listbox + scrollbar
        frame_lista = tk.Frame(self, bg=COLORES["fondo"])
        frame_lista.pack(fill="both", expand=True, padx=20)

        scrollbar = tk.Scrollbar(frame_lista, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self._listbox = tk.Listbox(
            frame_lista,
            font=FUENTE_LISTA,
            bg="#FFFFFF",
            fg=COLORES["texto"],
            selectbackground=COLORES["lista_sel"],
            selectforeground=COLORES["texto"],
            activestyle="none",
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORES["borde"],
            highlightcolor=COLORES["acento"],
            yscrollcommand=scrollbar.set,
        )
        self._listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._listbox.yview)

        if self._entradas:
            for num, empresa, fecha, _ in self._entradas:
                self._listbox.insert(
                    tk.END,
                    f"  N° {num:04d}   {empresa:<35}   {fecha}",
                )
        else:
            self._listbox.insert(tk.END, "  No hay cotizaciones guardadas.")
            self._listbox.config(state="disabled")

        self._listbox.bind("<Double-Button-1>", self._on_doble_clic)

        # Mensaje de estado
        self._lbl_estado = tk.Label(
            self, text="", font=FUENTE_LABEL,
            bg=COLORES["fondo"], fg=COLORES["error"],
            wraplength=620, justify="left",
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
        btn_cerrar.bind("<Enter>", lambda _: btn_cerrar.config(bg="#245480"))
        btn_cerrar.bind("<Leave>", lambda _: btn_cerrar.config(bg=COLORES["acento"]))

    # ── Acción doble clic ──────────────────────────────────────────────────────

    def _on_doble_clic(self, _):
        sel = self._listbox.curselection()
        if not sel or not self._entradas:
            return
        idx = sel[0]
        num, _, _, _ = self._entradas[idx]

        ruta_excel = carpeta_excel() / f"Cotización {num:04d}.xlsx"
        if not ruta_excel.exists():
            # Intentar sin cero-relleno por si el archivo fue creado con otro formato
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
