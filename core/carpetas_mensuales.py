"""
core/carpetas_mensuales.py
Helper genérico para carpetas que guardan JSON en subcarpetas AAAA/MM según
un campo de fecha del propio archivo — usado por core/repositorio_ops.py
(Fecha_ingreso) y core/repositorio_cotizaciones.py (Fecha). El motivo es
poder listar/filtrar por mes puntual sin tener que abrir los archivos de
los demás meses: elegir un año/mes es solo listar una subcarpeta.
"""

import json
from datetime import datetime
from pathlib import Path

FORMATO_FECHA = "%d/%m/%Y"


def anio_mes(datos: dict, campo_fecha: str, formato: str = FORMATO_FECHA) -> tuple[int, int]:
    """Año/mes desde `datos[campo_fecha]` ("dd/mm/aaaa"). Si falta o no se
    puede leer (dato viejo/corrupto), usa la fecha de hoy — mejor que
    reventar la migración/el guardado por un solo archivo con problemas."""
    try:
        fecha = datetime.strptime(datos[campo_fecha], formato)
        return fecha.year, fecha.month
    except Exception:
        hoy = datetime.now()
        return hoy.year, hoy.month


def subcarpeta_mes(base: Path, anio: int, mes: int) -> Path:
    p = base / f"{anio:04d}" / f"{mes:02d}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def migrar_archivos_planos(base: Path, campo_fecha: str, formato: str = FORMATO_FECHA) -> None:
    """Migración de JSON sueltos directo en `base` (formato de antes de
    AAAA/MM) a su subcarpeta correspondiente. Segura de llamar siempre:
    una vez migrados, el glob no-recursivo de acá no encuentra nada."""
    for archivo in base.glob("*.json"):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except Exception:
            continue
        anio, mes = anio_mes(datos, campo_fecha, formato)
        destino = subcarpeta_mes(base, anio, mes) / archivo.name
        archivo.replace(destino)


def buscar(carpeta: Path, numero: int) -> Path | None:
    """Ubica el JSON de `numero` dentro de `carpeta`, sin saber de
    antemano en qué subcarpeta AAAA/MM está."""
    return next(carpeta.rglob(f"{numero}.json"), None)


def mover_preservando_mes(origen_carpeta: Path, destino_carpeta: Path, numero: int) -> Path | None:
    """Mueve manteniendo la misma subcarpeta AAAA/MM relativa (la fecha
    que decide el mes no cambia al mover un archivo entre carpetas de
    ciclo de vida). Devuelve la ruta destino, o None si no se encontró."""
    origen = buscar(origen_carpeta, numero)
    if origen is None:
        return None
    relativo = origen.relative_to(origen_carpeta)
    destino = destino_carpeta / relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    origen.replace(destino)
    return destino


def eliminar(carpetas: list[Path], numero: int) -> bool:
    """Busca `numero` en cualquiera de `carpetas` y lo borra. Devuelve
    True si encontró y borró algo."""
    for carpeta in carpetas:
        ruta = buscar(carpeta, numero)
        if ruta is not None:
            ruta.unlink()
            return True
    return False


def listar_meses_disponibles(carpetas: list[Path]) -> list[tuple[int, int]]:
    """(año, mes) únicos con al menos un archivo, entre varias carpetas
    base. Solo lista nombres de subcarpeta, no abre ningún JSON."""
    metas = set()
    for base in carpetas:
        if not base.is_dir():
            continue
        for dir_anio in base.iterdir():
            if not (dir_anio.is_dir() and dir_anio.name.isdigit()):
                continue
            for dir_mes in dir_anio.iterdir():
                if dir_mes.is_dir() and dir_mes.name.isdigit():
                    metas.add((int(dir_anio.name), int(dir_mes.name)))
    return sorted(metas)


def listar_archivos_del_mes(
    carpetas_con_etiqueta: list[tuple[Path, str]], anio: int, mes: int
) -> list[tuple[dict, str]]:
    """[(datos, etiqueta), ...] de un año/mes puntual, juntando varias
    carpetas base (cada una con su propia etiqueta de origen). Solo abre
    los archivos de ese mes — el resto queda sin tocar."""
    resultado = []
    for base, etiqueta in carpetas_con_etiqueta:
        carpeta = base / f"{anio:04d}" / f"{mes:02d}"
        if not carpeta.is_dir():
            continue
        for archivo in carpeta.glob("*.json"):
            try:
                datos = json.loads(archivo.read_text(encoding="utf-8"))
            except Exception:
                continue
            resultado.append((datos, etiqueta))
    return resultado


def restar_meses(anio: int, mes: int, cantidad: int) -> tuple[int, int]:
    """(año, mes) resultante de retroceder `cantidad` meses desde
    (anio, mes) — con acarreo de año (ej. 2026-01 menos 1 mes = 2025-12)."""
    indice = (anio * 12 + (mes - 1)) - cantidad
    return indice // 12, indice % 12 + 1
