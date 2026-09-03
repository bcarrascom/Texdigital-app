"""
core/repositorio_cotizaciones.py
Persistencia de cotizaciones como JSON en la carpeta Dropbox compartida.
Fallback a AppData si Dropbox Desktop no está instalado.

JSON/ y Historial/ guardan cada cotización en una subcarpeta AAAA/MM según
su campo "Fecha" (la fecha de creación de la cotización) — mismo mecanismo
que las OPs (ver core/repositorio_ops.py y core/carpetas_mensuales.py),
para que "Buscar cotización" desde el historial de OPs (ui/historial_ops.py)
pueda ubicar la cotización de origen de una OP mirando solo un puñado de
meses, no todo Historial/.
"""

import json
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox
from core.repositorio import TEXTILES_ANCHOS
from core.precios import costo_cotizacion
from core import carpetas_mensuales as cm

_CAMPO_FECHA = "Fecha"


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


_migradas: set[str] = set()


def _carpeta_migrada(nombre: str) -> Path:
    """JSON/ o Historial/, migrada a la estructura AAAA/MM la primera vez
    que se pide en esta sesión (clave por ruta completa, no por nombre —
    ver el mismo patrón en core/repositorio_ops.py)."""
    p = _ruta_base() / nombre
    p.mkdir(parents=True, exist_ok=True)
    clave = str(p)
    if clave not in _migradas:
        cm.migrar_archivos_planos(p, _CAMPO_FECHA)
        _migradas.add(clave)
    return p


def carpeta_json() -> Path:
    return _carpeta_migrada("JSON")


def carpeta_historial() -> Path:
    return _carpeta_migrada("Historial")


def carpeta_excel() -> Path:
    """Excel exportado — no es la fuente de verdad, se deja plana."""
    p = _ruta_base() / "Excel"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_html() -> Path:
    """HTML impreso — se regenera cada vez, se deja plana."""
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
        # rglob (no glob): las carpetas de OPs guardan los JSON en
        # subcarpetas AAAA/MM (ver core/repositorio_ops.py); rglob también
        # encuentra los planos de Cotizaciones sin cambiar nada ahí.
        for archivo in carpeta.rglob("*.json"):
            try:
                numeros.append(int(archivo.stem))
            except ValueError:
                pass
    return max(numeros) + 1 if numeros else 1000


def numero_en_uso(numero: int, excluir: int | None = None) -> bool:
    """True si `numero` ya pertenece a una cotización (activa o en
    Historial) o a una OP (activa o en Historial) — mismo universo que
    evita siguiente_numero(), pero para consultar uno puntual (ver
    ui/api_cotizacion.py — validación en vivo del N° de cotización antes
    de dejar avanzar a cargar productos). `excluir` es el número que la
    pantalla ya tenía asignado al entrar (editando una cotización
    existente): ese no cuenta como choque contra sí mismo."""
    if excluir is not None and numero == excluir:
        return False

    from core import repositorio_ops

    for carpeta in (carpeta_json(), carpeta_historial(),
                     repositorio_ops.carpeta_json(), repositorio_ops.carpeta_historial()):
        if cm.buscar(carpeta, numero) is not None:
            return True
    return False


def listar_cotizaciones() -> list[dict]:
    """Lista todas las cotizaciones activas (JSON/, con sus subcarpetas
    AAAA/MM) — {numero, empresa, fecha} por cada una, más nuevas primero.
    No incluye las de Historial/ (esas son las que ya se aprobaron a OP) ni
    los "pendientes" (cotizaciones a medio hacer — ver
    core.repositorio_pendientes.listar_pendientes, un concepto aparte).

    Antes esta misma lectura (rglob sobre carpeta_json(), leyendo cada JSON
    para sacarle Cotizacion/Empresa/Fecha) vivía duplicada dentro de
    ui/revisar_cotizaciones.py — queda acá para que cualquier pantalla
    (Tkinter o la que reemplace al menú) pueda listar sin reinventar el
    escaneo."""
    entradas = []
    for archivo in sorted(carpeta_json().rglob("*.json")):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except Exception:
            continue
        try:
            numero = int(datos.get("Cotizacion", archivo.stem))
        except (TypeError, ValueError):
            continue
        entradas.append({
            "numero":  numero,
            "empresa": datos.get("Empresa", "—"),
            "fecha":   datos.get("Fecha", "—"),
        })
    entradas.sort(key=lambda e: e["numero"], reverse=True)
    return entradas


