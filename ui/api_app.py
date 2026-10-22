"""
ui/api_app.py
Clase Api ÚNICA de la ventana principal de la app. La ventana carga la
interfaz de React (frontend/dist/index.html, servida por el servidor HTTP
interno de pywebview — los módulos ES no cargan sobre file://) y TODA la
navegación es del cliente (React Router): Python no navega nunca, solo
sirve datos y hace lo que se le pide. Con `--dev` (ver main.py) carga en
cambio el servidor de Vite (http://localhost:5173), para tener recarga en
caliente dentro de la app real.

La lógica de cada parte vive en su propia clase (ApiMenu,
ApiVerCotizacion, ApiVerOp, ApiHistorialOps, ApiCotizacion, despachos,
inventario — cada una en su archivo): esta clase las instancia UNA vez y
les delega, para que React vea un solo objeto (window.pywebview.api).

La resolución de cada llamada es dinámica (get_nested_attribute en
webview/util.py), no una lista fija: agregar un método acá alcanza para
que React lo pueda llamar.

El panel de producción es su propia ventana aparte, con su propia API, sin
relación con esta clase (ver ui/panel_produccion.py).
"""

import json
import sys
import threading
from datetime import datetime

from core import config as _config
from core.config import MODULOS_HABILITADOS
from core.repositorio import cargar_preferencias, guardar_preferencia as _guardar_preferencia
from core.repositorio_inventario import migrar_formato_viejo as _migrar_inventario_formato_viejo
from core.rutas import DOCS as _DOCS, FRONTEND
from core.version import VERSION

from ui.api_menu import ApiMenu
from ui.api_ver_cotizacion import ApiVerCotizacion
from ui.api_ver_op import ApiVerOp
from ui.api_historial_ops import ApiHistorialOps
from ui.api_cotizacion import ApiCotizacion
from ui.api_ver_despacho import ApiVerDespacho
from ui.api_asignar_despacho import ApiAsignarDespacho
from ui.api_gestionar_direcciones import ApiGestionarDirecciones
from ui.api_inventario import ApiInventario


def _abrir_manual_usuario() -> None:
    """Abre el manual de usuario (docs/Manual_de_Uso.pdf) con el visor de
    PDF por defecto del SO."""
    ruta = _DOCS / "Manual_de_Uso.pdf"
    if not ruta.exists():
        return
    ruta = str(ruta)
    if sys.platform == "win32":
        import os
        os.startfile(ruta)
    elif sys.platform == "darwin":
        import subprocess
        subprocess.run(["open", ruta])
    else:
        import subprocess
        subprocess.run(["xdg-open", ruta])


