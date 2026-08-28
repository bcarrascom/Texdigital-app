"""
ui/api_asignar_despacho.py
Lógica de asignar-despacho.html — instanciada una sola vez por
ui.api_app.ApiApp (ver docstring de ui/api_app.py). Asignación de
dirección de entrega POR PRODUCTO a una OP recién llegada a Despachos
(OPs/NoAsignadas/) — ver core/repositorio_despachos.py. No hay un botón
"Completar" aparte: apenas el último producto que faltaba queda con
dirección, la OP pasa sola a OPs/Asignadas/ (ver
core.repositorio_despachos._sincronizar_carpeta) — el usuario simplemente
aprieta "Volver" cuando termina.
"""

from core import repositorio
from core import repositorio_despachos


def _nombre_producto(p: dict) -> str:
    """Mismo criterio que core.repositorio_despachos._nombre_producto —
    duplicado a propósito, ver ui/api_ver_despacho.py."""
    if "Caja" in p:
        return f"Backlight · {p.get('Tela', '')}".strip(" ·")
    return p.get("producto", "") or "—"


class ApiAsignarDespacho:

    def contexto_extra(self, numero) -> dict:
        return {"numero": int(numero) if numero is not None else None}

    def obtener(self, numero) -> dict | None:
        datos = repositorio_despachos.cargar_op_despacho(int(numero))
        if datos is None:
            return None
        productos = [
            {
                "nombre": _nombre_producto(p),
                "tema": p.get("Tema", ""),
                "cantidad": p.get("Cantidad", 0),
                "direccion": p.get("Direccion"),
            }
            for p in datos.get("productos", [])
        ]
        return {
            "numero":     datos.get("Cotizacion"),
            "nombre":     datos.get("Nombre", ""),
            "empresa":    datos.get("Empresa", ""),
            "rut":        datos.get("RUT", ""),
            "contacto":   datos.get("Contacto", ""),
            "instalacion": datos.get("Instalacion") is not None,
            "productos":  productos,
        }

    def cargar_todas_direcciones(self) -> list[dict]:
        """TODAS las direcciones guardadas (de cualquier cliente) — el
        selector de la pantalla las agrupa mostrando primero las del
        cliente de la OP (ver asignar-despacho.html)."""
        return repositorio.cargar_direcciones()

    def cargar_clientes(self) -> list[dict]:
        """Para el selector de cliente del panel "dirección nueva" —
        autocompletado por nombre/RUT (ver <datalist> en
        asignar-despacho.html)."""
        return repositorio.cargar_clientes()

    def cargar_regiones(self) -> list[str]:
        return repositorio.cargar_regiones()

    def guardar_direccion_nueva(self, direccion: dict) -> dict:
        """Guarda una dirección nueva en direcciones.json (la pantalla la
        agrega al selector, pero todavía NO la asigna a ningún producto —
        eso es un paso aparte, ver asignar_a_productos)."""
        repositorio.guardar_direccion(
            rut=direccion.get("rut", ""),
            empresa=direccion.get("empresa", ""),
            alias=direccion.get("alias", ""),
            calle=direccion.get("calle", ""),
            numero=direccion.get("numero", ""),
            comuna=direccion.get("comuna", ""),
            region=direccion.get("region", ""),
            referencia=direccion.get("referencia", ""),
        )
        return direccion

    def asignar_a_productos(self, numero_op, indices: list[int], direccion: dict) -> None:
        repositorio_despachos.asignar_direccion_productos(int(numero_op), indices, direccion)

    def quitar_de_productos(self, numero_op, indices: list[int]) -> None:
        repositorio_despachos.quitar_direccion_productos(int(numero_op), indices)
