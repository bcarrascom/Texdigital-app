"""
core/repositorio.py
Acceso a los datos de configuración: catálogos de referencia (productos,
textiles, perfiles, luces, fuentes de poder, precios de cajas, estructuras,
terminaciones) y datos editables por el usuario (clientes, contactos).

Los catálogos de referencia son de SOLO LECTURA y viven empaquetados en
recursos/ (ver core.rutas.RECURSOS) — cambiar un precio o agregar un ítem
requiere editar el JSON en el repo y sacar un release nuevo, igual que
cualquier otro cambio de código. Antes vivían en Dropbox/SGTD/Conf,
editables en caliente sin recompilar; se volvió a recursos/ para que el
valor que usa cada instalación sea exactamente el que se probó y se
versionó con esa versión de la app — un precio mal escrito a mano en
Dropbox (ver el caso real de "Denim crudo 6 onzas" sin "valor") ya no
puede quedar syncrhonizado silenciosamente a todas las instalaciones sin
pasar por revisión.

clientes.json y contactos.json SÍ siguen en Dropbox/SGTD/Conf (ver
core.rutas.CONF) — no son catálogos de referencia, son datos que el
operador va agregando en el día a día (clientes/contactos nuevos), y
recursos/ es de solo lectura: no se le puede "agregar un cliente" a un
archivo empaquetado con el instalador.
"""

import json
import shutil
import uuid

from core.rutas import CONF as _CONF_DIR, DATOS as _DATOS_DIR, RECURSOS as _RECURSOS_DIR

SEP = "|"  # separador del viejo formato clientes.txt/contactos.txt (solo para migrar)

CLIENTES_PATH     = _CONF_DIR / "clientes.json"
CONTACTOS_PATH    = _CONF_DIR / "contactos.json"
# Direcciones de despacho — archivo APARTE de clientes.json: un cliente
# puede tener varias direcciones (bodega, casa matriz, obra, ...), así que
# cada una es su propia entrada acá, ligada al cliente por RUT (ver
# módulo Despachos, core/repositorio_despachos.py).
DIRECCIONES_PATH  = _CONF_DIR / "direcciones.json"
# Preferencias de interfaz (ej. escala_ui, la A-/A+ de las pantallas HTML
# nuevas): en DATOS (local por máquina), NO en CONF — es una preferencia
# personal de quien usa esta instalación, no un dato de negocio compartido
# por Dropbox (si viviera en Conf, alguien agrandando su letra se la
# agrandaría a todo el mundo).
PREFERENCIAS_PATH = _DATOS_DIR / "preferencias.json"


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
    # Solo clientes/contactos — son datos que el operador agrega, no
    # catálogos de referencia (esos se leen directo de recursos/, ver
    # docstring del módulo, no necesitan copiarse a Conf).
    _migrar_a_conf("clientes", ["empresa", "rut", "razon_social"])
    _migrar_a_conf("contactos", ["contacto", "email", "fuente", "condicion"])
    _migrar_a_conf("direcciones")  # archivo nuevo, sin formato .txt legado


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


def guardar_cliente(empresa: str, rut: str, razon_social: str) -> bool:
    """Agrega un cliente nuevo a clientes.json si no existe ya (dedup por
    empresa). El RUT es el identificador interno real de un cliente — dos
    empresas no pueden compartir uno (ver grupo "Direcciones de <cliente>"
    en asignar-despacho.html, que agrupa las direcciones justamente por
    RUT: si dos clientes lo compartieran, cada uno vería las direcciones
    del otro mezcladas ahí). Devuelve False sin guardar nada si el RUT ya
    está registrado a nombre de OTRA empresa — nueva-cotizacion.html le
    avisa al usuario en ese caso. Si el cliente ya existe tal cual (mismo
    nombre de empresa — el caso común de volver a guardar una cotización
    de un cliente ya guardado) no hace nada pero devuelve True: no es un
    conflicto, es un no-op esperado."""
    clientes = cargar_clientes()
    for c in clientes:
        if c["empresa"].lower() == empresa.lower():
            return True  # ya existe, no duplicar — no es un error
    rut_fmt = formatear_rut(rut or "")
    if rut_fmt and any(formatear_rut(c.get("rut", "")) == rut_fmt for c in clientes):
        return False  # RUT ya usado por otra empresa
    clientes.append({"empresa": empresa, "rut": rut, "razon_social": razon_social})
    _escribir_json(CLIENTES_PATH, clientes)
    return True


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
# Gestión de direcciones.json — lista de direcciones de despacho, ligadas a
# un cliente por RUT (un cliente puede tener varias). Ningún campo de la
# dirección en sí (calle, número, comuna, región) es obligatorio — solo el
# RUT importa para poder encontrarlas de nuevo (ver core/repositorio_despachos.py).
# ══════════════════════════════════════════════════════════════════════════════

