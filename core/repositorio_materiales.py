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
  - El "valor" (precio por unidad/medida) de un material EDITABLE ACÁ pasa
    a pisar el catálogo estático que de verdad cobran las cotizaciones
    (core.repositorio.ESTRUCTURAS_LEGADO_VALORES — ver
    estructuras_legado_valores_efectivos más abajo) — a diferencia de
    rollo.valor, que es puramente informativo/sugerido y nunca entra en
    el cálculo de una cotización (ver core.repositorio_inventario.
    valor_sugerido_textil).

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
import uuid
from datetime import datetime
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox

TIPOS_VALIDOS = ("unidad", "metro")


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
    return _archivar_si_corresponde(m)


def _sembrar_desde_catalogo(existentes: list[dict]) -> list[dict]:
    """Crea (en disco, con id real) un registro de stock en cero para cada
    material del catálogo estático (recursos/estructuras_legado.json) que
    todavía no tenga ninguno — pedido de Bruno (2026-09-15): la tabla tiene
    que listar TODOS los materiales conocidos, aunque tengan 0 de cantidad
    y ningún dato cargado todavía, no solo los que alguien ya usó
    "Ingresar" sobre. Por ahora ese catálogo ES la lista de materiales que
    existen (ver docstring del módulo) — el día que Bruno traiga una lista
    real aparte, esta siembra cambia de fuente sin tocar el resto del
    archivo.

    Sembrado EN DISCO, con id real (no un dict "virtual" solo en memoria):
    así editar/ajustar un material recién aparecido en la tabla funciona
    igual que cualquier otro, sin un camino aparte para materiales
    "todavía sin guardar". "valor" queda en None a propósito (no se
    autocompleta con el precio del catálogo) — sembrar no tiene que
    cambiar ningún precio de cotización, eso sigue siendo una decisión
    explícita del usuario (ver editar_material); mientras valor sea None,
    estructuras_legado_valores_efectivos() sigue resolviendo este nombre
    contra el catálogo estático tal cual ya lo hacía.

    Barato después de la primera vez: si todos los nombres del catálogo ya
    tienen registro, no compara más que un set de strings, sin escribir
    nada."""
    from core.repositorio import ESTRUCTURAS_LEGADO, ESTRUCTURAS_LEGADO_VALORES

    nombres_existentes = {m.get("nombre", "").strip().lower() for m in existentes}
    creados = []
    for nombre in ESTRUCTURAS_LEGADO:
        nombre = nombre.strip()
        if not nombre or nombre.lower() in nombres_existentes:
            continue
        valores = ESTRUCTURAS_LEGADO_VALORES.get(nombre, {})
        nuevo = {
            "id":             uuid.uuid4().hex,
            "nombre":         nombre,
            "tipo":           "metro" if "valorML" in valores else "unidad",
            "cantidad":       0.0,
            "valor":          None,
            "proveedor":      "",
            "anio_historial": datetime.now().year,
            "historial":      [],
        }
        _escribir_material(nuevo)
        creados.append(nuevo)
        nombres_existentes.add(nombre.lower())
    return creados


