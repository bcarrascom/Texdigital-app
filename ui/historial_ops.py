"""
ui/historial_ops.py
Ventana que lista TODAS las OPs guardadas (activas + Completadas +
Pendiente + Historial) de un mes puntual — "hojas" por mes, igual que
Gmail pagina de a 50/100 correos, pero acá se ordena por calendario en
vez de por cantidad: cada "hoja" es un año/mes, elegido con ◀/▶ (un mes a
la vez) o «/» (salta al año anterior/siguiente con datos). Ver
core.repositorio_ops.listar_meses_disponibles/listar_ops_del_mes — solo
se abren los JSON de ese mes, no los miles que puede llegar a acumular
Historial/ con los años.

Selección múltiple:
  - "Imprimir" genera el HTML de cada OP (core.presentar_op, sin precios
    — mismo documento que ya usa el panel de producción) y lo abre en el
    navegador.
  - "Buscar cotización" busca, para cada OP seleccionada, la cotización
    de origen (mismo número) en Cotizaciones/JSON y Cotizaciones/Historial
    — acotado a los últimos 3 meses contando desde la Fecha_ingreso de la
    OP (la cotización se mueve a Historial justo al aprobarse la OP, así
    que su Fecha cae en ese mismo mes o poco antes). Si la encuentra abre
    su HTML (con precios, el documento para el cliente); si no, avisa.
  - "Eliminar" borra el JSON de la OP (con confirmación), sea cual sea su
    carpeta de ciclo de vida actual.
"""

import sys
import tkinter as tk
import tkinter.font as tkfont
import tkinter.ttk as ttk
import webbrowser

from core import escala as _esc
from core.repositorio_ops import (
    listar_meses_disponibles,
    listar_ops_del_mes,
    cargar_op,
    eliminar_op,
)
from core.presentar_op import generar_html as generar_html_op

# Separación mínima garantizada entre columnas de la tabla (ver
# _calcular_anchos_columnas): no es un padding fijo, se sustenta con el
# ancho REAL del texto más largo esperado en cada columna (medido con la
# fuente real, no adivinado) más este margen. Sin pasar por _esc.px(): las
# fuentes de este archivo (FUENTE_LISTA/FUENTE_HEAD) tampoco escalan, así
# que medirlas y garantizar la separación en píxeles reales, sin más
# factor de por medio, es lo consistente — 45 px de separación real,
# siempre, sin importar el factor de escala de pantalla.
_GAP_COLUMNAS = 45

_NOMBRES_MES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

_ETIQUETA_ESTADO = {
    "JSON":        "Activa",
    "Completadas": "Completada",
    "Pendiente":   "Pendiente",
    "Historial":   "Historial",
}

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
    FUENTE_TITULO = ("Helvetica Neue", 15, "bold")
    FUENTE_LABEL  = ("Helvetica Neue", 11)
    FUENTE_LISTA  = ("Helvetica Neue", 12)
    FUENTE_HEAD   = ("Helvetica Neue", 11, "bold")
    FUENTE_BTN    = ("Helvetica Neue", 11, "bold")
    FUENTE_PAGER  = ("Helvetica Neue", 14, "bold")
    FUENTE_PAGER_ANIO = ("Helvetica Neue", 12, "bold")
else:
    FUENTE_TITULO = ("Georgia", 14, "bold")
    FUENTE_LABEL  = ("Segoe UI", 10)
    FUENTE_LISTA  = ("Segoe UI", 11)
    FUENTE_HEAD   = ("Segoe UI", 10, "bold")
    FUENTE_BTN    = ("Segoe UI", 10, "bold")
    FUENTE_PAGER  = ("Segoe UI", 13, "bold")
    FUENTE_PAGER_ANIO = ("Segoe UI", 11, "bold")