class ApiApp:

    def __init__(self, url_dev: str | None = None):
        self._ventana = None
        # Servidor de Vite en vez del build (ver `--dev` en main.py).
        self._url_dev = url_dev
        # Ruta actual de React Router (ver notificar_ruta) — la usa la X
        # nativa para decidir entre "Volver" y cerrar la app.
        self._ruta_react = "/"

        self._menu = ApiMenu()
        self._ver_cotizacion = ApiVerCotizacion()
        self._ver_op = ApiVerOp()
        self._historial_ops = ApiHistorialOps()
        self._cotizacion = ApiCotizacion()
        self._ver_despacho = ApiVerDespacho()
        self._asignar_despacho = ApiAsignarDespacho()
        self._gestionar_direcciones = ApiGestionarDirecciones()
        self._inventario = ApiInventario()
        _migrar_inventario_formato_viejo()

    # ── Arranque ─────────────────────────────────────────────────────────────

    def crear_ventana(self):
        """Crea la única ventana de la app. Llamar UNA vez, antes de
        webview.start() (ver main.py) — junto con
        ui.panel_produccion.preparar_panel_oculto()."""
        import webview
        # Ruta pelada, sin file:// a propósito: pywebview la sirve con su
        # servidor HTTP interno (ver webview/util.py::is_local_url).
        url = self._url_dev or str(FRONTEND / "index.html")
        if not self._url_dev and not (FRONTEND / "index.html").exists():
            raise FileNotFoundError(
                f"No existe {FRONTEND / 'index.html'} — correr `npm run build` en frontend/."
            )
        self._ventana = webview.create_window(
            "TexDigital",
            url=url,
            js_api=self,
            width=1360,
            height=860,
        )
        self._ventana.events.closing += self._al_cerrar_nativo
        return self._ventana

    def _al_cerrar_nativo(self):
        """La X nativa de la ventana: en el inicio (el menú) cierra la app
        entera; en cualquier otra pantalla se comporta como "← Volver"
        (window.TD.volver, ver frontend/src/router/RutasAnimadas.jsx)."""
        if self._ruta_react in ("", "/"):
            from ui.panel_produccion import salir_app
            salir_app()
            return None
        # En un hilo aparte: no bloquear el evento nativo de cierre esperando
        # a la página.
        threading.Timer(0, lambda: self._ventana.run_js("window.TD && TD.volver && TD.volver()")).start()
        return False  # cancela el cierre nativo — React ya volvió

    # ── Contrato común ───────────────────────────────────────────────────────

    def obtener_contexto(self, pantalla: str | None = None, argumentos: dict | None = None) -> dict:
        """El contexto común de la app (lo pide UNA vez al arrancar, ver
        frontend/src/context/AppContext.jsx). Con `pantalla`, además lo
        propio de esa pantalla según los argumentos de su ruta — hoy solo
        Nueva cotización lo necesita."""
        preferencias = cargar_preferencias()
        hoy = datetime.now()
        ctx = {
            "version":             VERSION,
            "escala_ui":           preferencias.get("escala_ui", 1),
            "hoy_iso":             hoy.strftime("%Y-%m-%d"),
            "fecha":               hoy.strftime("%d-%m-%Y"),
            "modulos_habilitados": MODULOS_HABILITADOS,
            "stock_minimo_ml":     _config.STOCK_MINIMO_ML,
        }
        if pantalla == "nueva-cotizacion":
            args = argumentos or {}
            ctx.update(self._cotizacion.contexto_extra(args.get("editar"), args.get("pendiente")))
        return ctx

    def guardar_preferencia(self, clave: str, valor) -> bool:
        _guardar_preferencia(clave, valor)
        return True

    def abrir_manual(self) -> None:
        _abrir_manual_usuario()

    def notificar_ruta(self, ruta: str) -> None:
        """React avisa en cada cambio de ruta (ver frontend/src/router) —
        solo para que la X nativa sepa si está en el inicio o no (ver
        _al_cerrar_nativo)."""
        self._ruta_react = ruta or "/"

    def poner_titulo(self, titulo: str) -> None:
        """Título de la ventana nativa — pywebview no lo sincroniza solo
        con document.title."""
        if self._ventana is not None:
            self._ventana.set_title(titulo or "TexDigital")

    def _aviso(self, texto: str, tipo: str = "aviso", ms: int = 5000) -> None:
        if self._ventana is None:
            return
        script = f"window.TD && TD.aviso({json.dumps(texto)}, {json.dumps(tipo)}, {ms})"
        self._ventana.evaluate_js(script)

    # ── Menú ─────────────────────────────────────────────────────────────────

    def obtener_resumen(self) -> dict:
        return self._menu.obtener_resumen()

    def ir(self, destino: str) -> None:
        """Lo único que React no puede abrir por su cuenta: otra ventana."""
        if destino == "panel_produccion":
            if sys.platform == "darwin":
                from ui.panel_produccion import mostrar_panel_mac
                mostrar_panel_mac()
            else:
                from ui.panel_produccion import mostrar_panel
                mostrar_panel()
        else:
            self._aviso(f'Todavía no hay pantalla para "{destino}".', "aviso")

    def buscar_actualizacion(self) -> None:
        self._aviso("Todavía no está conectado el buscador de actualizaciones.", "info")

    # ── Ver cotización ───────────────────────────────────────────────────────

    def obtener_cotizacion(self, numero) -> dict | None:
        return self._ver_cotizacion.obtener_cotizacion(numero)

    def cotizacion_adyacente(self, numero, direccion: str) -> int | None:
        """Cuál es la cotización vecina (←/→, ver ApiVerCotizacion.
        numero_adyacente) — la navegación la hace React Router."""
        return self._ver_cotizacion.numero_adyacente(numero, direccion)

    # El aviso "cambiaron precios" de Ver cotización (ver core.lista_precios).
    def actualizar_precios_cotizacion(self, numero) -> bool:
        return self._ver_cotizacion.actualizar_precios(numero)

    def mantener_precios_cotizacion(self, numero) -> bool:
        return self._ver_cotizacion.mantener_precios(numero)

    def eliminar_cotizacion(self, numero) -> None:
        self._ver_cotizacion.eliminar_cotizacion(numero)

    def imprimir_cotizacion(self, numero) -> None:
        self._ver_cotizacion.imprimir_cotizacion(numero)

    def verificar_materiales_cotizacion(self, numero) -> list[dict]:
        return self._ver_cotizacion.verificar_materiales(numero)

    def aprobar_cotizacion(self, numero, ingreso, entrega, consumos_manuales: dict | None = None) -> dict:
        return self._ver_cotizacion.aprobar_cotizacion(numero, ingreso, entrega, consumos_manuales)

    def materiales_manuales_pendientes(self, numero) -> list[dict]:
        return self._ver_cotizacion.materiales_manuales_pendientes(numero)

    # ── Ver OP ───────────────────────────────────────────────────────────────

    def obtener_op(self, numero) -> dict | None:
        return self._ver_op.obtener_op(numero)

    def op_adyacente(self, numero, direccion: str) -> int | None:
        """La OP vecina (ver cotizacion_adyacente)."""
        return self._ver_op.numero_adyacente(numero, direccion)

    def imprimir_op(self, numero) -> None:
        self._ver_op.imprimir_op(numero)

    # recotizar_op/completar_op devuelven si se pudo: la pantalla decide
    # adónde ir después.
    def recotizar_op(self, numero) -> bool:
        ok = self._ver_op.recotizar_op(numero)
        if not ok:
            self._aviso("No se pudo recotizar: la OP ya no está activa.", "error")
        return ok

    def completar_op(self, numero) -> bool:
        ok = self._ver_op.completar_op(numero)
        if not ok:
            self._aviso("No se pudo completar: la OP ya no está activa.", "error")
        return ok

    def guardar_op_inser(self, numero, marcado) -> bool:
        return self._ver_op.guardar_op_inser(numero, marcado)

    # ── Historial de OPs ─────────────────────────────────────────────────────

    def obtener_historial(self, anio, mes) -> list[dict]:
        return self._historial_ops.obtener_historial(anio, mes)

    def buscar_historial(self, filtros: dict) -> list[dict]:
        return self._historial_ops.buscar_historial(filtros)

    # ── Nueva cotización ─────────────────────────────────────────────────────

    def obtener_catalogos(self) -> dict:
        return self._cotizacion.obtener_catalogos()

    def calcular_productos(self, productos: list) -> list[dict | None]:
        return self._cotizacion.calcular_productos(productos)

    def guardar_progreso(self, estado: dict) -> dict:
        return self._cotizacion.guardar_progreso(estado)

    def numero_disponible(self, numero, propio=None) -> bool:
        return self._cotizacion.numero_disponible(numero, propio)

    def verificar_materiales(self, productos: list) -> list[dict]:
        return self._cotizacion.verificar_materiales(productos)

    def guardar_cotizacion(self, estado: dict, abrir: bool = False) -> dict:
        return self._cotizacion.guardar_cotizacion(estado, abrir)

    def guardar_cliente(self, empresa, rut, razon_social) -> bool:
        return self._cotizacion.guardar_cliente(empresa, rut, razon_social)

    def guardar_contacto(self, contacto, email, descuento, condicion) -> None:
        self._cotizacion.guardar_contacto(contacto, email, descuento, condicion)

    # ── Despachos ─────────────────────────────────────────────────────────────

    def marcar_despacho_entregado(self, numero) -> bool:
        return self._menu.marcar_despacho_entregado(numero)

    def eliminar_despachos(self, numeros: list) -> int:
        return self._menu.eliminar_despachos(numeros)

    # ── Direcciones (compartido por asignar-despacho y ver-despacho) ──────────

    def cargar_todas_direcciones(self) -> list[dict]:
        return self._asignar_despacho.cargar_todas_direcciones()

    def cargar_regiones(self) -> list[str]:
        return self._asignar_despacho.cargar_regiones()

    # ── Asignar despacho ─────────────────────────────────────────────────────

    def obtener_asignacion_despacho(self, numero) -> dict | None:
        return self._asignar_despacho.obtener(numero)

    def cargar_clientes_direccion(self) -> list[dict]:
        return self._asignar_despacho.cargar_clientes()

    def guardar_direccion_nueva(self, direccion: dict) -> dict:
        return self._asignar_despacho.guardar_direccion_nueva(direccion)

    def asignar_direccion_productos(self, numero_op, indices: list, direccion: dict) -> None:
        self._asignar_despacho.asignar_a_productos(numero_op, indices, direccion)

    def quitar_direccion_productos(self, numero_op, indices: list) -> None:
        self._asignar_despacho.quitar_de_productos(numero_op, indices)

    # ── Ver despacho ─────────────────────────────────────────────────────────

    def obtener_despacho(self, numero) -> dict | None:
        return self._ver_despacho.obtener(numero)

    def generar_guia_despacho(self, numero_op, items: list, observaciones: str = "") -> dict | None:
        return self._ver_despacho.generar_guia(numero_op, items, observaciones)

    def reimprimir_guia(self, numero_guia) -> bool:
        return self._ver_despacho.reimprimir_guia(numero_guia)

    # ── Gestionar direcciones (submódulo de Despachos) ────────────────────────

    def listar_direcciones_gestion(self) -> list[dict]:
        return self._gestionar_direcciones.listar_direcciones()

    def cargar_clientes_gestion(self) -> list[dict]:
        return self._gestionar_direcciones.cargar_clientes()

    def guardar_direccion_gestion(self, direccion: dict) -> dict:
        return self._gestionar_direcciones.guardar_direccion(direccion)

    def eliminar_direccion_gestion(self, id_) -> bool:
        return self._gestionar_direcciones.eliminar_direccion(id_)

    # ── Inventario: rollos ───────────────────────────────────────────────────

    def obtener_rollo(self, id_) -> dict | None:
        return self._inventario.obtener_rollo(id_)

    def listar_rollos(self) -> list[dict]:
        return self._inventario.listar_rollos()

    def cargar_textiles_inventario(self) -> list[str]:
        return self._inventario.cargar_textiles()

    def cargar_proveedores(self) -> list[str]:
        return self._inventario.cargar_proveedores()

    def guardar_proveedor(self, nombre) -> None:
        self._inventario.guardar_proveedor(nombre)

    def editar_proveedor(self, nombre_actual, nombre_nuevo) -> bool:
        return self._inventario.editar_proveedor(nombre_actual, nombre_nuevo)

    def eliminar_proveedor(self, nombre) -> bool:
        return self._inventario.eliminar_proveedor(nombre)

    def valor_sugerido_textil(self, nombre_textil) -> float | None:
        return self._inventario.valor_sugerido_textil(nombre_textil)

    def crear_rollo(
        self, nombre_textil, ancho, metros_restantes,
        precio_compra=0.0, valor=None, proveedor="",
    ) -> dict:
        return self._inventario.crear_rollo(nombre_textil, ancho, metros_restantes, precio_compra, valor, proveedor)

    def editar_rollo(
        self, id_, nombre_textil, ancho,
        precio_compra=0.0, valor=None, proveedor="",
    ) -> dict | None:
        return self._inventario.editar_rollo(id_, nombre_textil, ancho, precio_compra, valor, proveedor)

    def cambiar_estado_rollo(self, id_, activo: bool) -> dict | None:
        return self._inventario.cambiar_estado_rollo(id_, activo)

    def decomisionar_rollo(self, id_) -> bool:
        return self._inventario.decomisionar_rollo(id_)

    def ajustar_restante_rollo(self, id_, nuevo_restante, descripcion: str = "") -> dict | None:
        return self._inventario.ajustar_restante_rollo(id_, nuevo_restante, descripcion)

    def ajustar_estado_rollo(self, id_, activo: bool, descripcion: str = "") -> dict | None:
        return self._inventario.ajustar_estado_rollo(id_, activo, descripcion)

    def eliminar_ajuste_rollo(self, id_rollo, id_ajuste) -> dict | None:
        return self._inventario.eliminar_ajuste_rollo(id_rollo, id_ajuste)

    # ── Inventario: materiales (ver ApiInventario) ─────────────────────────────

    def obtener_material(self, id_) -> dict | None:
        return self._inventario.obtener_material(id_)

    def listar_materiales(self) -> list[dict]:
        return self._inventario.listar_materiales()

    def cargar_nombres_materiales(self) -> list[str]:
        return self._inventario.cargar_nombres_materiales()

    def ingresar_material(
        self, nombre, cantidad, tipo="unidad", proveedor="",
        costo_total=None, costo_unitario=None,
        tipo_consumo=None, consumo_parametros=None,
        productos_asociados=None, estructuras_asociadas=None,
        fecha=None, valor=None,
    ) -> dict:
        return self._inventario.ingresar_material(
            nombre, cantidad, tipo, proveedor, costo_total, costo_unitario,
            tipo_consumo, consumo_parametros, productos_asociados, estructuras_asociadas,
            fecha, valor,
        )

    def editar_material(
        self, id_, nombre, tipo, valor=None, proveedor="",
        tipo_consumo=None, consumo_parametros=None,
        productos_asociados=None, estructuras_asociadas=None,
    ) -> dict | None:
        return self._inventario.editar_material(
            id_, nombre, tipo, valor, proveedor,
            tipo_consumo, consumo_parametros, productos_asociados, estructuras_asociadas,
        )

    def cargar_productos_catalogo(self) -> list[str]:
        return self._inventario.cargar_productos_catalogo()

    def cargar_estructuras_catalogo(self) -> list[str]:
        return self._inventario.cargar_estructuras_catalogo()

    def ajustar_cantidad_material(self, id_, nueva_cantidad, descripcion: str = "") -> dict | None:
        return self._inventario.ajustar_cantidad_material(id_, nueva_cantidad, descripcion)

    def ajustar_valor_material(self, id_, nuevo_valor, descripcion: str = "") -> dict | None:
        return self._inventario.ajustar_valor_material(id_, nuevo_valor, descripcion)

    def eliminar_ultimo_historial_material(self, id_material, id_entrada) -> dict | None:
        return self._inventario.eliminar_ultimo_historial_material(id_material, id_entrada)

    def eliminar_material(self, id_) -> None:
        self._inventario.eliminar_material(id_)
