"""
ui/api_inventario.py
Lógica de las dos tablas del panel de Inventario (menu.html) — instanciada
una sola vez por ui.api_app.ApiApp. Gestión de rollos de tela (CRUD sobre
core/repositorio_inventario.py) y, desde 2026-09-14, de materiales no
textiles (CRUD sobre core/repositorio_materiales.py) — más los catálogos
de nombres de textil (core.repositorio.TEXTILES), de materiales (nombres
YA cargados en la propia tabla, ver cargar_nombres_materiales) y de
proveedores (core.repositorio.cargar_proveedores/guardar_proveedor) para
el autocompletado de los formularios — mismo mecanismo que el campo
Cliente de gestionar-direcciones.html.
"""

from core import repositorio
from core import repositorio_inventario as _repo
from core import repositorio_materiales as _repo_mat


class ApiInventario:

    def contexto_extra(self, id_) -> dict:
        return {"id": id_}

    def listar_rollos(self) -> list[dict]:
        return _repo.listar_rollos()

    def obtener_rollo(self, id_: str) -> dict | None:
        return _repo.obtener_rollo(id_)

    def cargar_textiles(self) -> list[str]:
        return repositorio.TEXTILES

    def cargar_proveedores(self) -> list[str]:
        return repositorio.cargar_proveedores()

    def guardar_proveedor(self, nombre: str) -> None:
        repositorio.guardar_proveedor(nombre)

    def valor_sugerido_textil(self, nombre_textil: str) -> float | None:
        return _repo.valor_sugerido_textil(nombre_textil)

    def crear_rollo(
        self, nombre_textil: str, ancho, metros_restantes,
        precio_compra=0.0, valor=None, proveedor="",
    ) -> dict:
        return _repo.crear_rollo(nombre_textil, ancho, metros_restantes, precio_compra, valor, proveedor)

    def editar_rollo(
        self, id_: str, nombre_textil: str, ancho,
        precio_compra=0.0, valor=None, proveedor="",
    ) -> dict | None:
        return _repo.editar_rollo(id_, nombre_textil, ancho, precio_compra, valor, proveedor)

    def cambiar_estado_rollo(self, id_: str, activo: bool) -> dict | None:
        return _repo.cambiar_estado_rollo(id_, activo)

    def decomisionar_rollo(self, id_: str) -> bool:
        return _repo.decomisionar_rollo(id_)

    def ajustar_restante_rollo(self, id_: str, nuevo_restante, descripcion: str = "") -> dict | None:
        return _repo.ajustar_restante(id_, nuevo_restante, descripcion)

    def ajustar_estado_rollo(self, id_: str, activo: bool, descripcion: str = "") -> dict | None:
        return _repo.ajustar_estado(id_, activo, descripcion)

    def eliminar_ajuste_rollo(self, id_rollo: str, id_ajuste: str) -> dict | None:
        return _repo.eliminar_ajuste(id_rollo, id_ajuste)

    # ── Materiales ────────────────────────────────────────────────────────
    # "gasto_mes" se agrega ACÁ (no vive en el JSON persistido) — es un
    # derivado de 'historial' que cambia con el simple paso del tiempo (un
    # 1° de mes, la compra de ayer deja de contar), así que calcularlo al
    # servir en vez de guardarlo evita que quede desactualizado.

    def _con_gasto_mes(self, m: dict | None) -> dict | None:
        if m is not None:
            m["gasto_mes"] = _repo_mat.gasto_del_mes(m)
        return m

    def listar_materiales(self) -> list[dict]:
        return [self._con_gasto_mes(m) for m in _repo_mat.listar_materiales()]

    def obtener_material(self, id_: str) -> dict | None:
        return self._con_gasto_mes(_repo_mat.obtener_material(id_))

    def cargar_nombres_materiales(self) -> list[str]:
        return [m["nombre"] for m in _repo_mat.listar_materiales()]

    def ingresar_material(
        self, nombre: str, cantidad, tipo="unidad", proveedor="",
        costo_total=None, costo_unitario=None,
    ) -> dict:
        return self._con_gasto_mes(
            _repo_mat.ingresar_material(nombre, cantidad, tipo, proveedor, costo_total, costo_unitario)
        )

    def editar_material(self, id_: str, nombre: str, tipo: str, valor=None, proveedor="") -> dict | None:
        return self._con_gasto_mes(_repo_mat.editar_material(id_, nombre, tipo, valor, proveedor))

    def registrar_uso_material(self, id_: str, cantidad_usada, descripcion: str = "") -> dict | None:
        return self._con_gasto_mes(_repo_mat.registrar_uso(id_, cantidad_usada, descripcion))

    def ajustar_cantidad_material(self, id_: str, nueva_cantidad, descripcion: str = "") -> dict | None:
        return self._con_gasto_mes(_repo_mat.ajustar_cantidad(id_, nueva_cantidad, descripcion))

    def eliminar_ultimo_historial_material(self, id_material: str, id_entrada: str) -> dict | None:
        return self._con_gasto_mes(_repo_mat.eliminar_ultimo_historial(id_material, id_entrada))
