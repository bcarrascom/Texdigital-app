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
    FUENTE_AVISO,
    FUENTE_TABLA_CAB,
    FUENTE_TABLA,
    MAX_LADO,
    MARGEN,
    MARGEN_SUP,
    _construir_cabecera,
    _centrar,
)
from ui.pantalla_inicio import PantallaInicio
from ui.pantalla_medidas_base import PantallaMedidasBase
from core.repositorio import TEXTILES_ANCHOS, PERFILES, LUCES, FUENTES_PODER
from core.calculo_cajas import calcular_caja, luces1_default, es_perfil_60

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

# "Sin caja" es un valor centinela de la UI, no vive en perfiles.json (ese
# archivo es solo el catálogo de perfiles reales, editable en Dropbox/SGTD/Conf).
SIN_CAJA = "Sin caja"
OPCIONES_CAJA = [SIN_CAJA] + PERFILES
OPCIONES_LUCES = [l["corto"] for l in LUCES]  # incluye "sin luces" (viene del catálogo)

def _texto_cantidad(valor: float) -> str:
    """Texto a mostrar para una cantidad de la tabla de materiales. Traseras
    y FP ya vienen redondeados hacia arriba desde calcular_caja() (son
    unidades enteras — una plancha, una fuente de poder), así que acá no
    hace falta distinguir por material: si el valor ya es entero se muestra
    sin decimales, si no (Perfil, Luces) se muestran con 2 decimales."""
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.2f}"


def _desempaquetar_caja(valor) -> dict:
    """
    A partir del valor guardado en datos_previos["caja"] (SIN_CAJA, un
    string viejo con solo el perfil, o el dict con el detalle completo que
    arma _siguiente()), devuelve los valores iniciales para los campos del
    formulario de caja.
    """
    base = {
        "perfil": SIN_CAJA, "luces1": "M12", "luces2": "sin luces",
        "malla12v_1": "", "malla12v_2": "", "luces1_tocado": False,
    }
    if not valor or valor == SIN_CAJA:
        return base
    if isinstance(valor, str):
        # Formato de antes de esta funcionalidad: perfil sin detalle de luces.
        base["perfil"] = valor
        return base
    base["perfil"] = valor.get("perfil") or SIN_CAJA
    luces1 = valor.get("luces_1") or {}
    luces2 = valor.get("luces_2") or {}
    base["luces1"] = luces1.get("tipo") or "M12"
    base["luces2"] = luces2.get("tipo") or "sin luces"
    if base["luces1"].strip().lower() == "malla 12v":
        base["malla12v_1"] = str(luces1.get("cantidad_x_caja", ""))
    if base["luces2"].strip().lower() == "malla 12v":
        base["malla12v_2"] = str(luces2.get("cantidad_x_caja", ""))
    base["luces1_tocado"] = True  # ya venía con una elección guardada
    return base

# Ancho de columnas del resumen — ajustar aquí si la tabla queda angosta/ancha
# Orden: #, Textil, Tema, Cantidad, Alto, Ancho, Área
RESUMEN_COL_W = [_esc.px(v) for v in [35, 130, 130, 90, 90, 90, 100]]


# ══════════════════════════════════════════════════════════════════════════════
# Ventana principal — gestiona el flujo completo
# ══════════════════════════════════════════════════════════════════════════════

