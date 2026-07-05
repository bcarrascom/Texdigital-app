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
# Gestión de contactos.json — lista de {contacto, email, fuente, condicion}
# ══════════════════════════════════════════════════════════════════════════════

def cargar_contactos() -> list[dict]:
    """Lee contactos.json y devuelve lista de dicts {contacto, email, fuente, condicion}."""
    return _leer_json(CONTACTOS_PATH)


def guardar_contacto(contacto: str, email: str, fuente: str, condicion: str):
    """Agrega un contacto nuevo a contactos.json si no existe ya."""
    contactos = cargar_contactos()
    for c in contactos:
        if c["contacto"].lower() == contacto.lower():
            return  # ya existe, no duplicar
    contactos.append({"contacto": contacto, "email": email, "fuente": fuente, "condicion": condicion})
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


def cargar_textiles() -> tuple[list[str], dict[str, float]]:
    """
    Lee textiles.json: lista de {nombre, ancho}.
    Devuelve (lista_nombres, dict_anchos). Si un textil no trae "ancho",
    se agrega el nombre sin restricción de ancho.
    """
    nombres: list[str] = []
    anchos:  dict[str, float] = {}
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
    return nombres, anchos


PRODUCTOS                  = cargar_productos()
TEXTILES, TEXTILES_ANCHOS  = cargar_textiles()
