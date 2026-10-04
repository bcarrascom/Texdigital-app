"""
core/repositorio_materiales.py
Persistencia del módulo Inventario: materiales no textiles (estructuras —
bases, astas, soportes, etc.), segunda tabla del panel de Inventario en
menu.html, hermana de core/repositorio_inventario.py (rollos de tela).

Distinto de rollos en dos cosas a propósito (pedido de Bruno, 2026-09-14):
  - UN solo registro por material (una "bodega" con cantidad corriente),
    no varios lotes activos/inactivos como un textil puede tener en
    rollos — por eso acá no hay Activos/Decomisionados, ID visible, ni
    switch de estado: "no son rollos sino que stock suelto".
  - Un material tiene DOS precios (ver "Modelo económico" más abajo) y el
    de VENTA es lo que de verdad cobran las cotizaciones — a diferencia de
    rollo.valor, que es puramente informativo/sugerido y nunca entra en el
    cálculo de una cotización (ver core.repositorio_inventario.
    valor_sugerido_textil).

Modelo económico (pedido de Bruno, 2026-10-01 — "reinventar la forma de
cobrar por estructuras"): un material tiene un COSTO y un PRECIO DE VENTA,
y de la diferencia salen las ganancias. Las 9 cifras que muestra la tabla
de materiales de menu.html, agrupadas en tres de tres:

  Gastos   gasto unitario   "gasto_unitario": costo promedio ponderado móvil
                            del stock actual. NUNCA se escribe a mano: se
                            recalcula solo en cada restock (ver
                            ingresar_material) a partir de lo que de verdad
                            se pagó. Pedido explícito de Bruno: "los gastos
                            no se ingresan manualmente, sino que se cuentan
                            al restockear un material".
           gasto este mes   compras del mes calendario en curso (gasto_del_mes).
           gasto total      "gasto_acumulado": todo lo pagado en compras
                            desde siempre.

  Valor    valor unitario   "valor": precio de VENTA por unidad/metro. Es lo
                            único de los tres grupos que se fija a mano, y
                            cambiarlo es un ajuste que QUEDA EN EL HISTORIAL
                            (entrada tipo="precio", ver ajustar_valor —
                            pedido explícito de Bruno).
           valor restante   cantidad × valor (lo que vale el stock en bodega
                            a precio de venta).
           valor vendido    "vendido_acumulado": precio de venta de todo lo
                            que se consumió en OPs, valorizado al precio que
                            el material tenía en CADA OP (no al de hoy).
           ganancias        "ganancia_acumulada" y su versión unitaria/mensual:
                            margen de lo VENDIDO (valor de venta − gasto
                            unitario del momento), no flujo de caja — un mes
                            con un restock grande no las hunde (decisión de
                            Bruno, 2026-10-01).

Los acumulados ("gasto_acumulado"/"vendido_acumulado"/"ganancia_acumulada")
son campos GUARDADOS, no derivados del historial, justamente porque el
historial se vacía cada año nuevo (ver _archivar_si_corresponde): un "total"
derivado del array en memoria dejaría de ser un total el 1 de enero. Las
cifras MENSUALES sí se derivan del historial —"este mes" siempre cae dentro
del año en curso, que es lo que ese archivado garantiza que sigue ahí— y para
poder derivarlas cada entrada guarda los precios del momento (ver
_agregar_historial).

Un JSON por material en Materiales/ (mismo _ruta_base que rollos: Dropbox/
SGTD/Inventario, o DATOS/Inventario si no hay Dropbox instalado) — "id" es
un uuid4hex oculto en la UI (pedido de Bruno: "no hay número o ID textual,
es oculto y solo existe para lógica interna"), lo que se autocompleta y
busca es "nombre".

Historial anual: cada material guarda en "historial" solo las entradas del
año calendario en curso (ver "anio_historial") — al leer un material de un
año anterior, ese array completo se vuelca a un archivo aparte en
Historial/{año}/Materiales/{id}.json y se vacía (ver _archivar_si_corresponde),
mismo espíritu que Decomisionados/AAAA/MM de rollos: evitar que el JSON de
un material viejo con años de movimientos crezca sin límite.
"""

import json
import math
import uuid
from datetime import datetime
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox

TIPOS_VALIDOS = ("unidad", "metro")
TIPOS_CONSUMO_VALIDOS = (
    "fijo_por_producto", "metro_lineal_salto", "metro_lineal_directo", "perimetro", "manual",
)

# Nombre de producto reservado para asociar un material a TODOS los backlight
# (pedido de Bruno, 2026-10-01). "Backlight" no es un producto del catálogo sino
# un TIPO de producto —no tiene entrada en recursos/productos.json, así que no
# había ningún nombre al que asociarle la silicona, que se aplica a todos— por eso
# esta constante se ofrece a mano en la lista de productos asociables (ver
# ui/api_inventario.py::cargar_productos_catalogo) y matchea cualquier producto
# backlight, con caja o sin caja. Está verificado que ningún producto real del
# catálogo se llama así.
PRODUCTO_BACKLIGHT = "Backlight"


def _inventario_habilitado() -> bool:
    """True salvo que core.config.MODULOS_HABILITADOS["inventario"] esté en False
    — mismo helper y mismo criterio que core.repositorio_inventario (rollos).

    Con el módulo apagado, TODO lo que cruza de Inventario a Cotizaciones/OPs
    queda completamente inerte: no se descuenta stock, no se cuentan ventas ni
    ganancias, no se piden consumos manuales al aprobar, la OP no lista
    materiales, y las cotizaciones cobran por el catálogo estático y no por los
    materiales. Un módulo se deshabilita porque todavía no está listo, y en ese
    estado no puede ensuciar datos ni mover precios de los módulos que sí salieron
    (pedido de Bruno, 2026-10-01: "aún cabe la posibilidad de un release anterior
    de emergencia, por lo que DEBE funcionar bien con el módulo inhabilitado").

    Se chequea ACÁ ADENTRO de cada función que cruza de módulo (no solo del lado
    de quien llama, ni solo en la UI) para que quede a prueba de olvidos:
    cualquier caller nuevo hereda la protección gratis."""
    from core import config as _config
    return _config.MODULOS_HABILITADOS.get("inventario", True)


def _hoy_dma() -> str:
    return datetime.now().strftime("%d/%m/%Y")


def _ruta_base() -> Path:
    """Misma carpeta que core.repositorio_inventario._ruta_base (rollos) —
    Materiales/ es hermana de Activos/ dentro de Dropbox/SGTD/Inventario
    (o DATOS/Inventario sin Dropbox instalado). Redefinida acá en vez de
    importada de ahí a propósito: cada repositorio trae su propia
    _ruta_base privada (ver también core/repositorio_ops.py,
    core/repositorio_despachos.py) en vez de acoplarse entre módulos por
    una función de nombre "privado"."""
    dropbox = _detectar_dropbox()
    if dropbox:
        return dropbox / "SGTD" / "Inventario"
    return DATOS / "Inventario"


def carpeta_materiales() -> Path:
    p = _ruta_base() / "Materiales"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _carpeta_historial(anio: int) -> Path:
    p = _ruta_base() / "Historial" / str(anio) / "Materiales"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _escribir_material(m: dict) -> Path:
    destino = carpeta_materiales() / f"{m['id']}.json"
    destino.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


# ══════════════════════════════════════════════════════════════════════════════
# Índice invertido producto/estructura -> materiales (consumo automático al
# aprobar una OP, pedido de Bruno 2026-09-27) — ver docstring de
# materiales_para_producto/_reconstruir_indice_consumo más abajo.
# ══════════════════════════════════════════════════════════════════════════════

def _ruta_indice() -> Path:
    return _ruta_base() / "indice_consumo.json"


def _leer_indice() -> dict:
    ruta = _ruta_indice()
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {"productos": {}, "estructuras": {}}


