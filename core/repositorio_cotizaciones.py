"""
core/repositorio_cotizaciones.py
Persistencia de cotizaciones como JSON en la carpeta Dropbox compartida.
Fallback a AppData si Dropbox Desktop no está instalado.
"""

import json
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox
from core.repositorio import TEXTILES_ANCHOS


def _ruta_base() -> Path:
    dropbox = _detectar_dropbox()
    if dropbox:
        return dropbox / "SGTD" / "Cotizaciones"
    return DATOS / "Cotizaciones"


def carpeta_cotizaciones() -> Path:
    """Carpeta raíz de Cotizaciones (contiene JSON/Excel/Historial/HTML) —
    para el botón "abrir carpeta" de Revisar Cotizaciones."""
    p = _ruta_base()
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_json() -> Path:
    p = _ruta_base() / "JSON"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_excel() -> Path:
    p = _ruta_base() / "Excel"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_historial() -> Path:
    p = _ruta_base() / "Historial"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_html() -> Path:
    p = _ruta_base() / "HTML"
    p.mkdir(parents=True, exist_ok=True)
    return p


def siguiente_numero() -> int:
    """Devuelve max(números existentes) + 1, o 1000 si no hay ninguno.

    Revisa cotizaciones Y OPs (activas e historial), porque una OP puede
    tener un número más alto que las cotizaciones activas (su cotización de
    origen ya pasó a Historial), y reusar ese número causaría un choque.
    """
    from core import repositorio_ops

    carpetas = [
        carpeta_json(),
        carpeta_historial(),
        repositorio_ops.carpeta_json(),
        repositorio_ops.carpeta_historial(),
    ]
    numeros = []
    for carpeta in carpetas:
        for archivo in carpeta.glob("*.json"):
            try:
                numeros.append(int(archivo.stem))
            except ValueError:
                pass
    return max(numeros) + 1 if numeros else 1000


def cargar_cotizacion(numero: int) -> dict | None:
    """Lee el JSON de una cotización guardada por número, o None si no existe."""
    ruta = carpeta_json() / f"{numero}.json"
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return None


def guardar_cotizacion(datos: dict) -> Path:
    """Guarda datos como JSON. Sobreescribe si ya existe el número."""
    numero = datos["Cotizacion"]
    destino = carpeta_json() / f"{numero}.json"
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def mover_a_historial(numero: int) -> None:
    """Mueve el JSON de la cotización aprobada de JSON/ a Historial/."""
    origen = carpeta_json() / f"{numero}.json"
    if origen.exists():
        origen.replace(carpeta_historial() / origen.name)


def eliminar_excel(numero: int) -> None:
    """Elimina el Excel de la cotización aprobada (ya no se necesita)."""
    for nombre in (f"Cotización {numero:04d}.xlsx", f"Cotización {numero}.xlsx"):
        p = carpeta_excel() / nombre
        if p.exists():
            p.unlink()
            break


# ══════════════════════════════════════════════════════════════════════════════
# Esquema de producto: dict interno (usado por las pantallas del cotizador)
# ↔ esquema JSON (guardado en cotizaciones y OPs). Vive acá (no en ui/) para
# que tanto la UI como core/presentar_cotizacion.py puedan reusarlo sin que
# core/ termine dependiendo de ui/.
# ══════════════════════════════════════════════════════════════════════════════

def mapear_producto(d: dict) -> dict:
    """Convierte un dict interno de producto al esquema JSON de cotización/OP."""
    if "tela" in d:
        return {
            "Tela":     d.get("tela", ""),
            "Caja":     d.get("caja", ""),
            "Ancho":    float(d.get("ancho", 0.0)),
            "Alto":     float(d.get("alto", 0.0)),
            "Cantidad": int(d.get("cantidad", 0)),
            "Tema":     d.get("tema", ""),
            "Obs":      d.get("obs", ""),
        }
    return {
        "producto":      d.get("producto", ""),
        "Tela":          d.get("textil", ""),
        "Estructuras":   list(d.get("estructuras", [])),
        "Terminaciones": list(d.get("terminaciones", [])),
        "Impresion":     d.get("impresion", "Cara única"),
        "Ancho":         float(d.get("ancho", 0.0)),
        "Alto":          float(d.get("alto", 0.0)),
        "Cantidad":      int(d.get("cantidad", 0)),
        "Tema":          d.get("tema", ""),
        "Obs":           d.get("obs", ""),
    }


def _migrar_lista(d: dict, clave_lista: str, clave_vieja: str, placeholder: str) -> list[str]:
    """Cotizaciones guardadas antes del modelo aditivo traían una sola
    Estructura/Terminación como string (clave_vieja); esto la convierte a
    lista de un elemento, o lista vacía si era el placeholder ("Sin
    estructura"/"Sin terminaciones"). Si ya viene en formato lista
    (clave_lista, cotizaciones nuevas) se usa directo."""
    if clave_lista in d:
        return list(d[clave_lista])
    valor = str(d.get(clave_vieja, "")).strip()
    if not valor or valor.lower() == placeholder.lower():
        return []
    return [valor]


def producto_desde_json(d: dict) -> dict:
    """Inversa de `mapear_producto`: convierte un producto en esquema JSON
    de vuelta al esquema interno que usan las pantallas de edición."""
    if "Caja" in d:
        return {
            "tela":      d.get("Tela", ""),
            "caja":      d.get("Caja", ""),
            "ancho_max": TEXTILES_ANCHOS.get(d.get("Tela", ""), 0.0),
            "ancho":     d.get("Ancho", 0.0),
            "alto":      d.get("Alto", 0.0),
            "cantidad":  d.get("Cantidad", 0),
            "tema":      d.get("Tema", ""),
            "obs":       d.get("Obs", ""),
            "rotado":    False,
        }
    return {
        "producto":      d.get("producto", ""),
        "textil":        d.get("Tela", ""),
        "estructuras":   _migrar_lista(d, "Estructuras", "Estructura", "Sin estructura"),
        "terminaciones": _migrar_lista(d, "Terminaciones", "Terminacion", "Sin terminaciones"),
        "impresion":     d.get("Impresion", "Cara única"),
        "ancho":         d.get("Ancho", 0.0),
        "alto":          d.get("Alto", 0.0),
        "cantidad":      d.get("Cantidad", 0),
        "tema":          d.get("Tema", ""),
        "obs":           d.get("Obs", ""),
    }
