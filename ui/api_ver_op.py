"""
ui/api_ver_op.py
Lógica de ver-op.html — instanciada una sola vez por ui.api_app.ApiApp
(ver docstring de ese módulo). La OP es solo para producción — sin plata
(ver core/presentar_op.py, mismo criterio acá).
"""

import webbrowser

from core.repositorio_ops import (
    cargar_op, estado_op, listar_todas_las_ops, ESTADO_ACTIVA,
    completar_op as _completar_op,
)
from core.repositorio_cotizaciones import producto_desde_json
from core.precios import calcular_ml
from core.repositorio import TEXTILES_ANCHOS
from core.presentar_op import generar_html
from ui.dialogo_recotizar import recotizar_op as _recotizar_op


def _metros_producto(p_interno: dict) -> tuple[float | None, float | None]:
    """(ml, m2) reales — SIN piso de facturación, es producción, no plata
    (mismo criterio que core.presentar_op._metrica_producto: M² para
    backlight, ML para el resto)."""
    if "tela" in p_interno:
        area = p_interno.get("alto", 0.0) * p_interno.get("ancho", 0.0) * p_interno.get("cantidad", 0)
        return None, area
    ancho_tela = TEXTILES_ANCHOS.get(p_interno.get("textil", ""))
    _, ml = calcular_ml(p_interno, ancho_tela)
    return (ml or 0.0), None


def _producto_a_json_pantalla(p_interno: dict) -> dict:
    es_bl = "tela" in p_interno
    ml, m2 = _metros_producto(p_interno)
    return {
        "tipo":          "backlight" if es_bl else "estandar",
        "producto":      "" if es_bl else p_interno.get("producto", ""),
        "textil":        "" if es_bl else p_interno.get("textil", ""),
        "impresion":     "" if es_bl else p_interno.get("impresion", ""),
        "estructuras":   [] if es_bl else list(p_interno.get("estructuras", [])),
        "terminaciones": [] if es_bl else list(p_interno.get("terminaciones", [])),
        "tela":          p_interno.get("tela", "") if es_bl else "",
        "caja":          p_interno.get("caja", "") if es_bl else "",
        "tema":          p_interno.get("tema", ""),
        "obs":           p_interno.get("obs", ""),
        "ancho":         p_interno.get("ancho", 0.0),
        "alto":          p_interno.get("alto", 0.0),
        "cantidad":      p_interno.get("cantidad", 0),
        "ml":            ml,
        "m2":            m2,
    }


def op_a_json(datos: dict) -> dict:
    """Convierte una OP en esquema JSON (guardada por
    core.repositorio_ops.guardar_op/promover_a_op) al shape que esperan
    ver-op.html E historial-ops.html (mismos campos) — reusado por
    ApiVerOp.obtener_op y ApiHistorialOps (ver ui/api_historial_ops.py)."""
    productos_json = datos.get("productos", [])
    productos_internos = [producto_desde_json(p) for p in productos_json]
    return {
        "numero":        datos.get("Cotizacion"),
        "nombre":        datos.get("Nombre", ""),
        "empresa":       datos.get("Empresa", ""),
        "contacto":      datos.get("Contacto", ""),
        "email":         datos.get("Email", ""),
        "descripcion":   datos.get("Descripcion", ""),
        "fecha_ingreso": datos.get("Fecha_ingreso", ""),
        "fecha_entrega": datos.get("Fecha_entrega", ""),
        "estado":        estado_op(datos),
        "despacho":      datos.get("Despacho") is not None,
        "instalacion":   datos.get("Instalacion") is not None,
        "direccion":     None,
        "productos":     [_producto_a_json_pantalla(p) for p in productos_internos],
    }


class ApiVerOp:

    def contexto_extra(self, numero) -> dict:
        return {"numero": int(numero) if numero is not None else None}

    def numero_adyacente(self, numero, direccion: str) -> int | None:
        """Flechas ←/→ de ver-op.html: el número de la OP siguiente/
        anterior recorriendo TODAS las OPs (activas + Pendiente +
        Completadas + Historial, ver listar_todas_las_ops), ordenadas de
        más nueva a más antigua — mismo criterio que
        ApiVerCotizacion.numero_adyacente — con vuelta. None si `numero`
        no aparece en la lista o no hay ninguna otra OP guardada."""
        numeros = sorted(
            {int(op["Cotizacion"]) for op in listar_todas_las_ops() if op.get("Cotizacion") is not None},
            reverse=True,
        )
        numero = int(numero) if numero is not None else None
        if numero not in numeros or len(numeros) < 2:
            return None
        i = numeros.index(numero)
        paso = 1 if direccion == "siguiente" else -1
        return numeros[(i + paso) % len(numeros)]

    def obtener_op(self, numero) -> dict | None:
        datos = cargar_op(int(numero))
        if datos is None:
            return None
        return op_a_json(datos)

    def imprimir_op(self, numero) -> None:
        datos = cargar_op(int(numero))
        if datos is None:
            return
        ruta_html = generar_html(datos)
        webbrowser.open(ruta_html.as_uri())

    def recotizar_op(self, numero) -> bool:
        return _recotizar_op(numero)

    def completar_op(self, numero) -> bool:
        """Botón "Completar" de ver-op.html — hasta ahora esto solo se
        podía hacer desde el panel de producción (ver ui/panel_produccion.py,
        que usa el mismo core.repositorio_ops.completar_op). Solo tiene
        sentido para una OP activa; ver-op.html ya oculta el botón si no lo
        es (ver TD.iniciar ahí), esto es la red de seguridad — devuelve
        False sin hacer nada si la OP ya no está activa."""
        datos = cargar_op(int(numero))
        if datos is None or estado_op(datos) != ESTADO_ACTIVA:
            return False
        _completar_op(numero)
        return True
