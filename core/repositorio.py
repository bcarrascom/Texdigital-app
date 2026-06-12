"""
core/repositorio.py
Acceso a los datos persistentes de la app: catálogos (productos, textiles)
y datos editables por el usuario (clientes, contactos).
"""

import shutil

from core.rutas import DATOS as _DATOS_DIR, RECURSOS as _RECURSOS_DIR

SEP = "|"

CLIENTES_PATH  = _DATOS_DIR / "clientes.txt"
CONTACTOS_PATH = _DATOS_DIR / "contactos.txt"


def _migrar_datos_antiguos():
    """
    Si los archivos de datos existen en la carpeta de recursos (ubicación antigua)
    y NO existen todavía en la carpeta de datos del usuario (ubicación nueva),
    los copia automáticamente. Esto permite la transición tras actualizar.
    """
    for nombre in ("clientes.txt", "contactos.txt"):
        origen  = _RECURSOS_DIR / nombre
        destino = _DATOS_DIR    / nombre
        if origen.exists() and not destino.exists():
            shutil.copy2(origen, destino)


_migrar_datos_antiguos()


# ══════════════════════════════════════════════════════════════════════════════
# Gestión de clientes.txt
# Formato por línea:  Empresa|Rut|Razon Social
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
    """Lee clientes.txt y devuelve lista de dicts {empresa, rut, razon_social}."""
    clientes = []
    if not CLIENTES_PATH.exists():
        return clientes
    with open(CLIENTES_PATH, encoding="utf-8") as f:
        for i, linea in enumerate(f):
            if i < 2:  # Ignore first 2 lines
                continue
            linea = linea.strip()
            if not linea:
                continue
            partes = linea.split(SEP)
            if len(partes) >= 3:
                clientes.append({
                    "empresa":      partes[0].strip(),
                    "rut":          partes[1].strip(),
                    "razon_social": partes[2].strip(),
                })
    return clientes


def guardar_cliente(empresa: str, rut: str, razon_social: str):
    """Agrega un cliente nuevo a clientes.txt si no existe ya."""
    clientes = cargar_clientes()
    # Verificar que no exista ya (por nombre de empresa)
    for c in clientes:
        if c["empresa"].lower() == empresa.lower():
            return  # ya existe, no duplicar
    with open(CLIENTES_PATH, "a", encoding="utf-8") as f:
        f.write(f"{empresa}{SEP}{rut}{SEP}{razon_social}\n")


# ══════════════════════════════════════════════════════════════════════════════
# Gestión de contactos.txt
# Formato por línea:  Contacto|Email|Fuente|Condicion
# ══════════════════════════════════════════════════════════════════════════════

def cargar_contactos() -> list[dict]:
    """Lee contactos.txt y devuelve lista de dicts {contacto, email, fuente, condicion}."""
    contactos = []
    if not CONTACTOS_PATH.exists():
        return contactos
    with open(CONTACTOS_PATH, encoding="utf-8") as f:
        for i, linea in enumerate(f):
            if i < 2:  # Ignorar las 2 primeras líneas de cabecera
                continue
            linea = linea.strip()
            if not linea:
                continue
            partes = linea.split(SEP)
            if len(partes) >= 4:
                contactos.append({
                    "contacto":  partes[0].strip(),
                    "email":     partes[1].strip(),
                    "fuente":    partes[2].strip(),
                    "condicion": partes[3].strip(),
                })
    return contactos


def guardar_contacto(contacto: str, email: str, fuente: str, condicion: str):
    """Agrega un contacto nuevo a contactos.txt si no existe ya."""
    contactos = cargar_contactos()
    for c in contactos:
        if c["contacto"].lower() == contacto.lower():
            return  # ya existe, no duplicar
    if not CONTACTOS_PATH.exists():
        with open(CONTACTOS_PATH, "w", encoding="utf-8") as f:
            f.write("# Archivo de contactos\n")
            f.write("# contacto|email|fuente|condicion\n")
    with open(CONTACTOS_PATH, "a", encoding="utf-8") as f:
        f.write(f"{contacto}{SEP}{email}{SEP}{fuente}{SEP}{condicion}\n")


# ══════════════════════════════════════════════════════════════════════════════
# Catálogos de solo lectura: productos.txt y textiles.txt
# ══════════════════════════════════════════════════════════════════════════════

def _cargar_lista(nombre: str) -> list[str]:
    ruta = _RECURSOS_DIR / nombre
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def cargar_productos() -> list[str]:
    return _cargar_lista("productos.txt")


def cargar_textiles() -> tuple[list[str], dict[str, float]]:
    """
    Lee textiles.txt con formato  'Nombre | ancho_max'.
    Devuelve (lista_nombres, dict_anchos).
    Si una línea no tiene '|', se agrega el nombre sin restricción de ancho.
    """
    ruta = _RECURSOS_DIR / "textiles.txt"
    nombres: list[str] = []
    anchos:  dict[str, float] = {}
    if not ruta.exists():
        return nombres, anchos
    with open(ruta, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                partes = line.split("|", 1)
                nombre = partes[0].strip()
                try:
                    ancho = float(partes[1].strip())
                    anchos[nombre] = ancho
                except ValueError:
                    pass
                nombres.append(nombre)
            else:
                nombres.append(line)
    return nombres, anchos


PRODUCTOS                  = cargar_productos()
TEXTILES, TEXTILES_ANCHOS  = cargar_textiles()
