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
3. Devuelve al stock la tela y los materiales que descontó aprobarla, y
   recalcula los reportes mensuales de Inventario desde el mes en que se
   aprobó (pedido de Bruno, 2026-10-24) — ver
   core.repositorio_inventario.revertir_consumo_op y
   core.reportes_inventario.recalcular_desde.
"""

from datetime import datetime

from core.repositorio_cotizaciones import guardar_cotizacion
from core.repositorio_ops import retirar_activa
from core import repositorio_inventario as _repo_inv
from core import repositorio_materiales as _repo_mat
from core import reportes_inventario as _reportes

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
    # RollosUsados es la asignación de rollos que hizo la aprobación (ver
    # ui/api_ver_cotizacion.py::aprobar_cotizacion): con el consumo revertido
    # ya no vale, y aprobarla de nuevo elige los rollos otra vez.
    for producto in cot_dict.get("productos", []):
        producto.pop("RollosUsados", None)

    # La cotización se guarda ANTES de tocar el stock: retirar_activa ya
    # borró la OP, y si algo de lo que sigue fallara, el trabajo no puede
    # quedar perdido entre las dos carpetas.
    guardar_cotizacion(cot_dict)

    fechas = _repo_inv.revertir_consumo_op(int(numero)) + _repo_mat.revertir_consumo_op(int(numero))
    # Si falla, el stock ya volvió: el mes en curso se rearma al abrir la
    # página de reportes (los cerrados no, ver recalcular_desde).
    try:
        _reportes.recalcular_desde(fechas)
    except Exception:
        pass
    return True
