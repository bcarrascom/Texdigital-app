"""
ui/actualizador.py
Ventana "Buscar actualización" — botón del menú principal (ver
ui/interfaz.py). Consulta core.actualizador.buscar_actualizacion() y, si
hay una versión más nueva, descarga y aplica con
core.actualizador.aplicar_actualizacion(), mostrando progreso real y
cualquier error — a diferencia del auto-update viejo (ver
core/actualizador.py), que hacía todo esto en silencio al iniciar la app y
fallaba sin avisar nada.
"""

import sys
import threading
import tkinter as tk
from tkinter import ttk

from core.version import VERSION

# Mismos valores que ui/interfaz.py — esta ventana se abre desde ahí.
COLORES = {
    "fondo":        "#F5F3EE",
    "acento":       "#1A3A5C",
    "acento_hover": "#245480",
    "texto":        "#1C1C1C",
    "texto_suave":  "#6B6B6B",
    "borde":        "#D8D4CC",
    "error":        "#C0392B",
    "ok":           "#27AE60",
}

if sys.platform == "darwin":
    FUENTE_TITULO = ("Helvetica Neue", 15, "bold")
    FUENTE_LABEL  = ("Helvetica Neue", 12)
    FUENTE_BTN    = ("Helvetica Neue", 12, "bold")
else:
    FUENTE_TITULO = ("Georgia", 14, "bold")
    FUENTE_LABEL  = ("Segoe UI", 11)
    FUENTE_BTN    = ("Segoe UI", 11, "bold")


class VentanaActualizar(tk.Toplevel):

    ANCHO, ALTO = 540, 230*2

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Buscar actualización")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        self._centrar()
        self.lift()
        self.focus_force()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        self._release = None
        self._construir_ui()

        if not getattr(sys, "frozen", False):
            self._mostrar_estado(
                "Esta función solo está disponible en la versión instalada "
                "de la app, no corriendo desde el código fuente.",
                COLORES["texto_suave"])
            self._boton("Cerrar", self._cerrar)
            return

        self._buscar()

    def _centrar(self):
        x = (self.winfo_screenwidth() - self.ANCHO) // 2
        y = (self.winfo_screenheight() - self.ALTO) // 2
        self.geometry(f"{self.ANCHO}x{self.ALTO}+{x}+{y}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        cuerpo = tk.Frame(self, bg=COLORES["fondo"], padx=28, pady=24)
        cuerpo.pack(fill="both", expand=True)

        tk.Label(cuerpo, text="Buscar actualización", font=FUENTE_TITULO,
                 bg=COLORES["fondo"], fg=COLORES["texto"]).pack(anchor="w")
        tk.Label(cuerpo, text=f"Versión instalada: v{VERSION}", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]
                 ).pack(anchor="w", pady=(2, 14))

        self._lbl_estado = tk.Label(
            cuerpo, text="", font=FUENTE_LABEL, bg=COLORES["fondo"],
            fg=COLORES["texto"], wraplength=400, justify="left")
        self._lbl_estado.pack(anchor="w", fill="x")

        self._barra = ttk.Progressbar(cuerpo, orient="horizontal", mode="determinate")
        # Se empaqueta solo durante la descarga (ver _actualizar).

        self._frame_botones = tk.Frame(self, bg=COLORES["fondo"])
        self._frame_botones.pack(side="bottom", fill="x", padx=28, pady=(0, 20))

    def _boton(self, texto, comando, bg=None, fg="#FFFFFF"):
        btn = tk.Label(self._frame_botones, text=texto, font=FUENTE_BTN,
                        bg=bg or COLORES["acento"], fg=fg,
                        padx=18, pady=9, cursor="hand2")
        btn.pack(side="right", padx=(8, 0))
        btn.bind("<Button-1>", lambda _: comando())
        return btn

    def _limpiar_botones(self):
        for w in self._frame_botones.winfo_children():
            w.destroy()

    def _mostrar_estado(self, texto, color=None):
        self._lbl_estado.config(text=texto, fg=color or COLORES["texto"])

    # ── Buscar ────────────────────────────────────────────────────────────────

    def _buscar(self):
        self._mostrar_estado("Buscando actualizaciones...", COLORES["texto_suave"])
        self._limpiar_botones()

        def _hacer():
            from core.actualizador import buscar_actualizacion
            try:
                release = buscar_actualizacion()
                self.after(0, lambda: self._on_busqueda_ok(release))
            except Exception as e:
                self.after(0, lambda: self._on_busqueda_error(e))

        threading.Thread(target=_hacer, daemon=True).start()

    def _on_busqueda_ok(self, release):
        if release is None:
            self._mostrar_estado(f"Ya tienes la última versión (v{VERSION}).", COLORES["ok"])
            self._boton("Cerrar", self._cerrar)
            return
        self._release = release
        self._mostrar_estado(
            f"Hay una nueva versión disponible: {release['tag']} "
            f"(actual: v{VERSION}).", COLORES["texto"])
        self._boton("Actualizar ahora", self._actualizar)
        self._boton("Más tarde", self._cerrar, bg=COLORES["borde"], fg=COLORES["texto"])

    def _on_busqueda_error(self, error):
        self._mostrar_estado(f"⚠ No se pudo buscar actualizaciones:\n{error}", COLORES["error"])
        self._boton("Reintentar", self._buscar)
        self._boton("Cerrar", self._cerrar, bg=COLORES["borde"], fg=COLORES["texto"])

    # ── Aplicar ───────────────────────────────────────────────────────────────

    def _actualizar(self):
        self._limpiar_botones()
        self._mostrar_estado(f"Descargando {self._release['tag']}...", COLORES["texto"])
        self._barra["value"] = 0
        self._barra.pack(fill="x", pady=(10, 0))
        # No cerrar a mitad de la descarga (los archivos de la app quedan
        # en un estado intermedio hasta que aplicar_actualizacion() termina).
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        def _on_progreso(leidos, total):
            if total:
                pct = leidos / total * 100
                self.after(0, lambda: self._barra.config(value=pct))

        def _hacer():
            from core.actualizador import aplicar_actualizacion
            try:
                aplicar_actualizacion(self._release, on_progreso=_on_progreso)
                self.after(0, self._on_aplicar_ok)
            except Exception as e:
                self.after(0, lambda: self._on_aplicar_error(e))

        threading.Thread(target=_hacer, daemon=True).start()

    def _on_aplicar_ok(self):
        self._barra.pack_forget()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self._mostrar_estado(
            "Actualización lista. La aplicación se cerrará y volverá a "
            "abrir sola con la nueva versión.", COLORES["ok"])
        self.after(1500, self._salir_y_relanzar)

    def _salir_y_relanzar(self):
        from ui.panel_produccion import salir_app
        salir_app()

    def _on_aplicar_error(self, error):
        self._barra.pack_forget()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self._mostrar_estado(f"⚠ No se pudo aplicar la actualización:\n{error}", COLORES["error"])
        self._limpiar_botones()
        self._boton("Reintentar", self._actualizar)
        self._boton("Cerrar", self._cerrar, bg=COLORES["borde"], fg=COLORES["texto"])

    def _cerrar(self):
        self.grab_release()
        self.destroy()
