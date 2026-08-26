"""
ui/dialogo_recotizar.py
Lógica compartida para devolver una OP activa a Cotizaciones — inversa de
ui/dialogo_aprobar.py::promover_a_op. La usa ui/api_ver_op.py (botón
"Recotizar" de ver-op.html).

Al confirmar:
1. Saca el JSON de la OP de Dropbox/SGTD/OPs/JSON/ (solo activas — ver
   core.repositorio_ops.retirar_activa).
2. Lo guarda como cotización en Dropbox/SGTD/Cotizaciones/JSON/, con
   Fecha_ingreso/Fecha_entrega/Estado/Fecha_completada/ProductosListos
   descartados y Fecha = hoy (se está recotizando ahora, no en la fecha
   original de ingreso a producción).
"""

from datetime import datetime

from core.repositorio_cotizaciones import guardar_cotizacion
from core.repositorio_ops import retirar_activa

_CAMPOS_SOLO_OP = ("Fecha_ingreso", "Fecha_entrega", "Estado", "Fecha_completada", "ProductosListos")


def recotizar_op(numero: int) -> bool:
    """Convierte una OP activa de vuelta en cotización: sin UI. Devuelve
    False sin tocar nada si la OP no está activa (ya se completó, está
    pendiente, o directamente no existe)."""
    datos = retirar_activa(int(numero))
    if datos is None:
        return False

    cot_dict = {k: v for k, v in datos.items() if k not in _CAMPOS_SOLO_OP}
    cot_dict["Fecha"] = datetime.now().strftime("%d/%m/%Y")

    guardar_cotizacion(cot_dict)
    return True
