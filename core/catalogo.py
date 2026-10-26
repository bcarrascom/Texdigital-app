"""
core/catalogo.py
QUÉ textiles, estructuras, terminaciones y productos existen — un ajuste
GLOBAL (ver core.ajustes_globales), editable en Configuración. Pedido de
Bruno (2026-10-22): agregar estructuras y terminaciones, y agregar y
renombrar textiles, sin esperar una versión nueva de la app; y (2026-10-25)
agregar, renombrar y quitar productos. Cuánto vale cada uno es otro tema
(core.precios_textiles, core.precios_componentes).

Lo que trae la app (recursos/*.json) es la base; en Conf/catalogo.json se
guarda solo lo que se cambió:

    {"version": 1,
     "textiles_agregados":     [{"nombre", "ancho", "backlight"}],
     "textiles_renombrados":   {nombre anterior: nombre actual},
     "textiles_anchos":        {nombre: ancho}        (cambios de ancho)
     "textiles_backlight":     {nombre: true/false}   (si sirve para Backlight)
     "estructuras_agregadas":  [{"nombre", "unidad": "un." | "ML"}],
     "terminaciones_agregadas": [{"nombre", "unidad"}],
     "productos_agregados":    [nombre],
     "productos_renombrados":  {nombre anterior: nombre actual},
     "productos_quitados":     [nombre]}

Un producto es solo un nombre (lo que se elige en el cotizador); lo único
que cuelga de él son los materiales de Inventario asociados (ver
core.repositorio_materiales), así que renombrarlo o quitarlo los arrastra.
Como con los textiles, el nombre anterior de un producto renombrado queda
como alias: una cotización vieja que se aprueba sigue gastando sus
materiales (ver `nombre_producto`).

Cómo llega al resto de la app: core.repositorio carga los catálogos una vez
(TEXTILES, TEXTILES_ANCHOS, ESTRUCTURAS_LEGADO...) y todo el código usa esos
MISMOS objetos. `refrescar` les aplica este archivo EN EL LUGAR (mismo
criterio que core.config.STOCK_MINIMO_ML: variables compartidas que se leen
por referencia), así no hay que tocar cada lugar que lee un ancho o la lista
de textiles. Se llama al entrar a lo que usa el catálogo (cotizar, valorizar,
Inventario, Configuración); como otra instalación puede haberlo cambiado en
Dropbox, compara la fecha del archivo y solo lo vuelve a leer si cambió.

Renombrar un textil:
  - los rollos de Inventario sin decomisionar pasan al nombre nuevo;
  - el nombre anterior queda como alias del nuevo, porque las cotizaciones y
    OPs ya hechas guardan el nombre con que se hicieron: un ancho o un precio
    buscado por el nombre viejo encuentra el del textil renombrado, y una
    cotización vieja que se aprueba descuenta de sus rollos (ver
    `nombre_textil`);
  - su precio en Configuración › Textiles pasa al nombre nuevo.
"""

from core import ajustes_globales

NOMBRE = "catalogo"
VERSION = 1

UNIDADES = {"un.": "valorUNIT", "ML": "valorML"}
TIPOS_COMPONENTE = ("estructuras", "terminaciones")

# Telas que sirven para Backlight (necesitan ser translúcidas) — las que la
# app traía fijas en ui/api_cotizacion.py.
_TELAS_BACKLIGHT = ["Popelina 155", "Popelina 310", "Pearl 155", "Pearl 310", "Pearl 160 HP"]

ANCHO_MAXIMO = 10.0


# ── La base (recursos/) ─────────────────────────────────────────────────────

_semillas_cache = None