class VentanaHistorialOps(tk.Toplevel):

    ANCHO = _esc.px(1220)
    ALTO  = _esc.px(820)

    _C_IMP_OFF    = "#9E9E9E"
    _C_IMP_OFF_HV = "#BDBDBD"
    _C_IMP_ON     = COLORES["acento"]
    _C_IMP_ON_HV  = COLORES["acento_hover"]

    _C_BUS_OFF    = "#9E9E9E"
    _C_BUS_OFF_HV = "#BDBDBD"
    _C_BUS_ON     = COLORES["ok"]
    _C_BUS_ON_HV  = "#2ECC71"

    _C_ELIM_OFF    = "#9E9E9E"
    _C_ELIM_OFF_HV = "#BDBDBD"
    _C_ELIM_ON     = COLORES["error"]
    _C_ELIM_ON_HV  = COLORES["error_hover"]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Historial de OPs")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)

        self._entradas  = []   # [(numero, empresa, nombre, fecha_ing, fecha_ent, estado), ...]
        self._iid_tags  = {}
        self._selected  = set()
        self._hover_iid = None
        self._imp_on    = False
        self._bus_on    = False
        self._elim_on   = False

        self._meses = listar_meses_disponibles()
        self._indice_mes = len(self._meses) - 1 if self._meses else None  # más reciente

        # Anchos de columna medidos con la fuente real (ver
        # _calcular_anchos_columnas) — acá, antes de tener datos, es solo
        # una base a partir de encabezados; _cargar_mes_actual() los
        # vuelve a calcular ya considerando el texto real de cada fila y
        # agranda la ventana si hace falta (ver _ajustar_columnas_y_ventana).
        self._anchos_col = self._calcular_anchos_columnas()
        self.ANCHO = max(self.ANCHO, self._ancho_necesario())

        self._centrar()
        self.lift()
        self.focus_force()

        self._aplicar_estilo()
        self._construir_ui()
        self._cargar_mes_actual()

    # ── Anchos de columna ──────────────────────────────────────────────────────

    def _calcular_anchos_columnas(self) -> dict:
        """Ancho de cada columna = ancho REAL (medido, no adivinado) del
        texto más largo que aparece ahí — el encabezado, o el dato más
        largo entre las filas YA CARGADAS (self._entradas) — más
        _GAP_COLUMNAS de separación hacia la columna siguiente. Antes de
        cargar datos (primera vez, en __init__) usa una muestra genérica
        como piso para Empresa/Trabajo, así la ventana no arranca angosta;
        una vez hay datos reales (llamado de nuevo desde
        _cargar_mes_actual), esa muestra dejó de hacer falta — el ancho
        real de las filas ya manda."""
        f_head  = tkfont.Font(font=FUENTE_HEAD)
        f_lista = tkfont.Font(font=FUENTE_LISTA)

        def ancho(header, textos_datos, muestra_piso=None):
            candidatos = [f_head.measure(header)]
            for t in textos_datos:
                candidatos.append(f_lista.measure(str(t)))
            if not textos_datos and muestra_piso is not None:
                candidatos.append(f_lista.measure(muestra_piso))
            return max(candidatos) + _GAP_COLUMNAS

        nums     = [f"{e[0]:04d}" for e in self._entradas]
        empresas = [e[1] for e in self._entradas]
        nombres  = [e[2] for e in self._entradas]
        estado_mas_largo = max(_ETIQUETA_ESTADO.values(), key=len)

        return {
            "num":     ancho("N°", nums, "99999"),
            "empresa": ancho("Empresa", empresas, "Empresa Comercial Ejemplo Ltda."),
            "nombre":  ancho("Trabajo", nombres, "Nombre de trabajo de ejemplo"),
            "ingreso": ancho("Fecha ingreso", [], "15/08/2026"),
            "entrega": ancho("Fecha entrega", [], "15/08/2026"),
            "estado":  ancho("Estado", [], estado_mas_largo),
        }

    def _ancho_necesario(self) -> int:
        """Ancho total de ventana para que la tabla (con los anchos
        actuales de self._anchos_col) entre sin recortarse."""
        ancho_tabla = sum(self._anchos_col.values())
        # padx=20 del frame de la tabla (a cada lado, ver _construir_ui) +
        # ancho típico de la scrollbar + un margen chico de seguridad para
        # el tema ttk. Sin _esc.px(): el padx=20 de _construir_ui tampoco
        # escala, así que sumar en píxeles reales es lo consistente.
        return ancho_tabla + (20 * 2) + 20 + 20

    def _ajustar_columnas_y_ventana(self):
        """Recalcula los anchos de columna contra self._entradas (ya
        cargado) y, si no entran en el ANCHO actual, agranda la ventana
        (nunca la achica — cambiar de mes a uno con textos más cortos no
        debería hacerla saltar más chica en pantalla)."""
        self._anchos_col = self._calcular_anchos_columnas()
        a = self._anchos_col
        self._tree.column("num",     width=a["num"],     minwidth=a["num"])
        self._tree.column("empresa", width=a["empresa"], minwidth=a["empresa"])
        self._tree.column("nombre",  width=a["nombre"],  minwidth=a["nombre"])
        self._tree.column("ingreso", width=a["ingreso"], minwidth=a["ingreso"])
        self._tree.column("entrega", width=a["entrega"], minwidth=a["entrega"])
        self._tree.column("estado",  width=a["estado"],  minwidth=a["estado"])

        nuevo_ancho = max(self.ANCHO, self._ancho_necesario())
        if nuevo_ancho > self.ANCHO:
            self.ANCHO = nuevo_ancho
            self._centrar()

    # ── Estilo ttk ─────────────────────────────────────────────────────────────

    def _aplicar_estilo(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Hist.Treeview",
            background=COLORES["fila_par"],
            foreground=COLORES["texto"],
            fieldbackground=COLORES["fila_par"],
            rowheight=_esc.px(56),
            font=FUENTE_LISTA,
            borderwidth=0,
        )
        s.configure("Hist.Treeview.Heading",
            background=COLORES["acento"],
            foreground="#FFFFFF",
            font=FUENTE_HEAD,
            relief="flat",
            padding=(_esc.px(8), _esc.px(6)),
        )
        s.map("Hist.Treeview",
            background=[("selected", COLORES["lista_sel"])],
            foreground=[("selected", COLORES["texto"])],
        )
        s.map("Hist.Treeview.Heading",
            background=[("active", COLORES["acento_hover"])],
            relief=[("active", "flat")],
        )

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        # Cabecera
        cab = tk.Frame(self, bg=COLORES["acento"], padx=20, pady=12)
        cab.pack(fill="x")
        tk.Label(cab, text="Historial de OPs",
                 font=FUENTE_TITULO, bg=COLORES["acento"],
                 fg="#FFFFFF").pack(side="left", anchor="w")

        # Pager: « Año | ◀ Mes | [Mes Año] | Mes ▶ | Año » — ◀/▶ avanzan un
        # mes; «/» saltan directo al año anterior/siguiente que tenga
        # datos, sin tener que ir apretando ◀/▶ doce veces.
        pager = tk.Frame(self, bg=COLORES["fondo"])
        pager.pack(fill="x", padx=20, pady=(16, 4))

        def _flecha(parent, texto, fuente, comando, side, padx):
            lbl = tk.Label(parent, text=texto, font=fuente,
                           bg=COLORES["fondo"], fg=COLORES["acento"],
                           cursor="hand2", padx=padx)
            lbl.pack(side=side)
            lbl.bind("<Button-1>", lambda _: comando())
            return lbl

        self._btn_anio_ant = _flecha(pager, "«", FUENTE_PAGER_ANIO,
                                     lambda: self._cambiar_anio(-1), "left", 4)
        self._btn_mes_ant  = _flecha(pager, "◀", FUENTE_PAGER,
                                     lambda: self._cambiar_mes(-1), "left", 10)

        self._lbl_mes = tk.Label(pager, text="", font=FUENTE_PAGER,
                                 bg=COLORES["fondo"], fg=COLORES["texto"])
        self._lbl_mes.pack(side="left", expand=True)

        self._btn_mes_sig  = _flecha(pager, "▶", FUENTE_PAGER,
                                     lambda: self._cambiar_mes(1), "right", 10)
        self._btn_anio_sig = _flecha(pager, "»", FUENTE_PAGER_ANIO,
                                     lambda: self._cambiar_anio(1), "right", 4)

        tk.Label(self,
                 text="Incluye OPs activas, pendientes, completadas e historial de ese mes.",
                 font=FUENTE_LABEL, bg=COLORES["fondo"],
                 fg=COLORES["texto_suave"]).pack(anchor="w", padx=20, pady=(0, 6))

        # ── Footer empacado ANTES del árbol para que expand=True no lo tape ──
        frame_botones = tk.Frame(self, bg=COLORES["fondo"])
        frame_botones.pack(side="bottom", fill="x", padx=20, pady=(8, 16))

        self._btn_eliminar = tk.Label(
            frame_botones, text="Eliminar",
            font=FUENTE_BTN, bg=self._C_ELIM_OFF,
            fg="#FFFFFF", padx=16, pady=8, cursor="arrow",
        )
        self._btn_eliminar.pack(side="left")
        self._btn_eliminar.bind("<Enter>",    self._on_elim_enter)
        self._btn_eliminar.bind("<Leave>",    self._on_elim_leave)
        self._btn_eliminar.bind("<Button-1>", self._on_click_eliminar)

        self._btn_imprimir = tk.Label(
            frame_botones, text="Imprimir",
            font=FUENTE_BTN, bg=self._C_IMP_OFF,
            fg="#FFFFFF", padx=16, pady=8, cursor="arrow",
        )
        self._btn_imprimir.pack(side="right")
        self._btn_imprimir.bind("<Enter>",    self._on_imp_enter)
        self._btn_imprimir.bind("<Leave>",    self._on_imp_leave)
        self._btn_imprimir.bind("<Button-1>", self._on_click_imprimir)

        self._btn_buscar = tk.Label(
            frame_botones, text="Buscar cotización",
            font=FUENTE_BTN, bg=self._C_BUS_OFF,
            fg="#FFFFFF", padx=16, pady=8, cursor="arrow",
        )
        self._btn_buscar.pack(side="right", padx=(0, 8))
        self._btn_buscar.bind("<Enter>",    self._on_bus_enter)
        self._btn_buscar.bind("<Leave>",    self._on_bus_leave)
        self._btn_buscar.bind("<Button-1>", self._on_click_buscar)

        self._lbl_estado = tk.Label(
            self, text="", font=FUENTE_LABEL,
            bg=COLORES["fondo"], fg=COLORES["error"],
            wraplength=self.ANCHO - _esc.px(40), justify="left",
        )
        self._lbl_estado.pack(side="bottom", anchor="w", padx=20, pady=(0, 4))

        # ── Tabla ──
        frame_tree = tk.Frame(self, bg=COLORES["fondo"])
        frame_tree.pack(fill="both", expand=True, padx=20)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self._tree = ttk.Treeview(
            frame_tree,
            columns=("num", "empresa", "nombre", "ingreso", "entrega", "estado"),
            show="headings",
            style="Hist.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="extended",
        )
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._tree.yview)

        self._tree.heading("num",     text="N°",              anchor="w")
        self._tree.heading("empresa", text="Empresa",          anchor="w")
        self._tree.heading("nombre",  text="Trabajo",          anchor="w")
        self._tree.heading("ingreso", text="Fecha ingreso",    anchor="w")
        self._tree.heading("entrega", text="Fecha entrega",    anchor="w")
        self._tree.heading("estado",  text="Estado",           anchor="w")

        # Anchos medidos con la fuente real (ver _calcular_anchos_columnas,
        # llamado desde __init__ antes de decidir el ANCHO de la ventana) —
        # ya incluyen los _GAP_COLUMNAS de separación hacia la columna
        # siguiente, así que minwidth = width (no debe poder achicarse por
        # debajo del mínimo que garantiza la separación).
        a = self._anchos_col
        self._tree.column("num",     width=a["num"],     minwidth=a["num"],     anchor="w", stretch=False)
        self._tree.column("empresa", width=a["empresa"], minwidth=a["empresa"], anchor="w", stretch=True)
        self._tree.column("nombre",  width=a["nombre"],  minwidth=a["nombre"],  anchor="w", stretch=True)
        self._tree.column("ingreso", width=a["ingreso"], minwidth=a["ingreso"], anchor="w", stretch=False)
        self._tree.column("entrega", width=a["entrega"], minwidth=a["entrega"], anchor="w", stretch=False)
        self._tree.column("estado",  width=a["estado"],  minwidth=a["estado"],  anchor="w", stretch=False)

        self._tree.tag_configure("par",   background=COLORES["fila_par"])
        self._tree.tag_configure("impar", background=COLORES["fila_impar"])
        self._tree.tag_configure("hover", background=COLORES["hover"])

        self._tree.bind("<Motion>",           self._on_hover_motion)
        self._tree.bind("<Leave>",            self._on_hover_leave)
        self._tree.bind("<<TreeviewSelect>>", lambda _: self._on_selection_change())

        self._safe_widgets = {
            self._tree, self._btn_imprimir, self._btn_buscar, self._btn_eliminar,
            self._btn_mes_ant, self._btn_mes_sig, self._btn_anio_ant, self._btn_anio_sig,
        }
        self.bind("<ButtonPress-1>", self._on_window_click, add="+")

    # ── Carga de un mes ──────────────────────────────────────────────────────

    def _cambiar_mes(self, delta: int):
        if self._indice_mes is None:
            return
        nuevo = self._indice_mes + delta
        if 0 <= nuevo < len(self._meses):
            self._indice_mes = nuevo
            self._cargar_mes_actual()

    def _cambiar_anio(self, delta: int):
        """Salta directo al año anterior/siguiente que tenga datos (al
        primer mes de ese año si se avanza, al último si se retrocede),
        sin tener que recorrer ◀/▶ mes a mes."""
        if self._indice_mes is None:
            return
        anio_actual, _ = self._meses[self._indice_mes]
        if delta > 0:
            candidatos = [i for i, (a, _m) in enumerate(self._meses) if a > anio_actual]
            if candidatos:
                self._indice_mes = candidatos[0]
                self._cargar_mes_actual()
        else:
            candidatos = [i for i, (a, _m) in enumerate(self._meses) if a < anio_actual]
            if candidatos:
                self._indice_mes = candidatos[-1]
                self._cargar_mes_actual()

    def _cargar_mes_actual(self):
        self._selected.clear()
        self._lbl_estado.config(text="")

        if self._indice_mes is None:
            self._lbl_mes.config(text="Sin OPs guardadas")
            for btn in (self._btn_mes_ant, self._btn_mes_sig, self._btn_anio_ant, self._btn_anio_sig):
                btn.config(fg=COLORES["borde"], cursor="arrow")
            self._entradas = []
            self._ajustar_columnas_y_ventana()
            self._rellenar_tabla()
            self._actualizar_botones()
            return

        anio, mes = self._meses[self._indice_mes]
        self._lbl_mes.config(text=f"{_NOMBRES_MES[mes]} {anio}")

        hay_mes_ant = self._indice_mes > 0
        hay_mes_sig = self._indice_mes < len(self._meses) - 1
        hay_anio_ant = any(a < anio for a, _m in self._meses)
        hay_anio_sig = any(a > anio for a, _m in self._meses)
        for btn, hay in ((self._btn_mes_ant, hay_mes_ant), (self._btn_mes_sig, hay_mes_sig),
                         (self._btn_anio_ant, hay_anio_ant), (self._btn_anio_sig, hay_anio_sig)):
            btn.config(fg=COLORES["acento"] if hay else COLORES["borde"],
                      cursor="hand2" if hay else "arrow")

        crudos = listar_ops_del_mes(anio, mes)
        entradas = []
        for datos, origen in crudos:
            try:
                num = int(datos.get("Cotizacion"))
            except (TypeError, ValueError):
                continue
            entradas.append((
                num,
                datos.get("Empresa", "—"),
                datos.get("Nombre", "—"),
                datos.get("Fecha_ingreso", "—"),
                datos.get("Fecha_entrega", "—"),
                _ETIQUETA_ESTADO.get(origen, origen),
            ))
        self._entradas = sorted(entradas, key=lambda e: e[0], reverse=True)
        self._ajustar_columnas_y_ventana()
        self._rellenar_tabla()
        self._actualizar_botones()

    def _rellenar_tabla(self):
        self._tree.delete(*self._tree.get_children())
        self._iid_tags.clear()
        self._hover_iid = None

        if self._entradas:
            for i, (num, empresa, nombre, ingreso, entrega, estado) in enumerate(self._entradas):
                tag = "par" if i % 2 == 0 else "impar"
                iid = str(num)
                self._iid_tags[iid] = tag
                self._tree.insert("", tk.END, iid=iid,
                                  values=(f"{num:04d}", empresa, nombre, ingreso, entrega, estado),
                                  tags=(tag,))
        else:
            self._tree.insert("", tk.END,
                              values=("—", "No hay OPs en este mes.", "—", "—", "—", "—"))

    # ── Selección ──────────────────────────────────────────────────────────────

    def _on_selection_change(self):
        new_sel = set(self._tree.selection())
        for iid in (self._selected - new_sel):
            if iid == self._hover_iid:
                self._tree.item(iid, tags=("hover",))
            else:
                self._tree.item(iid, tags=(self._iid_tags.get(iid, "par"),))
        for iid in (new_sel - self._selected):
            self._tree.item(iid, tags=())
        self._selected = new_sel
        self._actualizar_botones()

    def _on_window_click(self, event):
        w = event.widget
        while w is not None and w is not self:
            if w in self._safe_widgets:
                return
            w = getattr(w, "master", None)
        self._tree.selection_set([])

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

    # ── Botones (habilitado con ≥1 fila seleccionada) ─────────────────────────

    def _actualizar_botones(self):
        habilitado = bool(self._selected)

        if habilitado != self._imp_on:
            self._imp_on = habilitado
            if habilitado:
                self._btn_imprimir.config(bg=self._C_IMP_ON, fg="#FFFFFF", cursor="hand2")
            else:
                self._btn_imprimir.config(bg=self._C_IMP_OFF, fg="#FFFFFF", cursor="arrow")

        if habilitado != self._bus_on:
            self._bus_on = habilitado
            if habilitado:
                self._btn_buscar.config(bg=self._C_BUS_ON, fg="#FFFFFF", cursor="hand2")
            else:
                self._btn_buscar.config(bg=self._C_BUS_OFF, fg="#FFFFFF", cursor="arrow")

        if habilitado != self._elim_on:
            self._elim_on = habilitado
            if habilitado:
                self._btn_eliminar.config(bg=self._C_ELIM_ON, fg="#FFFFFF", cursor="hand2")
            else:
                self._btn_eliminar.config(bg=self._C_ELIM_OFF, fg="#FFFFFF", cursor="arrow")

    def _on_imp_enter(self, _):
        self._btn_imprimir.config(bg=self._C_IMP_ON_HV if self._imp_on else self._C_IMP_OFF_HV)

    def _on_imp_leave(self, _):
        self._btn_imprimir.config(bg=self._C_IMP_ON if self._imp_on else self._C_IMP_OFF)

    def _on_bus_enter(self, _):
        self._btn_buscar.config(bg=self._C_BUS_ON_HV if self._bus_on else self._C_BUS_OFF_HV)

    def _on_bus_leave(self, _):
        self._btn_buscar.config(bg=self._C_BUS_ON if self._bus_on else self._C_BUS_OFF)

    def _on_elim_enter(self, _):
        self._btn_eliminar.config(bg=self._C_ELIM_ON_HV if self._elim_on else self._C_ELIM_OFF_HV)

    def _on_elim_leave(self, _):
        self._btn_eliminar.config(bg=self._C_ELIM_ON if self._elim_on else self._C_ELIM_OFF)

    # ── Botón Imprimir ─────────────────────────────────────────────────────────

    def _on_click_imprimir(self, _):
        if not self._imp_on:
            return
        numeros = sorted(int(iid) for iid in self._selected if iid.isdigit())
        if not numeros:
            return

        self._lbl_estado.config(text="")
        for numero in numeros:
            datos = cargar_op(numero)
            if datos is None:
                self._lbl_estado.config(
                    text=f"⚠ No se pudo leer el archivo de la OP {numero:04d}.",
                    fg=COLORES["error"])
                continue
            try:
                ruta_html = generar_html_op(datos)
                webbrowser.open(ruta_html.as_uri())
            except Exception as e:
                self._lbl_estado.config(
                    text=f"⚠ No se pudo generar la OP {numero:04d} en HTML: {e}",
                    fg=COLORES["error"])

    # ── Botón Buscar cotización ────────────────────────────────────────────────

    def _on_click_buscar(self, _):
        if not self._bus_on:
            return
        seleccionadas = []
        for iid in self._selected:
            if not iid.isdigit():
                continue
            numero = int(iid)
            fila = next((e for e in self._entradas if e[0] == numero), None)
            if fila is not None:
                seleccionadas.append((numero, fila))
        if not seleccionadas:
            return

        from core.repositorio_cotizaciones import buscar_en_ultimos_meses
        from core.presentar_cotizacion import generar_html as generar_html_cotizacion
        from datetime import datetime

        self._lbl_estado.config(text="")
        no_encontradas = []
        for numero, fila in seleccionadas:
            fecha_ingreso = fila[3]  # (num, empresa, nombre, ingreso, entrega, estado)
            try:
                fecha = datetime.strptime(fecha_ingreso, "%d/%m/%Y")
            except ValueError:
                no_encontradas.append(numero)
                continue
            datos = buscar_en_ultimos_meses(numero, fecha.year, fecha.month, cantidad_meses=3)
            if datos is None:
                no_encontradas.append(numero)
                continue
            try:
                ruta_html = generar_html_cotizacion(datos)
                webbrowser.open(ruta_html.as_uri())
            except Exception as e:
                self._lbl_estado.config(
                    text=f"⚠ No se pudo generar la cotización {numero:04d} en HTML: {e}",
                    fg=COLORES["error"])

        if no_encontradas:
            nums = ", ".join(f"{n:04d}" for n in sorted(no_encontradas))
            self._lbl_estado.config(
                text=f"⚠ No se encontró la cotización de origen (últimos 3 meses) para: {nums}.",
                fg=COLORES["error"])

    # ── Botón Eliminar ─────────────────────────────────────────────────────────

    def _on_click_eliminar(self, _):
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

        if len(sel) == 1:
            try:
                num = int(sel[0])
                texto_titulo = f"¿Eliminar OP {num:04d}?"
            except ValueError:
                texto_titulo = "¿Eliminar la OP seleccionada?"
            texto_lista = ""
        else:
            nums = sorted(int(iid) for iid in sel if iid.isdigit())
            texto_titulo = "Eliminar OPs:"
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
            eliminar_op(num)
            self._tree.delete(iid)
            self._entradas = [e for e in self._entradas if e[0] != num]
            self._iid_tags.pop(iid, None)

        self._selected.clear()

        for i, iid in enumerate(self._tree.get_children()):
            tag = "par" if i % 2 == 0 else "impar"
            self._iid_tags[iid] = tag
            self._tree.item(iid, tags=(tag,))

        self._actualizar_botones()

    # ── Utilidades ─────────────────────────────────────────────────────────────

    def _centrar(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - self.ANCHO) // 2
        y = (self.winfo_screenheight() - self.ALTO)  // 2
        self.geometry(f"{self.ANCHO}x{self.ALTO}+{x}+{y}")