def cargar_direcciones() -> list[dict]:
    """Lee direcciones.json: lista de
    {id, rut, empresa, alias, calle, numero, comuna, region, referencia}.
    Las direcciones guardadas antes de que existiera "id" (ver
    editar_direccion/eliminar_direccion, que lo necesitan para saber cuál es
    cuál) lo reciben acá mismo, la primera vez que se leen — así no hace
    falta una migración aparte."""
    direcciones = _leer_json(DIRECCIONES_PATH)
    faltan_ids = False
    for d in direcciones:
        if not d.get("id"):
            d["id"] = uuid.uuid4().hex
            faltan_ids = True
    if faltan_ids:
        _escribir_json(DIRECCIONES_PATH, direcciones)
    return direcciones


def direcciones_de_cliente(rut: str) -> list[dict]:
    """Direcciones guardadas para un RUT puntual (normalizado con
    formatear_rut, para que no importe cómo se haya escrito antes)."""
    rut_fmt = formatear_rut(rut or "")
    return [d for d in cargar_direcciones() if formatear_rut(d.get("rut", "")) == rut_fmt]


def guardar_direccion(
    rut: str, empresa: str, alias: str = "", calle: str = "", numero: str = "",
    comuna: str = "", region: str = "", codigo_postal: str = "", referencia: str = "",
) -> dict:
    """Agrega una dirección nueva a direcciones.json si no existe ya (dedup
    por rut+calle+numero, en minúsculas — mismo criterio que guardar_cliente).
    calle/numero/comuna/region son los únicos campos obligatorios en la
    pantalla (ver ui/api_asignar_despacho.py); código postal y referencia
    quedan opcionales incluso a nivel de datos. Devuelve la dirección ya
    guardada (o la existente, si era un duplicado) con su "id"."""
    direcciones = cargar_direcciones()
    rut_fmt = formatear_rut(rut or "")
    for d in direcciones:
        if (
            formatear_rut(d.get("rut", "")) == rut_fmt
            and d.get("calle", "").strip().lower() == calle.strip().lower()
            and d.get("numero", "").strip().lower() == numero.strip().lower()
        ):
            return d  # ya existe, no duplicar
    nueva = {
        "id": uuid.uuid4().hex,
        "rut": rut_fmt, "empresa": empresa, "alias": alias,
        "calle": calle, "numero": numero, "comuna": comuna,
        "region": region, "codigo_postal": codigo_postal, "referencia": referencia,
    }
    direcciones.append(nueva)
    _escribir_json(DIRECCIONES_PATH, direcciones)
    return nueva


def editar_direccion(id_: str, **campos) -> dict | None:
    """Sobreescribe los campos de la dirección `id_` (cliente/gestión de
    direcciones, ver ui/api_gestionar_direcciones.py) — NO toca las OPs de
    Despachos que ya tengan esta dirección asignada a algún producto: ahí
    queda una COPIA hecha en el momento de asignar (ver
    core.repositorio_despachos.asignar_direccion_productos), no una
    referencia viva. Devuelve la dirección actualizada, o None si `id_` no
    existe."""
    direcciones = cargar_direcciones()
    for d in direcciones:
        if d.get("id") == id_:
            if "rut" in campos:
                campos["rut"] = formatear_rut(campos["rut"] or "")
            d.update(campos)
            _escribir_json(DIRECCIONES_PATH, direcciones)
            return d
    return None


def eliminar_direccion(id_: str) -> bool:
    """Borra la dirección `id_` de direcciones.json — mismo criterio que
    editar_direccion sobre las OPs que ya la tengan asignada: no se tocan,
    quedan con su copia. Devuelve True si encontró y borró algo."""
    direcciones = cargar_direcciones()
    nuevas = [d for d in direcciones if d.get("id") != id_]
    if len(nuevas) == len(direcciones):
        return False
    _escribir_json(DIRECCIONES_PATH, nuevas)
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Preferencias de interfaz — local por máquina, ver PREFERENCIAS_PATH.
# Formato libre {clave: valor} (no una lista, a diferencia de clientes/
# contactos) — hoy solo guarda "escala_ui", pero cualquier pantalla nueva
# puede sumar una clave propia sin tocar este módulo.
# ══════════════════════════════════════════════════════════════════════════════

