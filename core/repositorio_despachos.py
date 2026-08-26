"""
core/repositorio_despachos.py
Persistencia del módulo Despachos: OPs completadas que tienen Despacho y/o
Instalacion (ver core/repositorio_ops.py::mover_a_despachos) y las guías de
despacho que se generan para ellas.

La dirección de entrega es POR PRODUCTO, no por OP — una misma OP puede
repartirse a varias direcciones (ver asignar_direccion_productos). Por eso
el ciclo de vida de una OP dentro de Despachos tiene TRES carpetas:
  OPs/NoAsignadas/  — recién llegada, todavía falta ponerle dirección a
                       algún producto (o a todos).
  OPs/Asignadas/    — TODOS los productos ya tienen dirección asignada
                       (ver _sincronizar_carpeta) — ahí se pueden generar
                       guías de despacho y seleccionar la OP en el panel
                       de Despachos (menu.html) para marcarla Entregada.
  OPs/Historial/    — ya entregada (ver marcar_entregado), fuera de
                       circulación del módulo.
Guias de despacho/JSON/ y HTML/ — igual que antes, una guía por archivo.

Mismo patrón de carpetas Dropbox que core/repositorio_ops.py (_ruta_base()
con fallback a DATOS). Todo queda plano — ver docstring de la versión
anterior de este archivo: no hay nada acá que crezca sin límite mes a mes
como para justificar organizarlo por AAAA/MM (se puede sumar después con
core/carpetas_mensuales.py si hiciera falta).
"""

import json
from datetime import datetime
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox

ESTADO_DESPACHO_PENDIENTE  = "pendiente"
ESTADO_DESPACHO_PARCIAL    = "parcial"
ESTADO_DESPACHO_DESPACHADO = "despachado"

ESTADO_ASIGNACION_NO_ASIGNADA = "no_asignada"
ESTADO_ASIGNACION_ASIGNADA    = "asignada"


def _hoy_dma() -> str:
    return datetime.now().strftime("%d/%m/%Y")


def _ruta_base() -> Path:
    dropbox = _detectar_dropbox()
    if dropbox:
        return dropbox / "SGTD" / "Despachos"
    return DATOS / "Despachos"


def carpeta_no_asignadas() -> Path:
    p = _ruta_base() / "OPs" / "NoAsignadas"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_asignadas() -> Path:
    p = _ruta_base() / "OPs" / "Asignadas"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_historial() -> Path:
    """Despachos ya entregados (ver marcar_entregado) — plana, igual
    criterio que el resto de este módulo: no hay nada acá que vaya a
    crecer sin límite como para justificar AAAA/MM todavía."""
    p = _ruta_base() / "OPs" / "Historial"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_guias_json() -> Path:
    p = _ruta_base() / "Guias de despacho" / "JSON"
    p.mkdir(parents=True, exist_ok=True)
    return p


def carpeta_guias_html() -> Path:
    p = _ruta_base() / "Guias de despacho" / "HTML"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ══════════════════════════════════════════════════════════════════════════════
# OPs en Despachos
# ══════════════════════════════════════════════════════════════════════════════

def estado_despacho(datos: dict) -> str:
    """Estado derivado a partir de CantidadDespachada vs Cantidad de cada
    producto — igual espíritu que core.repositorio_ops.estado_op (se
    calcula, no se elige a mano): "pendiente" si nada se despachó todavía,
    "despachado" si todo quedó cubierto, "parcial" en cualquier punto
    intermedio. Una OP sin productos se considera "despachado" (no hay
    nada pendiente que despachar)."""
    productos = datos.get("productos", [])
    if not productos:
        return ESTADO_DESPACHO_DESPACHADO
    despachado_algo = False
    falta_algo = False
    for p in productos:
        cantidad = p.get("Cantidad", 0) or 0
        despachada = p.get("CantidadDespachada", 0) or 0
        if despachada > 0:
            despachado_algo = True
        if despachada < cantidad:
            falta_algo = True
    if not despachado_algo:
        return ESTADO_DESPACHO_PENDIENTE
    if falta_algo:
        return ESTADO_DESPACHO_PARCIAL
    return ESTADO_DESPACHO_DESPACHADO


def estado_asignacion(datos: dict) -> str:
    """"asignada" solo si CADA producto de la OP tiene una Direccion
    puesta; "no_asignada" si falta en cualquiera (incluida una OP sin
    productos, por consistencia — no hay nada asignado). Se calcula, no
    se elige a mano, igual que estado_despacho."""
    productos = datos.get("productos", [])
    if not productos:
        return ESTADO_ASIGNACION_NO_ASIGNADA
    if all(p.get("Direccion") for p in productos):
        return ESTADO_ASIGNACION_ASIGNADA
    return ESTADO_ASIGNACION_NO_ASIGNADA


def _carpeta_actual(numero: int) -> Path | None:
    """En cuál de las dos carpetas de OPs vive `numero` ahora mismo, o
    None si no está en ninguna."""
    if (carpeta_no_asignadas() / f"{numero}.json").exists():
        return carpeta_no_asignadas()
    if (carpeta_asignadas() / f"{numero}.json").exists():
        return carpeta_asignadas()
    return None


