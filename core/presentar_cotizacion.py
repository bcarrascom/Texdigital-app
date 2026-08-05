"""
core/presentar_cotizacion.py
Genera el documento HTML imprimible de una cotización (recursos/plantilla_cotizacion.html
con los datos reales), para mostrarle al cliente o guardar como PDF (botón
"Guardar como PDF" de la propia plantilla, window.print()).

Sustitución simple por texto (.replace), sin dependencia de templating —
la plantilla es HTML+CSS fijo, lo único que cambia entre cotizaciones es
el contenido de los placeholders {{...}}.
"""

from pathlib import Path

from core.rutas import RECURSOS
from core.repositorio_cotizaciones import carpeta_html, producto_desde_json
from core.precios import costo_cotizacion, costo_producto, formatear_clp, parsear_valor_manual

RUTA_PLANTILLA = RECURSOS / "plantilla_cotizacion.html"


def _fmt_medida(valor: float) -> str:
    """1.5 -> '1,500' (formato chileno, 3 decimales, como el mockup)."""
    return f"{float(valor):.3f}".replace(".", ",")


def _fila_producto(p: dict) -> str:
    # producto_desde_json ya migra el esquema viejo de una sola Estructura/
    # Terminación (string) a listas — se usa una sola vez acá tanto para el
    # costo como para lo que se muestra, así los dos siempre coinciden
    # incluso en cotizaciones guardadas antes del modelo aditivo.
    interno = producto_desde_json(p)
    costo = costo_producto(interno)
    cantidad = p.get("Cantidad", 0)
    valor_unit = formatear_clp(costo["valor_unitario"])
    total_fila = formatear_clp(costo["total"])
    medidas = f"{_fmt_medida(p.get('Ancho', 0))} × {_fmt_medida(p.get('Alto', 0))} m"

    if "Caja" in p:
        caja = p.get("Caja")
        con_caja = isinstance(caja, dict)
        tema = p.get("Tema", "")
        if con_caja:
            nombre = f"Backlight + Caja · {p.get('Tela', '')}"
            detalle = caja.get("perfil", "")
        else:
            nombre = f"Backlight · {p.get('Tela', '')}"
            detalle = "Solo tela impresa"
        if tema:
            detalle = f"{detalle} · Tema: {tema}" if detalle else f"Tema: {tema}"
        extras_html = ""
    else:
        nombre = p.get("producto", "")
        tema = p.get("Tema", "")
        detalle = p.get("Tela", "")
        if tema:
            detalle = f"{detalle} · Tema: {tema}" if detalle else f"Tema: {tema}"

        # Los ajustes manuales (montos escritos directo, ver
        # core.precios.parsear_valor_manual) se suman al total pero NUNCA
        # se muestran acá — el cliente solo ve el total del producto, no
        # el detalle de un parche puntual de precio.
        partes_extra = []
        estructuras = [e for e in interno.get("estructuras", [])
                       if parsear_valor_manual(e) is None]
        if estructuras:
            partes_extra.append(f"<b>Estructuras:</b> {' · '.join(estructuras)}")
        terminaciones = [t for t in interno.get("terminaciones", [])
                         if parsear_valor_manual(t) is None]
        if terminaciones:
            partes_extra.append(f"<b>Terminaciones:</b> {' · '.join(terminaciones)}")
        extras_html = (
            f'<div class="prod-extras">{"<br>".join(partes_extra)}</div>'
            if partes_extra else ""
        )

    return f"""      <tr>
        <td>
          <div class="prod-nombre">{nombre}</div>
          <div class="prod-detalle">{detalle}</div>
          {extras_html}
        </td>
        <td>{medidas}</td>
        <td class="num">{cantidad}</td>
        <td class="num">{valor_unit}</td>
        <td class="num">{total_fila}</td>
      </tr>"""


def _fila_despacho(valor: float) -> str:
    """Fila del despacho en la tabla de productos — sin medidas ni
    cantidad (no es un producto), solo el nombre y el monto, sumado al
    total igual que cualquier otra fila. Se cobra a mano mientras el
    sistema no genera guías de despacho."""
    monto = formatear_clp(valor)
    return f"""      <tr>
        <td>
          <div class="prod-nombre">Despacho</div>
        </td>
        <td></td>
        <td class="num"></td>
        <td class="num"></td>
        <td class="num">{monto}</td>
      </tr>"""


def generar_html(json_dict: dict) -> Path:
    """Genera el HTML de la cotización y lo deja guardado en carpeta_html().
    Devuelve la ruta del archivo."""
    plantilla = RUTA_PLANTILLA.read_text(encoding="utf-8")

    numero = json_dict.get("Cotizacion", "")
    productos = json_dict.get("productos", [])

    productos_internos = [producto_desde_json(p) for p in productos]
    descuento_pct = json_dict.get("Descuento", 0.0) or 0.0
    despacho = json_dict.get("Despacho")
    totales = costo_cotizacion(productos_internos, descuento_pct, despacho=despacho or 0.0)

    contacto = json_dict.get("Contacto", "")
    email    = json_dict.get("Email", "")
    contacto_email = " · ".join(x for x in (contacto, email) if x)

    descripcion = json_dict.get("Descripcion", "").strip()
    descripcion_bloque = (
        f'<div class="descripcion"><b>Descripción</b>\n    {descripcion}\n  </div>'
        if descripcion else ""
    )

    # Sin descuento, Neto == Neto total — mostrar ambas filas es redundante,
    # así que se omiten las dos y queda solo "Neto total".
    fila_neto = (
        f'      <tr class="sub"><td>Neto</td><td>{formatear_clp(totales["neto"])}</td></tr>'
        if descuento_pct else ""
    )
    fila_descuento = (
        f'      <tr class="sub"><td>Descuento ({descuento_pct:g}%)</td>'
        f'<td>−{formatear_clp(totales["descuento"])}</td></tr>'
        if descuento_pct else ""
    )

    reemplazos = {
        "{{numero}}":          str(numero),
        "{{fecha}}":           json_dict.get("Fecha", ""),
        "{{empresa}}":         json_dict.get("Empresa", ""),
        "{{contacto_email}}":  contacto_email,
        "{{condicion_pago}}":  json_dict.get("Condicion de pago", ""),
        "{{descripcion_bloque}}": descripcion_bloque,
        "{{filas_productos}}": "\n".join(
            [_fila_producto(p) for p in productos]
            + ([_fila_despacho(despacho)] if despacho else [])
        ),
        "{{fila_neto}}":       fila_neto,
        "{{fila_descuento}}":  fila_descuento,
        "{{neto_total}}":      formatear_clp(totales["neto_total"]),
        "{{iva}}":             formatear_clp(totales["iva"]),
        "{{total}}":           formatear_clp(totales["total"]),
    }
    html = plantilla
    for placeholder, valor in reemplazos.items():
        html = html.replace(placeholder, str(valor))

    destino = carpeta_html() / f"{numero}.html"
    destino.write_text(html, encoding="utf-8")
    return destino