def _semillas() -> dict:
    """Los catálogos tal como vienen con la app, leídos de recursos/ (no de
    los objetos de core.repositorio, que este módulo modifica)."""
    global _semillas_cache
    if _semillas_cache is None:
        from core import repositorio
        textiles, anchos, valores = repositorio.cargar_textiles()
        estructuras, estructuras_valores = repositorio.cargar_estructuras_legado()
        terminaciones, terminaciones_valores = repositorio.cargar_terminaciones_legado()
        _semillas_cache = {
            "textiles": textiles, "anchos": anchos, "valores": valores, "backlight": list(_TELAS_BACKLIGHT),
            "estructuras": (estructuras, estructuras_valores),
            "terminaciones": (terminaciones, terminaciones_valores),
            "productos": repositorio.cargar_productos(),
        }
    return _semillas_cache


# ── Leer ─────────────────────────────────────────────────────────────────────

def _texto(v) -> str:
    return " ".join(str(v or "").split())


def _numero(v) -> float | None:
    if v is None or isinstance(v, bool) or v == "":
        return None
    try:
        n = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return n if n == n and abs(n) != float("inf") else None


def _leer() -> dict:
    """El archivo, con cada parte en su forma (lo que no se pueda leer, vacío)."""
    g = ajustes_globales.leer(NOMBRE)

    def lista(clave):
        return [x for x in g.get(clave) or [] if isinstance(x, dict) and _texto(x.get("nombre"))]

    def mapa(clave):
        return g.get(clave) if isinstance(g.get(clave), dict) else {}

    return {
        "textiles_agregados": lista("textiles_agregados"),
        "textiles_renombrados": {k: v for k, v in mapa("textiles_renombrados").items() if isinstance(v, str) and k != v},
        "textiles_anchos": mapa("textiles_anchos"),
        "textiles_backlight": mapa("textiles_backlight"),
        "estructuras_agregadas": lista("estructuras_agregadas"),
        "terminaciones_agregadas": lista("terminaciones_agregadas"),
        "productos_agregados": [_texto(n) for n in g.get("productos_agregados") or [] if isinstance(n, str) and _texto(n)],
        "productos_renombrados": {k: v for k, v in mapa("productos_renombrados").items() if isinstance(v, str) and k != v},
        "productos_quitados": [n for n in g.get("productos_quitados") or [] if isinstance(n, str)],
    }


def textiles(datos: dict | None = None) -> list[dict]:
    """[{"nombre", "ancho", "backlight", "agregado": bool, "anteriores": [nombres]}]
    — los textiles vigentes, primero los de la app (con su nombre actual) y
    después los agregados."""
    datos = datos or _leer()
    s = _semillas()
    renombrados = datos["textiles_renombrados"]
    filas = []
    for original in s["textiles"]:
        filas.append({"nombre": renombrados.get(original, original), "ancho": s["anchos"].get(original),
                      "backlight": original in s["backlight"], "agregado": False})
    for t in datos["textiles_agregados"]:
        filas.append({"nombre": _texto(t["nombre"]), "ancho": _numero(t.get("ancho")),
                      "backlight": bool(t.get("backlight")), "agregado": True})
    for f in filas:
        n = _numero(datos["textiles_anchos"].get(f["nombre"]))
        if n is not None and n > 0:
            f["ancho"] = n
        if isinstance(datos["textiles_backlight"].get(f["nombre"]), bool):
            f["backlight"] = datos["textiles_backlight"][f["nombre"]]
        f["anteriores"] = sorted(viejo for viejo, nuevo in renombrados.items() if nuevo == f["nombre"])
    return filas


def alias_textiles() -> dict[str, str]:
    """{nombre anterior: nombre actual} de los textiles renombrados."""
    return dict(_leer()["textiles_renombrados"])


def nombre_textil(nombre: str) -> str:
    """El nombre actual de un textil, si `nombre` es uno anterior (ver
    docstring del módulo); si no, el mismo."""
    return alias_textiles().get(nombre, nombre)


def telas_backlight() -> list[str]:
    return [t["nombre"] for t in textiles() if t["backlight"]]


