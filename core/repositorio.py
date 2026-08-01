"""
core/repositorio.py
Acceso a los datos de configuración compartida: catálogos (productos,
textiles) y datos editables por el usuario (clientes, contactos). Todo
vive en JSON dentro de Dropbox/SGTD/Conf (ver core.rutas.CONF), para que
sea el mismo dato en todas las instalaciones.
"""

import json
import shutil

from core.rutas import CONF as _CONF_DIR, DATOS as _DATOS_DIR, RECURSOS as _RECURSOS_DIR

SEP = "|"  # separador del viejo formato clientes.txt/contactos.txt (solo para migrar)

CLIENTES_PATH  = _CONF_DIR / "clientes.json"
CONTACTOS_PATH = _CONF_DIR / "contactos.json"


def _parsear_pipe(texto: str, campos: list[str]) -> list[dict]:
    """Parsea el viejo formato 'campo1|campo2|...' de clientes.txt/contactos.txt
    (instalaciones previas a la migración a JSON). Ignora las 2 primeras
    líneas (cabecera) y cualquier campo de más al final de una línea."""
    filas = []
    for i, linea in enumerate(texto.splitlines()):
        if i < 2:
            continue
        linea = linea.strip()
        if not linea:
            continue
        partes = linea.split(SEP)
        if len(partes) >= len(campos):
            filas.append({campo: partes[j].strip() for j, campo in enumerate(campos)})
    return filas


def _migrar_a_conf(nombre: str, campos: list[str] | None = None) -> None:
    """
    Asegura que <nombre>.json exista en la carpeta de configuración
    compartida (Dropbox/SGTD/Conf, o localmente si no hay Dropbox). Si ya
    está ahí no hace nada (puede haberlo dejado otra instalación). Si no,
    busca datos existentes y los copia, en este orden:
    1. <nombre>.json ya migrado localmente en esta máquina (instalaciones
       de la semana pasada, antes de que esto viviera en Dropbox).
    2. <nombre>.txt viejo (formato previo a JSON) — solo para clientes y
       contactos, que son los únicos que llegaron a existir en ese formato.
    3. recursos/<nombre>.json (dato de fábrica), para una instalación
       nueva que nunca tuvo nada de esto.
    """
    destino = _CONF_DIR / f"{nombre}.json"
    if destino.exists():
        return

    local_json = _DATOS_DIR / f"{nombre}.json"
    if local_json.exists():
        shutil.copy2(local_json, destino)
        return

    if campos is not None:
        local_txt = _DATOS_DIR / f"{nombre}.txt"
        if local_txt.exists():
            filas = _parsear_pipe(local_txt.read_text(encoding="utf-8"), campos)
            destino.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
            return

    seed = _RECURSOS_DIR / f"{nombre}.json"
    if seed.exists():
        shutil.copy2(seed, destino)


def _migrar_datos_antiguos():
    _migrar_a_conf("clientes", ["empresa", "rut", "razon_social"])
    _migrar_a_conf("contactos", ["contacto", "email", "fuente", "condicion"])
    _migrar_a_conf("productos")
    _migrar_a_conf("textiles")
    _migrar_a_conf("perfiles")
    _migrar_a_conf("luces")
    _migrar_a_conf("fuentes_poder")
    _migrar_a_conf("estructuras")
    _migrar_a_conf("terminaciones")
    _migrar_a_conf("precios_cajas")


_migrar_datos_antiguos()


def _leer_json(ruta) -> list:
    if not ruta.exists():
        return []
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return []


def _escribir_json(ruta, datos: list) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# Gestión de clientes.json — lista de {empresa, rut, razon_social}
# ══════════════════════════════════════════════════════════════════════════════

