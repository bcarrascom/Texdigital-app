"""
core/presentar_despacho.py
Genera el documento HTML imprimible de una guía de despacho —
recursos/plantilla_despacho.html con los datos reales. Mismo patrón que
core/presentar_op.py: placeholders "{{...}}" reemplazados con .replace(),
sin motor de templating. Documento operativo (sin precios) — solo qué se
despacha, cuánto, y adónde.
"""

from pathlib import Path

from core.rutas import RECURSOS
from core.repositorio_despachos import carpeta_guias_html

RUTA_PLANTILLA = RECURSOS / "plantilla_despacho.html"


def _fmt_cantidad(valor: float) -> str:
    """Mismo formato chileno que core.presentar_op._fmt_cantidad."""
    valor = round(valor, 2)
    if valor == int(valor):
        return f"{int(valor):,}".replace(",", ".")
    entero, _, decimales = f"{valor:,.2f}".partition(".")
    return entero.replace(",", ".") + "," + decimales.rstrip("0")


def _fila_item(item: dict) -> str:
    tema = item.get("tema", "").strip() or "—"
    return f"""      <tr>
        <td>{item.get('producto', '')}</td>
        <td>{tema}</td>
        <td class="num">{_fmt_cantidad(item.get('cantidad', 0))}</td>
      </tr>"""


def _linea_direccion(direccion: dict) -> str:
    calle = direccion.get("calle", "").strip()
    numero = direccion.get("numero", "").strip()
    partes = [p for p in (calle, numero) if p]
    return " ".join(partes) or "—"


def generar_html(guia: dict) -> Path:
    """Genera el HTML de una guía de despacho y lo deja guardado en
    carpeta_guias_html() (de core.repositorio_despachos). Devuelve la
    ruta del archivo."""
    plantilla = RUTA_PLANTILLA.read_text(encoding="utf-8")

    direccion = guia.get("direccion", {}) or {}
    cliente = guia.get("cliente", {}) or {}
    items = guia.get("items", [])

    referencia = direccion.get("referencia", "").strip()
    referencia_bloque = (
        f'<div class="dato"><div class="k">Referencia</div><div class="v2">{referencia}</div></div>'
        if referencia else ""
    )

    observaciones = guia.get("observaciones", "").strip()
    observaciones_bloque = (
        f'<div class="observaciones"><b>Observaciones</b>\n    {observaciones}\n  </div>'
        if observaciones else ""
    )

    instalacion_bloque = (
        '<span class="etiqueta-instalacion">Incluye instalación</span>'
        if guia.get("incluye_instalacion") else ""
    )

    reemplazos = {
        "{{numero_guia}}":   str(guia.get("numero_guia", "")),
        "{{numero_op}}":     str(guia.get("numero_op", "")),
        "{{fecha}}":         guia.get("fecha", ""),
        "{{empresa}}":       cliente.get("empresa", ""),
        "{{rut}}":           cliente.get("rut", ""),
        "{{contacto}}":      cliente.get("contacto", ""),
        "{{direccion_linea}}": _linea_direccion(direccion),
        "{{comuna}}":        direccion.get("comuna", "") or "—",
        "{{region}}":        direccion.get("region", "") or "—",
        "{{referencia_bloque}}": referencia_bloque,
        "{{filas_items}}":   "\n".join(_fila_item(i) for i in items),
        "{{observaciones_bloque}}": observaciones_bloque,
        "{{instalacion_bloque}}": instalacion_bloque,
    }
    html = plantilla
    for placeholder, valor in reemplazos.items():
        html = html.replace(placeholder, str(valor))

    destino = carpeta_guias_html() / f"{guia.get('numero_guia')}.html"
    destino.write_text(html, encoding="utf-8")
    return destino
