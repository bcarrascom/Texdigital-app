"""
ui/cotizador_backlight.py
Ventana principal del Cotizador Backlight.
Flujo: pantalla-cantidad → iteraciones de medidas → ventana-resumen separada.
"""

import sys
import tkinter as tk
from tkinter import ttk

if sys.platform == "win32":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from core import escala as _esc
from ui.estilos import (
    COLORES,
    FUENTE_SUBTITULO,
    FUENTE_TITULO,
    FUENTE_LABEL,
    FUENTE_MEDIDA,
    MAX_LADO,
    MARGEN,
    _construir_cabecera,
    _centrar,
)
from ui.pantalla_inicio import PantallaInicio
from ui.pantalla_medidas_base import PantallaMedidasBase
from core.repositorio import TEXTILES_ANCHOS

# Anchos máximos leídos desde recursos/textiles.json (única fuente de verdad).
# Editar este orden solo si se quiere cambiar cómo aparecen en el dropdown.
_NOMBRES_TELAS_BACKLIGHT = [
    "Popelina 155",
    "Popelina 310",
    "Pearl 155",
    "Pearl 310",
    "Pearl 160 HP",
]
TELAS = [(nombre, TEXTILES_ANCHOS[nombre]) for nombre in _NOMBRES_TELAS_BACKLIGHT]

# Editar esta lista para agregar/quitar opciones de cajas y perfiles
LISTA_CAJAS = [
    "PERFIL 60 MM",
    "PERFIL 80 MM",
    "PERFIL 100 MM SIMPLE",
    "PERFIL 100 MM DOBLE",
    "PERFIL 120 MM DOBLE"
]

# Ancho de columnas del resumen — ajustar aquí si la tabla queda angosta/ancha
# Orden: #, Textil, Tema, Cantidad, Alto, Ancho, Área
RESUMEN_COL_W = [_esc.px(v) for v in [35, 130, 130, 90, 90, 90, 100]]


# ══════════════════════════════════════════════════════════════════════════════
# Ventana principal — gestiona el flujo completo
# ══════════════════════════════════════════════════════════════════════════════