def cargar_cotizacion(numero: int) -> dict | None:
    """Lee el JSON de una cotización guardada por número, o None si no existe."""
    ruta = cm.buscar(carpeta_json(), numero)
    if ruta is None:
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return None


def guardar_cotizacion(datos: dict) -> Path:
    """Guarda datos como JSON, en la subcarpeta AAAA/MM de JSON/ que
    corresponde a su Fecha. Sobreescribe si ya existe el número (mismo
    mes — editar una cotización no cambia su Fecha de creación)."""
    numero = datos["Cotizacion"]
    anio, mes = cm.anio_mes(datos, _CAMPO_FECHA)
    destino = cm.subcarpeta_mes(carpeta_json(), anio, mes) / f"{numero}.json"
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def recalcular_descuentos(datos: dict, *, guardar: bool = True) -> dict:
    """
    Recalcula Neto/NetoTotal/IVA/Total de una cotización ya guardada, a
    partir de sus productos y su % de Descuento manual — misma fórmula que
    usa ui/formulario_cliente.py al crearla (ver core.precios.costo_cotizacion).
    Pensada para refrescar cotizaciones guardadas ANTES de un cambio a la
    fórmula de precios (ej. el descuento-textil, ver
    core.precios.descuento_textil) sin tener que reabrirlas y reguardarlas
    a mano una por una.

    Se llama justo antes de abrir el HTML (botón Ver/Imprimir) y justo
    antes de editar (botón Editar), ambos en ui/revisar_cotizaciones.py,
    para que los dos caminos siempre reflejen la lógica de precios
    vigente, no la que estaba vigente cuando se guardó por última vez. El
    % de Descuento manual y los productos NO se tocan — solo los montos
    derivados de ellos.

    Muta y devuelve el mismo dict recibido. Si `guardar` es True (default)
    y algún monto cambió, además reescribe el archivo en disco (mismo
    mecanismo que guardar_cotizacion) para que la corrección quede
    permanente y no solo para esta vista puntual.
    """
    productos_internos = [producto_desde_json(p) for p in datos.get("productos", [])]
    descuento_pct = datos.get("Descuento", 0.0) or 0.0
    despacho = datos.get("Despacho")
    instalacion = datos.get("Instalacion")
    totales = costo_cotizacion(productos_internos, descuento_pct,
                                despacho=despacho or 0.0, instalacion=instalacion or 0.0)

    cambio = (
        datos.get("Neto") != totales["neto"]
        or datos.get("NetoTotal") != totales["neto_total"]
        or datos.get("IVA") != totales["iva"]
        or datos.get("Total") != totales["total"]
    )
    datos["Neto"]      = totales["neto"]
    datos["NetoTotal"] = totales["neto_total"]
    datos["IVA"]       = totales["iva"]
    datos["Total"]     = totales["total"]

    if guardar and cambio and "Cotizacion" in datos:
        guardar_cotizacion(datos)

    return datos


def mover_a_historial(numero: int) -> None:
    """Mueve el JSON de la cotización aprobada de JSON/ a Historial/
    (misma subcarpeta AAAA/MM, la Fecha no cambia)."""
    cm.mover_preservando_mes(carpeta_json(), carpeta_historial(), numero)


def eliminar_cotizacion(numero: int) -> bool:
    """Elimina el JSON de una cotización, esté activa o en Historial.
    Devuelve True si encontró y borró algo."""
    return cm.eliminar([carpeta_json(), carpeta_historial()], numero)


def buscar_en_ultimos_meses(numero: int, anio_ref: int, mes_ref: int, cantidad_meses: int = 3) -> dict | None:
    """Busca una cotización por número dentro de los `cantidad_meses`
    meses terminando en (anio_ref, mes_ref) inclusive (ese mes y los
    anteriores) — para "Buscar cotización" desde el historial de OPs
    (ui/historial_ops.py): la cotización de origen se mueve a Historial/
    en el momento en que se aprueba la OP, así que su Fecha debería caer
    en el mismo mes que la Fecha_ingreso de la OP, o poco antes. Revisa
    JSON/ (por si la cotización, contra lo esperado, no llegó a moverse) e
    Historial/, sin abrir ningún archivo fuera de esos meses."""
    anio, mes = anio_ref, mes_ref
    for _ in range(cantidad_meses):
        for carpeta in (carpeta_json(), carpeta_historial()):
            ruta = carpeta / f"{anio:04d}" / f"{mes:02d}" / f"{numero}.json"
            if ruta.exists():
                try:
                    return json.loads(ruta.read_text(encoding="utf-8"))
                except Exception:
                    return None
        anio, mes = cm.restar_meses(anio, mes, 1)
    return None


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