def listar_materiales() -> list[dict]:
    """Todos los materiales, alfabético por nombre — no hay activo/
    inactivo que ordenar ni priorizar ("todos son activos", pedido de
    Bruno), así que a diferencia de listar_rollos no hace falta un criterio
    de orden por ID/fecha. Incluye los del catálogo estático todavía sin
    ningún movimiento propio (ver _sembrar_desde_catalogo)."""
    materiales = []
    for archivo in carpeta_materiales().glob("*.json"):
        m = _leer_material(archivo)
        if m is not None:
            materiales.append(m)
    materiales.extend(_sembrar_desde_catalogo(materiales))
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
) -> dict:
    """Un solo formato de entrada para todo lo que le pasa a un material —
    mismo espíritu que _agregar_registro de rollos (guarda cantidad de
    ANTES y DESPUÉS, no un delta, para poder revisar y deshacer la más
    reciente sin ambigüedad). proveedor/costo_total/costo_unitario SOLO se
    guardan para tipo="compra" — son el detalle de esa compra puntual, no
    tienen sentido en un "uso" o un "ajuste"."""
    entrada = {
        "id":                uuid.uuid4().hex,
        "fecha":             _hoy_dma(),
        "tipo":              tipo,  # "compra" (ingreso) | "uso" (consumo manual) | "ajuste" (corrección manual)
        "cantidad_anterior": anterior,
        "cantidad_nueva":    nuevo,
        "descripcion":       (descripcion or "").strip(),
    }
    if tipo == "compra":
        entrada["proveedor"]      = (proveedor or "").strip()
        entrada["costo_total"]    = float(costo_total) if costo_total is not None else None
        entrada["costo_unitario"] = float(costo_unitario) if costo_unitario is not None else None
    m.setdefault("historial", []).append(entrada)
    return entrada


def ingresar_material(
    nombre: str, cantidad: float, tipo: str = "unidad", proveedor: str = "",
    costo_total: float | None = None, costo_unitario: float | None = None,
) -> dict:
    """La acción única del diálogo "+" de materiales (pedido de Bruno:
    elegir el material con autocompletado, cantidad, proveedor opcional,
    costo total O unitario) — sirve tanto para crear un material que no
    existía todavía como para sumar stock a uno que ya existe, buscando
    por nombre (buscar_material_por_nombre): el usuario no elige entre
    "nuevo" o "existente" a mano, simplemente tipea el nombre.

    `tipo` (metro/unidad) SOLO se usa si el material es nuevo — uno que ya
    existe conserva el que tenía (ese switch vive en editar_material, a
    propósito: pedido de Bruno, "al editar un material, hay un switch").

    `costo_total`/`costo_unitario` son opcionales y se autocompletan entre
    sí (si viene uno y no el otro, y hay cantidad > 0, se deriva el que
    falta) — quedan los dos guardados en la entrada de historial para
    poder calcular gasto_del_mes más tarde sin volver a derivar nada.

    El "valor" (precio que pisa cotizaciones, ver
    estructuras_legado_valores_efectivos) NUNCA lo toca esta función en un
    material que YA TIENE uno cargado — solo se siembra con costo_unitario
    si todavía está en None (mejor estimación disponible cuando no hay
    ninguna), sea porque el material se acaba de crear acá o porque venía
    de _sembrar_desde_catalogo (registro en cero, sin valor, esperando su
    primera compra real); después, cambiarlo es una decisión explícita del
    usuario (ver editar_material), no un efecto colateral de cada compra
    nueva."""
    nombre = (nombre or "").strip()
    cantidad = float(cantidad)
    if costo_total is not None and costo_unitario is None and cantidad:
        costo_unitario = costo_total / cantidad
    elif costo_unitario is not None and costo_total is None:
        costo_total = costo_unitario * cantidad

    m = buscar_material_por_nombre(nombre)
    if m is None:
        m = {
            "id":             uuid.uuid4().hex,
            "nombre":         nombre,
            "tipo":           tipo if tipo in TIPOS_VALIDOS else "unidad",
            "cantidad":       0.0,
            "valor":          None,
            "proveedor":      "",
            "anio_historial": datetime.now().year,
            "historial":      [],
        }
    if m.get("valor") is None and costo_unitario is not None:
        m["valor"] = float(costo_unitario)

    proveedor = (proveedor or "").strip()
    if proveedor:
        m["proveedor"] = proveedor

    anterior = m.get("cantidad", 0.0)
    nuevo = round(anterior + cantidad, 3)
    m["cantidad"] = nuevo
    _agregar_historial(
        m, tipo="compra", anterior=anterior, nuevo=nuevo,
        proveedor=proveedor, costo_total=costo_total, costo_unitario=costo_unitario,
    )
    _escribir_material(m)
    return m


