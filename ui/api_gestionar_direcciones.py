"""
ui/api_gestionar_direcciones.py
Lógica de gestionar-direcciones.html — instanciada una sola vez por
ui.api_app.ApiApp. Submódulo de Despachos (ver menu.html, botón
"Gestionar direcciones" del panel Despachos) para agregar, editar,
eliminar y ver a qué cliente está asociada cada dirección de
direcciones.json (ver core/repositorio.py).

Editar/eliminar acá NO toca las OPs de Despachos que ya tengan alguna de
estas direcciones asignada a un producto: esa asignación es una COPIA
hecha en el momento (ver core.repositorio_despachos.
asignar_direccion_productos), no una referencia viva a direcciones.json.
"""

from core import repositorio


class ApiGestionarDirecciones:

    def contexto_extra(self) -> dict:
        return {}

    def listar_direcciones(self) -> list[dict]:
        return repositorio.cargar_direcciones()

    def cargar_clientes(self) -> list[dict]:
        return repositorio.cargar_clientes()

    def cargar_regiones(self) -> list[str]:
        return repositorio.cargar_regiones()

    def guardar_direccion(self, direccion: dict) -> dict:
        """Crea una dirección nueva si `direccion` no trae "id", o edita la
        existente si lo trae — un solo botón "Guardar" en el panel para
        los dos casos (ver gestionar-direcciones.html)."""
        id_ = direccion.get("id")
        campos = dict(
            rut=direccion.get("rut", ""),
            empresa=direccion.get("empresa", ""),
            alias=direccion.get("alias", ""),
            calle=direccion.get("calle", ""),
            numero=direccion.get("numero", ""),
            comuna=direccion.get("comuna", ""),
            region=direccion.get("region", ""),
            referencia=direccion.get("referencia", ""),
        )
        if id_:
            return repositorio.editar_direccion(id_, **campos) or direccion
        return repositorio.guardar_direccion(**campos)

    def eliminar_direccion(self, id_: str) -> bool:
        return repositorio.eliminar_direccion(id_)