def componentes(tipo: str, datos: dict | None = None) -> list[dict]:
    """[{"nombre", "unidad", "agregado"}] de estructuras o terminaciones."""
    datos = datos or _leer()
    nombres, valores = _semillas()[tipo]
    filas = [{"nombre": n, "unidad": "ML" if "valorML" in valores.get(n, {}) else "un.", "agregado": False}
             for n in nombres if n in valores]
    filas += [{"nombre": _texto(c["nombre"]), "unidad": c.get("unidad") if c.get("unidad") in UNIDADES else "un.",
               "agregado": True} for c in datos[f"{tipo}_agregadas"]]
    return filas


# ── Aplicar a los catálogos de core.repositorio ─────────────────────────────

_SIN_APLICAR = object()
_aplicado = _SIN_APLICAR   # fecha del archivo que se aplicó (None: no había archivo)


def refrescar(forzar: bool = False) -> None:
    """Pone los catálogos de core.repositorio al día con Conf/catalogo.json,
    si el archivo cambió desde la última vez (ver docstring del módulo)."""
    global _aplicado
    ruta = ajustes_globales._ruta(NOMBRE)
    try:
        fecha = ruta.stat().st_mtime_ns
    except OSError:
        fecha = None
    if not forzar and (fecha == _aplicado or (_aplicado is _SIN_APLICAR and fecha is None)):
        return
    _aplicar(_leer())
    _aplicado = fecha


def _olvidar() -> None:
    """Para los tests: que el próximo refrescar no dé nada por aplicado."""
    global _aplicado
    _aplicado = _SIN_APLICAR


def _aplicar(datos: dict) -> None:
    from core import repositorio

    s = _semillas()
    filas = textiles(datos)
    repositorio.TEXTILES[:] = [t["nombre"] for t in filas]
    repositorio.PRODUCTOS[:] = productos(datos)
    anchos = {t["nombre"]: t["ancho"] for t in filas if t["ancho"] is not None}
    # Los nombres anteriores también, para las cotizaciones que los usan.
    anchos.update({viejo: anchos[nuevo] for viejo, nuevo in datos["textiles_renombrados"].items() if nuevo in anchos})
    repositorio.TEXTILES_ANCHOS.clear()
    repositorio.TEXTILES_ANCHOS.update(anchos)
    # El valor de la app, como punto de partida de Configuración › Textiles,
    # sigue al textil renombrado.
    renombrados = datos["textiles_renombrados"]
    repositorio.TEXTILES_VALORES.clear()
    repositorio.TEXTILES_VALORES.update({renombrados.get(n, n): v for n, v in s["valores"].items()})

    for tipo, nombres_obj, valores_obj in (
        ("estructuras", repositorio.ESTRUCTURAS_LEGADO, repositorio.ESTRUCTURAS_LEGADO_VALORES),
        ("terminaciones", repositorio.TERMINACIONES_LEGADO, repositorio.TERMINACIONES_LEGADO_VALORES),
    ):
        nombres_base, valores_base = s[tipo]
        agregadas = [c for c in componentes(tipo, datos) if c["agregado"]]
        nombres_obj[:] = list(nombres_base) + [c["nombre"] for c in agregadas]
        valores_obj.clear()
        valores_obj.update({n: dict(v) for n, v in valores_base.items()})
        # Su valor está en Configuración (core.precios_componentes); acá, 0 de base.
        valores_obj.update({c["nombre"]: {UNIDADES[c["unidad"]]: 0.0} for c in agregadas})


# ── Validar ─────────────────────────────────────────────────────────────────

def _validar_nombre(nombre: str, existentes: list[str], ocupados: dict[str, str] | None = None) -> str | None:
    """`existentes`: los nombres vigentes con los que no puede repetirse.
    `ocupados`: {nombre anterior: de qué textil es} que tampoco se pueden usar."""
    if not nombre:
        return "Falta el nombre."
    if len(nombre) > 80:
        return "El nombre es demasiado largo."
    clave = nombre.casefold()
    if any(e.casefold() == clave for e in existentes):
        return "Ya existe uno con ese nombre."
    for viejo, de_quien in (ocupados or {}).items():
        if viejo.casefold() == clave:
            return f"Ese nombre lo usaba «{de_quien}» antes de renombrarlo: las cotizaciones viejas lo usan."
    return None


