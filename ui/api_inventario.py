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


def _iso_a_dma(iso: str) -> str:
    """"yyyy-mm-dd" (lo que manda un <input type="date">) -> "dd/mm/aaaa"
    (lo que usa el resto del sistema) — mismo criterio que _iso_a_dma de
    ui/api_ver_cotizacion.py, acá para el panel "Restock" de
    ver-material.html (pedido de Bruno, 2026-09-29)."""
    anio, mes, dia = iso.split("-")
    return f"{dia}/{mes}/{anio}"


class ApiInventario:

    def contexto_extra(self, id_) -> dict:
        return {"id": id_}

    # Las 9 cifras del modelo económico (ver
    # core.repositorio_inventario.metricas_rollo) se agregan ACÁ, igual que en
    # materiales: son derivados que cambian con el paso del tiempo ("gasto este
    # mes") o cuentas de dos campos guardados, así que calcularlas al servir evita
    # que queden desactualizadas y le ahorra a la UI saber de dónde sale cada una.

    def _con_metricas_rollo(self, r: dict | None) -> dict | None:
        if r is not None:
            r.update(_repo.metricas_rollo(r))
        return r

    def listar_rollos(self) -> list[dict]:
        return [self._con_metricas_rollo(r) for r in _repo.listar_rollos()]

    def obtener_rollo(self, id_: str) -> dict | None:
        return self._con_metricas_rollo(_repo.obtener_rollo(id_))

    def cargar_textiles(self) -> list[str]:
        return repositorio.TEXTILES

    def cargar_proveedores(self) -> list[str]:
        return repositorio.cargar_proveedores()

    def guardar_proveedor(self, nombre: str) -> None:
        repositorio.guardar_proveedor(nombre)

    def editar_proveedor(self, nombre_actual: str, nombre_nuevo: str) -> bool:
        return repositorio.editar_proveedor(nombre_actual, nombre_nuevo)

    def eliminar_proveedor(self, nombre: str) -> bool:
        return repositorio.eliminar_proveedor(nombre)

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
    # Las 9 cifras del modelo económico (ver
    # core.repositorio_materiales.metricas_material) se agregan ACÁ, no viven
    # en el JSON persistido: unas son derivados de 'historial' que cambian con
    # el simple paso del tiempo (un 1° de mes, la compra de ayer deja de
    # contar en "gasto este mes") y otras son cuentas de dos campos que sí
    # están guardados. Calcularlas al servir en vez de guardarlas evita que
    # queden desactualizadas, y le ahorra a la UI tener que saber de dónde
    # sale cada una.

    def _con_metricas(self, m: dict | None) -> dict | None:
        if m is not None:
            m.update(_repo_mat.metricas_material(m))
        return m

    def listar_materiales(self) -> list[dict]:
        return [self._con_metricas(m) for m in _repo_mat.listar_materiales()]

    def obtener_material(self, id_: str) -> dict | None:
        return self._con_metricas(_repo_mat.obtener_material(id_))

    def cargar_nombres_materiales(self) -> list[str]:
        return [m["nombre"] for m in _repo_mat.listar_materiales()]

    def ingresar_material(
        self, nombre: str, cantidad, tipo="unidad", proveedor="",
        costo_total=None, costo_unitario=None,
        tipo_consumo=None, consumo_parametros=None,
        productos_asociados=None, estructuras_asociadas=None,
        fecha=None, valor=None,
    ) -> dict:
        return self._con_metricas(
            _repo_mat.ingresar_material(
                nombre, cantidad, tipo, proveedor, costo_total, costo_unitario,
                tipo_consumo, consumo_parametros, productos_asociados, estructuras_asociadas,
                _iso_a_dma(fecha) if fecha else None, valor,
            )
        )

    def editar_material(
        self, id_: str, nombre: str, tipo: str, valor=None, proveedor="",
        tipo_consumo=None, consumo_parametros=None,
        productos_asociados=None, estructuras_asociadas=None,
    ) -> dict | None:
        return self._con_metricas(
            _repo_mat.editar_material(
                id_, nombre, tipo, valor, proveedor,
                tipo_consumo, consumo_parametros, productos_asociados, estructuras_asociadas,
            )
        )

    def cargar_productos_catalogo(self) -> list[str]:
        """Los nombres de producto a los que se puede asociar un material. Va
        "Backlight" primero, que NO es un producto del catálogo sino un tipo de
        producto (ver core.repositorio_materiales.PRODUCTO_BACKLIGHT): asociarle
        un material lo hace gastar en todo backlight, con caja o sin caja. Era lo
        que faltaba para la silicona, que se aplica a todos y no tenía ningún
        nombre al que colgarse (pedido de Bruno, 2026-10-01)."""
        return [_repo_mat.PRODUCTO_BACKLIGHT] + list(repositorio.PRODUCTOS)

    def cargar_estructuras_catalogo(self) -> list[str]:
        return list(repositorio.ESTRUCTURAS_LEGADO)

    def ajustar_cantidad_material(self, id_: str, nueva_cantidad, descripcion: str = "") -> dict | None:
        return self._con_metricas(_repo_mat.ajustar_cantidad(id_, nueva_cantidad, descripcion))

    def ajustar_valor_material(self, id_: str, nuevo_valor, descripcion: str = "") -> dict | None:
        """Ajuste del precio de VENTA — hermano de ajustar_cantidad_material y
        el único camino desde la UI para cambiarlo (queda en el historial, ver
        core.repositorio_materiales.ajustar_valor). El costo no tiene método
        acá a propósito: sale de los restocks, no de un formulario."""
        return self._con_metricas(_repo_mat.ajustar_valor(id_, nuevo_valor, descripcion))

    def eliminar_ultimo_historial_material(self, id_material: str, id_entrada: str) -> dict | None:
        return self._con_metricas(_repo_mat.eliminar_ultimo_historial(id_material, id_entrada))

    def eliminar_material(self, id_: str) -> bool:
        return _repo_mat.eliminar_material(id_)