def editar_material(id_: str, nombre: str, tipo: str, valor: float | None = None, proveedor: str = "") -> dict | None:
    """nombre/tipo/valor/proveedor son editables después de creado —
    cantidad se maneja aparte (ver registrar_uso/ajustar_cantidad), para
    que no se pise sin dejar rastro por acá (mismo criterio que
    editar_rollo). El switch metro/unidad ("tipo") vive acá a propósito:
    pedido de Bruno, no en el alta."""
    m = obtener_material(id_)
    if m is None:
        return None
    m["nombre"] = (nombre or "").strip()
    m["tipo"] = tipo if tipo in TIPOS_VALIDOS else m.get("tipo", "unidad")
    m["valor"] = float(valor) if valor is not None else None
    m["proveedor"] = (proveedor or "").strip()
    _escribir_material(m)
    return m


def registrar_uso(id_: str, cantidad_usada: float, descripcion: str = "") -> dict | None:
    """Consumo manual de stock (pedido de Bruno: sin auto-descuento al
    aprobar una cotización todavía, el usuario lo carga a mano) — resta
    `cantidad_usada` de la cantidad corriente y queda en 'historial' con
    tipo="uso". Devuelve el material actualizado, o None si no existe."""
    m = obtener_material(id_)
    if m is None:
        return None
    anterior = m.get("cantidad", 0.0)
    nuevo = round(anterior - float(cantidad_usada), 3)
    m["cantidad"] = nuevo
    _agregar_historial(m, tipo="uso", anterior=anterior, nuevo=nuevo, descripcion=descripcion)
    _escribir_material(m)
    return m


def ajustar_cantidad(id_: str, nueva_cantidad: float, descripcion: str = "") -> dict | None:
    """Corrección manual del stock (mismo criterio que ajustar_restante de
    rollos) — acá el usuario pone DIRECTO la cantidad que corresponde, no
    un delta. Queda en 'historial' SIEMPRE, con tipo="ajuste"."""
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
    devuelve None."""
    m = obtener_material(id_material)
    if m is None:
        return None
    historial = m.get("historial", [])
    if not historial or historial[-1].get("id") != id_entrada:
        return None
    objetivo = historial.pop()
    m["cantidad"] = objetivo.get("cantidad_anterior", m.get("cantidad", 0.0))
    _escribir_material(m)
    return m


def gasto_del_mes(m: dict) -> float:
    """Suma de lo gastado en compras de este material durante el mes
    calendario en curso (pedido de Bruno: reemplaza la columna "Origen" de
    rollos en la tabla de materiales) — alcanza con mirar 'historial' (el
    array en memoria del material, nunca el archivado): "este mes" siempre
    cae dentro del año en curso, que es justo lo que _archivar_si_corresponde
    garantiza que sigue ahí. Si una compra vino solo con costo_unitario
    (no costo_total), se deriva desde la diferencia de cantidad de esa
    misma entrada."""
    hoy = datetime.now()
    total = 0.0
    for entrada in m.get("historial", []):
        if entrada.get("tipo") != "compra":
            continue
        try:
            fecha = datetime.strptime(entrada.get("fecha", ""), "%d/%m/%Y")
        except (ValueError, TypeError):
            continue
        if fecha.year != hoy.year or fecha.month != hoy.month:
            continue
        costo = entrada.get("costo_total")
        if costo is None:
            costo_unitario = entrada.get("costo_unitario")
            if costo_unitario is not None:
                costo = costo_unitario * (entrada.get("cantidad_nueva", 0.0) - entrada.get("cantidad_anterior", 0.0))
        total += costo or 0.0
    return round(total, 2)


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
    from core import config as _config
    from core.repositorio import ESTRUCTURAS_LEGADO_VALORES
    if not _config.MODULOS_HABILITADOS.get("inventario", True):
        return dict(ESTRUCTURAS_LEGADO_VALORES)
    return {**ESTRUCTURAS_LEGADO_VALORES, **valores_legado_materiales()}