def cargar_preferencias() -> dict:
    """Lee preferencias.json. {} si no existe o está corrupto (nunca
    revienta el arranque de una pantalla por esto)."""
    if not PREFERENCIAS_PATH.exists():
        return {}
    try:
        datos = json.loads(PREFERENCIAS_PATH.read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except Exception:
        return {}


def guardar_preferencia(clave: str, valor) -> None:
    """Escribe una preferencia, preservando las demás ya guardadas."""
    preferencias = cargar_preferencias()
    preferencias[clave] = valor
    PREFERENCIAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREFERENCIAS_PATH.write_text(
        json.dumps(preferencias, ensure_ascii=False, indent=2), encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# Catálogos: productos.json y textiles.json — de solo lectura, ver docstring
# del módulo (viven en recursos/, no en Dropbox/SGTD/Conf).
# ══════════════════════════════════════════════════════════════════════════════

def cargar_productos() -> list[str]:
    """Lee productos.json: lista de nombres de producto."""
    return _leer_json(_RECURSOS_DIR / "productos.json")


def cargar_regiones() -> list[str]:
    """Lee regiones.json: las 16 regiones de Chile, para el selector de
    región del módulo Despachos. "Región Metropolitana" (el nombre exacto)
    es el que se compara para decidir si una dirección es de RM o no —
    ver ui/api_menu.py y la tarjeta del menú en recursos/pantallas/menu.html."""
    return _leer_json(_RECURSOS_DIR / "regiones.json")


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
    for item in _leer_json(_RECURSOS_DIR / "textiles.json"):
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
# backlight. De solo lectura, ver docstring del módulo (recursos/, no Conf).
# ══════════════════════════════════════════════════════════════════════════════

def cargar_perfiles() -> list[str]:
    """Lee perfiles.json: lista de nombres de perfil de caja."""
    return _leer_json(_RECURSOS_DIR / "perfiles.json")


def cargar_luces() -> list[dict]:
    """Lee luces.json: lista de {corto, largo, medida, watts}."""
    return _leer_json(_RECURSOS_DIR / "luces.json")


def cargar_fuentes_poder() -> list[dict]:
    """Lee fuentes_poder.json: lista de {watts, nombre}, ordenada por watts."""
    datos = _leer_json(_RECURSOS_DIR / "fuentes_poder.json")
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
    datos = _leer_json(_RECURSOS_DIR / "precios_cajas.json")
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
# los backlight usan su propia Caja, ver calculo_cajas.py). De solo lectura,
# ver docstring del módulo (recursos/, no Conf).
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
    for item in _leer_json(_RECURSOS_DIR / "estructuras.json"):
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
    for item in _leer_json(_RECURSOS_DIR / "terminaciones.json"):
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
# Catálogos LEGADO (ver core.precios.costo_producto modelo="legado", el
# modelo PRINCIPAL/default) — transcripción directa de la lista de precios
# vieja (un solo Excel con 100+ combinaciones producto+estructura+
# terminación, cada una con su propio precio). A diferencia de ESTRUCTURAS/
# TERMINACIONES (aditivo/"Neo"), acá cada entrada es el nombre compuesto
# completo tal como aparecía en el Excel viejo. Casi todas son por unidad
# (valorUNIT × Cantidad efectiva), pero algunas son por ML impreso
# (valorML × ml_facturable) — mismo mecanismo que ya usa cargar_estructuras()
# para el modelo aditivo. Viven en recursos/ (no en Dropbox/SGTD/Conf).
# ══════════════════════════════════════════════════════════════════════════════

def _cargar_legado(nombre_archivo: str) -> tuple[list[str], dict[str, dict]]:
    """Lee un catálogo legado desde recursos/ (no desde Dropbox/SGTD/Conf):
    lista de {nombre, valor} (por unidad) o {nombre, valorML} (por ML
    impreso). Devuelve (lista_nombres, dict_valores) — dict_valores mapea
    nombre a {"valorUNIT": x} o {"valorML": x}, igual formato que
    cargar_estructuras() (ver core/precios.py para cómo se usa cada uno)."""
    nombres: list[str] = []
    valores: dict[str, dict] = {}
    for item in _leer_json(_RECURSOS_DIR / nombre_archivo):
        nombre = str(item.get("nombre", "")).strip()
        if not nombre:
            continue
        nombres.append(nombre)
        if item.get("valorML") is not None:
            try:
                valores[nombre] = {"valorML": float(item["valorML"])}
            except (TypeError, ValueError):
                pass
        elif item.get("valor") is not None:
            try:
                valores[nombre] = {"valorUNIT": float(item["valor"])}
            except (TypeError, ValueError):
                pass
    return nombres, valores


def cargar_estructuras_legado() -> tuple[list[str], dict[str, dict]]:
    """recursos/estructuras_legado.json — ver _cargar_legado."""
    return _cargar_legado("estructuras_legado.json")


def cargar_terminaciones_legado() -> tuple[list[str], dict[str, dict]]:
    """recursos/terminaciones_legado.json — ver _cargar_legado."""
    return _cargar_legado("terminaciones_legado.json")


ESTRUCTURAS_LEGADO, ESTRUCTURAS_LEGADO_VALORES      = cargar_estructuras_legado()
TERMINACIONES_LEGADO, TERMINACIONES_LEGADO_VALORES  = cargar_terminaciones_legado()
