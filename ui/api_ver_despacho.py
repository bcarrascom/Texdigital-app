"""
ui/api_ver_despacho.py
Lógica de ver-despacho.html — instanciada una sola vez por ui.api_app.ApiApp
(ver docstring de ui/api_app.py). Detalle de una OP ya asignada (ver
ui/api_asignar_despacho.py — cada producto ya tiene su dirección puesta):
acá se generan las guías de despacho, posiblemente parciales.
"""

import webbrowser

from core import repositorio_despachos
from core.presentar_despacho import generar_html


def _nombre_producto(p: dict) -> str:
    """Mismo criterio que core.repositorio_despachos._nombre_producto —
    duplicado acá a propósito (cada Api* de pantalla queda autocontenida,
    igual que las pantallas HTML) en vez de importar un helper privado de
    otro módulo."""
    if "Caja" in p:
        return f"Backlight · {p.get('Tela', '')}".strip(" ·")
    return p.get("producto", "") or "—"


def op_despacho_a_json(datos: dict) -> dict:
    """Convierte una OP guardada en Despachos/OPs (core.repositorio_despachos)
    al shape que espera ver-despacho.html."""
    productos = []
    sin_direccion = 0
    for p in datos.get("productos", []):
        cantidad = p.get("Cantidad", 0) or 0
        despachada = p.get("CantidadDespachada", 0) or 0
        direccion = p.get("Direccion")
        if not direccion:
            sin_direccion += 1
        productos.append({
            "nombre": _nombre_producto(p),
            "tema": p.get("Tema", ""),
            "cantidad": cantidad,
            "cantidad_despachada": despachada,
            "pendiente": max(0, cantidad - despachada),
            "direccion": direccion,
        })
    return {
        "numero":            datos.get("Cotizacion"),
        "nombre":            datos.get("Nombre", ""),
        "empresa":           datos.get("Empresa", ""),
        "rut":               datos.get("RUT", ""),
        "contacto":          datos.get("Contacto", ""),
        "email":             datos.get("Email", ""),
        "fecha_completada":  datos.get("Fecha_completada", ""),
        "estado_despacho":   datos.get("EstadoDespacho") or repositorio_despachos.estado_despacho(datos),
        "estado_asignacion": datos.get("EstadoAsignacion") or repositorio_despachos.estado_asignacion(datos),
        "instalacion":       datos.get("Instalacion") is not None,
        "productos":         productos,
        "productos_sin_direccion": sin_direccion,
    }


class ApiVerDespacho:

    def contexto_extra(self, numero) -> dict:
        return {"numero": int(numero) if numero is not None else None}

    def obtener(self, numero) -> dict | None:
        datos = repositorio_despachos.cargar_op_despacho(int(numero))
        if datos is None:
            return None
        resultado = op_despacho_a_json(datos)
        resultado["guias"] = repositorio_despachos.listar_guias_de_op(int(numero))
        return resultado

    def generar_guia(self, numero_op, items: list[dict], observaciones: str = "") -> dict | None:
        """Genera la guía (todos los productos de `items` tienen que
        compartir la misma dirección, ver core.repositorio_despachos.
        generar_guia), la imprime (abre el HTML en el navegador, mismo
        patrón que ApiVerOp.imprimir_op) y devuelve el dict de la guía —
        o None si falló, para que el JS muestre un aviso en vez de
        romper."""
        try:
            guia = repositorio_despachos.generar_guia(int(numero_op), items, observaciones)
        except ValueError as e:
            print("No se pudo generar la guía de despacho:", e)
            return None
        ruta_html = generar_html(guia)
        webbrowser.open(ruta_html.as_uri())
        return guia

    def reimprimir_guia(self, numero_guia) -> bool:
        guia = repositorio_despachos.cargar_guia(numero_guia)
        if guia is None:
            return False
        ruta_html = generar_html(guia)
        webbrowser.open(ruta_html.as_uri())
        return True
