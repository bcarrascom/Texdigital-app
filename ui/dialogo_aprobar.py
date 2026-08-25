"""
ui/dialogo_aprobar.py
Lógica compartida para promover una cotización a Orden de Producción (OP) —
la usa ui/api_ver_cotizacion.py (botón "Aprobar" de ver-cotizacion.html).

Al confirmar:
1. Guarda el JSON de la OP en Dropbox/SGTD/OPs/JSON/ (Fecha → Fecha_ingreso/Fecha_entrega).
2. Mueve el JSON de la cotización a Dropbox/SGTD/Cotizaciones/Historial/.
3. Elimina el Excel de la cotización (ya no se necesita).
"""

from core.repositorio_cotizaciones import mover_a_historial, eliminar_excel
from core.repositorio_ops import guardar_op


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
