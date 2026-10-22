"""
core/lista_precios.py
La lista de precios CONGELADA de una cotización: con qué precios se calculó.

Una cotización guardada no se revaloriza sola. Al guardarla se le adjunta
la lista de los precios que usó (solo los de sus componentes: el valor de
cada textil, cada estructura y terminación, la caja y lo que cobró cada
material de Inventario), y verla, imprimirla o aprobarla la calcula con ESA
lista, no con los precios de hoy. Recién al editarla (o recotizarla) se
vuelve a calcular con los precios actuales. Pedido de Bruno (2026-10-22):
los precios se van a poder cambiar desde la app, y una cotización ya
enviada no puede cambiar de monto en silencio.

Si los precios cambiaron desde que se hizo, la pantalla avisa (ver
`cambios`) y el usuario elige: actualizarla a los precios de hoy
(`actualizar`) o mantener los suyos (`mantener`, que deja la marca
"PreciosRevisados" para no volver a preguntar mientras los precios no
vuelvan a cambiar).

Funciona porque core.precios.costo_producto ya recibe todos los catálogos
como parámetros: calcular con la lista congelada es pasarle los catálogos
de la lista en vez de los vigentes (ver `kwargs_congelados`). Las reglas
(IVA, mínimo de ML/M², tramos del descuento por volumen) todavía son
constantes de core.precios; cuando sean editables, entran acá también —
para eso está "version".

En el JSON de la cotización:
    "ListaPrecios": {
        "version": 2,
        "textiles":      {nombre: valor por ML o M²},
        "valores_textil": [el valor por ML o M² que cobró cada producto, en orden]
        "anchos":        {nombre: ancho de la tela en m}   (solo no-backlight)
        "estructuras":   {nombre: {"valorUNIT": x} | {"valorML": x}},
        "terminaciones": {nombre: {"valorUNIT": x} | {"valorML": x}},
        "cajas":         precios de cajas (si algún producto lleva caja),
        "materiales":    [lo que cobró cada producto por materiales, en orden]
    }

"valores_textil" (versión 2) existe porque un textil que se cobra por rollo
(ver core.precios_textiles) no tiene un solo valor: dos productos del mismo
textil pueden salir de rollos con precios distintos. Lo que manda es esa
lista; "textiles" queda como respaldo (las listas de la versión 1 no la
traen) y para mostrar.
"""

import copy
import hashlib
import json

from core.precios import costo_cotizacion, costo_producto, ml_o_area_facturable_por_producto, parsear_valor_manual

VERSION = 2

# Diferencias de menos de medio peso son redondeo, no un cambio de precio.
_TOLERANCIA = 0.5

_SECCIONES_CAJA = {
    "luces": "Luz", "traseras": "Trasera", "armado": "Armado",
    "fp": "Fuente de poder", "perfiles": "Perfil", "pintura_por_ml": "Pintura por ML",
}


# ── Armar ────────────────────────────────────────────────────────────────────

def _usados(internos: list[dict]):
    """Qué componentes usa la cotización: textiles (con su unidad),
    estructuras, terminaciones y si alguno lleva caja. Los montos escritos a
    mano ("$10.000") no son de catálogo: no entran."""
    textiles: dict[str, str] = {}
    estructuras: set[str] = set()
    terminaciones: set[str] = set()
    con_caja = False
    for d in internos:
        if "tela" in d:
            if d.get("tela"):
                textiles[d["tela"]] = "M²"
            con_caja = con_caja or isinstance(d.get("caja"), dict)
        else:
            if d.get("textil"):
                textiles.setdefault(d["textil"], "ML")
            estructuras |= {e for e in d.get("estructuras") or [] if parsear_valor_manual(e) is None}
            terminaciones |= {t for t in d.get("terminaciones") or [] if parsear_valor_manual(t) is None}
    return textiles, estructuras, terminaciones, con_caja


def _nombre_textil(d: dict) -> str:
    return (d.get("tela") if "tela" in d else d.get("textil")) or ""