class CotizadorBacklight(tk.Tk):

    if sys.platform == "darwin":
        TAM_CANTIDAD = (_esc.px(800), _esc.px(730))
        TAM_MEDIDAS  = (_esc.px(1100), _esc.px(1250))
    else:
        TAM_CANTIDAD = (_esc.px(800), _esc.px(560))
        TAM_MEDIDAS  = (_esc.px(960), _esc.px(960))

    def __init__(self, edicion: dict | None = None):
        super().__init__()
        self.title("Cotizador Backlight")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)
        _centrar(self, *self.TAM_CANTIDAD)

        from ui.panel_produccion import salir_app
        self.protocol("WM_DELETE_WINDOW", lambda: salir_app())
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

        self._total_productos  = 0
        self._iteracion_actual = 0
        self._desde_resumen    = False
        self._datos: list[dict] = []
        self._tela_defecto   = TELAS[0][0]
        self._nombre_trabajo = ""
        # edicion = {"json": <dict completo de la cotización>, "productos": [<dict interno>, ...]}
        # No None ⇒ se está editando una cotización ya guardada (viene de Revisar Cotizaciones).
        self._edicion         = edicion

        _construir_cabecera(self, self._volver)

        self._area = tk.Frame(self, bg=COLORES["fondo"])
        self._area.pack(fill="both", expand=True)

        if edicion:
            self._datos            = edicion["productos"]
            self._nombre_trabajo   = edicion["json"].get("Nombre", "")
            self._total_productos  = len(self._datos)
            if self._datos:
                self._tela_defecto = self._datos[0]["tela"]
            self._abrir_resumen()
        else:
            self._mostrar_pantalla_cantidad()

    # ── Navegación entre pantallas ─────────────────────────────────────────────
    def _limpiar(self):
        for w in self._area.winfo_children():
            w.destroy()
        # Limpiar bindings de Enter que pudiera haber dejado la pantalla anterior
        self.unbind("<Return>")

    def _mostrar_pantalla_cantidad(self):
        self._limpiar()
        _centrar(self, *self.TAM_CANTIDAD)
        PantallaInicio(self._area, subtitulo="Cotizador Backlight",
                       on_confirmar=self._on_cantidad_confirmada)

    def _on_cantidad_confirmada(self, y: int, nombre: str):
        self._total_productos  = y
        self._nombre_trabajo   = nombre
        self._datos            = [None] * y
        self._iteracion_actual = 0
        self._mostrar_medidas()

    def _mostrar_medidas(self, desde_resumen=False):
        self._desde_resumen = desde_resumen
        self._limpiar()
        _centrar(self, *self.TAM_MEDIDAS)
        PantallaMedidas(
            self._area,
            ventana_raiz=self,
            indice=self._iteracion_actual,
            total=self._total_productos,
            datos_previos=self._datos[self._iteracion_actual],
            datos_todos=self._datos,
            tela_defecto=self._tela_defecto,
            on_siguiente=self._on_medidas_confirmadas,
            on_nav=self._on_nav,
        )

    def _on_medidas_confirmadas(self, datos: dict):
        self._datos[self._iteracion_actual] = datos
        if self._iteracion_actual == 0:
            self._tela_defecto = datos["tela"]

        if self._desde_resumen:
            self._abrir_resumen()
            return

        sig = self._iteracion_actual + 1
        if sig < self._total_productos:
            self._iteracion_actual = sig
            self._mostrar_medidas()
        else:
            self._abrir_resumen()

    def _on_nav(self, indice: int):
        if self._datos[indice] is not None or indice == self._iteracion_actual:
            self._iteracion_actual = indice
            self._mostrar_medidas(desde_resumen=self._desde_resumen)

    def _abrir_resumen(self):
        from ui.ventana_resumen import VentanaResumen

        COLS = ["#", "Textil", "Tema", "Cantidad", "Ancho (m)", "Alto (m)", "M² imp."]

        filas      = []
        total_cant = 0
        total_ml   = 0.0

        for i, d in enumerate(self._datos):
            uxa   = d["ancho_max"] / d["ancho"]
            ratio = d["cantidad"]  / uxa
            ml    = d["alto"] * d["cantidad"] * ratio
            total_cant += d["cantidad"]
            total_ml   += ml
            filas.append([
                str(i + 1),
                d["tela"],
                d.get("tema", ""),
                str(d["cantidad"]),
                str(d["ancho"]),
                str(d["alto"]),
                f"{ml:.4f}",
            ])

        total_ml = round(total_ml, 4)
        totales  = ["", "TOTAL", "", str(total_cant), "", "", f"{total_ml:.4f}"]

        self.withdraw()
        VentanaResumen(
            ancho_ventana=_esc.px(1600),
            columnas=COLS,
            col_w=RESUMEN_COL_W,
            filas=filas,
            totales=totales,
            titulo="Resumen — Cotizador Backlight",
            subtitulo="Cotizador Backlight",
            nombre_trabajo=self._nombre_trabajo,
            on_editar=self._on_editar_desde_resumen,
            on_confirmar=self._on_confirmar_resumen,
            on_cerrar=self._on_cerrar_resumen,
        )

    def _on_editar_desde_resumen(self, indice: int):
        # La ventana resumen se destruye sola antes de llamar esto
        self.deiconify()
        self.lift()
        self.focus_force()
        self._iteracion_actual = indice
        self._mostrar_medidas(desde_resumen=True)

    def _on_confirmar_resumen(self):
        if self._edicion:
            self._guardar_edicion_y_volver()
            return
        # Abre el formulario de cliente
        from ui.formulario_cliente import FormularioCliente
        FormularioCliente(
            self,
            datos_productos=self._datos,
            nombre_trabajo=self._nombre_trabajo,
            on_cerrar=None,
        )

    # ── Modo edición (cotización ya guardada, viene de Revisar Cotizaciones) ──

    def _guardar_edicion_y_volver(self):
        from ui.formulario_cliente import _mapear_producto
        from core.repositorio_cotizaciones import guardar_cotizacion

        json_actualizado = dict(self._edicion["json"])
        json_actualizado["productos"] = [_mapear_producto(d) for d in self._datos]
        guardar_cotizacion(json_actualizado)

        self._volver_a_revisar()

    def _volver_a_revisar(self):
        from ui.interfaz import VentanaPrincipal
        self.destroy()
        root = VentanaPrincipal()
        root.after(0, root._abrir_revisar_cotizaciones)
        root.mainloop()

    def _on_cerrar_resumen(self):
        # El usuario cerró el resumen sin confirmar → volver a medidas
        self.deiconify()
        self.lift()
        self.focus_force()
        self._mostrar_medidas(desde_resumen=True)

    def _volver(self, _=None):
        if self._edicion:
            self._volver_a_revisar()
            return
        from ui.interfaz import VentanaPrincipal
        self.destroy()
        VentanaPrincipal().mainloop()