class CotizadorBacklight(tk.Tk):

    # TAM_MEDIDAS incluye el espacio para la sección de caja (Luces 1/2 +
    # tabla de materiales), que ocupa espacio fijo aunque el producto no
    # tenga caja (se oculta el contenido, no se achica la ventana).
    if sys.platform == "darwin":
        TAM_CANTIDAD = (_esc.px(800), _esc.px(730))
        TAM_MEDIDAS  = (_esc.px(1100), _esc.px(1550))
    else:
        TAM_CANTIDAD = (_esc.px(800), _esc.px(560))
        TAM_MEDIDAS  = (_esc.px(960), _esc.px(1280))

    def __init__(self, edicion: dict | None = None):
        super().__init__()
        self.title("Cotizador Backlight")
        self.configure(bg=COLORES["fondo"])
        # En macOS las fuentes nativas a veces desbordan el alto fijo
        # calculado; se deja redimensionar a mano para asegurar que todo
        # quepa. En Windows/Linux el tamaño fijo ya está afinado.
        self.resizable(sys.platform == "darwin", sys.platform == "darwin")
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
        # Despacho (opcional, ver ui/pantalla_despacho.py): todavía no se
        # generan guías de despacho, pero igual se cobra — no es un
        # producto, es un monto aparte que se suma al total.
        self._con_despacho     = False
        self._despacho_valor: float | None = None
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
            despacho_json = edicion["json"].get("Despacho")
            if despacho_json is not None:
                self._con_despacho   = True
                self._despacho_valor = float(despacho_json)
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

    def _on_cantidad_confirmada(self, y: int, nombre: str, con_despacho: bool):
        self._total_productos  = y
        self._nombre_trabajo   = nombre
        self._datos            = [None] * y
        self._iteracion_actual = 0
        self._con_despacho     = con_despacho
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
            con_despacho=self._con_despacho,
            despacho_completo=self._despacho_valor is not None,
        )

    def _mostrar_despacho(self, volver_a_resumen: bool):
        self._despacho_volver_resumen = volver_a_resumen
        self._limpiar()
        _centrar(self, *self.TAM_CANTIDAD)
        from ui.pantalla_despacho import PantallaDespacho
        PantallaDespacho(
            self._area, subtitulo="Cotizador Backlight",
            valor_inicial=self._despacho_valor,
            on_confirmar=self._on_despacho_confirmado,
        )

    def _on_despacho_confirmado(self, valor: float):
        self._despacho_valor = valor
        if self._despacho_volver_resumen:
            self._abrir_resumen()
        else:
            self._mostrar_medidas(desde_resumen=self._desde_resumen)

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
        elif self._con_despacho and self._despacho_valor is None:
            self._mostrar_despacho(volver_a_resumen=True)
        else:
            self._abrir_resumen()

    def _on_nav(self, indice: int):
        if indice == self._total_productos:
            if self._con_despacho:
                self._mostrar_despacho(volver_a_resumen=self._desde_resumen)
            return
        if self._datos[indice] is not None or indice == self._iteracion_actual:
            self._iteracion_actual = indice
            self._mostrar_medidas(desde_resumen=self._desde_resumen)

    def _abrir_resumen(self):
        from ui.ventana_resumen import VentanaResumen

        COLS = ["#", "Textil", "Tema", "Cantidad", "Ancho (m)", "Alto (m)", "M² imp."]

        filas      = []
        total_cant = 0
        total_m2   = 0.0

        for i, d in enumerate(self._datos):
            # Backlight se imprime en el área exacta pedida, sin encajar
            # varias unidades a lo ancho del rollo (eso es solo para
            # productos no-backlight, ver _calc_ml en ui/cotizacion.py) —
            # el área es simplemente Alto × Ancho × Cantidad.
            m2 = d["alto"] * d["ancho"] * d["cantidad"]
            total_cant += d["cantidad"]
            total_m2   += m2
            filas.append([
                str(i + 1),
                d["tela"],
                d.get("tema", ""),
                str(d["cantidad"]),
                str(d["ancho"]),
                str(d["alto"]),
                f"{m2:.4f}",
            ])

        total_m2 = round(total_m2, 4)
        totales  = ["", "TOTAL", "", str(total_cant), "", "", f"{total_m2:.4f}"]

        fila_despacho = None
        if self._con_despacho and self._despacho_valor is not None:
            from core.precios import formatear_clp
            fila_despacho = (["Despacho"] + [""] * (len(COLS) - 2)
                              + [formatear_clp(self._despacho_valor)])

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
            on_agregar=self._on_agregar_desde_resumen,
            on_eliminar=self._on_eliminar_desde_resumen,
            fila_despacho=fila_despacho,
        )

    def _on_agregar_desde_resumen(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self._datos.append(None)
        self._total_productos = len(self._datos)
        self._iteracion_actual = self._total_productos - 1
        self._mostrar_medidas(desde_resumen=True)

    def _on_eliminar_desde_resumen(self, indice: int):
        del self._datos[indice]
        self._total_productos = len(self._datos)
        self._abrir_resumen()

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
            despacho=self._despacho_valor if self._con_despacho else None,
        )

    # ── Modo edición (cotización ya guardada, viene de Revisar Cotizaciones) ──

    def _guardar_edicion_y_volver(self):
        from core.precios import costo_cotizacion
        from core.repositorio_cotizaciones import (
            guardar_cotizacion, mapear_producto, producto_desde_json,
        )

        json_actualizado = dict(self._edicion["json"])
        json_actualizado["productos"] = [mapear_producto(d) for d in self._datos]
        if self._con_despacho and self._despacho_valor is not None:
            json_actualizado["Despacho"] = self._despacho_valor
        else:
            json_actualizado.pop("Despacho", None)

        productos_internos = [producto_desde_json(p) for p in json_actualizado["productos"]]
        descuento_pct = json_actualizado.get("Descuento", 0.0) or 0.0
        totales = costo_cotizacion(productos_internos, descuento_pct,
                                    despacho=self._despacho_valor or 0.0)
        json_actualizado["Neto"]      = totales["neto"]
        json_actualizado["NetoTotal"] = totales["neto_total"]
        json_actualizado["IVA"]       = totales["iva"]
        json_actualizado["Total"]     = totales["total"]

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
                 on_siguiente, on_nav,
                 con_despacho=False, despacho_completo=False):
        super().__init__(parent, ventana_raiz, indice, total,
                          datos_previos, datos_todos, on_siguiente, on_nav,
                          con_despacho=con_despacho, despacho_completo=despacho_completo)

        self._rotado = False

        if datos_previos:
            tela_ini = datos_previos["tela"]
            caja_ini = _desempaquetar_caja(datos_previos.get("caja", SIN_CAJA))
        else:
            tela_ini = tela_defecto
            caja_ini = _desempaquetar_caja(SIN_CAJA)

        self._var_tela   = tk.StringVar(value=tela_ini)
        self._var_caja   = tk.StringVar(value=caja_ini["perfil"])
        self._var_luces1 = tk.StringVar(value=caja_ini["luces1"])
        self._var_luces2 = tk.StringVar(value=caja_ini["luces2"])
        self._var_malla12v_1 = tk.StringVar(value=caja_ini["malla12v_1"])
        self._var_malla12v_2 = tk.StringVar(value=caja_ini["malla12v_2"])
        # Si ya venía con una elección de Luces 1 guardada (edición), no se
        # pisa con el default al recalcular por cambios de Ancho/Alto/Perfil.
        self._luces1_tocado = caja_ini["luces1_tocado"]
        # Guard de reentrancia: True mientras _actualizar_caja() está
        # asignando el default de Luces 1 por código. Sin esto, no hay forma
        # confiable de distinguir "el usuario eligió una luz" de "el código
        # acaba de poner el default" — el trace de escritura de la variable
        # se dispara en ambos casos, y su orden contra <<ComboboxSelected>>
        # no está garantizado (podría marcar "tocado" tarde y perder la
        # elección real del usuario).
        self._seteando_default_luces1 = False
        self._ultima_tabla = None  # última tabla calculada, para _siguiente()

        self._construir_ui()

        self._var_tela.trace_add("write",  self._actualizar)
        self._var_alto.trace_add("write",  self._actualizar)
        self._var_ancho.trace_add("write", self._actualizar)
        self._var_cant.trace_add("write",  self._actualizar)
        self._var_tema.trace_add("write",  self._actualizar)
        self._var_caja.trace_add("write",       self._actualizar_caja)
        self._var_luces1.trace_add("write",     self._on_luces1_cambiada)
        self._var_luces2.trace_add("write",     self._actualizar_caja)
        self._var_malla12v_1.trace_add("write", self._actualizar_caja)
        self._var_malla12v_2.trace_add("write", self._actualizar_caja)
        self._var_alto.trace_add("write",  self._actualizar_caja)
        self._var_ancho.trace_add("write", self._actualizar_caja)
        self._var_cant.trace_add("write",  self._actualizar_caja)
        self._var_forzar.trace_add("write", self._actualizar)

        self._actualizar()
        self._actualizar_caja()
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
                                        values=OPCIONES_CAJA,
                                        state="readonly", style="Custom.TCombobox",
                                        width=30, font=FUENTE_MEDIDA)
        self._combo_caja.pack(anchor="w", ipady=4)

        self._crear_lbl_ancho_tela(sup)
        self._construir_seccion_caja(sup)

    def _construir_seccion_caja(self, sup):
        """Luces 1/2 + tabla de materiales, visible solo si Caja != Sin caja.
        El frame se arma siempre (para que exista Ancho/Alto/etc.) pero se
        empaqueta/oculta desde _actualizar_caja()."""
        self._frame_caja = tk.Frame(sup, bg=COLORES["fondo"])

        fila_luces = tk.Frame(self._frame_caja, bg=COLORES["fondo"])
        fila_luces.pack(anchor="w", pady=(10, 0))

        grp_l1 = tk.Frame(fila_luces, bg=COLORES["fondo"])
        grp_l1.pack(side="left")
        tk.Label(grp_l1, text="Luces 1", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._combo_luces1 = ttk.Combobox(grp_l1, textvariable=self._var_luces1,
                                          values=OPCIONES_LUCES, state="readonly",
                                          style="Custom.TCombobox", width=13, font=FUENTE_MEDIDA)
        self._combo_luces1.pack(anchor="w", ipady=4)

        grp_l2 = tk.Frame(fila_luces, bg=COLORES["fondo"])
        grp_l2.pack(side="left", padx=(16, 0))
        tk.Label(grp_l2, text="Luces 2", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        self._combo_luces2 = ttk.Combobox(grp_l2, textvariable=self._var_luces2,
                                          values=OPCIONES_LUCES, state="readonly",
                                          style="Custom.TCombobox", width=13, font=FUENTE_MEDIDA)
        self._combo_luces2.pack(anchor="w", ipady=4)

        vcmd = (self.register(self._validar_numero), "%P")

        self._grp_malla12v_1 = tk.Frame(fila_luces, bg=COLORES["fondo"])
        tk.Label(self._grp_malla12v_1, text="Cant. x caja (Malla 12v)", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Entry(self._grp_malla12v_1, textvariable=self._var_malla12v_1,
                 validate="key", validatecommand=vcmd,
                 font=FUENTE_MEDIDA, width=8, relief="flat", bd=0,
                 bg="#FFFFFF", fg=COLORES["texto"], insertbackground=COLORES["texto"],
                 highlightthickness=1, highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"]).pack(ipady=6, ipadx=6)
        # Se empaqueta solo cuando Luces 1 == "Malla 12v" (ver _actualizar_caja)

        self._grp_malla12v_2 = tk.Frame(fila_luces, bg=COLORES["fondo"])
        tk.Label(self._grp_malla12v_2, text="Cant. x caja (Malla 12v)", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Entry(self._grp_malla12v_2, textvariable=self._var_malla12v_2,
                 validate="key", validatecommand=vcmd,
                 font=FUENTE_MEDIDA, width=8, relief="flat", bd=0,
                 bg="#FFFFFF", fg=COLORES["texto"], insertbackground=COLORES["texto"],
                 highlightthickness=1, highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"]).pack(ipady=6, ipadx=6)
        # Se empaqueta solo cuando Luces 2 == "Malla 12v" (ver _actualizar_caja)

        self._lbl_watts = tk.Label(self._frame_caja, text="", font=FUENTE_AVISO,
                                   bg=COLORES["fondo"], fg=COLORES["texto_suave"])
        self._lbl_watts.pack(anchor="w", pady=(8, 0))

        self._frame_tabla = tk.Frame(self._frame_caja, bg=COLORES["fondo"])
        self._frame_tabla.pack(anchor="w", pady=(4, 0), fill="x")

    def _on_luces1_cambiada(self, *_):
        """Trace de escritura de _var_luces1. Si el cambio no vino de
        _actualizar_caja() asignando el default (ver _seteando_default_luces1),
        es una elección real del usuario: la marca como tocada para que no
        se vuelva a pisar con el default."""
        if not self._seteando_default_luces1:
            self._luces1_tocado = True
        self._actualizar_caja()

    def _limpiar_tabla(self):
        for w in self._frame_tabla.winfo_children():
            w.destroy()

    def _rebuild_tabla(self, tabla):
        self._limpiar_tabla()
        columnas = ["Material", "Tipo", "Cant. x caja", "Cant. total"]
        col_w = [80, 300, 90, 90]
        for col, w in enumerate(col_w):
            self._frame_tabla.columnconfigure(col, minsize=w)
        for col, txt in enumerate(columnas):
            tk.Label(self._frame_tabla, text=txt, font=FUENTE_TABLA_CAB,
                     bg=COLORES["tabla_cab"], fg="#FFFFFF",
                     anchor="w", padx=6, pady=4).grid(row=0, column=col, sticky="ew")
        for i, fila in enumerate(tabla["filas"]):
            bg = COLORES["tabla_fila1"] if i % 2 == 0 else COLORES["tabla_fila2"]
            tipo_txt = fila["tipo"] or "—"
            if fila.get("pendiente_manual"):
                tipo_txt += "  (falta ingresar cantidad)"
            valores = [
                fila["material"], tipo_txt,
                _texto_cantidad(fila["cantidad_x_caja"]),
                _texto_cantidad(fila["cantidad_total"]),
            ]
            for col, val in enumerate(valores):
                tk.Label(self._frame_tabla, text=val, font=FUENTE_TABLA,
                         bg=bg, fg=COLORES["texto"], anchor="w", padx=6, pady=4
                         ).grid(row=i + 1, column=col, sticky="ew")

    def _actualizar_caja(self, *_):
        perfil = self._var_caja.get()
        if perfil == SIN_CAJA:
            self._frame_caja.pack_forget()
            self._ultima_tabla = None
            return

        self._frame_caja.pack(anchor="w", fill="x")

        alto  = self._parse_float(self._var_alto)
        ancho = self._parse_float(self._var_ancho)
        cant  = self._parse_int(self._var_cant)
        dimensiones_ok = bool(alto and ancho and alto > 0 and ancho > 0)

        # Default de Luces 1 (§4) si el usuario no lo eligió a mano — al
        # cambiar el valor, este mismo trace se vuelve a disparar solo, así
        # que no hace falta seguir con el resto de este cálculo acá.
        # PERFIL 60 MM es un caso especial: su default (Malla 150) NO
        # depende de Ancho/Alto, así que se aplica apenas se elige el
        # perfil — si esperáramos a que las medidas sean válidas como con
        # el resto de los perfiles, el combo de Luces 1 se quedaría
        # mostrando el valor anterior y parecería que no pasó nada.
        if not self._luces1_tocado:
            if es_perfil_60(perfil):
                nuevo_default = "Malla 150"
            elif dimensiones_ok:
                nuevo_default = luces1_default(perfil, ancho, alto)
            else:
                nuevo_default = None
            if nuevo_default is not None and self._var_luces1.get() != nuevo_default:
                self._seteando_default_luces1 = True
                try:
                    self._var_luces1.set(nuevo_default)
                finally:
                    self._seteando_default_luces1 = False
                return

        if not dimensiones_ok:
            self._limpiar_tabla()
            self._lbl_watts.config(text="")
            self._ultima_tabla = None
            return

        luces1 = self._var_luces1.get()
        luces2 = self._var_luces2.get()

        if luces1.strip().lower() == "malla 12v":
            self._grp_malla12v_1.pack(side="left", padx=(16, 0))
        else:
            self._grp_malla12v_1.pack_forget()
        if luces2.strip().lower() == "malla 12v":
            self._grp_malla12v_2.pack(side="left", padx=(16, 0))
        else:
            self._grp_malla12v_2.pack_forget()

        cant_manual_1 = self._parse_float(self._var_malla12v_1)
        cant_manual_2 = self._parse_float(self._var_malla12v_2)

        tabla = calcular_caja(
            ancho=ancho, alto=alto, cantidad=cant or 1, perfil=perfil,
            luces1=luces1, luces2=luces2,
            catalogo_luces=LUCES, catalogo_fp=FUENTES_PODER,
            cantidad_malla12v_1=cant_manual_1, cantidad_malla12v_2=cant_manual_2,
        )
        self._ultima_tabla = tabla
        self._lbl_watts.config(
            text=f"Watts totales por caja: {tabla['watts']:.0f} W" if tabla["watts"] else "Sin luces — sin watts")
        self._rebuild_tabla(tabla)

    def _valor_caja_guardado(self):
        """Arma el valor a guardar en datos["caja"]: SIN_CAJA, o el detalle
        completo calculado (ver core/calculo_cajas.calcular_caja)."""
        perfil = self._var_caja.get()
        if perfil == SIN_CAJA or self._ultima_tabla is None:
            return SIN_CAJA

        tabla = self._ultima_tabla

        def _fila(material):
            return next(f for f in tabla["filas"] if f["material"] == material)

        def _sub(material):
            f = _fila(material)
            return {"tipo": f["tipo"], "cantidad_x_caja": f["cantidad_x_caja"],
                    "cantidad_total": f["cantidad_total"]}

        return {
            "perfil": perfil,
            "watts": tabla["watts"],
            "traseras": _sub("Traseras"),
            "luces_1": _sub("Luces 1"),
            "luces_2": _sub("Luces 2"),
            "fp": _sub("FP"),
            "obs": "",
        }

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
        else:
            self._lbl_error.config(text="")
            self._lbl_rotacion.config(
                text="↺ La impresión será rotada para ajustarse a la tela."
                if (self._rotado and tela) else "")

        forzado = self._var_forzar.get()
        if error and forzado:
            self._set_btn(tela is not None and cant is not None, forzado=True)
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

        x1, y1 = MARGEN, MARGEN_SUP
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
            "caja":      self._valor_caja_guardado(),
            "ancho_max": tela[1],
            "alto":      float(self._var_alto.get().replace(",", ".")),
            "ancho":     float(self._var_ancho.get().replace(",", ".")),
            "cantidad":  int(self._var_cant.get()),
            "tema":      self._var_tema.get().strip() if hasattr(self, "_var_tema") else "",
            "obs":       self._var_obs.get().strip() if hasattr(self, "_var_obs") else "",
            "rotado":    self._rotado,
        })