def _valores_textil(internos: list[dict], kwargs: dict) -> list[float | None]:
    """El valor por ML/M² del textil de cada producto con estos kwargs
    (None si el producto no lleva textil) — el mismo que usa costo_producto."""
    from core.precios import _valor_tela
    from core.repositorio import TEXTILES_VALORES

    # Sin textiles_valores, el mismo default que costo_producto.
    catalogo = kwargs["textiles_valores"] if kwargs.get("textiles_valores") is not None else TEXTILES_VALORES
    return [_valor_tela(d, _nombre_textil(d), catalogo, kwargs.get("valor_textil"))
            if _nombre_textil(d) else None for d in internos]


def armar(internos: list[dict], vigentes: dict | None = None) -> dict:
    """La lista de precios VIGENTE para estos productos (esquema interno, ver
    core.repositorio_cotizaciones.producto_desde_json). `vigentes`: unos
    kwargs_precios() ya armados, para calcular con exactamente los mismos."""
    from core.repositorio import PRECIOS_CAJAS, TEXTILES_ANCHOS, TERMINACIONES_LEGADO_VALORES
    from core.repositorio_materiales import kwargs_precios

    vigentes = vigentes or kwargs_precios()
    estructuras_cat = vigentes["estructuras_legado_valores"]
    textiles, estructuras, terminaciones, con_caja = _usados(internos)
    valores_textil = _valores_textil(internos, vigentes)
    primero = {}
    for d, v in zip(internos, valores_textil):
        primero.setdefault(_nombre_textil(d), v)
    return {
        "version":       VERSION,
        "textiles":      {n: primero.get(n) or 0.0 for n in sorted(textiles)},
        "valores_textil": valores_textil,
        "anchos":        {n: TEXTILES_ANCHOS.get(n) for n in sorted(textiles) if textiles[n] == "ML"},
        "estructuras":   {n: dict(estructuras_cat[n]) for n in sorted(estructuras) if n in estructuras_cat},
        "terminaciones": {n: dict(TERMINACIONES_LEGADO_VALORES[n]) for n in sorted(terminaciones)
                          if n in TERMINACIONES_LEGADO_VALORES},
        "cajas":         copy.deepcopy(PRECIOS_CAJAS) if con_caja else {},
        "materiales":    [vigentes["cobro_materiales"](d) for d in internos],
    }


def firma(lista: dict) -> str:
    """Huella de una lista de precios: igual firma, mismos precios."""
    texto = json.dumps(lista, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:16]


# ── Calcular con la lista congelada ─────────────────────────────────────────

def _internos(datos: dict) -> list[dict]:
    from core.repositorio_cotizaciones import producto_desde_json
    return [producto_desde_json(p) for p in datos.get("productos", [])]


def congelar(datos: dict) -> bool:
    """Le pone su lista de precios a una cotización que todavía no la tiene
    (las guardadas antes de que existiera esto): con los precios de hoy, que
    son con los que se venía mostrando. Devuelve si la agregó (hay que
    guardarla)."""
    if datos.get("ListaPrecios"):
        return False
    datos["ListaPrecios"] = armar(_internos(datos))
    return True


def kwargs_congelados(lista: dict) -> dict:
    """Los parámetros de costo_producto/costo_cotizacion que calculan con la
    lista. Los productos tienen que venir de `internos_congelados` (traen lo
    que cobraron sus materiales)."""
    from core.repositorio import PRECIOS_CAJAS
    return {
        "textiles_valores":             lista.get("textiles", {}),
        "textiles_anchos":              lista.get("anchos", {}),
        "estructuras_legado_valores":   lista.get("estructuras", {}),
        "terminaciones_legado_valores": lista.get("terminaciones", {}),
        # Sin caja no se lee; con caja siempre viene en la lista.
        "precios_cajas":                lista.get("cajas") or PRECIOS_CAJAS,
        "cobro_materiales":             lambda d: d.get("_cobro_materiales"),
        # Sin "valores_textil" (versión 1) da None y vale "textiles".
        "valor_textil":                 lambda d: d.get("_valor_textil"),
    }


