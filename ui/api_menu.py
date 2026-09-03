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
from core.repositorio_despachos import (
    listar_ops_despacho, ESTADO_ASIGNACION_ASIGNADA,
    marcar_entregado, eliminar_despacho,
)
from core.repositorio_inventario import listar_rollos


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


def _despachos_pendientes() -> list[dict]:
    """OPs en Despachos/OPs/NoAsignadas — todavía les falta dirección a
    algún producto (la dirección es POR PRODUCTO, no por OP, ver
    core/repositorio_despachos.py). Mismo shape que _completos_pendiente
    (completos/total) para que la tarjeta del menú se vea y se comporte
    igual que las cotizaciones incompletas (ver tarjetaDespacho en
    menu.html, calcada de tarjetaPendiente)."""
    pendientes = []
    for datos in listar_ops_despacho():
        if datos.get("EstadoAsignacion") == ESTADO_ASIGNACION_ASIGNADA:
            continue
        productos = datos.get("productos", [])
        asignados = sum(1 for p in productos if p.get("Direccion"))
        pendientes.append({
            "numero": datos.get("Cotizacion"),
            "nombre": datos.get("Nombre", ""),
            "asignados": asignados,
            "total": len(productos),
        })
    pendientes.sort(key=lambda d: d["numero"], reverse=True)
    return pendientes


REGION_METROPOLITANA = "Región Metropolitana"


def _ubicaciones(datos: dict) -> list[str]:
    """Comuna (o región, si el producto no es de la Región Metropolitana) de
    cada producto de la OP, sin repetidos y en orden de aparición — la
    dirección es POR PRODUCTO (ver core/repositorio_despachos.py), así que
    una OP puede tener varios destinos distintos. Se usa para la tarjeta del
    panel "Con dirección asignada" (ver tarjetaDespachoAsignado en
    menu.html), que rota entre estos en vez de mostrar un estado que es
    "Pendiente" en casi todas."""
    ubicaciones = []
    for p in datos.get("productos", []):
        direccion = p.get("Direccion") or {}
        region = direccion.get("region", "")
        lugar = direccion.get("comuna", "") if region == REGION_METROPOLITANA else region
        if lugar and lugar not in ubicaciones:
            ubicaciones.append(lugar)
    return ubicaciones


def _despachos_asignados() -> list[dict]:
    """OPs en Despachos/OPs/Asignadas — ya tienen dirección en todos sus
    productos, listas para seleccionar en el panel y marcar Entregadas o
    eliminar (ver ApiMenu.marcar_despacho_entregado/eliminar_despachos)."""
    asignados = [
        {
            "numero":          datos.get("Cotizacion"),
            "nombre":          datos.get("Nombre", ""),
            "empresa":         datos.get("Empresa", "—"),
            "estado_despacho": datos.get("EstadoDespacho", ""),
            "ubicaciones":     _ubicaciones(datos),
        }
        for datos in listar_ops_despacho()
        if datos.get("EstadoAsignacion") == ESTADO_ASIGNACION_ASIGNADA
    ]
    asignados.sort(key=lambda d: d["numero"], reverse=True)
    return asignados


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
            "pendientes":          pendientes,
            "cotizaciones":        listar_cotizaciones(),
            "ops":                 _ops_activas(),
            "despachos":           _despachos_pendientes(),
            "despachos_asignados": _despachos_asignados(),
            "rollos":              listar_rollos(),
        }

    def marcar_despacho_entregado(self, numero) -> bool:
        return marcar_entregado(numero)

    def eliminar_despachos(self, numeros: list) -> int:
        """Elimina varios despachos de una (selección múltiple con Shift,
        ver menu.html) — devuelve cuántos encontró y borró de verdad."""
        return sum(1 for n in numeros if eliminar_despacho(n))

    def generar_guia_despacho(self, numero) -> None:
        """Botón 'Generar guía' del panel de Despachos — todavía sin
        implementar, Bruno la completa en una sesión aparte."""
