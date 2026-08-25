"""
ui/api_menu.py
Lógica de menu.html — instanciada una sola vez por ui.api_app.ApiApp, que
es quien de verdad queda expuesta a pywebview (ver docstring de ese
módulo: ya no hay una ventana/instancia por pantalla, así que esta clase
no tiene estado propio ni sabe nada de navegación — eso lo resuelve
ApiApp.ir()/abrir_cotizacion()/abrir_pendiente()/abrir_op()).
"""

from core.repositorio_cotizaciones import listar_cotizaciones
from core.repositorio_pendientes import listar_pendientes
from core.repositorio_ops import listar_todas_las_ops, ESTADO_ACTIVA


def _completos_pendiente(p: dict) -> tuple[int, int]:
    """(completos, total) de una cotización pendiente — soporta las dos
    formas que puede tener "productos" en un pendiente guardado:
    - Formato viejo (cotizadores Tkinter, ya retirados): lista con
      huecos, None = todavía sin llenar.
    - Formato nuevo (ui/api_cotizacion.py, ApiCotizacion.guardar_progreso):
      nunca tiene huecos None — cada producto es un dict del esquema
      frontend, "completo" si tiene medidas/cantidad cargadas (mismo
      criterio que completo(p) en nueva-cotizacion.html)."""
    productos = p.get("productos", [])
    if "cliente" in p:
        completos = sum(
            1 for x in productos
            if x and str(x.get("ancho", "")).strip() and str(x.get("alto", "")).strip()
            and str(x.get("cantidad", "")).strip()
        )
        return completos, len(productos)
    return sum(1 for x in productos if x is not None), len(productos)


def _ops_activas() -> list[dict]:
    """OPs con Estado == "activa", de todos los meses."""
    activas = [
        {
            "numero":        datos.get("Cotizacion"),
            "empresa":       datos.get("Empresa", "—"),
            "fecha_entrega": datos.get("Fecha_entrega", ""),
        }
        for datos in listar_todas_las_ops()
        if datos.get("Estado") == ESTADO_ACTIVA
    ]
    activas.sort(key=lambda o: o["numero"], reverse=True)
    return activas


class ApiMenu:

    def obtener_resumen(self) -> dict:
        pendientes = []
        for p in listar_pendientes():
            completos, total = _completos_pendiente(p)
            pendientes.append({
                "id": p.get("id"),
                "nombre_trabajo": p.get("nombre_trabajo", "Sin nombre"),
                "completos": completos,
                "total": total,
            })
        return {
            "pendientes":   pendientes,
            "cotizaciones": listar_cotizaciones(),
            "ops":          _ops_activas(),
        }