def internos_congelados(datos: dict) -> tuple[list[dict], dict]:
    """(productos en esquema interno, kwargs) para calcular la cotización con
    SU lista de precios. Si no la tiene, primero se congela (en memoria)."""
    congelar(datos)
    lista = datos["ListaPrecios"]
    internos = _internos(datos)
    for d, cobro in zip(internos, lista.get("materiales") or []):
        d["_cobro_materiales"] = cobro
    for d, valor in zip(internos, lista.get("valores_textil") or []):
        d["_valor_textil"] = valor
    return internos, kwargs_congelados(lista)


def totales(datos: dict, internos: list[dict], kwargs: dict) -> dict:
    """costo_cotizacion con el descuento, despacho e instalación de la cotización."""
    return costo_cotizacion(internos, datos.get("Descuento", 0.0) or 0.0,
                            despacho=datos.get("Despacho") or 0.0,
                            instalacion=datos.get("Instalacion") or 0.0, **kwargs)


def _por_producto(internos: list[dict], kwargs: dict) -> list[float]:
    facturables = ml_o_area_facturable_por_producto(internos, **kwargs)
    return [costo_producto(d, ml_o_area_facturable=f, **kwargs)["total"] for d, f in zip(internos, facturables)]


# ── Comparar con los precios de hoy ─────────────────────────────────────────

def _nombre_producto(d: dict, i: int) -> str:
    if "tela" in d:
        return f"Backlight · {d.get('tela') or '—'}"
    return d.get("producto") or f"Producto {i + 1}"


def _valor_y_unidad(valores: dict | None) -> tuple[float | None, str]:
    if not valores:
        return None, ""
    if "valorML" in valores:
        return valores["valorML"], "/ML"
    return valores.get("valorUNIT"), "/un."


def _aplanar(d: dict, prefijo: tuple = ()) -> dict:
    plano = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            plano.update(_aplanar(v, prefijo + (str(k),)))
        else:
            plano[prefijo + (str(k),)] = v
    return plano


def _nombre_caja(clave: tuple) -> str:
    seccion = _SECCIONES_CAJA.get(clave[0], clave[0])
    if len(clave) == 1:
        return seccion
    if clave[0] == "fp":
        return f"{seccion} {clave[1]} W"
    return f"{seccion} · {' · '.join(clave[1:])}"


def _valores_materiales(cobros: list) -> dict:
    """{material: (precio de venta, unidad)} de lo que cobraron los productos."""
    valores = {}
    for cobro in cobros or []:
        for nombre, d in ((cobro or {}).get("detalle") or {}).items():
            unidad = "/m" if d.get("tipo") == "metro" else "/un."
            valores[nombre] = (d.get("valor"), unidad)
    return valores


def _valor_textil_de(lista: dict, i: int, nombre: str):
    valores = lista.get("valores_textil")
    if valores and i < len(valores) and valores[i] is not None:
        return valores[i]
    return lista.get("textiles", {}).get(nombre)


def _textiles(antes: dict, ahora: dict, internos: list[dict]) -> list[tuple]:
    """(nombre, antes, ahora, unidad) de los textiles que cambiaron. Producto
    por producto (por rollo, un mismo textil puede cobrar distinto en cada
    uno), pero juntando en una fila los productos de un textil que cambian
    igual — lo normal. Si un textil cambia de más de una forma, una fila por
    producto, con su nombre."""
    por_textil: dict[str, list] = {}
    for i, d in enumerate(internos):
        n = _nombre_textil(d)
        if not n:
            continue
        a, b = _valor_textil_de(antes, i, n), _valor_textil_de(ahora, i, n)
        if a != b:
            por_textil.setdefault(n, []).append((i, d, a, b))
    filas = []
    for n in sorted(por_textil):
        unidad = "/M²" if "tela" in por_textil[n][0][1] else "/ML"
        distintos = {(a, b) for _, _, a, b in por_textil[n]}
        if len(distintos) == 1:
            a, b = distintos.pop()
            filas.append((n, a, b, unidad))
        else:
            filas += [(f"{n} · {_nombre_producto(d, i)}", a, b, unidad) for i, d, a, b in por_textil[n]]
    return filas