def _reconstruir_indice_consumo() -> None:
    """Recalcula indice_consumo.json ENTERO a partir de los
    productos_asociados/estructuras_asociadas de TODOS los materiales —
    pedido de Bruno (2026-09-27): "por temas de optimización" quería el
    vínculo guardado del lado del producto/estructura para no escanear
    todos los materiales al aprobar una OP, pero productos.json/
    estructuras_legado.json son catálogos de solo lectura (no hay un
    archivo por producto/estructura como sí hay por rollo/material) — este
    índice aparte da la misma consulta O(1) sin tocarlos.

    Reconstrucción TOTAL (no un parche incremental sobre el índice viejo)
    a propósito: con unas pocas docenas de materiales es barato, y así no
    existe la posibilidad de un índice desincronizado (una asociación que
    se borró en el material pero quedó huérfana en el índice) — se llama
    SIEMPRE que ingresar_material/editar_material tocan esas listas, nunca
    hay que mantenerlo a mano."""
    indice: dict = {"productos": {}, "estructuras": {}}
    for m in listar_materiales():
        for nombre in m.get("productos_asociados", []):
            indice["productos"].setdefault(nombre, []).append(m["id"])
        for nombre in m.get("estructuras_asociadas", []):
            indice["estructuras"].setdefault(nombre, []).append(m["id"])
    _ruta_indice().write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8")


def materiales_para_producto(nombre_producto: str, nombres_estructuras: list[str] | None = None) -> list[dict]:
    """Materiales (con tipo_consumo, no solo el nombre) que aplican a un
    producto — por su propio nombre (catálogo Productos, o el nombre reservado
    PRODUCTO_BACKLIGHT) y/o por cualquiera de sus Estructuras — vía el índice
    invertido, sin escanear todos los materiales. Deduplicado: un material
    asociado tanto al producto como a una de sus estructuras aparece una sola
    vez. Quien llama resuelve el nombre con nombre_producto_para_consumo.

    Con el módulo Inventario apagado devuelve [] (ver _inventario_habilitado):
    es la consulta de la que cuelga TODO lo que materiales le hace a una
    cotización o a una OP, así que apagarla acá deja inerte la cadena completa
    aunque alguien agregue un camino nuevo más adelante."""
    if not _inventario_habilitado():
        return []
    indice = _leer_indice()
    ids: list[str] = []
    for id_ in indice.get("productos", {}).get(nombre_producto, []):
        if id_ not in ids:
            ids.append(id_)
    for nombre_estructura in (nombres_estructuras or []):
        for id_ in indice.get("estructuras", {}).get(nombre_estructura, []):
            if id_ not in ids:
                ids.append(id_)
    materiales = [obtener_material(id_) for id_ in ids]
    return [m for m in materiales if m is not None]


def _archivar_si_corresponde(m: dict) -> dict:
    """Si el "historial" en memoria es de un año calendario que ya pasó,
    lo vuelca completo a Historial/{año}/Materiales/{id}.json y lo vacía
    acá — se llama SIEMPRE al leer (mismo criterio que el backfill de
    "fecha" en core.repositorio_inventario.listar_rollos), así que no hace
    falta ningún cron ni hook de arranque aparte: apenas se abre un
    material de un año vencido, se pone al día solo, una única vez (la
    próxima lectura ya encuentra "anio_historial" == el año actual y no
    vuelve a escribir nada)."""
    anio_actual = datetime.now().year
    anio_hist = m.get("anio_historial") or anio_actual
    if anio_hist >= anio_actual:
        return m
    if m.get("historial"):
        destino = _carpeta_historial(anio_hist) / f"{m['id']}.json"
        destino.write_text(json.dumps(m["historial"], ensure_ascii=False, indent=2), encoding="utf-8")
    m["historial"] = []
    m["anio_historial"] = anio_actual
    _escribir_material(m)
    return m


# Tipos de entrada de historial que ya no se escriben, y en qué se convierten al
# leerlos (pedido de Bruno, 2026-10-01). No hay migración en bloque: cada
# material se normaliza al leerlo y el archivo queda con el tipo nuevo la próxima
# vez que algo lo escriba — así no hay un paso manual que haya que acordarse de
# correr, ni una ventana donde el programa y los datos no se entiendan.
_TIPOS_RENOMBRADOS = {
    # "compra" era el nombre interno del ingreso de stock, pero el panel que lo
    # carga se llama "Restock" desde el principio: ahora los dos coinciden.
    "compra": "restock",
    # "uso" (descuento manual) existía porque aprobar una OP todavía no
    # descontaba nada; desde consumir_para_op eso es automático, y lo que se
    # gasta sin OP (merma, rotura) es un ajuste como cualquier otro — decisión
    # de Bruno: "dejémoslo como ajuste".
    "uso": "ajuste",
}


def _normalizar_tipos_historial(m: dict) -> None:
    for entrada in m.get("historial", []):
        nuevo = _TIPOS_RENOMBRADOS.get(entrada.get("tipo"))
        if nuevo:
            entrada["tipo"] = nuevo


def _leer_material(ruta: Path) -> dict | None:
    try:
        m = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return None
    # Defaults para materiales guardados antes de que existiera algún campo
    # (mismo criterio que _leer_rollo en core.repositorio_inventario).
    m.setdefault("tipo", "unidad")
    m.setdefault("cantidad", 0.0)
    m.setdefault("valor", None)
    m.setdefault("proveedor", "")
    m.setdefault("historial", [])
    m.setdefault("anio_historial", datetime.now().year)
    # tipo_consumo en None = "sin fórmula todavía" (no auto-consume al
    # aprobar una OP, ver consumir_para_op) — mismo criterio que un
    # material guardado antes de que existiera este campo (pedido de
    # Bruno, 2026-09-27): no se le inventa un tipo, queda esperando a que
    # alguien lo edite y elija uno de los 4.
    m.setdefault("tipo_consumo", None)
    m.setdefault("consumo_parametros", {})
    m.setdefault("productos_asociados", [])
    m.setdefault("estructuras_asociadas", [])
    # Modelo económico (ver docstring del módulo). gasto_unitario en None =
    # "nunca se cargó una compra con costo" (no es lo mismo que costo 0):
    # sin él no hay ganancia que calcular, y la columna muestra "—". Los
    # tres acumulados arrancan en 0 para un material viejo — lo que pasó
    # antes de que existieran estos campos no se puede reconstruir (el
    # historial de años anteriores ya está archivado), así que cuentan
    # desde acá en adelante.
    m.setdefault("gasto_unitario", None)
    m.setdefault("gasto_acumulado", 0.0)
    m.setdefault("vendido_acumulado", 0.0)
    m.setdefault("ganancia_acumulada", 0.0)
    _normalizar_tipos_historial(m)
    return _archivar_si_corresponde(m)


def listar_materiales() -> list[dict]:
    """Todos los materiales, alfabético por nombre — no hay activo/
    inactivo que ordenar ni priorizar ("todos son activos", pedido de
    Bruno), así que a diferencia de listar_rollos no hace falta un criterio
    de orden por ID/fecha. Ya NO se siembra nada desde el catálogo estático
    (pedido de Bruno, 2026-09-27: eso era un placeholder temporal) — un
    material solo existe acá si alguien lo cargó a mano."""
    materiales = []
    for archivo in carpeta_materiales().glob("*.json"):
        m = _leer_material(archivo)
        if m is not None:
            materiales.append(m)
    return sorted(materiales, key=lambda m: m.get("nombre", "").strip().lower())


def obtener_material(id_: str) -> dict | None:
    return _leer_material(carpeta_materiales() / f"{id_}.json")