def cargar_op_despacho(numero: int) -> dict | None:
    carpeta = _carpeta_actual(int(numero))
    if carpeta is None:
        return None
    try:
        return json.loads((carpeta / f"{numero}.json").read_text(encoding="utf-8"))
    except Exception:
        return None


def guardar_op_despacho(datos: dict) -> Path:
    """Sobreescribe el JSON en la carpeta donde la OP viva ahora mismo
    (NoAsignadas o Asignadas). Si es la primera vez que se guarda (recién
    recibida, ver recibir_op) todavía no está en ninguna — cae a
    NoAsignadas, que es de donde siempre nace una OP en este módulo."""
    numero = datos["Cotizacion"]
    carpeta = _carpeta_actual(numero) or carpeta_no_asignadas()
    destino = carpeta / f"{numero}.json"
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def listar_ops_despacho() -> list[dict]:
    """Todas las OPs de Despachos (NoAsignadas + Asignadas), cada una con
    su EstadoDespacho y EstadoAsignacion normalizados (ver estado_despacho/
    estado_asignacion)."""
    ops = []
    for carpeta in (carpeta_no_asignadas(), carpeta_asignadas()):
        for archivo in sorted(carpeta.glob("*.json")):
            try:
                datos = json.loads(archivo.read_text(encoding="utf-8"))
            except Exception:
                continue
            datos["EstadoDespacho"] = estado_despacho(datos)
            datos["EstadoAsignacion"] = estado_asignacion(datos)
            ops.append(datos)
    return ops


def marcar_entregado(numero_op: int) -> bool:
    """Mueve la OP de Asignadas/ a Historial/ y la saca de circulación del
    módulo — botón "Entregado" del panel de Despachos (menu.html). Solo
    tiene sentido para una OP que ya está en Asignadas/ (con dirección
    puesta en todos sus productos); devuelve False sin mover nada si no
    la encuentra ahí."""
    numero_op = int(numero_op)
    origen = carpeta_asignadas() / f"{numero_op}.json"
    if not origen.exists():
        return False
    datos = json.loads(origen.read_text(encoding="utf-8"))
    datos["Entregado"] = _hoy_dma()
    destino = carpeta_historial() / origen.name
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    origen.unlink()
    return True


def eliminar_despacho(numero_op: int) -> bool:
    """Borra el JSON de la OP, esté en la carpeta que esté (NoAsignadas,
    Asignadas o Historial) — botón "Eliminar" del panel de Despachos. NO
    toca las guías ya generadas para esa OP (son documentos ya emitidos,
    quedan como registro aunque se elimine la OP del módulo). Devuelve
    True si encontró y borró algo."""
    numero_op = int(numero_op)
    for carpeta in (carpeta_no_asignadas(), carpeta_asignadas(), carpeta_historial()):
        ruta = carpeta / f"{numero_op}.json"
        if ruta.exists():
            ruta.unlink()
            return True
    return False


def recibir_op(datos: dict) -> None:
    """La OP llega desde core.repositorio_ops.mover_a_despachos ya con
    Fecha_completada/Estado grabados. Le agrega EstadoDespacho="pendiente"
    y, a cada producto, CantidadDespachada=0 (si no lo tenía ya — no pisa
    un valor existente, por si esto se llama dos veces sobre la misma
    OP), y la guarda en NoAsignadas/ — ningún producto trae Direccion
    todavía, eso se hace a mano en la pantalla de asignación."""
    for p in datos.get("productos", []):
        p.setdefault("CantidadDespachada", 0)
    datos["EstadoDespacho"] = ESTADO_DESPACHO_PENDIENTE
    guardar_op_despacho(datos)


def asignar_direccion_productos(numero_op: int, indices: list[int], direccion: dict) -> None:
    """Pone `direccion` en los productos de `indices` (0-based) de la OP y
    la deja en la carpeta que corresponda según quede su EstadoAsignacion
    (ver _sincronizar_carpeta) — si esto completa el último producto que
    faltaba, la OP pasa sola a Asignadas/, sin un paso "Completar" aparte."""
    numero_op = int(numero_op)
    datos = cargar_op_despacho(numero_op)
    if datos is None:
        return
    productos = datos.get("productos", [])
    for i in indices:
        i = int(i)
        if 0 <= i < len(productos):
            productos[i]["Direccion"] = direccion
    guardar_op_despacho(datos)
    _sincronizar_carpeta(datos)


def quitar_direccion_productos(numero_op: int, indices: list[int]) -> None:
    """Saca la Direccion de los productos de `indices` — si la OP ya
    estaba en Asignadas/ y esto la deja incompleta de nuevo, vuelve sola a
    NoAsignadas/ (ver _sincronizar_carpeta)."""
    numero_op = int(numero_op)
    datos = cargar_op_despacho(numero_op)
    if datos is None:
        return
    productos = datos.get("productos", [])
    for i in indices:
        i = int(i)
        if 0 <= i < len(productos):
            productos[i].pop("Direccion", None)
    guardar_op_despacho(datos)
    _sincronizar_carpeta(datos)


