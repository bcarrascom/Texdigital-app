"""
ui/dialogo_aprobar.py
Diálogo compartido para promover una cotización a Orden de Producción (OP).
Lo usan tanto "Revisar Cotizaciones" (botón Aprobar directo) como el flujo de
edición de cotización (botón "Guardar y aprobar").

Al confirmar:
1. Guarda el JSON de la OP en Dropbox/SGTD/OPs/JSON/ (Fecha → Fecha_ingreso/Fecha_entrega).
2. Mueve el JSON de la cotización a Dropbox/SGTD/Cotizaciones/Historial/.
3. Elimina el Excel de la cotización (ya no se necesita).
"""

import tkinter as tk
from datetime import datetime

from ui.estilos import COLORES, FUENTE_TITULO, FUENTE_LABEL, FUENTE_BTN, _centrar
from core import escala as _esc
from core.repositorio_cotizaciones import mover_a_historial, eliminar_excel
from core.repositorio_ops import guardar_op


def _fecha_valida(texto: str) -> bool:
    try:
        datetime.strptime(texto.strip(), "%d/%m/%Y")
        return True
    except ValueError:
        return False


def promover_a_op(json_cotizacion: dict, fecha_ingreso: str, fecha_entrega: str) -> None:
    """Convierte una cotización en OP: guarda el JSON de OP, mueve la
    cotización a Historial y elimina su Excel. Sin UI."""
    numero = json_cotizacion["Cotizacion"]

    op_dict = {}
    for k, v in json_cotizacion.items():
        if k == "Fecha":
            op_dict["Fecha_ingreso"] = fecha_ingreso
            op_dict["Fecha_entrega"] = fecha_entrega
        else:
            op_dict[k] = v

    guardar_op(op_dict)
    mover_a_historial(numero)
    eliminar_excel(numero)


def abrir_dialogo_aprobar(parent, json_cotizacion: dict, on_aprobado):
    """
    parent           Tk o Toplevel sobre el que se centra el modal.
    json_cotizacion  Dict completo de la cotización (incluye "productos").
    on_aprobado      Callback() sin argumentos, llamado tras aprobar con éxito.
    """
    numero = json_cotizacion["Cotizacion"]

    dlg = tk.Toplevel(parent)
    dlg.title("Aprobar cotización")
    dlg.configure(bg=COLORES["fondo"])
    dlg.resizable(False, False)
    dlg.transient(parent)

    ancho, alto = _esc.px(630), _esc.px(495)
    _centrar(dlg, ancho, alto)
    dlg.grab_set()

    frame = tk.Frame(dlg, bg=COLORES["fondo"], padx=42, pady=33)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text=f"¿Aprobar Cotización {numero:04d}?",
             font=FUENTE_TITULO, bg=COLORES["fondo"], fg=COLORES["texto"],
             justify="center").pack()

    tk.Label(frame, text="La cotización pasará a ser una Orden de Producción.",
             font=FUENTE_LABEL, bg=COLORES["fondo"], fg=COLORES["texto_suave"],
             wraplength=_esc.px(540), justify="center").pack(pady=(9, 24))

    hoy = datetime.now().strftime("%d/%m/%Y")
    var_ingreso = tk.StringVar(value=hoy)
    var_entrega = tk.StringVar(value="")

    def _crear_campo_fecha(label, var):
        tk.Label(frame, text=label, font=FUENTE_LABEL,
                 bg=COLORES["fondo"], fg=COLORES["texto_suave"]).pack(anchor="w")
        tk.Entry(frame, textvariable=var, font=FUENTE_LABEL, width=21,
                 relief="flat", bd=0, bg="#FFFFFF", fg=COLORES["texto"],
                 insertbackground=COLORES["texto"], highlightthickness=1,
                 highlightbackground=COLORES["borde"],
                 highlightcolor=COLORES["acento"]).pack(
                     anchor="w", ipady=9, ipadx=9, pady=(0, 15))

    _crear_campo_fecha("Fecha de ingreso", var_ingreso)
    _crear_campo_fecha("Fecha de entrega", var_entrega)

    lbl_error = tk.Label(frame, text="", font=FUENTE_LABEL,
                          bg=COLORES["fondo"], fg=COLORES["error"],
                          wraplength=_esc.px(540), justify="left")
    lbl_error.pack(anchor="w")

    frame_btns = tk.Frame(dlg, bg=COLORES["fondo"])
    frame_btns.pack(fill="x", padx=42, pady=(0, 27))

    def _cancelar(_e=None):
        dlg.grab_release()
        dlg.destroy()

    def _confirmar(_e=None):
        ingreso = var_ingreso.get().strip()
        entrega = var_entrega.get().strip()
        if not _fecha_valida(ingreso) or not _fecha_valida(entrega):
            lbl_error.config(text="⚠ Ambas fechas deben tener formato dd/mm/aaaa.")
            return

        promover_a_op(json_cotizacion, ingreso, entrega)

        dlg.grab_release()
        dlg.destroy()
        on_aprobado()

    btn_cancelar = tk.Label(
        frame_btns, text="Cancelar", font=FUENTE_BTN, bg="#AAAAAA",
        fg="#FFFFFF", padx=24, pady=12, cursor="hand2",
    )
    btn_cancelar.pack(side="left")

    btn_confirmar = tk.Label(
        frame_btns, text="Aprobar", font=FUENTE_BTN, bg=COLORES["btn_enabled"],
        fg="#FFFFFF", padx=24, pady=12, cursor="hand2",
    )
    btn_confirmar.pack(side="right")

    btn_cancelar.bind("<Button-1>", _cancelar)
    btn_confirmar.bind("<Button-1>", _confirmar)
    btn_cancelar.bind("<Enter>", lambda _: btn_cancelar.config(bg="#888888"))
    btn_cancelar.bind("<Leave>", lambda _: btn_cancelar.config(bg="#AAAAAA"))
    btn_confirmar.bind("<Enter>", lambda _: btn_confirmar.config(bg=COLORES["btn_en_hover"]))
    btn_confirmar.bind("<Leave>", lambda _: btn_confirmar.config(bg=COLORES["btn_enabled"]))

    dlg.bind("<Return>", _confirmar)
    dlg.bind("<Escape>", _cancelar)

    dlg.focus_force()
    dlg.wait_window()