def buscar_material_por_nombre(nombre: str) -> dict | None:
    """Match case-insensitive por nombre completo — usado por
    ingresar_material para decidir si una compra suma a un material que
    ya existe o crea uno nuevo (el nombre es lo único que el usuario tipea
    con autocompletado, no hay ID visible que elegir)."""
    nombre = (nombre or "").strip().lower()
    if not nombre:
        return None
    for m in listar_materiales():
        if m.get("nombre", "").strip().lower() == nombre:
            return m
    return None


def _agregar_historial(
    m: dict, *, tipo: str, anterior: float, nuevo: float, descripcion: str = "",
    proveedor: str | None = None, costo_total: float | None = None, costo_unitario: float | None = None,
    numero_op=None, cliente: str | None = None, fecha: str | None = None,
    gasto_unitario_anterior: float | None = None,
    valor_anterior: float | None = None, valor_nuevo: float | None = None,
    valor_venta: float | None = None, gasto_unitario: float | None = None,
) -> dict:
    """Un solo formato de entrada para todo lo que le pasa a un material —
    mismo espíritu que _agregar_registro de rollos (guarda cantidad de
    ANTES y DESPUÉS, no un delta, para poder revisar y deshacer la más
    reciente sin ambigüedad). proveedor/costo_total/costo_unitario SOLO se
    guardan para tipo="restock" — son el detalle de esa compra puntual, no
    tienen sentido en un "ajuste". numero_op/cliente SOLO para
    tipo="consumo" (descuento automático al aprobar una OP, ver
    consumir_para_op más abajo — pedido de Bruno 2026-09-27, mismo criterio
    que el "consumo" de rollos): así ver-material.html puede mostrar de
    qué OP salió cada descuento, igual que ver-rollo.html ya hace. `fecha`
    (dd/mm/aaaa) es HOY salvo que se pase explícito — el panel "Restock" de
    ver-material.html (pedido de Bruno, 2026-09-29) deja elegirla, para
    poder cargar una compra que en verdad pasó unos días antes.

    Cada entrada guarda además los PRECIOS DEL MOMENTO que hagan falta para
    poder (a) derivar las cifras mensuales del modelo económico sin volver a
    valorizar nada con los precios de hoy, y (b) deshacer la entrada sin
    recalcular (ver eliminar_ultimo_historial) — pedido de Bruno
    (2026-10-01), ver docstring del módulo:
      tipo="restock" → gasto_unitario_anterior (el promedio ponderado que
                       había ANTES de esta compra, para poder volver a él).
      tipo="consumo" → valor_venta y gasto_unitario con los que se valorizó
                       ESA OP, más la ganancia que salió de los dos.
      tipo="precio"  → valor_anterior/valor_nuevo del precio de venta; no
                       mueve stock, así que cantidad_anterior == cantidad_nueva."""
    entrada = {
        "id":                uuid.uuid4().hex,
        "fecha":             fecha or _hoy_dma(),
        # "restock" (ingreso de stock) | "ajuste" (corrección o merma, en + o en -)
        # | "consumo" (automático, al aprobar una OP) | "precio" (cambio del
        # precio de venta, el único que no mueve stock). Ver _TIPOS_RENOMBRADOS
        # para los dos nombres viejos que ya no se escriben.
        "tipo":              tipo,
        "cantidad_anterior": anterior,
        "cantidad_nueva":    nuevo,
        "descripcion":       (descripcion or "").strip(),
    }
    if tipo == "restock":
        entrada["proveedor"]      = (proveedor or "").strip()
        entrada["costo_total"]    = float(costo_total) if costo_total is not None else None
        entrada["costo_unitario"] = float(costo_unitario) if costo_unitario is not None else None
        entrada["gasto_unitario_anterior"] = (
            float(gasto_unitario_anterior) if gasto_unitario_anterior is not None else None
        )
    if tipo == "consumo":
        entrada["numero_op"] = numero_op
        entrada["cliente"]   = (cliente or "").strip()
        entrada["valor_venta"]    = float(valor_venta) if valor_venta is not None else None
        entrada["gasto_unitario"] = float(gasto_unitario) if gasto_unitario is not None else None
        if valor_venta is None:
            entrada["ganancia"] = None
        else:
            consumido = anterior - nuevo
            entrada["ganancia"] = round(
                consumido * (float(valor_venta) - float(gasto_unitario or 0.0)), 2
            )
    if tipo == "precio":
        entrada["valor_anterior"] = float(valor_anterior) if valor_anterior is not None else None
        entrada["valor_nuevo"]    = float(valor_nuevo) if valor_nuevo is not None else None
    m.setdefault("historial", []).append(entrada)
    return entrada


def _promedio_ponderado(
    gasto_unitario: float | None, cantidad_previa: float,
    costo_total: float, cantidad_comprada: float,
) -> float | None:
    """Costo promedio móvil después de una compra (ver ingresar_material):
    (valor del stock que ya había + lo que se pagó ahora) / unidades totales.

    El stock previo solo "vale" algo si hay stock Y ya había un promedio con
    el que valorizarlo; si no, el promedio nuevo es directamente el costo de
    esta compra. Un stock en NEGATIVO (consumos de OPs que se pasaron de lo
    que había, que acá no se bloquean — ver consumir_para_op) cuenta como 0:
    si no, restaría valor y daría un promedio más bajo que cualquier precio
    realmente pagado. Devuelve None solo si no hay con qué calcular nada."""
    cantidad_comprada = float(cantidad_comprada or 0.0)
    base = max(float(cantidad_previa or 0.0), 0.0)
    if gasto_unitario is None:
        base = 0.0
    total_unidades = base + cantidad_comprada
    if total_unidades <= 0:
        return gasto_unitario
    valor_previo = (gasto_unitario or 0.0) * base
    return round((valor_previo + float(costo_total)) / total_unidades, 4)