# ══════════════════════════════════════════════════════════════════════════════
# Pantalla de medidas
# ══════════════════════════════════════════════════════════════════════════════

class PantallaMedidas(PantallaMedidasBase):

    def __init__(self, parent, ventana_raiz, indice, total,
                 datos_previos, datos_todos, tela_defecto,
                 on_siguiente, on_nav):
        super().__init__(parent, ventana_raiz, indice, total,
                          datos_previos, datos_todos, on_siguiente, on_nav)

        self._rotado = False

        if datos_previos:
            tela_ini = datos_previos["tela"]
            caja_ini = datos_previos.get("caja", "Sin caja")
        else:
            tela_ini = tela_defecto
            caja_ini = "Sin caja"

        self._var_tela = tk.StringVar(value=tela_ini)
        self._var_caja = tk.StringVar(value=caja_ini)

        self._construir_ui()

        self._var_tela.trace_add("write",  self._actualizar)
        self._var_alto.trace_add("write",  self._actualizar)
        self._var_ancho.trace_add("write", self._actualizar)
        self._var_cant.trace_add("write",  self._actualizar)
        self._var_tema.trace_add("write",  self._actualizar)

        self._actualizar()
        ventana_raiz.bind("<Return>", lambda _: self._enter_sig())

    # ── Sección superior: selección de tela y caja ──────────────────────────────
    def _construir_seccion_superior(self, sup):
        tk.Label(sup,
                 text=f"Cotizador Backlight  ·  Producto {self._indice+1} de {self._total}",
                 font=FUENTE_SUBTITULO, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Label(sup, text="Selección de Tela", font=FUENTE_TITULO,
                 bg=COLORES["fondo"], fg=COLORES["texto"]).pack(anchor="w", pady=(4, 10))
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.TCombobox",
                        fieldbackground="#FFFFFF", background="#FFFFFF",
                        foreground=COLORES["texto"], arrowcolor=COLORES["acento"],
                        bordercolor=COLORES["borde"], relief="flat")

        fila_seleccion = tk.Frame(sup, bg=COLORES["fondo"])
        fila_seleccion.pack(anchor="w")

        grp_tela = tk.Frame(fila_seleccion, bg=COLORES["fondo"])
        grp_tela.pack(side="left")
        tk.Label(grp_tela, text="Tela", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._combo = ttk.Combobox(grp_tela, textvariable=self._var_tela,
                                   values=[n for n, _ in TELAS],
                                   state="readonly", style="Custom.TCombobox",
                                   width=24, font=FUENTE_MEDIDA)
        self._combo.pack(anchor="w", ipady=4)

        grp_caja = tk.Frame(fila_seleccion, bg=COLORES["fondo"])
        grp_caja.pack(side="left", padx=(16, 0))
        tk.Label(grp_caja, text="Caja / Perfil", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._combo_caja = ttk.Combobox(grp_caja, textvariable=self._var_caja,
                                        values=LISTA_CAJAS,
                                        state="readonly", style="Custom.TCombobox",
                                        width=30, font=FUENTE_MEDIDA)
        self._combo_caja.pack(anchor="w", ipady=4)

        self._crear_lbl_ancho_tela(sup)

    def _tela_activa(self):
        n = self._var_tela.get()
        for nombre, ancho in TELAS:
            if nombre == n:
                return nombre, ancho
        return None

    # ── Lógica ────────────────────────────────────────────────────────────────
    def _actualizar(self, *_):
        tela  = self._tela_activa()
        alto  = self._parse_float(self._var_alto)
        ancho = self._parse_float(self._var_ancho)
        cant  = self._parse_int(self._var_cant)

        self._lbl_ancho_tela.config(
            text=f"Ancho máximo de impresión: {tela[1]:.2f} m" if tela else "")

        if not (alto and ancho and alto > 0 and ancho > 0):
            self._lbl_rotacion.config(text="")
            self._lbl_error.config(text="")
            self._btn_omitir.pack_forget()
            self._dibujar_vacio()
            self._set_btn(False)
            return

        lado_corto = min(alto, ancho)
        self._rotado = False
        error = False

        if tela and lado_corto > tela[1]:
            self._rotado = True
            error = True

        if error:
            self._lbl_rotacion.config(text="")
            self._lbl_error.config(
                text=f"⚠ El lado corto ({lado_corto:.2f} m) excede el ancho "
                     f"máximo de la tela ({tela[1]:.2f} m).")
            if not self._omitir_activo:
                self._btn_omitir.pack(anchor="w", pady=(8, 0))
            else:
                self._btn_omitir.pack_forget()
        else:
            self._omitir_activo = False
            self._btn_omitir.pack_forget()
            self._lbl_error.config(text="")
            self._lbl_rotacion.config(
                text="↺ La impresión será rotada para ajustarse a la tela."
                if (self._rotado and tela) else "")

        if error and self._omitir_activo:
            self._set_btn(tela is not None and cant is not None)
            self._dibujar_rect(alto, ancho, "#F0C040")
        elif error:
            self._set_btn(False)
            self._dibujar_rect(alto, ancho, COLORES["error"])
        else:
            self._set_btn(tela is not None and cant is not None)
            self._dibujar_rect(alto, ancho, COLORES["rect_relleno"])

    def _dibujar_rect(self, alto, ancho, color):
        self._canvas.delete("all")
        ad = ancho if self._rotado else alto
        aw = alto  if self._rotado else ancho

        rh, rw = (MAX_LADO, MAX_LADO * (aw/ad)) if ad >= aw else (MAX_LADO * (ad/aw), MAX_LADO)

        x1, y1 = MARGEN, MARGEN
        x2, y2 = x1 + rw, y1 + rh

        self._canvas.create_rectangle(x1, y1, x2, y2,
                                      fill=color, outline=COLORES["rect_borde"], width=2)
        self._canvas.create_text((x1+x2)/2, y1-6, text=f"{aw} m",
                                 font=FUENTE_MEDIDA, fill=COLORES["texto"], anchor="s")
        self._canvas.create_text(x1-8, (y1+y2)/2, text=f"{ad} m",
                                 font=FUENTE_MEDIDA, fill=COLORES["texto"],
                                 anchor="e", angle=90)

    def _siguiente(self):
        tela = self._tela_activa()
        self._on_siguiente({
            "tela":      tela[0],
            "caja":      self._var_caja.get(),
            "ancho_max": tela[1],
            "alto":      float(self._var_alto.get().replace(",", ".")),
            "ancho":     float(self._var_ancho.get().replace(",", ".")),
            "cantidad":  int(self._var_cant.get()),
            "tema":      self._var_tema.get().strip() if hasattr(self, "_var_tema") else "",
            "obs":       self._var_obs.get().strip() if hasattr(self, "_var_obs") else "",
            "rotado":    self._rotado,
        })
