"""
ui/revisar_cotizaciones.py
Ventana que lista las cotizaciones guardadas en JSON. Doble clic edita la
cotización; "Aprobar" la promueve a Orden de Producción (OP).
"""

import json
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

    # Colores del botón Aprobar (habilitado solo con exactamente 1 seleccionada)
    _C_APROB_OFF    = "#9E9E9E"
    _C_APROB_OFF_HV = "#BDBDBD"
    _C_APROB_ON     = COLORES["ok"]
    _C_APROB_ON_HV  = "#2ECC71"

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
        self._aprob_on     = False

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
                 text="Doble clic sobre una fila para editarla.",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w", padx=20, pady=(12, 6))

        # ── Footer empacado ANTES del árbol para que expand=True no lo tape ──

        # Barra de botones
        frame_botones = tk.Frame(self, bg=COLORES["fondo"])
        frame_botones.pack(side="bottom", fill="x", padx=20, pady=(8, 16))

        self._btn_eliminar = tk.Label(
            frame_botones, text="Eliminar",
            font=FUENTE_BTN, bg=self._C_ELIM_OFF,
            fg="#FFFFFF", padx=16, pady=8, cursor="arrow",
        )
        self._btn_eliminar.pack(side="left")

        self._btn_aprobar = tk.Label(
            frame_botones, text="Aprobar",
            font=FUENTE_BTN, bg=self._C_APROB_OFF,
            fg="#FFFFFF", padx=16, pady=8, cursor="arrow",
        )
        self._btn_aprobar.pack(side="right")

        # Frame intermedio: ocupa el espacio restante entre Eliminar y Aprobar,
        # con "Seleccionar múltiples" centrado dentro de él.
        frame_centro = tk.Frame(frame_botones, bg=COLORES["fondo"])
        frame_centro.pack(side="left", fill="both", expand=True)

        self._btn_multi = tk.Label(
            frame_centro, text="Seleccionar múltiples",
            font=FUENTE_BTN, bg=self._C_MULTI_OFF,
            fg=COLORES["texto"], padx=16, pady=8, cursor="hand2",
        )
        self._btn_multi.place(relx=0.5, rely=0.5, anchor="center")

        self._btn_aprobar.bind("<Enter>",    self._on_aprob_enter)
        self._btn_aprobar.bind("<Leave>",    self._on_aprob_leave)
        self._btn_aprobar.bind("<Button-1>", self._on_click_aprobar)

        self._btn_eliminar.bind("<Enter>",    self._on_elim_enter)
        self._btn_eliminar.bind("<Leave>",    self._on_elim_leave)
        self._btn_eliminar.bind("<Button-1>", self._on_eliminar)

        self._btn_multi.bind("<Enter>",    self._on_multi_enter)
        self._btn_multi.bind("<Leave>",    self._on_multi_leave)
        self._btn_multi.bind("<Button-1>", self._toggle_multi_select)

        # Mensaje de estado (también bottom, encima del barra de botones)
        self._lbl_estado = tk.Label(
            self, text="", font=FUENTE_LABEL,
            bg=COLORES["fondo"], fg=COLORES["error"],
            wraplength=_esc.px(830), justify="left",
        )
        self._lbl_estado.pack(side="bottom", anchor="w", padx=20, pady=(0, 4))

        # ── Tabla (al final, recibe todo el espacio restante) ──
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
        # Teclado — return "break" para anular los bindings de clase del Treeview
        self._tree.bind("<Up>",          self._on_key_up)
        self._tree.bind("<Down>",        self._on_key_down)
        self._tree.bind("<Shift-Up>",    self._on_key_shift_up)
        self._tree.bind("<Shift-Down>",  self._on_key_shift_down)
        self._tree.bind("<Return>",      self._on_key_return)

        # Click fuera de árbol y botones → deseleccionar
        self._safe_widgets = {self._tree, self._btn_aprobar, self._btn_eliminar,
                              self._btn_multi}
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
        self._actualizar_btn_aprobar()

    def _on_window_click(self, event):
        """Deselecciona al hacer click fuera del árbol y los botones."""
        w = event.widget
        while w is not None and w is not self:
            if w in self._safe_widgets:
                return
            w = getattr(w, "master", None)
        self._tree.selection_set([])

    # ── Botón Aprobar ──────────────────────────────────────────────────────────

    def _actualizar_btn_aprobar(self):
        habilitado = len(self._selected) == 1
        if habilitado == self._aprob_on:
            return
        self._aprob_on = habilitado
        if habilitado:
            self._btn_aprobar.config(bg=self._C_APROB_ON, fg="#FFFFFF", cursor="hand2")
        else:
            self._btn_aprobar.config(bg=self._C_APROB_OFF, fg="#FFFFFF", cursor="arrow")

    def _on_aprob_enter(self, _):
        self._btn_aprobar.config(
            bg=self._C_APROB_ON_HV if self._aprob_on else self._C_APROB_OFF_HV)

    def _on_aprob_leave(self, _):
        self._btn_aprobar.config(
            bg=self._C_APROB_ON if self._aprob_on else self._C_APROB_OFF)

    def _on_click_aprobar(self, _):
        if self._aprob_on:
            self._dialogo_aprobar_directo()

    def _dialogo_aprobar_directo(self):
        sel = list(self._selected)
        if len(sel) != 1:
            return
        iid = sel[0]

        archivo = next((e[3] for e in self._entradas if str(e[0]) == iid), None)
        if archivo is None:
            return
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except Exception:
            self._lbl_estado.config(
                text="⚠ No se pudo leer el archivo de la cotización.",
                fg=COLORES["error"])
            return

        from datetime import datetime
        from ui.dialogo_aprobar import _fecha_valida, promover_a_op

        dlg = tk.Toplevel(self)
        dlg.title("Aprobar cotización")
        dlg.configure(bg=COLORES["fondo"])
        dlg.resizable(False, False)
        dlg.transient(self)

        ancho, alto = _esc.px(630), _esc.px(480)
        ox = self.winfo_x() + (self.ANCHO - ancho) // 2
        oy = self.winfo_y() + (self.ALTO  - alto)  // 2
        dlg.geometry(f"{ancho}x{alto}+{ox}+{oy}")
        dlg.grab_set()

        # Botones empacados ANTES (side="bottom") para que expand=True del
        # mensaje no los tape — mismo bug que en el listado de cotizaciones.
        frame_btns = tk.Frame(dlg, bg=COLORES["fondo"])
        frame_btns.pack(side="bottom", fill="x", padx=36, pady=(0, 27))

        frame_msg = tk.Frame(dlg, bg=COLORES["fondo"], padx=36, pady=30)
        frame_msg.pack(fill="both", expand=True)

        tk.Label(frame_msg, text="Aprobar una cotización la volverá una OP",
                 font=FUENTE_TITULO, bg=COLORES["fondo"], fg=COLORES["texto"],
                 wraplength=_esc.px(540), justify="center").pack(pady=(0, 18))

        hoy = datetime.now()

        def _crear_cajas_fecha(parent, dia_ini, mes_ini, anio_ini, on_cambio=None):
            """
            Fila de 3 cajas (día / mes / año) que avanzan solas: al
            completar 2 dígitos válidos en día o mes, salta a la siguiente
            caja. Si se deja un solo dígito y se sale de la caja, se
            rellena con un cero (3 -> 03). En el año, si se sale con 2
            dígitos, se expanden a 20XX (26 -> 2026).
            `on_cambio` (opcional) se llama en cada cambio de valor.
            Devuelve (valor, primer_entry): valor() arma "dd/mm/aaaa".
            """
            fila = tk.Frame(parent, bg=COLORES["fondo"])
            fila.pack(anchor="w")

            var_dia  = tk.StringVar(value=dia_ini)
            var_mes  = tk.StringVar(value=mes_ini)
            var_anio = tk.StringVar(value=anio_ini)

            def _caja(var, ancho):
                e = tk.Entry(fila, textvariable=var, font=FUENTE_LABEL,
                             width=ancho, justify="center", relief="flat", bd=0,
                             bg="#FFFFFF", fg=COLORES["texto"],
                             insertbackground=COLORES["texto"],
                             highlightthickness=1, highlightbackground=COLORES["borde"],
                             highlightcolor=COLORES["acento"])
                e.pack(side="left", ipady=9, ipadx=6)
                return e

            e_dia = _caja(var_dia, 3)
            tk.Label(fila, text="/", font=FUENTE_LABEL, bg=COLORES["fondo"],
                     fg=COLORES["texto_suave"]).pack(side="left", padx=3)
            e_mes = _caja(var_mes, 3)
            tk.Label(fila, text="/", font=FUENTE_LABEL, bg=COLORES["fondo"],
                     fg=COLORES["texto_suave"]).pack(side="left", padx=3)
            e_anio = _caja(var_anio, 5)

            def _seleccionar_todo(entry):
                entry.after_idle(lambda: (entry.selection_range(0, "end"), entry.icursor("end")))

            def _validar(texto, tope):
                if texto and not texto.isdigit():
                    return False
                if len(texto) > 2:
                    return False
                if len(texto) == 2 and not (1 <= int(texto) <= tope):
                    return False
                return True

            vc_dia  = dlg.register(lambda t: _validar(t, 31))
            vc_mes  = dlg.register(lambda t: _validar(t, 12))
            vc_anio = dlg.register(lambda t: t == "" or (t.isdigit() and len(t) <= 4))

            e_dia.config(validate="key",  validatecommand=(vc_dia, "%P"))
            e_mes.config(validate="key",  validatecommand=(vc_mes, "%P"))
            e_anio.config(validate="key", validatecommand=(vc_anio, "%P"))

            def _notificar_cambio(_e=None):
                if on_cambio:
                    on_cambio()

            def _avanzar_si_completo(var, siguiente, _e=None):
                if len(var.get()) == 2:
                    siguiente.focus_set()

            def _normalizar(_e=None):
                if len(var_dia.get())  == 1: var_dia.set(var_dia.get().zfill(2))
                if len(var_mes.get())  == 1: var_mes.set(var_mes.get().zfill(2))
                if len(var_anio.get()) == 2: var_anio.set("20" + var_anio.get())
                _notificar_cambio()

            e_dia.bind("<KeyRelease>", lambda e: (_avanzar_si_completo(var_dia, e_mes), _notificar_cambio()))
            e_mes.bind("<KeyRelease>", lambda e: (_avanzar_si_completo(var_mes, e_anio), _notificar_cambio()))
            e_anio.bind("<KeyRelease>", _notificar_cambio)
            e_dia.bind("<FocusOut>",  _normalizar)
            e_mes.bind("<FocusOut>",  _normalizar)
            e_anio.bind("<FocusOut>", _normalizar)
            for e in (e_dia, e_mes, e_anio):
                e.bind("<FocusIn>", lambda _e, w=e: _seleccionar_todo(w))

            def _valor():
                dia, mes, anio = var_dia.get().strip(), var_mes.get().strip(), var_anio.get().strip()
                if len(dia) == 1: dia = dia.zfill(2)
                if len(mes) == 1: mes = mes.zfill(2)
                if len(anio) == 2: anio = "20" + anio
                return f"{dia}/{mes}/{anio}"

            return _valor, e_dia

        # ── Fecha de ingreso: viene horneada con la fecha de hoy; "Cambiar"
        # revela las mismas 3 cajas que la fecha de entrega. Así el Tab no
        # empieza ahí en el caso común (no se cambia casi nunca).
        tk.Label(frame_msg, text="Fecha de ingreso", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")

        contenedor_ingreso = tk.Frame(frame_msg, bg=COLORES["fondo"])
        contenedor_ingreso.pack(anchor="w", fill="x", pady=(0, 12))

        fecha_ingreso_horneada = hoy.strftime("%d/%m/%Y")
        estado_ingreso = {"valor": lambda: fecha_ingreso_horneada}

        vista_horneada = tk.Frame(contenedor_ingreso, bg=COLORES["fondo"])
        vista_horneada.pack(anchor="w")

        tk.Label(vista_horneada, text=fecha_ingreso_horneada, font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto"]).pack(side="left", ipady=9)

        btn_cambiar_ingreso = tk.Label(
            vista_horneada, text="Cambiar", font=FUENTE_LABEL,
            bg=COLORES["borde"], fg=COLORES["texto"],
            padx=10, pady=4, cursor="hand2",
        )
        btn_cambiar_ingreso.pack(side="left", padx=(12, 0))
        btn_cambiar_ingreso.bind("<Enter>", lambda _: btn_cambiar_ingreso.config(bg="#C0BCBA"))
        btn_cambiar_ingreso.bind("<Leave>", lambda _: btn_cambiar_ingreso.config(bg=COLORES["borde"]))

        def _activar_edicion_ingreso(_e=None):
            vista_horneada.pack_forget()
            valor_fn, primer_entry = _crear_cajas_fecha(
                contenedor_ingreso, hoy.strftime("%d"), hoy.strftime("%m"), hoy.strftime("%Y"))
            estado_ingreso["valor"] = valor_fn
            primer_entry.focus_set()

        btn_cambiar_ingreso.bind("<Button-1>", _activar_edicion_ingreso)

        def valor_ingreso():
            return estado_ingreso["valor"]()

        # ── Fecha de entrega: siempre editable, primera parada del Tab.
        # El botón "Aprobar" se define más abajo; esta indirección permite
        # avisarle cambios sin tener que reordenar la construcción del diálogo.
        _cb_cambio_entrega = {"fn": lambda: None}

        tk.Label(frame_msg, text="Fecha de entrega", font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        contenedor_entrega = tk.Frame(frame_msg, bg=COLORES["fondo"])
        contenedor_entrega.pack(anchor="w", fill="x", pady=(0, 12))
        valor_entrega, primer_campo = _crear_cajas_fecha(
            contenedor_entrega, "", "", hoy.strftime("%Y"),
            on_cambio=lambda: _cb_cambio_entrega["fn"]())

        lbl_error = tk.Label(frame_msg, text="", font=FUENTE_LABEL,
                              bg=COLORES["fondo"], fg=COLORES["error"],
                              wraplength=_esc.px(540), justify="left")
        lbl_error.pack(anchor="w")

        def _cancelar(_e=None):
            dlg.grab_release()
            dlg.destroy()

        def _editar(_e=None):
            dlg.grab_release()
            dlg.destroy()
            self._editar_cotizacion(iid)

        def _aprobar(_e=None):
            ingreso = valor_ingreso()
            entrega = valor_entrega()
            if not _fecha_valida(ingreso) or not _fecha_valida(entrega):
                lbl_error.config(text="⚠ Ambas fechas deben tener formato dd/mm/aaaa.")
                return

            promover_a_op(datos, ingreso, entrega)
            dlg.grab_release()
            dlg.destroy()
            self._quitar_de_lista(iid)

        def _on_return(_e=None):
            # Enter confirma solo si ambas fechas ya están completas y válidas.
            if _fecha_valida(valor_ingreso()) and _fecha_valida(valor_entrega()):
                _aprobar()

        btn_cancelar = tk.Label(
            frame_btns, text="Cancelar", font=FUENTE_BTN,
            bg=COLORES["borde"], fg=COLORES["texto"],
            padx=21, pady=12, cursor="hand2",
        )
        btn_cancelar.pack(side="left")

        btn_editar = tk.Label(
            frame_btns, text="Editar", font=FUENTE_BTN,
            bg=COLORES["acento"], fg="#FFFFFF",
            padx=21, pady=12, cursor="hand2",
        )
        btn_editar.pack(side="left", padx=(12, 0))

        btn_aprobar = tk.Label(
            frame_btns, text="Aprobar", font=FUENTE_BTN,
            bg=self._C_APROB_OFF, fg="#FFFFFF",
            padx=21, pady=12, cursor="arrow",
        )
        btn_aprobar.pack(side="right")

        estado_aprobar = {"habilitado": False}

        def _actualizar_btn_aprobar():
            habilitado = _fecha_valida(valor_entrega())
            estado_aprobar["habilitado"] = habilitado
            if habilitado:
                btn_aprobar.config(bg=self._C_APROB_ON, cursor="hand2")
            else:
                btn_aprobar.config(bg=self._C_APROB_OFF, cursor="arrow")

        def _click_aprobar(_e=None):
            if estado_aprobar["habilitado"]:
                _aprobar()

        _cb_cambio_entrega["fn"] = _actualizar_btn_aprobar
        _actualizar_btn_aprobar()

        btn_cancelar.bind("<Button-1>", _cancelar)
        btn_editar.bind("<Button-1>",   _editar)
        btn_aprobar.bind("<Button-1>",  _click_aprobar)
        btn_cancelar.bind("<Enter>", lambda _: btn_cancelar.config(bg="#C0BCBA"))
        btn_cancelar.bind("<Leave>", lambda _: btn_cancelar.config(bg=COLORES["borde"]))
        btn_editar.bind("<Enter>", lambda _: btn_editar.config(bg=COLORES["acento_hover"]))
        btn_editar.bind("<Leave>", lambda _: btn_editar.config(bg=COLORES["acento"]))
        btn_aprobar.bind("<Enter>", lambda _: btn_aprobar.config(
            bg=self._C_APROB_ON_HV if estado_aprobar["habilitado"] else self._C_APROB_OFF))
        btn_aprobar.bind("<Leave>", lambda _: btn_aprobar.config(
            bg=self._C_APROB_ON if estado_aprobar["habilitado"] else self._C_APROB_OFF))

        dlg.bind("<Escape>", _cancelar)
        dlg.bind("<Return>", _on_return)
        dlg.focus_force()
        primer_campo.focus_set()
        dlg.wait_window()

    def _quitar_de_lista(self, iid):
        self._tree.delete(iid)
        self._entradas = [e for e in self._entradas if str(e[0]) != iid]
        self._iid_tags.pop(iid, None)
        self._selected.discard(iid)
        self._actualizar_btn_eliminar()
        self._actualizar_btn_aprobar()

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
        if self._elim_on:
            self._dialogo_eliminar()

    def _dialogo_eliminar(self):
        sel = list(self._selected)
        if not sel:
            return

        dlg = tk.Toplevel(self)
        dlg.title("Confirmar eliminación")
        dlg.configure(bg=COLORES["fondo"])
        dlg.resizable(False, False)
        dlg.transient(self)

        ancho, alto = _esc.px(480), _esc.px(252)
        ox = self.winfo_x() + (self.ANCHO - ancho) // 2
        oy = self.winfo_y() + (self.ALTO  - alto)  // 2
        dlg.geometry(f"{ancho}x{alto}+{ox}+{oy}")
        dlg.grab_set()

        # Mensaje principal
        if len(sel) == 1:
            try:
                num = int(sel[0])
                texto_titulo = f"¿Eliminar Cotización {num:04d}?"
            except ValueError:
                texto_titulo = "¿Eliminar la cotización seleccionada?"
            texto_lista = ""
        else:
            nums = sorted(int(iid) for iid in sel if iid.isdigit())
            texto_titulo = "Eliminar cotizaciones:"
            texto_lista  = ", ".join(f"{n:04d}" for n in nums)

        frame_msg = tk.Frame(dlg, bg=COLORES["fondo"], padx=24, pady=18)
        frame_msg.pack(fill="both", expand=True)

        tk.Label(frame_msg, text=texto_titulo,
                 font=FUENTE_TITULO, bg=COLORES["fondo"], fg=COLORES["texto"],
                 wraplength=_esc.px(408), justify="center").pack()

        if texto_lista:
            tk.Label(frame_msg, text=texto_lista,
                     font=FUENTE_LABEL, bg=COLORES["fondo"], fg=COLORES["texto"],
                     wraplength=_esc.px(408), justify="center").pack(pady=(4, 0))

        tk.Label(frame_msg, text="Esta acción no se puede deshacer.",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(pady=(10, 0))

        # Botones
        frame_btns = tk.Frame(dlg, bg=COLORES["fondo"])
        frame_btns.pack(fill="x", padx=24, pady=(0, 18))

        def _confirmar(_e=None):
            dlg.grab_release()
            dlg.destroy()
            self._ejecutar_eliminacion()

        def _cancelar(_e=None):
            dlg.grab_release()
            dlg.destroy()

        btn_cancelar = tk.Label(
            frame_btns, text="Cancelar",
            font=FUENTE_BTN, bg=COLORES["borde"],
            fg=COLORES["texto"], padx=19, pady=10, cursor="hand2",
        )
        btn_cancelar.pack(side="left")

        btn_confirmar = tk.Label(
            frame_btns, text="Eliminar",
            font=FUENTE_BTN, bg=COLORES["error"],
            fg="#FFFFFF", padx=19, pady=10, cursor="hand2",
        )
        btn_confirmar.pack(side="right")

        btn_cancelar.bind("<Enter>",    lambda _: btn_cancelar.config(bg="#C0BCBA"))
        btn_cancelar.bind("<Leave>",    lambda _: btn_cancelar.config(bg=COLORES["borde"]))
        btn_confirmar.bind("<Enter>",   lambda _: btn_confirmar.config(bg=COLORES["error_hover"]))
        btn_confirmar.bind("<Leave>",   lambda _: btn_confirmar.config(bg=COLORES["error"]))
        btn_cancelar.bind("<Button-1>",  _cancelar)
        btn_confirmar.bind("<Button-1>", _confirmar)

        dlg.bind("<Return>", _confirmar)
        dlg.bind("<Escape>", _cancelar)

        dlg.focus_force()
        dlg.wait_window()

    def _ejecutar_eliminacion(self):
        for iid in list(self._selected):
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
            self._entradas = [e for e in self._entradas if str(e[0]) != iid]
            self._iid_tags.pop(iid, None)

        self._selected.clear()

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

    # ── Teclado ────────────────────────────────────────────────────────────────

    def _on_key_up(self, _):
        children = self._tree.get_children()
        if not children:
            return "break"
        focus = self._tree.focus()
        idx = list(children).index(focus) if focus in children else 1
        new_iid = children[max(0, idx - 1)]
        self._tree.selection_set([new_iid])
        self._tree.focus(new_iid)
        self._tree.see(new_iid)
        return "break"

    def _on_key_down(self, _):
        children = self._tree.get_children()
        if not children:
            return "break"
        focus = self._tree.focus()
        idx = list(children).index(focus) if focus in children else -1
        new_iid = children[min(len(children) - 1, idx + 1)]
        self._tree.selection_set([new_iid])
        self._tree.focus(new_iid)
        self._tree.see(new_iid)
        return "break"

    def _on_key_shift_up(self, _):
        children = self._tree.get_children()
        if not children:
            return "break"
        focus = self._tree.focus()
        idx = list(children).index(focus) if focus in children else 1
        new_iid = children[max(0, idx - 1)]
        self._tree.selection_add(new_iid)
        self._tree.focus(new_iid)
        self._tree.see(new_iid)
        return "break"

    def _on_key_shift_down(self, _):
        children = self._tree.get_children()
        if not children:
            return "break"
        focus = self._tree.focus()
        idx = list(children).index(focus) if focus in children else -1
        new_iid = children[min(len(children) - 1, idx + 1)]
        self._tree.selection_add(new_iid)
        self._tree.focus(new_iid)
        self._tree.see(new_iid)
        return "break"

    def _on_key_return(self, _):
        focus = self._tree.focus()
        if focus and focus in self._iid_tags:
            self._editar_cotizacion(focus)
        return "break"

    # ── Editar cotización ──────────────────────────────────────────────────────

    def _editar_cotizacion(self, iid: str):
        archivo = next((e[3] for e in self._entradas if str(e[0]) == iid), None)
        if archivo is None:
            return
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except Exception:
            self._lbl_estado.config(
                text="⚠ No se pudo leer el archivo de la cotización.",
                fg=COLORES["error"])
            return

        from ui.formulario_cliente import producto_desde_json
        productos = [producto_desde_json(p) for p in datos.get("productos", [])]
        edicion = {"json": datos, "productos": productos}
        es_backlight = bool(productos) and "caja" in productos[0]

        # Destruye la ventana principal (Tk root) junto con este Toplevel,
        # y la reemplaza por el cotizador correspondiente en modo edición.
        self.master.destroy()
        if es_backlight:
            from ui.cotizador_backlight import CotizadorBacklight
            CotizadorBacklight(edicion=edicion).mainloop()
        else:
            from ui.cotizacion import CotizacionNueva
            CotizacionNueva(edicion=edicion).mainloop()

    def _on_doble_clic(self, _):
        iid = self._tree.focus()
        if iid and iid in self._iid_tags:
            self._editar_cotizacion(iid)

    # ── Utilidades ─────────────────────────────────────────────────────────────

    def _centrar(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - self.ANCHO) // 2
        y = (self.winfo_screenheight() - self.ALTO)  // 2
        self.geometry(f"{self.ANCHO}x{self.ALTO}+{x}+{y}")
