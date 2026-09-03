"""
ui/api_inventario.py
Lógica de la tabla de rollos del panel de Inventario (menu.html) —
instanciada una sola vez por ui.api_app.ApiApp. Gestión de rollos de tela,
el único tipo de material del módulo Inventario por ahora (ver
core/config.py). CRUD sobre core/repositorio_inventario.py más el
catálogo de nombres de textil (core.repositorio.TEXTILES) para el
autocompletado del formulario — mismo mecanismo que el campo Cliente de
gestionar-direcciones.html.
"""

from core import repositorio
from core import repositorio_inventario as _repo


class ApiInventario:

    def listar_rollos(self) -> list[dict]:
        return _repo.listar_rollos()

    def cargar_textiles(self) -> list[str]:
        return repositorio.TEXTILES

    def crear_rollo(self, nombre_textil: str, ancho, metros_restantes, metros_iniciales=None) -> dict:
        return _repo.crear_rollo(nombre_textil, ancho, metros_restantes, metros_iniciales)

    def editar_rollo(self, id_: str, nombre_textil: str, ancho) -> dict | None:
        return _repo.editar_rollo(id_, nombre_textil, ancho)

    def decomisionar_rollo(self, id_: str) -> bool:
        return _repo.decomisionar_rollo(id_)

    def ajustar_restante_rollo(self, id_: str, nuevo_restante, descripcion: str = "") -> dict | None:
        return _repo.ajustar_restante(id_, nuevo_restante, descripcion)

    def eliminar_ajuste_rollo(self, id_rollo: str, id_ajuste: str) -> dict | None:
        return _repo.eliminar_ajuste(id_rollo, id_ajuste)