def ingresar_material(
    nombre: str, cantidad: float, tipo: str = "unidad", proveedor: str = "",
    costo_total: float | None = None, costo_unitario: float | None = None,
    tipo_consumo: str | None = None, consumo_parametros: dict | None = None,
    productos_asociados: list[str] | None = None, estructuras_asociadas: list[str] | None = None,
    fecha: str | None = None, valor: float | None = None,
) -> dict:
    """La acción única del diálogo "+" de materiales (pedido de Bruno:
    elegir el material con autocompletado, cantidad, proveedor opcional,
    costo total O unitario) — sirve tanto para crear un material que no
    existía todavía como para sumar stock a uno que ya existe, buscando
    por nombre (buscar_material_por_nombre): el usuario no elige entre
    "nuevo" o "existente" a mano, simplemente tipea el nombre.

    `tipo` (metro/unidad) y `tipo_consumo`/`consumo_parametros`/
    `productos_asociados`/`estructuras_asociadas` SOLO se usan si el
    material es nuevo — uno que ya existe conserva lo que tenía (esos
    campos viven en editar_material, a propósito: pedido de Bruno, "al
    editar un material, se puede cambiar el tipo de consumo").

    `costo_total`/`costo_unitario` son opcionales y se autocompletan entre
    sí (si viene uno y no el otro, y hay cantidad > 0, se deriva el que
    falta) — quedan los dos guardados en la entrada de historial para
    poder calcular gasto_del_mes más tarde sin volver a derivar nada.

    `fecha` (dd/mm/aaaa) es HOY salvo que se pase explícito — ver
    docstring de _agregar_historial.

    `valor` (precio de VENTA) solo se aplica si el material es NUEVO, igual que
    `tipo` y las asociaciones: desde 2026-10-01 el formulario de alta lo pide
    obligatorio (pedido de Bruno), así que un material nace con su precio puesto
    y queda registrado en el historial como cualquier cambio de precio (entrada
    tipo="precio", ver _fijar_valor_venta). En un material que YA EXISTE no se
    toca: un restock no es el lugar para cambiar el precio de venta, para eso
    está el panel de ajuste.

    Lo que NO se hace nunca es DERIVAR el precio de venta del costo. Antes se
    sembraba con costo_unitario como "mejor estimación disponible", pero eso sería
    cobrar exactamente lo que costó (ganancia 0) y ensuciaría las ganancias con un
    precio que nadie decidió: ponerlo es una decisión comercial explícita.

    Lo que SÍ actualiza cada compra es el lado del costo (pedido de Bruno:
    "los gastos no se ingresan manualmente, sino que se cuentan al
    restockear"):
      - "gasto_unitario" ← promedio ponderado móvil: (lo que vale el stock
        que ya había + lo que se pagó por esta compra) / cantidad total. Si
        no había stock (o quedó en negativo por consumos), el promedio ES el
        costo de esta compra. Una compra SIN costo cargado no mueve el
        promedio: no se sabe qué se pagó, y suponer 0 lo hundiría.
      - "gasto_acumulado" += costo_total."""
    nombre = (nombre or "").strip()
    cantidad = float(cantidad)
    if costo_total is not None and costo_unitario is None and cantidad:
        costo_unitario = costo_total / cantidad
    elif costo_unitario is not None and costo_total is None:
        costo_total = costo_unitario * cantidad

    m = buscar_material_por_nombre(nombre)
    es_nuevo = m is None
    if es_nuevo:
        m = {
            "id":                    uuid.uuid4().hex,
            "nombre":                nombre,
            "tipo":                  tipo if tipo in TIPOS_VALIDOS else "unidad",
            "cantidad":              0.0,
            "valor":                 None,
            "proveedor":             "",
            "anio_historial":        datetime.now().year,
            "historial":             [],
            "tipo_consumo":          tipo_consumo if tipo_consumo in TIPOS_CONSUMO_VALIDOS else None,
            "consumo_parametros":    dict(consumo_parametros or {}),
            "productos_asociados":   list(productos_asociados or []),
            "estructuras_asociadas": list(estructuras_asociadas or []),
            "gasto_unitario":        None,
            "gasto_acumulado":       0.0,
            "vendido_acumulado":     0.0,
            "ganancia_acumulada":    0.0,
        }

    proveedor = (proveedor or "").strip()
    if proveedor:
        m["proveedor"] = proveedor

    anterior = m.get("cantidad", 0.0)
    nuevo = round(anterior + cantidad, 3)
    gasto_unitario_anterior = m.get("gasto_unitario")
    if costo_total is not None:
        m["gasto_unitario"] = _promedio_ponderado(
            gasto_unitario_anterior, anterior, costo_total, cantidad,
        )
        m["gasto_acumulado"] = round(m.get("gasto_acumulado", 0.0) + float(costo_total), 2)
    m["cantidad"] = nuevo
    _agregar_historial(
        m, tipo="restock", anterior=anterior, nuevo=nuevo,
        proveedor=proveedor, costo_total=costo_total, costo_unitario=costo_unitario,
        gasto_unitario_anterior=gasto_unitario_anterior, fecha=fecha,
    )
    # El precio de venta se registra DESPUÉS del restock: así el historial se lee
    # en el orden en que pasaron las cosas (entró el stock, se le puso precio) y
    # la entrada de precio guarda la cantidad real, no el 0 de antes del ingreso.
    if es_nuevo and valor is not None:
        _fijar_valor_venta(m, float(valor), "precio de venta inicial")
    _escribir_material(m)
    if es_nuevo and (m["productos_asociados"] or m["estructuras_asociadas"]):
        _reconstruir_indice_consumo()
    return m


def _fijar_valor_venta(m: dict, nuevo_valor: float | None, descripcion: str = "") -> bool:
    """Cambia el precio de venta de `m` dejando una entrada tipo="precio" en
    el historial — punto único por donde pasa cualquier cambio de precio
    (editar_material y ajustar_valor), para que no exista una segunda forma
    de cambiarlo sin registro. No escribe el archivo (eso lo hace quien
    llama, que normalmente toca más campos en la misma pasada).

    Si el precio nuevo es IGUAL al que ya había no registra nada y devuelve
    False: guardar el formulario sin tocar el precio no es un ajuste de
    precio, y llenar el historial de entradas que no cambian nada haría
    ilegible justo lo que se quiere poder auditar."""
    anterior = m.get("valor")
    if nuevo_valor is None and anterior is None:
        return False
    if anterior is not None and nuevo_valor is not None and float(anterior) == float(nuevo_valor):
        return False
    m["valor"] = float(nuevo_valor) if nuevo_valor is not None else None
    cantidad = m.get("cantidad", 0.0)
    _agregar_historial(
        m, tipo="precio", anterior=cantidad, nuevo=cantidad, descripcion=descripcion,
        valor_anterior=anterior, valor_nuevo=nuevo_valor,
    )
    return True


def ajustar_valor(id_: str, nuevo_valor: float | None, descripcion: str = "") -> dict | None:
    """Ajuste del PRECIO DE VENTA de un material (panel propio de
    ver-material.html, hermano del ajuste de cantidad — pedido de Bruno,
    2026-10-01: "el cambio de precio de venta sí es manual, se hace en
    forma de ajuste Y SE DEBE REGISTRAR EN EL HISTORIAL"). No toca el
    stock ni los acumulados: lo ya vendido quedó valorizado al precio que
    regía en cada OP (ver consumir_para_op), así que un precio nuevo solo
    rige de acá en adelante. Devuelve el material actualizado, o None si no
    existe."""
    m = obtener_material(id_)
    if m is None:
        return None
    _fijar_valor_venta(m, nuevo_valor, descripcion)
    _escribir_material(m)
    return m


def editar_material(
    id_: str, nombre: str, tipo: str, valor: float | None = None, proveedor: str = "",
    tipo_consumo: str | None = None, consumo_parametros: dict | None = None,
    productos_asociados: list[str] | None = None, estructuras_asociadas: list[str] | None = None,
) -> dict | None:
    """nombre/tipo/valor/proveedor/tipo_consumo/consumo_parametros/
    productos_asociados/estructuras_asociadas son editables después de
    creado — cantidad se maneja aparte (ver ajustar_cantidad), para que no se pise sin dejar rastro por acá (mismo
    criterio que editar_rollo). El switch metro/unidad ("tipo") y el de
    consumo viven acá a propósito: pedido de Bruno, no en el alta.

    productos_asociados/estructuras_asociadas se REEMPLAZAN enteros (no se
    "mezclan" con lo que había) — mismo criterio que el resto de los
    campos de este formulario; siempre reconstruye el índice invertido
    (ver _reconstruir_indice_consumo) por si cambiaron, es barato y así
    nunca queda desincronizado.

    `valor` es el precio de VENTA: si cambia por acá, queda igual de
    registrado en el historial que si se hubiera cambiado desde el panel de
    ajuste (entrada tipo="precio", ver ajustar_valor) — pedido explícito de
    Bruno (2026-10-01): un cambio de precio de venta NUNCA pasa sin dejar
    rastro, por qué formulario entró no cambia eso. El costo
    ("gasto_unitario") no se puede tocar acá a propósito: sale de los
    restocks, no de un formulario."""
    m = obtener_material(id_)
    if m is None:
        return None
    m["nombre"] = (nombre or "").strip()
    m["tipo"] = tipo if tipo in TIPOS_VALIDOS else m.get("tipo", "unidad")
    _fijar_valor_venta(m, float(valor) if valor is not None else None)
    m["proveedor"] = (proveedor or "").strip()
    m["tipo_consumo"] = tipo_consumo if tipo_consumo in TIPOS_CONSUMO_VALIDOS else None
    m["consumo_parametros"] = dict(consumo_parametros or {})
    m["productos_asociados"] = list(productos_asociados or [])
    m["estructuras_asociadas"] = list(estructuras_asociadas or [])
    _escribir_material(m)
    _reconstruir_indice_consumo()
    return m