def _validar_ancho(ancho) -> tuple[float | None, str | None]:
    n = _numero(ancho)
    if n is None or not 0 < n <= ANCHO_MAXIMO:
        return None, f"El ancho tiene que ser más que 0 y hasta {ANCHO_MAXIMO:g} m."
    return n, None


def _guardar(datos: dict) -> str | None:
    """Escribe el catálogo y lo aplica. Devuelve un error, o None."""
    try:
        ajustes_globales.guardar(NOMBRE, datos, VERSION)
    except ajustes_globales.AjusteMasNuevo:
        return "El catálogo lo guardó una versión más nueva de la app. Actualiza esta instalación para poder cambiarlo."
    refrescar(forzar=True)
    return None


def solo_lectura() -> bool:
    return ajustes_globales.es_mas_nuevo(NOMBRE, VERSION)


# ── Textiles ────────────────────────────────────────────────────────────────

def agregar_textil(nombre: str, ancho, backlight: bool = False, valor=None) -> dict:
    """Un textil nuevo, con su ancho y su valor por metro. El valor puede
    faltar solo si el textil se va a cobrar por rollo (ver core.precios_textiles).
    {"ok": True} o {"ok": False, "errores": {campo: mensaje}}."""
    from core import precios_textiles

    datos = _leer()
    nombre = _texto(nombre)
    errores = {}
    if (m := _validar_nombre(nombre, [t["nombre"] for t in textiles(datos)], datos["textiles_renombrados"])):
        errores["nombre"] = m
    ancho, m = _validar_ancho(ancho)
    if m:
        errores["ancho"] = m
    ajustes = precios_textiles.cargar()
    con_valor = valor not in (None, "")
    if con_valor and not (_numero(valor) or 0) > 0:
        errores["valor"] = "El valor tiene que ser un monto mayor que 0."
    elif not con_valor and precios_textiles.cobro_efectivo(ajustes["modo"], "fijo") == "fijo":
        errores["valor"] = "Falta el valor por metro."
    if errores:
        return {"ok": False, "errores": errores}

    datos["textiles_agregados"].append({"nombre": nombre, "ancho": ancho, "backlight": bool(backlight)})
    if (m := _guardar(datos)):
        return {"ok": False, "errores": {"general": m}}
    precios_textiles.fijar(nombre, cobro="fijo", valor=_numero(valor) if con_valor else None)
    return {"ok": True}


def editar_textil(nombre_actual: str, nombre_nuevo: str, ancho, backlight: bool) -> dict:
    """Cambia el nombre, el ancho o si sirve para Backlight de un textil (ver
    "Renombrar" en el docstring del módulo). {"ok": True, "rollos": n
    renombrados} o {"ok": False, "errores": {campo: mensaje}}."""
    from core import precios_textiles
    from core.repositorio_inventario import renombrar_textil_rollos

    datos = _leer()
    vigentes = textiles(datos)
    if not any(t["nombre"] == nombre_actual for t in vigentes):
        return {"ok": False, "errores": {"general": "Ese textil ya no existe: recarga la página."}}
    nombre_nuevo = _texto(nombre_nuevo)
    renombra = nombre_nuevo != nombre_actual
    errores = {}
    if renombra:
        # Su propio nombre anterior sí se puede volver a usar.
        ocupados = {v: n for v, n in datos["textiles_renombrados"].items() if n != nombre_actual}
        otros = [t["nombre"] for t in vigentes if t["nombre"] != nombre_actual]
        if (m := _validar_nombre(nombre_nuevo, otros, ocupados)):
            errores["nombre"] = m
    ancho, m = _validar_ancho(ancho)
    if m:
        errores["ancho"] = m
    if errores:
        return {"ok": False, "errores": errores}

    rollos = 0
    if renombra:
        _renombrar(datos, nombre_actual, nombre_nuevo)
    datos["textiles_anchos"][nombre_nuevo] = ancho
    datos["textiles_backlight"][nombre_nuevo] = bool(backlight)
    if (m := _guardar(datos)):
        return {"ok": False, "errores": {"general": m}}
    if renombra:
        precios_textiles.renombrar(nombre_actual, nombre_nuevo)
        rollos = renombrar_textil_rollos(nombre_actual, nombre_nuevo)
    return {"ok": True, "rollos": rollos}