def formatear_rut(rut_raw: str) -> str:
    """
    Recibe una cadena con cualquier contenido y devuelve el RUT con formato
    XX.XXX.XXX-X. Solo conserva dígitos y la letra K (dígito verificador).
    """
    chars = "".join(c for c in rut_raw.upper() if c.isdigit() or c == "K")
    if len(chars) < 2:
        return chars  # muy corto para formatear
    cuerpo, dv = chars[:-1], chars[-1]
    # Insertar puntos cada 3 dígitos desde la derecha
    partes = []
    while cuerpo:
        partes.append(cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    cuerpo_fmt = ".".join(reversed(partes))
    return f"{cuerpo_fmt}-{dv}"


def cargar_clientes() -> list[dict]:
    """Lee clientes.json y devuelve lista de dicts {empresa, rut, razon_social}."""
    return _leer_json(CLIENTES_PATH)


def guardar_cliente(empresa: str, rut: str, razon_social: str):
    """Agrega un cliente nuevo a clientes.json si no existe ya."""
    clientes = cargar_clientes()
    for c in clientes:
        if c["empresa"].lower() == empresa.lower():
            return  # ya existe, no duplicar
    clientes.append({"empresa": empresa, "rut": rut, "razon_social": razon_social})
    _escribir_json(CLIENTES_PATH, clientes)


# ══════════════════════════════════════════════════════════════════════════════
# Gestión de contactos.json — lista de {contacto, email, descuento, condicion}
# "descuento" se llamaba "fuente" antes de la cotización con precios — es un
# renombramiento puro, no un campo nuevo (ver ui/formulario_cliente.py).
# ══════════════════════════════════════════════════════════════════════════════

def cargar_contactos() -> list[dict]:
    """Lee contactos.json y devuelve lista de dicts {contacto, email, descuento, condicion}."""
    return _leer_json(CONTACTOS_PATH)


def guardar_contacto(contacto: str, email: str, descuento: str, condicion: str):
    """Agrega un contacto nuevo a contactos.json si no existe ya."""
    contactos = cargar_contactos()
    for c in contactos:
        if c["contacto"].lower() == contacto.lower():
            return  # ya existe, no duplicar
    contactos.append({"contacto": contacto, "email": email, "descuento": descuento, "condicion": condicion})
    _escribir_json(CONTACTOS_PATH, contactos)


# ══════════════════════════════════════════════════════════════════════════════
# Catálogos: productos.json y textiles.json
# Antes vivían empaquetados en recursos/ (de solo lectura, requerían un
# release nuevo para cambiar un producto o una tela). Ahora viven en
# Dropbox/SGTD/Conf junto con clientes/contactos: editar el JSON ahí se
# refleja en todas las instalaciones sin recompilar nada.
# ══════════════════════════════════════════════════════════════════════════════

def cargar_productos() -> list[str]:
    """Lee productos.json: lista de nombres de producto."""
    return _leer_json(_CONF_DIR / "productos.json")


def cargar_textiles() -> tuple[list[str], dict[str, float], dict[str, float]]:
    """
    Lee textiles.json: lista de {nombre, ancho, valor}.
    Devuelve (lista_nombres, dict_anchos, dict_valores). Si un textil no
    trae "ancho" o "valor", se omite del dict correspondiente (no se
    inventa un 0 que rompa validaciones o abarate un cálculo sin querer).
    "valor" es el precio por metro impreso: por ML en productos normales,
    por M² en Backlight (el único que mide su tela en área — ver core/precios.py).
    """
    nombres: list[str] = []
    anchos:  dict[str, float] = {}
    valores: dict[str, float] = {}
    for item in _leer_json(_CONF_DIR / "textiles.json"):
        nombre = str(item.get("nombre", "")).strip()
        if not nombre:
            continue
        nombres.append(nombre)
        if item.get("ancho") is not None:
            try:
                anchos[nombre] = float(item["ancho"])
            except (TypeError, ValueError):
                pass
        if item.get("valor") is not None:
            try:
                valores[nombre] = float(item["valor"])
            except (TypeError, ValueError):
                pass
    return nombres, anchos, valores


PRODUCTOS                                = cargar_productos()
TEXTILES, TEXTILES_ANCHOS, TEXTILES_VALORES = cargar_textiles()


# ══════════════════════════════════════════════════════════════════════════════
# Catálogos de cajas de backlight: perfiles.json, luces.json, fuentes_poder.json
# Usados por core/calculo_cajas.py y por el formulario de caja del cotizador
# backlight. Mismo criterio que productos/textiles: viven en Dropbox/SGTD/Conf,
# editables sin recompilar la app.
# ══════════════════════════════════════════════════════════════════════════════

def cargar_perfiles() -> list[str]:
    """Lee perfiles.json: lista de nombres de perfil de caja."""
    return _leer_json(_CONF_DIR / "perfiles.json")


def cargar_luces() -> list[dict]:
    """Lee luces.json: lista de {corto, largo, medida, watts}."""
    return _leer_json(_CONF_DIR / "luces.json")


def cargar_fuentes_poder() -> list[dict]:
    """Lee fuentes_poder.json: lista de {watts, nombre}, ordenada por watts."""
    datos = _leer_json(_CONF_DIR / "fuentes_poder.json")
    return sorted(datos, key=lambda d: d.get("watts", 0))


def cargar_precios_cajas() -> dict:
    """
    Lee precios_cajas.json: precios CLP para el cálculo de valor de una
    caja de backlight (ver core/valor_cajas.py). Estructura:
    {"luces": {corto: precio_unidad}, "traseras": {tipo: precio_plancha},
     "armado": {tramo: tarifa_por_ml}, "fp": {watts: precio_unidad},
     "perfiles": {nombre: tarifa_por_ml}, "pintura_por_ml": precio}.
    Los watts de "fp" vienen como texto en el JSON (las claves de un objeto
    JSON siempre son string) — se convierten a int acá para poder buscar
    directo por el "watts_unidad" que devuelve calculo_cajas.seleccionar_fp.
    """
    datos = _leer_json(_CONF_DIR / "precios_cajas.json")
    if not isinstance(datos, dict):
        datos = {}
    resultado = {
        "luces":     datos.get("luces", {}),
        "traseras":  datos.get("traseras", {}),
        "armado":    datos.get("armado", {}),
        "fp":        {int(k): v for k, v in datos.get("fp", {}).items()},
        "perfiles":  datos.get("perfiles", {}),
        "pintura_por_ml": datos.get("pintura_por_ml", 0.0),
    }
    return resultado


PERFILES       = cargar_perfiles()
LUCES          = cargar_luces()
FUENTES_PODER  = cargar_fuentes_poder()
PRECIOS_CAJAS  = cargar_precios_cajas()


# ══════════════════════════════════════════════════════════════════════════════
# Catálogos de estructuras.json y terminaciones.json — solo para productos
# NO backlight (esos productos pueden tener estructura y/o terminación;
# los backlight usan su propia Caja, ver calculo_cajas.py).
# ══════════════════════════════════════════════════════════════════════════════

def cargar_estructuras() -> tuple[list[str], dict[str, dict]]:
    """
    Lee estructuras.json: lista de {nombre, valorML} o {nombre, valorUNIT}.
    Devuelve (lista_nombres, dict_valores) — dict_valores mapea nombre a
    {"valorML": x} o {"valorUNIT": x} según cuál traiga esa entrada (ver
    core/precios.py para cómo se usa cada uno). Tolera también el formato
    viejo (lista de strings, sin precio) por si esta máquina no alcanzó a
    sincronizar el catálogo nuevo — esas entradas quedan sin precio (se
    tratan como $0) en vez de romper la carga de toda la app.
    """
    nombres: list[str] = []
    valores: dict[str, dict] = {}
    for item in _leer_json(_CONF_DIR / "estructuras.json"):
        if isinstance(item, str):
            nombre = item.strip()
            if nombre:
                nombres.append(nombre)
            continue
        nombre = str(item.get("nombre", "")).strip()
        if not nombre:
            continue
        nombres.append(nombre)
        if "valorML" in item:
            valores[nombre] = {"valorML": float(item["valorML"])}
        elif "valorUNIT" in item:
            valores[nombre] = {"valorUNIT": float(item["valorUNIT"])}
    return nombres, valores


def cargar_terminaciones() -> tuple[list[str], dict[str, float]]:
    """
    Lee terminaciones.json: lista de {nombre, valor} (precio por ML impreso).
    Devuelve (lista_nombres, dict_valores). Tolera el formato viejo (lista
    de strings, sin precio) — ver cargar_estructuras."""
    nombres: list[str] = []
    valores: dict[str, float] = {}
    for item in _leer_json(_CONF_DIR / "terminaciones.json"):
        if isinstance(item, str):
            nombre = item.strip()
            if nombre:
                nombres.append(nombre)
            continue
        nombre = str(item.get("nombre", "")).strip()
        if not nombre:
            continue
        nombres.append(nombre)
        if item.get("valor") is not None:
            try:
                valores[nombre] = float(item["valor"])
            except (TypeError, ValueError):
                pass
    return nombres, valores


ESTRUCTURAS, ESTRUCTURAS_VALORES      = cargar_estructuras()
TERMINACIONES, TERMINACIONES_VALORES  = cargar_terminaciones()


# ══════════════════════════════════════════════════════════════════════════════
# Catálogos LEGADO (demo/comparación, ver core.precios.costo_producto
# modelo="legado") — transcripción directa de la lista de precios vieja
# (un solo Excel con 100+ combinaciones producto+estructura+terminación, cada
# una con su propio precio). A diferencia de ESTRUCTURAS/TERMINACIONES (que
# son piezas reusables que se suman aditivamente), acá cada entrada es el
# nombre compuesto completo tal como aparecía en el Excel viejo, con su valor
# fijo por unidad. Viven en recursos/ (no en Dropbox/SGTD/Conf): son solo
# para comparar contra el modelo aditivo nuevo, no es catálogo en uso real.
# ══════════════════════════════════════════════════════════════════════════════

def _cargar_legado(nombre_archivo: str) -> tuple[list[str], dict[str, float]]:
    """Lee un catálogo legado (mismo formato {nombre, valor} que
    terminaciones.json) desde recursos/, no desde Dropbox/SGTD/Conf."""
    nombres: list[str] = []
    valores: dict[str, float] = {}
    for item in _leer_json(_RECURSOS_DIR / nombre_archivo):
        nombre = str(item.get("nombre", "")).strip()
        if not nombre:
            continue
        nombres.append(nombre)
        if item.get("valor") is not None:
            try:
                valores[nombre] = float(item["valor"])
            except (TypeError, ValueError):
                pass
    return nombres, valores


def cargar_estructuras_legado() -> tuple[list[str], dict[str, float]]:
    """recursos/estructuras_legado.json — ver _cargar_legado."""
    return _cargar_legado("estructuras_legado.json")


def cargar_terminaciones_legado() -> tuple[list[str], dict[str, float]]:
    """recursos/terminaciones_legado.json — ver _cargar_legado."""
    return _cargar_legado("terminaciones_legado.json")


ESTRUCTURAS_LEGADO, ESTRUCTURAS_LEGADO_VALORES      = cargar_estructuras_legado()
TERMINACIONES_LEGADO, TERMINACIONES_LEGADO_VALORES  = cargar_terminaciones_legado()