def ajustar_cantidad(id_: str, nueva_cantidad: float, descripcion: str = "") -> dict | None:
    """Corrección manual del stock — el ÚNICO movimiento de stock que se carga
    a mano (mismo criterio que ajustar_restante de rollos). Queda en 'historial'
    SIEMPRE, con tipo="ajuste".

    Recibe la cantidad que CORRESPONDE, no un delta: el delta se deriva de la
    diferencia con lo que había, y la entrada guarda las dos cantidades, así que
    el movimiento queda igual de explícito por las dos vías. La UI deja escribir
    cualquiera de las dos y calcula la otra (pedido de Bruno, 2026-10-01:
    "restar o sumar metros a la par que solo ingresar el número nuevo") — pero
    acá llega siempre resuelta a cantidad final, para que no existan dos formas
    de guardar el mismo movimiento.

    Cubre también lo que antes era tipo="uso" (merma, rotura, uso interno sin
    OP): ese tipo ya no se escribe, ver _TIPOS_RENOMBRADOS."""
    m = obtener_material(id_)
    if m is None:
        return None
    anterior = m.get("cantidad", 0.0)
    nueva_cantidad = round(float(nueva_cantidad), 3)
    m["cantidad"] = nueva_cantidad
    _agregar_historial(m, tipo="ajuste", anterior=anterior, nuevo=nueva_cantidad, descripcion=descripcion)
    _escribir_material(m)
    return m


def eliminar_ultimo_historial(id_material: str, id_entrada: str) -> dict | None:
    """Deshace una entrada cargada por error — solo tiene sentido sobre la
    MÁS RECIENTE (historial[-1]), mismo motivo que eliminar_ajuste de
    rollos: cada entrada nueva parte del restante que dejó la anterior, así
    que deshacer una del medio dejaría el resto apuntando a un valor que
    ya no es real. Si `id_entrada` no es la más reciente, no hace nada y
    devuelve None.

    Deshace TAMBIÉN lo que esa entrada le hizo al modelo económico (ver
    docstring del módulo), no solo la cantidad: si no, borrar una compra
    cargada por error dejaría el costo promedio y el gasto total contando una
    plata que nunca se pagó. Cada entrada guarda los precios del momento justo
    para poder volver atrás exacto (no recalculando sobre los de hoy):
      "restock" → vuelve al gasto_unitario_anterior y descuenta el costo_total
                  del gasto_acumulado.
      "consumo" → descuenta de vendido_acumulado/ganancia_acumulada lo que esa
                  OP había sumado.
      "precio"  → vuelve al valor_anterior.
    Una entrada vieja (guardada antes de que existieran estos campos) no trae
    los precios del momento: ahí se deshace la cantidad nomás, que es
    exactamente lo que hacía esta función antes."""
    m = obtener_material(id_material)
    if m is None:
        return None
    historial = m.get("historial", [])
    if not historial or historial[-1].get("id") != id_entrada:
        return None
    objetivo = historial.pop()
    m["cantidad"] = objetivo.get("cantidad_anterior", m.get("cantidad", 0.0))

    tipo = objetivo.get("tipo")
    if tipo == "restock" and objetivo.get("costo_total") is not None:
        m["gasto_acumulado"] = round(
            m.get("gasto_acumulado", 0.0) - float(objetivo["costo_total"]), 2
        )
        if "gasto_unitario_anterior" in objetivo:
            m["gasto_unitario"] = objetivo["gasto_unitario_anterior"]
    elif tipo == "consumo" and objetivo.get("valor_venta") is not None:
        consumido = objetivo.get("cantidad_anterior", 0.0) - objetivo.get("cantidad_nueva", 0.0)
        m["vendido_acumulado"] = round(
            m.get("vendido_acumulado", 0.0) - consumido * float(objetivo["valor_venta"]), 2
        )
        m["ganancia_acumulada"] = round(
            m.get("ganancia_acumulada", 0.0) - float(objetivo.get("ganancia") or 0.0), 2
        )
    elif tipo == "precio":
        m["valor"] = objetivo.get("valor_anterior")

    _escribir_material(m)
    return m


def eliminar_material(id_: str) -> bool:
    """Borra un material para siempre — a diferencia de decomisionar_rollo
    (rollos), acá no hay archivo aparte para preservar: un material es "un
    registro, stock suelto" (ver docstring del módulo), sin lotes que
    valga la pena conservar por separado. La confirmación (tipear el
    nombre exacto, mismo criterio que borrar un repositorio en GitHub)
    vive en ver-material.html — acá, si llega la llamada, se borra sin
    preguntar de nuevo (pedido de Bruno, 2026-10-01). Se reconstruye el
    índice de consumo después, por si el material borrado tenía productos/
    estructuras asociadas (ver _reconstruir_indice_consumo: más barato
    reconstruir entero que buscar y sacar solo sus entradas). Devuelve
    True si encontró y borró algo."""
    ruta = carpeta_materiales() / f"{id_}.json"
    if not ruta.exists():
        return False
    ruta.unlink()
    _reconstruir_indice_consumo()
    return True


def es_backlight(producto_interno: dict) -> bool:
    """Si este producto interno es backlight. Se mira por la CLAVE "tela" (los
    estándar traen "textil") — mismo criterio estructural que usan
    core.repositorio_inventario._metros_lineales y core.precios.costo_producto,
    para no depender de que alguien haya escrito un nombre en algún campo."""
    return "tela" in producto_interno


def nombre_producto_para_consumo(producto_interno: dict) -> str:
    """El nombre con el que este producto busca materiales asociados (ver
    materiales_para_producto). Un backlight responde al nombre reservado
    PRODUCTO_BACKLIGHT, porque no tiene producto de catálogo propio; el resto, al
    nombre de producto que eligió el usuario."""
    if es_backlight(producto_interno):
        return PRODUCTO_BACKLIGHT
    return producto_interno.get("producto", "") or ""


def medida_unitaria(producto_interno: dict) -> float:
    """La medida que gasta material en UNA pieza del producto: su ALTO
    físico, en metros (decisión de Bruno, 2026-10-01).

    Antes acá se usaba el ML de rollo que consume el producto
    (core.repositorio_inventario._metros_lineales con con_margen=False), y
    estaba mal por dos motivos:
      - Era el ML de TODA la línea (cantidad / UxA × alto), no el de una
        pieza, así que las fórmulas por metro lineal —que multiplican por
        `cantidad_producto`— contaban la cantidad DOS VECES.
      - Aun arreglando eso, el ML de rollo depende de cuántas piezas entran
        a lo ancho de la tela: la misma pieza en dos telas de distinto ancho
        daría consumos distintos de astas o de adhesivo, que es absurdo —
        un asta se gasta por lo que mide la pieza terminada, no por cómo se
        acomodó en el rollo.

    El margen de tensión de la tela tampoco entra (nunca entró): es tela en
    la impresora, no se le gasta de más a un adhesivo/ojal/remache."""
    return _dimension(producto_interno, "alto")