def _renombrar(datos: dict, viejo: str, nuevo: str) -> None:
    """Aplica viejo → nuevo a `datos` (en memoria)."""
    agregado = next((t for t in datos["textiles_agregados"] if _texto(t["nombre"]) == viejo), None)
    if agregado is not None:
        agregado["nombre"] = nuevo
    # Cada nombre anterior apunta al actual (A → B → C deja A → C y B → C).
    renombrados = {v: (nuevo if n == viejo else n) for v, n in datos["textiles_renombrados"].items()}
    renombrados[viejo] = nuevo
    datos["textiles_renombrados"] = {v: n for v, n in renombrados.items() if v != n}
    for clave in ("textiles_anchos", "textiles_backlight"):
        if viejo in datos[clave]:
            datos[clave][nuevo] = datos[clave].pop(viejo)


# ── Estructuras y terminaciones ─────────────────────────────────────────────

def agregar_componente(tipo: str, nombre: str, unidad: str, valor) -> dict:
    """Una estructura o terminación nueva, con su unidad ("un." o "ML") y su
    valor. {"ok": True} o {"ok": False, "errores": {campo: mensaje}}."""
    from core import precios_componentes

    if tipo not in TIPOS_COMPONENTE:
        return {"ok": False, "errores": {"general": "Tipo desconocido."}}
    datos = _leer()
    nombre = _texto(nombre)
    errores = {}
    if (m := _validar_nombre(nombre, [c["nombre"] for c in componentes(tipo, datos)])):
        errores["nombre"] = m
    if unidad not in UNIDADES:
        errores["unidad"] = "Elige si se cobra por unidad o por metro lineal."
    if not (_numero(valor) or 0) > 0:
        errores["valor"] = "Falta el valor." if valor in (None, "") else "El valor tiene que ser un monto mayor que 0."
    if errores:
        return {"ok": False, "errores": errores}

    datos[f"{tipo}_agregadas"].append({"nombre": nombre, "unidad": unidad})
    if (m := _guardar(datos)):
        return {"ok": False, "errores": {"general": m}}
    precios_componentes.fijar(tipo, nombre, _numero(valor))
    return {"ok": True}


# ── Productos ───────────────────────────────────────────────────────────────

# Nombres que usa Inventario para asociar materiales a TODOS los backlight
# (ver core.repositorio_materiales): no pueden ser el nombre de un producto.
def _reservados() -> set[str]:
    from core.repositorio_materiales import PRODUCTO_BACKLIGHT, PRODUCTO_BACKLIGHT_CAJA
    return {PRODUCTO_BACKLIGHT.casefold(), PRODUCTO_BACKLIGHT_CAJA.casefold()}


def productos(datos: dict | None = None) -> list[str]:
    """Los productos vigentes: los de la app (con su nombre actual) y después
    los agregados, sin los quitados."""
    datos = datos or _leer()
    renombrados = datos["productos_renombrados"]
    quitados = {n.casefold() for n in datos["productos_quitados"]}
    nombres = [renombrados.get(n, n) for n in _semillas()["productos"]] + datos["productos_agregados"]
    vistos, resultado = set(), []
    for n in nombres:
        if n.casefold() in quitados or n.casefold() in vistos:
            continue
        vistos.add(n.casefold())
        resultado.append(n)
    return resultado


