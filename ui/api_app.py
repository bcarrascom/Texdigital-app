"""
ui/api_app.py
Clase Api ÚNICA de la ventana principal de la app (menú + las 4 pantallas
a las que se navega desde ahí: ver-cotizacion, ver-op, historial-ops,
nueva-cotizacion) — reemplaza a ui/api_base.py (ApiPantallaBase) y a
ui/pantallas_web.py (que abría una ventana pywebview NUEVA por cada
navegación, destruyendo la anterior).

Ahora hay UNA sola ventana para toda la sesión: "navegar" es
ventana.load_url() al siguiente archivo .html (que sigue existiendo
aparte — recursos/pantallas/ no se tocó), nunca crear/destruir una
ventana. Esto es exactamente el patrón que ya usa ui/panel_produccion.py
entre panel_lista.html/display_op.html (una ventana, un solo js_api,
navegación por location.href/load_url entre archivos HTML separados) —
generalizado acá a las 4 pantallas restantes. El panel de producción
sigue siendo su propia ventana aparte, sin relación con esta clase.

Motivo del cambio (reportado por el usuario): la app se usa maximizada;
con una ventana nueva por pantalla, cada navegación la recreaba en la
posición/tamaño por defecto, obligando a reposicionarla/maximizarla a
mano una y otra vez. Con una sola ventana persistente, el tamaño/posición
que el usuario le dé se mantiene durante toda la sesión.

Verificado contra el código fuente de pywebview 6.2.1 (no asumido):
window.load_url() dispara el mismo pipeline de eventos/inyección
(before_load/inject_pywebview/loaded/pywebviewready) que la carga
inicial — confirmado en platforms/edgechromium.py::on_navigation_completed,
que llama a inject_pywebview(...) en CUALQUIER navegación completada, sin
importar si la disparó Python (load_url) o el propio JS (location.href).
La resolución de un método TD.api.<nombre>(...) es dinámica por llamada
(get_nested_attribute(window._js_api, func_name) en webview/util.py), no
una lista fija armada una sola vez — así que un mismo objeto js_api sirve
sin problema páginas HTML distintas a lo largo de la sesión.

Cada pantalla (recursos/pantallas/*.html) sigue llamando a
TD.api.obtener_contexto() con CERO argumentos al arrancar (ver app.js —
no se tocó, ni hacía falta). Como ya no hay una instancia por ventana con
numero/editar/pendiente/origen inyectados por constructor, esta clase
recuerda "a qué pantalla se navegó y con qué argumentos"
(self._pantalla_actual / self._args_actuales, actualizado en el único
punto de navegación real, _ir()) y arma el contexto de la pantalla ACTUAL
a partir de eso — mismo patrón que ya usa ui.panel_produccion con sus
globals _op_objetivo/_en_detalle ("dejar el dato listo para que la
próxima página lo pida").

Volver() usa una PILA de navegación de verdad (self._historial: cada
_ir() apila de dónde se viene, volver() desapila) — no un destino fijo
por pantalla. Ese destino fijo (una versión anterior de este archivo)
daba resultados incorrectos: ver-op se abre tanto desde el menú como
desde historial-ops.html, y "Volver" tiene que respetar cuál de los dos
fue; peor aún, dentro del propio menú.html una cotización/OP/pendiente
se puede abrir de DOS maneras — desde el mazo de tarjetas que asoma al
pasar el mouse sobre un módulo SIN abrirlo (moduloActivo sigue null,
cuerpo.dataset.fase sigue "menu") o desde el panel ya expandido de ese
módulo (cuerpo.dataset.fase = "panel") — y "Volver" debe reproducir
exactamente ese mismo estado, no uno fijo. menu.html es 100% cliente en
ese toggle (abrirModulo/cerrarModulo nunca llaman a Python), así que la
única forma de que la pila capture bien el estado del menú es que
menu.html avise cuando abre/cierra un panel — ver notificar_panel() más
abajo y las 3 llamadas nuevas agregadas en menu.html (abrirModulo,
abrirModuloDirecto, cerrarModulo).

Cada pantalla sigue teniendo su propia clase de lógica (ApiMenu,
ApiVerCotizacion, ApiVerOp, ApiHistorialOps, ApiCotizacion, cada una en
su propio archivo, sin cambios de fondo) — esta clase las instancia UNA
vez y les delega; lo único que se centraliza acá es la navegación (antes
repartida como self._navegar()/_destino_volver por cada clase).
"""