def _sincronizar_carpeta(datos: dict) -> None:
    """Mueve el JSON a la carpeta que le corresponde según su
    EstadoAsignacion actual — Asignadas/ si TODOS los productos ya tienen
    dirección, NoAsignadas/ si no. Reemplaza al viejo botón "Completar":
    el traslado ahora es automático, apenas se asigna o se quita una
    dirección, no un paso manual aparte (ver ui/api_asignar_despacho.py)."""
    numero = datos["Cotizacion"]
    destino_esperado = (
        carpeta_asignadas() if estado_asignacion(datos) == ESTADO_ASIGNACION_ASIGNADA
        else carpeta_no_asignadas()
    )
    actual = _carpeta_actual(numero)
    if actual is None or actual == destino_esperado:
        return
    origen = actual / f"{numero}.json"
    origen.replace(destino_esperado / origen.name)


# ══════════════════════════════════════════════════════════════════════════════
# Guías de despacho
# ══════════════════════════════════════════════════════════════════════════════

def siguiente_numero_guia(numero_op: int) -> str:
    """"{numero_op}-{n+1}", contando las guías que ya existen para esta OP
    — mismo espíritu que core.repositorio_cotizaciones.siguiente_numero:
    contar archivos existentes, sin llevar un contador aparte."""
    existentes = list(carpeta_guias_json().glob(f"{numero_op}-*.json"))
    return f"{numero_op}-{len(existentes) + 1}"


def _nombre_producto(p: dict) -> str:
    if "Caja" in p:
        return f"Backlight · {p.get('Tela', '')}".strip(" ·")
    return p.get("producto", "") or "—"


def generar_guia(numero_op, items: list[dict], observaciones: str = "") -> dict:
    """Genera una guía de despacho para `numero_op`. `items` es
    [{"indice_producto": i, "cantidad": n}, ...] — cuánto se despacha de
    cada producto EN ESTA guía. Como la dirección es por producto, TODOS
    los productos incluidos en `items` tienen que compartir la MISMA
    dirección — una guía va a un solo lugar. Suma las cantidades a
    CantidadDespachada, recalcula EstadoDespacho, guarda la OP
    actualizada, y escribe la guía en carpeta_guias_json(). Devuelve el
    dict de la guía.

    Lanza ValueError si la OP no existe, algún producto de `items` no
    tiene dirección asignada, o los productos de `items` no comparten la
    misma dirección."""
    numero_op = int(numero_op)
    datos = cargar_op_despacho(numero_op)
    if datos is None:
        raise ValueError(f"No existe la OP {numero_op} en Despachos.")

    productos = datos.get("productos", [])
    direccion = None
    items_guia = []
    for item in items:
        indice = int(item["indice_producto"])
        cantidad = float(item["cantidad"])
        if cantidad <= 0 or indice >= len(productos):
            continue
        p = productos[indice]
        p_direccion = p.get("Direccion")
        if not p_direccion:
            raise ValueError(f"El producto {indice} de la OP {numero_op} no tiene dirección asignada.")
        if direccion is None:
            direccion = p_direccion
        elif p_direccion != direccion:
            raise ValueError("Los productos de una misma guía tienen que compartir la misma dirección.")
        p["CantidadDespachada"] = (p.get("CantidadDespachada", 0) or 0) + cantidad
        items_guia.append({
            "producto": _nombre_producto(p),
            "tema": p.get("Tema", ""),
            "cantidad": cantidad,
        })

    if direccion is None:
        raise ValueError("No hay ningún producto con cantidad a despachar.")

    datos["EstadoDespacho"] = estado_despacho(datos)
    guardar_op_despacho(datos)

    numero_guia = siguiente_numero_guia(numero_op)
    guia = {
        "numero_guia": numero_guia,
        "numero_op": numero_op,
        "fecha": _hoy_dma(),
        "direccion": dict(direccion),
        "cliente": {
            "empresa": datos.get("Empresa", ""),
            "rut": direccion.get("rut", ""),
            "contacto": datos.get("Contacto", ""),
        },
        "items": items_guia,
        "observaciones": observaciones,
        "incluye_instalacion": datos.get("Instalacion") is not None,
    }
    destino = carpeta_guias_json() / f"{numero_guia}.json"
    destino.write_text(json.dumps(guia, ensure_ascii=False, indent=2), encoding="utf-8")
    return guia


def cargar_guia(numero_guia: str) -> dict | None:
    ruta = carpeta_guias_json() / f"{numero_guia}.json"
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return None


def listar_guias_de_op(numero_op: int) -> list[dict]:
    guias = []
    for archivo in sorted(carpeta_guias_json().glob(f"{numero_op}-*.json")):
        try:
            guias.append(json.loads(archivo.read_text(encoding="utf-8")))
        except Exception:
            continue
    guias.sort(key=lambda g: int(g["numero_guia"].split("-")[-1]))
    return guias