def productos_detalle() -> list[dict]:
    """[{"nombre", "agregado", "anteriores": [nombres]}] para Configuración."""
    datos = _leer()
    agregados = {n.casefold() for n in datos["productos_agregados"]}
    renombrados = datos["productos_renombrados"]
    return [{"nombre": n, "agregado": n.casefold() in agregados,
             "anteriores": sorted(v for v, a in renombrados.items() if a == n)} for n in productos(datos)]


def nombre_producto(nombre: str) -> str:
    """El nombre ACTUAL de un producto, si `nombre` es uno anterior."""
    return _leer()["productos_renombrados"].get(nombre, nombre)


def _validar_producto(nombre: str, datos: dict, actual: str | None = None) -> str | None:
    if nombre.casefold() in _reservados():
        return f"«{nombre}» es un nombre reservado de Inventario (los materiales que gastan todos los backlight)."
    otros = [n for n in productos(datos) if actual is None or n != actual]
    ocupados = {v: a for v, a in datos["productos_renombrados"].items() if a != actual}
    return _validar_nombre(nombre, otros, ocupados)


def agregar_producto(nombre: str) -> dict:
    """{"ok": True} o {"ok": False, "errores": {campo: mensaje}}. Si es uno de
    la app que se había quitado, vuelve a su lugar."""
    datos = _leer()
    nombre = _texto(nombre)
    quitado = next((q for q in datos["productos_quitados"] if q.casefold() == nombre.casefold()), None)
    if quitado is None and (m := _validar_producto(nombre, datos)):
        return {"ok": False, "errores": {"nombre": m}}
    if quitado is not None:
        datos["productos_quitados"] = [q for q in datos["productos_quitados"] if q != quitado]
    else:
        datos["productos_agregados"].append(nombre)
    if (m := _guardar(datos)):
        return {"ok": False, "errores": {"general": m}}
    return {"ok": True}


def renombrar_producto(actual: str, nuevo: str) -> dict:
    """Cambia el nombre de un producto y el de sus asociaciones en Inventario.
    {"ok": True, "materiales": n} o {"ok": False, "errores": {...}}."""
    from core.repositorio_materiales import renombrar_asociacion

    datos = _leer()
    if actual not in productos(datos):
        return {"ok": False, "errores": {"general": "Ese producto ya no existe: recarga la página."}}
    nuevo = _texto(nuevo)
    if nuevo == actual:
        return {"ok": True, "materiales": 0}
    if (m := _validar_producto(nuevo, datos, actual)):
        return {"ok": False, "errores": {"nombre": m}}
    datos["productos_agregados"] = [nuevo if n == actual else n for n in datos["productos_agregados"]]
    renombrados = {v: (nuevo if n == actual else n) for v, n in datos["productos_renombrados"].items()}
    renombrados[actual] = nuevo
    datos["productos_renombrados"] = {v: n for v, n in renombrados.items() if v != n}
    if (m := _guardar(datos)):
        return {"ok": False, "errores": {"general": m}}
    return {"ok": True, "materiales": renombrar_asociacion("productos", actual, nuevo)}


def quitar_producto(nombre: str) -> dict:
    """Saca un producto del cotizador y de las asociaciones de Inventario. Las
    cotizaciones y OPs ya hechas lo conservan. {"ok": True, "materiales": n}."""
    from core.repositorio_materiales import renombrar_asociacion

    datos = _leer()
    if nombre not in productos(datos):
        return {"ok": False, "errores": {"general": "Ese producto ya no existe: recarga la página."}}
    if nombre in datos["productos_agregados"]:
        datos["productos_agregados"] = [n for n in datos["productos_agregados"] if n != nombre]
    else:
        datos["productos_quitados"].append(nombre)
    if (m := _guardar(datos)):
        return {"ok": False, "errores": {"general": m}}
    return {"ok": True, "materiales": renombrar_asociacion("productos", nombre, None)}