def _dimension(producto_interno: dict, clave: str) -> float:
    try:
        return max(float(producto_interno.get(clave, 0.0) or 0.0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def perimetro_unitario(producto_interno: dict) -> float:
    """El contorno de UNA pieza, en metros: 2 × (ancho + alto).

    Para los materiales que se aplican por el BORDE de la pieza y no por su
    largo: la silicona de un backlight se pasa por los 4 lados del rectángulo,
    así que lo que gasta no es el alto ni el área, es el perímetro (pedido de
    Bruno, 2026-10-01 — ninguna de las fórmulas anteriores podía expresarlo).
    Si falta una de las dos medidas devuelve 0: media pieza no tiene contorno."""
    ancho = _dimension(producto_interno, "ancho")
    alto = _dimension(producto_interno, "alto")
    if ancho <= 0 or alto <= 0:
        return 0.0
    return 2 * (ancho + alto)


def calcular_consumo(material: dict, producto_interno: dict) -> float:
    """Cuánto gasta de `material` una línea de producto, según su `tipo_consumo` y
    `consumo_parametros` (ver docstring del módulo) — pedido de Bruno
    (2026-09-27). Recibe el producto interno completo y saca de ahí la geometría
    que cada fórmula necesita, en lugar de una medida suelta: así agregar una
    fórmula que mire otra dimensión no cambia la firma ni obliga a revisar a
    quién la llama.

    Todas las fórmulas son POR PIEZA y se multiplican por la cantidad al final:

      "fijo_por_producto"    — n × cantidad (el tamaño no importa).
      "metro_lineal_salto"   — techo(alto / paso) × n × cantidad: el material se
                                gasta en bloques enteros de `paso`, y una pieza
                                que no completa un bloque igual lo gasta entero.
      "metro_lineal_directo" — alto × cantidad, sin tramos.
      "perimetro"            — 2 × (ancho + alto) × n × cantidad: para lo que se
                                aplica por el borde de la pieza (la silicona de un
                                backlight va por los 4 lados). `n` son las
                                pasadas; si no se carga, 1.
      "manual" o sin tipo_consumo — 0 acá (el manual se resuelve aparte, ver
                                consumir_para_op; sin tipo_consumo el material
                                simplemente no auto-consume)."""
    tipo_consumo = material.get("tipo_consumo")
    parametros = material.get("consumo_parametros") or {}
    try:
        cantidad = int(producto_interno.get("cantidad", 0) or 0)
    except (TypeError, ValueError):
        cantidad = 0

    if tipo_consumo == "fijo_por_producto":
        return float(parametros.get("n", 0.0)) * cantidad

    if tipo_consumo == "metro_lineal_salto":
        paso = float(parametros.get("paso", 0.0))
        n = float(parametros.get("n", 0.0))
        alto = medida_unitaria(producto_interno)
        if paso <= 0 or alto <= 0:
            return 0.0
        return math.ceil(alto / paso) * n * cantidad

    if tipo_consumo == "metro_lineal_directo":
        return medida_unitaria(producto_interno) * cantidad

    if tipo_consumo == "perimetro":
        # n por default 1: el caso normal es una sola pasada por el contorno, y
        # pedirle al usuario que escriba "1" para eso sería un trámite.
        n = parametros.get("n")
        n = 1.0 if n in (None, "", 0) else float(n)
        return perimetro_unitario(producto_interno) * n * cantidad

    return 0.0


def consumir_para_op(
    productos_internos: list[dict], numero_op, referencia: str = "",
    consumos_manuales: dict[str, float] | None = None,
) -> dict[str, float]:
    """Descuenta de los materiales lo que gasta `productos_internos` — se
    llama SOLO al aprobar una cotización (ui/api_ver_cotizacion.py::
    aprobar_cotizacion), junto con el consumir_para_op de rollos (pedido
    de Bruno, 2026-09-27). Para cada producto, resuelve qué materiales le
    aplican por su nombre y sus Estructuras (ver materiales_para_producto)
    y les calcula el consumo (calcular_consumo, o `consumos_manuales[id]`
    si el material es tipo_consumo="manual" — un monto único por OP, no
    por producto, ver docstring del módulo).

    Igual que ya se decidió para rollos (2026-09-16): un mismo material
    puede tocarle a MÁS DE UN producto de la misma OP — el historial
    queda con UN SOLO registro tipo="consumo" por material, sumando lo
    que le tocó a cada producto, no uno por producto.

    A diferencia de rollos, NO bloquea nada si el stock queda negativo
    (pedido de Bruno: la mecánica de stock de materiales es más nueva,
    no se pidió replicar ese bloqueo acá) — simplemente descuenta.
    materiales sin tipo_consumo (o "manual" sin monto en
    `consumos_manuales`) no se tocan.

    Cada descuento queda valorizado al PRECIO DE VENTA y al COSTO que el
    material tiene en ESTE momento (ver _agregar_historial), y de ahí se
    suman "vendido_acumulado"/"ganancia_acumulada" (ver docstring del
    módulo): lo vendido en una OP vieja no se revaloriza nunca si después
    cambia el precio.

    Con el módulo Inventario apagado no toca NADA y devuelve {} (ver
    _inventario_habilitado): ni stock, ni historial, ni los acumulados de vendido
    y ganancia. Se chequea acá además de en materiales_para_producto porque esta
    es la función que ESCRIBE: que quede explícito que con el módulo apagado no
    hay ningún dato que se ensucie, incluidos los consumos manuales que llegan
    por parámetro.

    Devuelve {id_material: metros/unidades descontados} — informativo,
    quien llama no está obligado a usarlo."""
    if not _inventario_habilitado():
        return {}
    consumos_manuales = consumos_manuales or {}
    descripcion = f"OP {numero_op}" + (f" · {referencia}" if referencia else "")

    acumulado: dict[str, float] = {}
    for producto in productos_internos:
        # Un backlight responde al nombre reservado "Backlight" (ver
        # nombre_producto_para_consumo): no tiene producto de catálogo propio ni
        # lista de Estructuras, así que ese nombre es su única vía de asociación
        # — y alcanza para lo que se gasta en TODOS los backlight, con caja o sin
        # caja, que es el caso de la silicona.
        nombre_producto = nombre_producto_para_consumo(producto)
        nombres_estructuras = list(producto.get("estructuras", []) or [])

        for material in materiales_para_producto(nombre_producto, nombres_estructuras):
            tipo_consumo = material.get("tipo_consumo")
            if tipo_consumo == "manual":
                if material["id"] not in consumos_manuales:
                    continue
                consumo = float(consumos_manuales[material["id"]])
                # Un monto único por OP (no por producto) — ya se contó
                # la primera vez que apareció este material en la OP, los
                # productos siguientes que también lo disparan no lo
                # vuelven a sumar.
                if material["id"] in acumulado:
                    continue
            else:
                consumo = calcular_consumo(material, producto)
                if consumo <= 0:
                    continue
            acumulado[material["id"]] = acumulado.get(material["id"], 0.0) + consumo

    for id_material, consumo in acumulado.items():
        m = obtener_material(id_material)
        if m is None:
            continue
        anterior = m.get("cantidad", 0.0)
        nuevo = round(anterior - consumo, 3)
        m["cantidad"] = nuevo
        valor_venta = m.get("valor")
        entrada = _agregar_historial(
            m, tipo="consumo", anterior=anterior, nuevo=nuevo, descripcion=descripcion,
            numero_op=numero_op, cliente=referencia,
            valor_venta=valor_venta, gasto_unitario=m.get("gasto_unitario"),
        )
        if valor_venta is not None:
            m["vendido_acumulado"] = round(
                m.get("vendido_acumulado", 0.0) + consumo * float(valor_venta), 2
            )
            m["ganancia_acumulada"] = round(
                m.get("ganancia_acumulada", 0.0) + float(entrada.get("ganancia") or 0.0), 2
            )
        _escribir_material(m)

    return acumulado


def gasto_del_mes(m: dict) -> float:
    """Suma de lo gastado en compras de este material durante el mes
    calendario en curso (pedido de Bruno: reemplaza la columna "Origen" de
    rollos en la tabla de materiales) — alcanza con mirar 'historial' (el
    array en memoria del material, nunca el archivado): "este mes" siempre
    cae dentro del año en curso, que es justo lo que _archivar_si_corresponde
    garantiza que sigue ahí. Si una compra vino solo con costo_unitario
    (no costo_total), se deriva desde la diferencia de cantidad de esa
    misma entrada."""
    total = 0.0
    for entrada in m.get("historial", []):
        if entrada.get("tipo") != "restock" or not _es_del_mes_en_curso(entrada):
            continue
        costo = entrada.get("costo_total")
        if costo is None:
            costo_unitario = entrada.get("costo_unitario")
            if costo_unitario is not None:
                costo = costo_unitario * (entrada.get("cantidad_nueva", 0.0) - entrada.get("cantidad_anterior", 0.0))
        total += costo or 0.0
    return round(total, 2)


def consumo_estimado(productos_internos: list[dict]) -> dict[str, dict]:
    """{nombre_material: {"consumo": x, "tipo": "metro"|"unidad"}} que gastaría
    esta lista de productos — la misma cuenta que consumir_para_op pero SIN tocar
    stock ni escribir historial.

    Es para MOSTRAR: el documento de la OP lista los materiales que el trabajo va
    a gastar (pedido de Bruno, 2026-10-01), igual que ya lista textiles y
    materiales de caja. Hasta ahora los materiales de Inventario no aparecían en
    la OP para ningún tipo de producto, ni backlight ni estándar.

    Los materiales "manual" y los que no tienen fórmula quedan afuera: su consumo
    no se puede calcular desde la geometría, así que no hay cifra que mostrar.

    Con el módulo Inventario apagado devuelve {} (ver _inventario_habilitado), y
    la OP no imprime el bloque: con el módulo apagado no se descuenta nada, así
    que listar materiales en la hoja prometería un gasto que nadie va a registrar."""
    if not _inventario_habilitado():
        return {}
    total: dict[str, dict] = {}
    for producto in productos_internos:
        nombre_producto = nombre_producto_para_consumo(producto)
        nombres_estructuras = list(producto.get("estructuras", []) or [])
        for material in materiales_para_producto(nombre_producto, nombres_estructuras):
            if material.get("tipo_consumo") in (None, "manual"):
                continue
            consumo = calcular_consumo(material, producto)
            if consumo <= 0:
                continue
            slot = total.setdefault(material["nombre"],
                                    {"consumo": 0.0, "tipo": material.get("tipo", "unidad")})
            slot["consumo"] = round(slot["consumo"] + consumo, 3)
    return total


def _cobrable(material: dict, producto_interno: dict) -> tuple[float, bool]:
    """(monto a cobrar por este material en esta línea de producto, se_puede).

    se_puede=False significa "no hay con qué cobrarlo acá", y pasa en tres
    casos — en los tres, quien llama NO debe cobrar $0: debe caer al valor
    de catálogo de la estructura (ver cobro_materiales_producto):
      - sin precio de venta cargado (valor=None): nadie decidió cuánto vale.
      - tipo_consumo None o "manual": no hay fórmula que se pueda resolver al
        cotizar (el "manual" se resuelve recién al aprobar la OP, a mano).
      - la fórmula da 0 o menos (ej. metro_lineal_salto con paso=0, o un
        producto sin alto): cobrar $0 por una estructura que el catálogo
        cobraba sería una rebaja silenciosa, no un precio."""
    if material.get("valor") is None:
        return 0.0, False
    if material.get("tipo_consumo") in (None, "manual"):
        return 0.0, False
    consumo = calcular_consumo(material, producto_interno)
    if consumo <= 0:
        return 0.0, False
    return round(consumo * float(material["valor"]), 2), True


def cobro_materiales_producto(producto_interno: dict) -> dict:
    """Cuánto cobra una línea de producto por los materiales que de verdad
    gasta — la nueva forma de cobrar estructuras (pedido de Bruno,
    2026-10-01, en reemplazo del valorUNIT/valorML plano del catálogo).

    Devuelve:
      "estructuras"         {nombre_estructura: monto} — SOLO las estructuras
                            cuyos materiales se pudieron cobrar enteros. Ese
                            monto REEMPLAZA el del catálogo estático (decisión
                            de Bruno: "reemplaza").
      "materiales_producto" {nombre_material: monto} de los materiales
                            asociados al PRODUCTO y no a una de sus
                            estructuras — también se cobran (decisión de
                            Bruno): si se gasta y tiene precio de venta, se
                            cobra. Un material asociado al producto Y a una
                            de sus estructuras se cobra una sola vez, por la
                            estructura.
      "incompletas"         estructuras que SÍ tienen materiales asociados
                            pero no se pudieron cobrar enteros (ver
                            _cobrable) — siguen cobrando por catálogo, y acá
                            quedan nombradas para poder avisarlo en la UI.
      "detalle"             {nombre_material: {consumo, valor, monto, tipo, origen}}
                            de todo lo que se cobró, para el desglose — "tipo" es
                            metro/unidad, para poder escribir la unidad al lado
                            del consumo.

    Una estructura se cobra entera o no se cobra: si uno solo de sus
    materiales no es cobrable, la estructura completa vuelve al catálogo. Un
    cobro parcial sería peor que cualquiera de las dos opciones — cobraría
    una fracción arbitraria de lo que corresponde, sin que nadie se entere.

    Con el módulo Inventario apagado (core.config.MODULOS_HABILITADOS)
    devuelve todo vacío: los materiales no afectan el precio de ninguna
    cotización mientras el módulo no esté habilitado (pedido explícito de
    Bruno, mismo criterio que estructuras_legado_valores_efectivos).

    La cantidad que se cobra es la cantidad REAL de piezas, no la "cantidad
    efectiva" que duplica terminaciones en Tiro y retiro: imprimir las dos
    caras no gasta dos astas. Es la misma cantidad con la que se descuenta el
    stock al aprobar (ver consumir_para_op), y eso es a propósito — lo que se
    cobra y lo que se gasta tienen que ser la misma cuenta."""
    vacio = {"estructuras": {}, "materiales_producto": {}, "incompletas": [], "detalle": {}}
    if not _inventario_habilitado():
        return vacio

    nombres_estructuras = list(producto_interno.get("estructuras", []) or [])
    nombre_producto = nombre_producto_para_consumo(producto_interno)
    if not nombres_estructuras and not nombre_producto:
        return vacio

    indice = _leer_indice()
    por_estructura = indice.get("estructuras", {})
    por_producto = indice.get("productos", {})

    estructuras: dict[str, float] = {}
    incompletas: list[str] = []
    detalle: dict[str, dict] = {}

    for nombre_estructura in nombres_estructuras:
        ids = por_estructura.get(nombre_estructura, [])
        if not ids:
            continue  # sin materiales asociados: la sigue cobrando el catálogo
        total = 0.0
        parcial: dict[str, dict] = {}
        completo = True
        for id_ in ids:
            material = obtener_material(id_)
            if material is None:
                continue
            monto, se_puede = _cobrable(material, producto_interno)
            if not se_puede:
                completo = False
                break
            total += monto
            parcial[material["nombre"]] = {
                "consumo": calcular_consumo(material, producto_interno),
                "valor":   material["valor"],
                "monto":   monto,
                "tipo":    material.get("tipo", "unidad"),
                "origen":  nombre_estructura,
            }
        if completo and parcial:
            estructuras[nombre_estructura] = round(total, 2)
            detalle.update(parcial)
        else:
            incompletas.append(nombre_estructura)

    ids_ya_cobrados = {id_ for e in nombres_estructuras for id_ in por_estructura.get(e, [])}
    materiales_producto: dict[str, float] = {}
    for id_ in por_producto.get(nombre_producto, []):
        if id_ in ids_ya_cobrados:
            continue
        material = obtener_material(id_)
        if material is None:
            continue
        monto, se_puede = _cobrable(material, producto_interno)
        if not se_puede:
            continue
        materiales_producto[material["nombre"]] = monto
        detalle[material["nombre"]] = {
            "consumo": calcular_consumo(material, producto_interno),
            "valor":   material["valor"],
            "monto":   monto,
            "tipo":    material.get("tipo", "unidad"),
            "origen":  nombre_producto,
        }

    return {
        "estructuras":         estructuras,
        "materiales_producto": materiales_producto,
        "incompletas":         incompletas,
        "detalle":             detalle,
    }


def _es_del_mes_en_curso(entrada: dict) -> bool:
    """Si la entrada cae en el mes calendario en curso. Alcanza con mirar el
    'historial' en memoria (nunca el archivado): "este mes" siempre cae dentro
    del año en curso, que es justo lo que _archivar_si_corresponde garantiza
    que sigue ahí."""
    hoy = datetime.now()
    try:
        fecha = datetime.strptime(entrada.get("fecha", ""), "%d/%m/%Y")
    except (ValueError, TypeError):
        return False
    return fecha.year == hoy.year and fecha.month == hoy.month


def vendido_del_mes(m: dict) -> float:
    """Precio de venta de todo lo que se consumió en OPs este mes — cada
    entrada de consumo trae el valor de venta con el que se valorizó esa OP
    (ver _agregar_historial), así que esto NO se revaloriza si el precio
    cambió después: es lo que de verdad se cobró."""
    total = 0.0
    for entrada in m.get("historial", []):
        if entrada.get("tipo") != "consumo" or not _es_del_mes_en_curso(entrada):
            continue
        valor_venta = entrada.get("valor_venta")
        if valor_venta is None:
            continue
        consumido = entrada.get("cantidad_anterior", 0.0) - entrada.get("cantidad_nueva", 0.0)
        total += consumido * float(valor_venta)
    return round(total, 2)


def ganancia_del_mes(m: dict) -> float:
    """Margen de lo vendido este mes (no flujo de caja — decisión de Bruno,
    2026-10-01): suma las ganancias que ya quedaron calculadas en cada
    consumo del mes, con los precios que regían en esa OP. Un mes con un
    restock grande no la hunde; lo que se gastó en comprar se ve en
    gasto_del_mes, que es otra columna."""
    return round(sum(
        float(e.get("ganancia") or 0.0)
        for e in m.get("historial", [])
        if e.get("tipo") == "consumo" and _es_del_mes_en_curso(e)
    ), 2)


def metricas_material(m: dict) -> dict:
    """Las 9 cifras del modelo económico de un material, tal como las
    muestra la tabla de materiales de menu.html en tres grupos de tres (ver
    docstring del módulo) — se calculan acá, de una sola pasada, para que la
    UI no tenga que saber de dónde sale cada una ni repetir la cuenta:

      gasto_unitario / gasto_mes / gasto_total
      valor_unitario / valor_restante / valor_vendido
      ganancia_unitaria / ganancia_mes / ganancia_total

    Las unitarias son None cuando falta el dato con el que se calculan
    (nunca 0): sin precio de venta cargado no hay "valor restante" de $0,
    hay un valor que todavía no se sabe — y la UI los muestra distinto ("—"
    en vez de "$0")."""
    valor = m.get("valor")
    gasto_unitario = m.get("gasto_unitario")
    cantidad = m.get("cantidad", 0.0)
    # Si nunca se registró un costo, las tres cifras de Gastos son None, no 0:
    # el material costó algo, solo que no se cargó. gasto_unitario en None y
    # acumulado en 0 solo pasan juntos (todo restock con costo mueve los dos), así
    # que alcanza con mirarlos. Mismo criterio que un rollo sin precio de compra
    # (core.repositorio_inventario.metricas_rollo) — las dos tablas de Inventario
    # tienen que mostrar lo mismo en la misma celda.
    acumulado = round(m.get("gasto_acumulado", 0.0), 2)
    sin_costo = gasto_unitario is None and not acumulado
    return {
        "gasto_unitario":     gasto_unitario,
        "gasto_mes":          None if sin_costo else gasto_del_mes(m),
        "gasto_total":        None if sin_costo else acumulado,
        "valor_unitario":     valor,
        "valor_restante":     None if valor is None else round(float(valor) * cantidad, 2),
        "valor_vendido":      round(m.get("vendido_acumulado", 0.0), 2),
        "ganancia_unitaria":  None if (valor is None or gasto_unitario is None)
                              else round(float(valor) - float(gasto_unitario), 2),
        "ganancia_mes":       ganancia_del_mes(m),
        "ganancia_total":     round(m.get("ganancia_acumulada", 0.0), 2),
    }


def valores_legado_materiales() -> dict[str, dict]:
    """{nombre: {"valorUNIT": x}} (tipo="unidad") o {"valorML": x}
    (tipo="metro") de cada material CON valor fijado — mismo shape que
    core.repositorio.cargar_estructuras_legado(), para poder mezclarse
    directo con ESTRUCTURAS_LEGADO_VALORES (ver
    estructuras_legado_valores_efectivos). Un material sin valor (nunca
    editado) no aparece acá — deja el catálogo estático a cargo de ese
    nombre hasta que alguien le ponga un valor a mano."""
    valores: dict[str, dict] = {}
    for m in listar_materiales():
        if m.get("valor") is None:
            continue
        clave = "valorML" if m.get("tipo") == "metro" else "valorUNIT"
        valores[m["nombre"]] = {clave: float(m["valor"])}
    return valores


def kwargs_precios() -> dict:
    """Los parámetros con los que hay que llamar a core.precios.costo_producto
    (y costo_cotizacion, que los reenvía) para que una cotización se cobre con
    el Inventario puesto. Existe para que TODOS los caminos que valorizan una
    cotización —crearla, verla, imprimirla, recalcularla al abrirla— usen
    exactamente los mismos precios: antes solo ui/api_cotizacion.py pasaba el
    catálogo efectivo, así que una cotización creada con precios de Inventario
    se reabría valorizada con el catálogo estático y los totales cambiaban
    solos. Son dos cosas, y conviven:

      estructuras_legado_valores → el catálogo con los precios de venta de los
          materiales pisándolo POR NOMBRE (ver
          estructuras_legado_valores_efectivos). Sigue siendo lo que cobra una
          estructura que no tiene materiales asociados.
      cobro_materiales → el cobro por los materiales que la estructura de
          verdad gasta (ver cobro_materiales_producto), que REEMPLAZA al
          catálogo donde se puede resolver.

    Orden de precedencia, de más fuerte a más débil: monto escrito a mano en
    la cotización ("$10.000") > materiales asociados a la estructura > precio
    de venta del material del mismo nombre > catálogo estático.

    Las dos partes ya se apagan solas con el módulo Inventario deshabilitado
    (core.config.MODULOS_HABILITADOS), así que esto se puede pasar siempre sin
    preguntar nada."""
    return {
        "estructuras_legado_valores": estructuras_legado_valores_efectivos(),
        "cobro_materiales":           cobro_materiales_producto,
    }


def estructuras_legado_valores_efectivos() -> dict:
    """El catálogo que de verdad hay que usar para cobrar una cotización
    NUEVA: ESTRUCTURAS_LEGADO_VALORES (recursos/estructuras_legado.json,
    de solo lectura) con los materiales editados en Inventario PISÁNDOLO
    por nombre — pedido explícito de Bruno (2026-09-14): el valor que se
    carga acá pasa a ser lo que cobran las cotizaciones nuevas de ahí en
    adelante. Import adentro de la función (no al tope del módulo) por el
    mismo motivo que valor_sugerido_textil en core.repositorio_inventario:
    evitar acoplar el import a nivel de módulo con core.repositorio.

    Con el módulo Inventario apagado (core.config.MODULOS_HABILITADOS,
    pedido de Bruno 2026-09-16 pensando en sacar un release con el módulo
    todavía pausado) devuelve el catálogo estático TAL CUAL, sin pisar
    nada — los materiales de Inventario, si los hay, no deben afectar el
    precio de ninguna cotización mientras el módulo no esté habilitado."""
    from core.repositorio import ESTRUCTURAS_LEGADO_VALORES
    if not _inventario_habilitado():
        return dict(ESTRUCTURAS_LEGADO_VALORES)
    return {**ESTRUCTURAS_LEGADO_VALORES, **valores_legado_materiales()}