import json
import sys
import threading
from datetime import datetime
from urllib.parse import urlencode

from core.config import MODULOS_HABILITADOS
from core.repositorio import cargar_preferencias, guardar_preferencia as _guardar_preferencia
from core.rutas import RECURSOS, DOCS as _DOCS
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

RUTA_PANTALLAS = RECURSOS / "pantallas"

_TITULOS = {
    "menu":             "TexDigital",
    "ver-cotizacion":   "Cotización",
    "ver-op":           "Orden de producción",
    "historial-ops":    "Historial de OPs",
    "nueva-cotizacion": "Nueva cotización",
    "ver-despacho":     "Despacho",
    "asignar-despacho": "Asignar dirección",
    "gestionar-direcciones": "Gestionar direcciones",
}

_ARCHIVOS = {
    "menu":             "menu.html",
    "ver-cotizacion":   "ver-cotizacion.html",
    "ver-op":           "ver-op.html",
    "historial-ops":    "historial-ops.html",
    "nueva-cotizacion": "nueva-cotizacion.html",
    "ver-despacho":     "ver-despacho.html",
    "asignar-despacho": "asignar-despacho.html",
    "gestionar-direcciones": "gestionar-direcciones.html",
}

# Ver _cargar()/_recargando.html: paso intermedio para forzar una recarga
# real cuando se navega dos veces seguidas al mismo archivo .html.
_RECARGA = (RUTA_PANTALLAS / "_recargando.html").as_uri()

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

    def __init__(self):
        self._ventana = None
        self._pantalla_actual = "menu"
        self._args_actuales: dict = {}
        # Pila de navegación real — cada _ir() apila de dónde se viene,
        # volver() desapila (ver docstring del módulo). Entradas
        # (pantalla, argumentos), mismo shape que self._pantalla_actual/
        # self._args_actuales.
        self._historial: list[tuple[str, dict]] = []

        self._menu = ApiMenu()
        self._ver_cotizacion = ApiVerCotizacion()
        self._ver_op = ApiVerOp()
        self._historial_ops = ApiHistorialOps()
        self._cotizacion = ApiCotizacion()
        self._ver_despacho = ApiVerDespacho()
        self._asignar_despacho = ApiAsignarDespacho()
        self._gestionar_direcciones = ApiGestionarDirecciones()
        self._inventario = ApiInventario()

    # ── Arranque / navegación ────────────────────────────────────────────────

    def crear_ventana(self):
        """Crea la única ventana de la app, arrancando en el menú. Llamar
        UNA vez, antes de webview.start() (ver main.py) — junto con
        ui.panel_produccion.preparar_panel_oculto()."""
        import webview
        self._ventana = webview.create_window(
            _TITULOS["menu"],
            url=(RUTA_PANTALLAS / _ARCHIVOS["menu"]).as_uri(),
            js_api=self,
            width=1360,
            height=860,
        )
        self._ventana.events.closing += self._al_cerrar_nativo
        return self._ventana

    def _cargar(self, pantalla: str, argumentos: dict) -> None:
        # Si el destino es el MISMO archivo .html que ya está cargado (p.
        # ej. paginar() entre dos cotizaciones: ver-cotizacion.html
        # #numero=9006 -> #numero=9005), la navegación cambia SOLO el
        # fragmento — confirmado en vivo que WebView2 la trata como
        # navegación interna de la misma página, sin recargar el
        # documento: no vuelve a disparar NavigationCompleted, pywebview
        # nunca reinyecta su puente (inject_pywebview) y la pantalla se
        # queda mostrando los datos de ANTES (o directo cuelga esperando
        # un evento "loaded" que no vuelve a llegar). Forzamos una
        # recarga real pasando primero por _recargando.html — dos
        # navegaciones de archivo distinto de verdad, así que WebView2 no
        # tiene forma de "optimizar" ninguna de las dos a un cambio de
        # fragmento.
        recarga_forzada = pantalla == self._pantalla_actual

        self._pantalla_actual = pantalla
        self._args_actuales = argumentos
        self._ventana.set_title(_TITULOS.get(pantalla, "TexDigital"))
        # file:// explícito (no una ruta pelada — pywebview la trataría
        # como "local, levantar el servidor HTTP interno") + argumentos
        # como FRAGMENTO (#clave=valor, no ?clave=valor: confirmado que
        # WebView2 en Windows trata el "?" de una URI file:// como parte
        # del nombre de archivo). Hoy solo menu.html lee el fragmento
        # (#panel=cotizaciones/ops, ver abrirModuloDirecto) — las demás
        # pantallas ya reciben lo que necesitan vía obtener_contexto()
        # (self._args_actuales), así que para ellas el fragmento
        # simplemente no se usa, sin que eso rompa nada.
        base = (RUTA_PANTALLAS / _ARCHIVOS[pantalla]).as_uri()
        url = f"{base}#{urlencode(argumentos)}" if argumentos else base

        def _navegar():
            if recarga_forzada:
                # NO "about:blank": pywebview solo reconoce como URL "de
                # verdad" (externa) lo que empieza con "http://",
                # "https://" o "file://" — cualquier otra cosa la trata
                # como ruta local a servir con su servidor HTTP interno
                # (ver webview/util.py::is_local_url), y con "about:blank"
                # eso significaba buscar un archivo llamado así, no
                # encontrarlo, y mostrar un 404 real por una fracción de
                # segundo antes de la navegación real — justo el bug que
                # el usuario reportó. _recargando.html es un archivo de
                # verdad (file://), sin ese problema.
                self._ventana.load_url(_RECARGA)
                # load_url() limpia (Window.load_url, en la librería)
                # events.loaded ANTES de navegar y lo vuelve a marcar recién
                # cuando esa navegación puntual termina de verdad
                # (on_navigation_completed -> inject_pywebview) — esperarlo
                # es la forma correcta de saber que _recargando.html ya
                # cargó antes de mandar la navegación real, en vez de
                # adivinar un número de milisegundos fijo (que además
                # falló: con un delay fijo corto, la navegación real podía
                # arrancar mientras la intermedia todavía estaba
                # terminando la suya, y pywebview nunca llegaba a
                # inyectarse en la real).
                self._ventana.events.loaded.wait(2)
                self._ventana.load_url(url)
            else:
                self._ventana.load_url(url)

        # Retraso mínimo antes de navegar de verdad. Cada método que llega
        # hasta acá (volver, abrir_cotizacion, abrir_op, ir, etc.) fue
        # invocado desde JS como TD.api.xxx() — pywebview SIEMPRE espera
        # entregar el resultado a un callback registrado en la página
        # ACTUAL (window.pywebview._returnValuesCallbacks), sin importar si
        # el JS que llamó lo usa o no (ver webview/util.py::js_bridge_call).
        # Si load_url() navegaba antes de esa entrega, la entrega apuntaba
        # a la página nueva —que nunca registró ese callback— y pywebview
        # tiraba una JavascriptException ("... is not a function") en un
        # hilo de fondo, en CADA navegación (inofensiva pero ruidosa en la
        # consola). Este retraso le da tiempo de sobra a ese round-trip
        # para terminar sobre la página vieja antes de reemplazarla.
        threading.Timer(0.05, _navegar).start()

    def _ir(self, pantalla: str, **argumentos) -> None:
        """Navega HACIA ADELANTE — apila de dónde se viene, para que
        volver() pueda desapilarlo. Todo lo que "abre" una pantalla nueva
        (ir, abrir_cotizacion, abrir_op, abrir_pendiente, editar_cotizacion,
        eliminar/aprobar_cotizacion) pasa por acá; volver() usa _cargar()
        directo, sin apilar de nuevo (si no, "volver" empujaría una
        entrada nueva en vez de retroceder)."""
        self._historial.append((self._pantalla_actual, self._args_actuales))
        self._cargar(pantalla, argumentos)

    def _al_cerrar_nativo(self):
        """La X nativa de la ventana: en el menú (pantalla raíz) cierra la
        app entera, en cualquier otra pantalla se comporta como "Volver"
        — mismo criterio que tenía VentanaPrincipal antes de retirar
        Tkinter. A diferencia del modelo anterior (una ventana por
        pantalla), acá NUNCA hace falta desenganchar este manejador antes
        de una navegación normal: como load_url() no destruye la
        ventana, "closing" solo se dispara con un cierre nativo de
        verdad."""
        if self._pantalla_actual == "menu":
            from ui.panel_produccion import salir_app
            salir_app()
            return None
        self.volver()
        return False  # cancela el cierre nativo — volver() ya navegó

    # ── Contrato común (ver app.js) ──────────────────────────────────────────

    def obtener_contexto(self) -> dict:
        preferencias = cargar_preferencias()
        hoy = datetime.now()
        ctx = {
            "version":             VERSION,
            "escala_ui":           preferencias.get("escala_ui", 1),
            "hoy_iso":             hoy.strftime("%Y-%m-%d"),
            "fecha":               hoy.strftime("%d-%m-%Y"),
            "modulos_habilitados": MODULOS_HABILITADOS,
        }
        pantalla, args = self._pantalla_actual, self._args_actuales
        if pantalla == "ver-cotizacion":
            ctx.update(self._ver_cotizacion.contexto_extra(args.get("numero")))
        elif pantalla == "ver-op":
            ctx.update(self._ver_op.contexto_extra(args.get("numero")))
        elif pantalla == "historial-ops":
            ctx.update(self._historial_ops.contexto_extra())
        elif pantalla == "nueva-cotizacion":
            ctx.update(self._cotizacion.contexto_extra(args.get("editar"), args.get("pendiente")))
        elif pantalla == "ver-despacho":
            ctx.update(self._ver_despacho.contexto_extra(args.get("numero")))
        elif pantalla == "asignar-despacho":
            ctx.update(self._asignar_despacho.contexto_extra(args.get("numero")))
        elif pantalla == "gestionar-direcciones":
            ctx.update(self._gestionar_direcciones.contexto_extra())
        return ctx

    def guardar_preferencia(self, clave: str, valor) -> bool:
        _guardar_preferencia(clave, valor)
        return True

    def abrir_manual(self) -> None:
        _abrir_manual_usuario()

    def volver(self) -> None:
        pantalla, argumentos = self._historial.pop() if self._historial else ("menu", {})
        self._cargar(pantalla, argumentos)

    def paginar(self, direccion: str) -> None:
        """Flechas ←/→ de ver-cotizacion.html/ver-op.html: pasa a la
        cotización/OP siguiente o anterior (ver *.numero_adyacente) SIN
        apilar en el historial — a diferencia de _ir(), esto reemplaza la
        pantalla actual en el lugar (_cargar() directo, mismo criterio que
        usa volver()): "Volver" desde cualquiera de ellas debe volver
        adonde se entró originalmente (menú, historial-ops, etc.), no ir
        retrocediendo cotización por cotización. direccion: "siguiente" o
        "anterior"."""
        numero_actual = self._args_actuales.get("numero")
        if self._pantalla_actual == "ver-cotizacion":
            numero = self._ver_cotizacion.numero_adyacente(numero_actual, direccion)
            if numero is not None:
                self._cargar("ver-cotizacion", {"numero": numero})
        elif self._pantalla_actual == "ver-op":
            numero = self._ver_op.numero_adyacente(numero_actual, direccion)
            if numero is not None:
                self._cargar("ver-op", {"numero": numero})

    def notificar_panel(self, nombre) -> None:
        """menu.html avisa cuando el usuario abre/cierra un módulo (el
        mazo de tarjetas que asoma al pasar el mouse NO cuenta como
        "abrir" — sigue siendo el menú a secas; solo el panel expandido
        cuenta). Puramente informativo: no navega nada, solo mantiene
        self._args_actuales al día mientras se está en "menu", para que
        la próxima vez que se navegue AFUERA del menú (abrir_cotizacion,
        abrir_op, abrir_pendiente, ir) la pila capture el estado real del
        menú en ese momento — ver docstring del módulo. `nombre` es
        "cotizaciones"/"ops" al abrir un panel, o None/vacío al cerrarlo."""
        if self._pantalla_actual == "menu":
            self._args_actuales = {"panel": nombre} if nombre else {}

    def _aviso(self, texto: str, tipo: str = "aviso", ms: int = 5000) -> None:
        if self._ventana is None:
            return
        script = f"window.TD && TD.aviso({json.dumps(texto)}, {json.dumps(tipo)}, {ms})"
        self._ventana.evaluate_js(script)

    # ── Menú ─────────────────────────────────────────────────────────────────

    def obtener_resumen(self) -> dict:
        return self._menu.obtener_resumen()

    def ir(self, destino: str) -> None:
        if destino == "nueva_cotizacion":
            self._ir("nueva-cotizacion")
        elif destino == "historial_ops":
            self._ir("historial-ops")
        elif destino == "gestionar_direcciones":
            self._ir("gestionar-direcciones")
        elif destino == "panel_produccion":
            if sys.platform == "darwin":
                from ui.panel_produccion import mostrar_panel_mac
                mostrar_panel_mac()
            else:
                from ui.panel_produccion import mostrar_panel
                mostrar_panel()
        else:
            self._aviso(f'Todavía no hay pantalla para "{destino}".', "aviso")

    def abrir_cotizacion(self, numero) -> None:
        self._ir("ver-cotizacion", numero=numero)

    def abrir_pendiente(self, id_) -> None:
        self._ir("nueva-cotizacion", pendiente=id_)

    def abrir_op(self, numero) -> None:
        # Mismo método sirve al botón del menú y al de historial-ops.html
        # — "Volver" desde ver-op sabe adónde regresar solo, gracias a la
        # pila de navegación (ver _ir/volver), sin necesidad de que quien
        # llama distinga de dónde viene.
        self._ir("ver-op", numero=numero)

    def buscar_actualizacion(self) -> None:
        self._aviso("Todavía no está conectado el buscador de actualizaciones.", "info")

    # ── Ver cotización ───────────────────────────────────────────────────────

    def obtener_cotizacion(self, numero) -> dict | None:
        return self._ver_cotizacion.obtener_cotizacion(numero)

    def eliminar_cotizacion(self, numero) -> None:
        self._ver_cotizacion.eliminar_cotizacion(numero)
        self._ir("menu", panel="cotizaciones")

    def editar_cotizacion(self, numero) -> None:
        self._ir("nueva-cotizacion", editar=numero)

    def imprimir_cotizacion(self, numero) -> None:
        self._ver_cotizacion.imprimir_cotizacion(numero)

    def verificar_materiales_cotizacion(self, numero) -> list[dict]:
        return self._ver_cotizacion.verificar_materiales(numero)

    def aprobar_cotizacion(self, numero, ingreso, entrega) -> dict:
        resultado = self._ver_cotizacion.aprobar_cotizacion(numero, ingreso, entrega)
        if resultado.get("ok"):
            self._ir("menu", panel="ops")
        return resultado

    # ── Ver OP ───────────────────────────────────────────────────────────────

    def obtener_op(self, numero) -> dict | None:
        return self._ver_op.obtener_op(numero)

    def imprimir_op(self, numero) -> None:
        self._ver_op.imprimir_op(numero)

    def recotizar_op(self, numero) -> None:
        if self._ver_op.recotizar_op(numero):
            self._ir("menu", panel="cotizaciones")
        else:
            self._aviso("No se pudo recotizar: la OP ya no está activa.", "error")

    def completar_op(self, numero) -> None:
        if self._ver_op.completar_op(numero):
            self._ir("menu", panel="ops")
        else:
            self._aviso("No se pudo completar: la OP ya no está activa.", "error")

    # ── Historial de OPs ─────────────────────────────────────────────────────

    def obtener_historial(self, anio, mes) -> list[dict]:
        return self._historial_ops.obtener_historial(anio, mes)

    def buscar_historial(self, filtros: dict) -> list[dict]:
        return self._historial_ops.buscar_historial(filtros)

    # ── Nueva cotización ─────────────────────────────────────────────────────

    def obtener_catalogos(self) -> dict:
        return self._cotizacion.obtener_catalogos()

    def calcular_producto(self, p: dict) -> dict | None:
        return self._cotizacion.calcular_producto(p)

    def guardar_progreso(self, estado: dict) -> dict:
        return self._cotizacion.guardar_progreso(estado)

    def numero_disponible(self, numero, propio=None) -> bool:
        return self._cotizacion.numero_disponible(numero, propio)

    def verificar_materiales(self, productos: list) -> list[dict]:
        return self._cotizacion.verificar_materiales(productos)

    def guardar_cotizacion(self, estado: dict, abrir: bool = False) -> dict:
        r = self._cotizacion.guardar_cotizacion(estado, abrir)
        if not r.get("error"):
            self._ir("menu", panel="cotizaciones")
        return r

    def guardar_cliente(self, empresa, rut, razon_social) -> bool:
        return self._cotizacion.guardar_cliente(empresa, rut, razon_social)

    def guardar_contacto(self, contacto, email, descuento, condicion) -> None:
        self._cotizacion.guardar_contacto(contacto, email, descuento, condicion)

    # ── Despachos (panel de menu.html — ya no hay pantalla de listado aparte) ─

    def abrir_despacho(self, numero) -> None:
        self._ir("ver-despacho", numero=numero)

    def abrir_asignar_despacho(self, numero) -> None:
        self._ir("asignar-despacho", numero=numero)

    def marcar_despacho_entregado(self, numero) -> bool:
        return self._menu.marcar_despacho_entregado(numero)

    def eliminar_despachos(self, numeros: list) -> int:
        return self._menu.eliminar_despachos(numeros)

    def generar_guia_despacho(self, numero) -> None:
        return self._menu.generar_guia_despacho(numero)

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

    # ── Inventario ──────────────────────────────────────────────────────────
    # La tabla de rollos vive directo en el panel de Inventario de menu.html
    # (ya no es una pantalla aparte) — por eso no hay un "abrir_rollo" acá:
    # saltar a un rollo puntual desde su tarjeta del mazo es 100% del lado
    # del cliente (ver irARollo en menu.html), sin pasar por Python.

    def listar_rollos(self) -> list[dict]:
        return self._inventario.listar_rollos()

    def cargar_textiles_inventario(self) -> list[str]:
        return self._inventario.cargar_textiles()

    def crear_rollo(self, nombre_textil, ancho, metros_restantes, metros_iniciales=None) -> dict:
        return self._inventario.crear_rollo(nombre_textil, ancho, metros_restantes, metros_iniciales)

    def editar_rollo(self, id_, nombre_textil, ancho) -> dict | None:
        return self._inventario.editar_rollo(id_, nombre_textil, ancho)

    def decomisionar_rollo(self, id_) -> bool:
        return self._inventario.decomisionar_rollo(id_)

    def ajustar_restante_rollo(self, id_, nuevo_restante, descripcion: str = "") -> dict | None:
        return self._inventario.ajustar_restante_rollo(id_, nuevo_restante, descripcion)

    def eliminar_ajuste_rollo(self, id_rollo, id_ajuste) -> dict | None:
        return self._inventario.eliminar_ajuste_rollo(id_rollo, id_ajuste)

    def abrir_inventario_nuevo_rollo(self, textil, pendiente_id=None) -> None:
        """Atajo "+ Nuevo rollo" del aviso de materiales insuficientes
        (nueva-cotizacion.html): si veníamos de una cotización en
        progreso, actualiza el registro de "de dónde se viene" con el id
        de pendiente recién guardado (guardarProgreso ya corrió del lado
        JS antes de esta llamada) — así "Volver" desde el panel de
        Inventario reabre ESE borrador puntual, no una pantalla de
        cotización nueva y vacía (ver volverAlCerrarPanel en menu.html,
        que por eso mismo usa TD.api.volver() en vez de solo colapsar el
        panel)."""
        if pendiente_id and self._pantalla_actual == "nueva-cotizacion":
            self._args_actuales = {"pendiente": pendiente_id}
        self._ir("menu", panel="inventario", nuevo_textil=textil)