def _componentes(antes: dict, ahora: dict, internos: list[dict], cajas_importan: bool) -> list[dict]:
    """Qué cambió de precio, componente por componente."""
    cambios = []

    def agregar(tipo, nombre, a, b, unidad="", formato="pesos"):
        if a != b:
            cambios.append({"tipo": tipo, "nombre": nombre, "antes": a, "ahora": b, "unidad": unidad, "formato": formato})

    for n, a, b, unidad in _textiles(antes, ahora, internos):
        agregar("Textil", n, a, b, unidad)
    for n in sorted(set(antes.get("anchos", {})) | set(ahora.get("anchos", {}))):
        agregar("Ancho de tela", n, antes.get("anchos", {}).get(n), ahora.get("anchos", {}).get(n), " m", "metros")
    for tipo, clave in (("Estructura", "estructuras"), ("Terminación", "terminaciones")):
        for n in sorted(set(antes.get(clave, {})) | set(ahora.get(clave, {}))):
            a, ua = _valor_y_unidad(antes.get(clave, {}).get(n))
            b, ub = _valor_y_unidad(ahora.get(clave, {}).get(n))
            agregar(tipo, n, a, b, ub or ua)
    if cajas_importan:
        plano_a, plano_b = _aplanar(antes.get("cajas")), _aplanar(ahora.get("cajas"))
        for k in sorted(set(plano_a) | set(plano_b)):
            agregar("Caja", _nombre_caja(k), plano_a.get(k), plano_b.get(k))
    mat_a, mat_b = _valores_materiales(antes.get("materiales")), _valores_materiales(ahora.get("materiales"))
    for n in sorted(set(mat_a) | set(mat_b)):
        a, ua = mat_a.get(n, (None, ""))
        b, ub = mat_b.get(n, (None, ""))
        agregar("Material", n, a, b, ub or ua)
    return cambios


def cambios(datos: dict) -> dict | None:
    """Si la cotización cobraría distinto con los precios de hoy, qué cambió:

        {"firma": ..., "componentes": [{tipo, nombre, antes, ahora, unidad, formato}],
         "productos": [{indice, nombre, antes, ahora}],   ← solo los que cambian
         "total": {"antes": ..., "ahora": ...}}

    None si no cambia nada, o si el usuario ya decidió mantener sus precios
    frente a ESTOS precios (PreciosRevisados = firma de los de hoy)."""
    from core.repositorio_materiales import kwargs_precios

    internos_c, kwargs_c = internos_congelados(datos)
    internos_v = _internos(datos)
    kwargs_v = kwargs_precios()
    actual = armar(internos_v, kwargs_v)
    firma_actual = firma(actual)
    if datos.get("PreciosRevisados") == firma_actual:
        return None

    antes_p, ahora_p = _por_producto(internos_c, kwargs_c), _por_producto(internos_v, kwargs_v)
    total_antes = totales(datos, internos_c, kwargs_c)["total"]
    total_ahora = totales(datos, internos_v, kwargs_v)["total"]
    productos = [
        {"indice": i, "nombre": _nombre_producto(d, i), "antes": a, "ahora": b}
        for i, (d, a, b) in enumerate(zip(internos_v, antes_p, ahora_p))
        if abs(a - b) >= _TOLERANCIA
    ]
    if not productos and abs(total_antes - total_ahora) < _TOLERANCIA:
        return None

    cajas_importan = any("tela" in internos_v[p["indice"]] for p in productos)
    return {
        "firma":       firma_actual,
        "componentes": _componentes(datos["ListaPrecios"], actual, internos_v, cajas_importan),
        "productos":   productos,
        "total":       {"antes": total_antes, "ahora": total_ahora},
    }


# ── Decidir ─────────────────────────────────────────────────────────────────

def actualizar(datos: dict) -> None:
    """Pasa la cotización a los precios de hoy (en memoria: guarda quien llama)."""
    datos["ListaPrecios"] = armar(_internos(datos))
    datos.pop("PreciosRevisados", None)


def mantener(datos: dict) -> None:
    """Se queda con sus precios, y no vuelve a preguntar hasta que los
    precios de hoy cambien otra vez (en memoria: guarda quien llama)."""
    datos["PreciosRevisados"] = firma(armar(_internos(datos)))
