"""
core/presentar_op.py
Genera el documento HTML imprimible de una OP (orden de producción) para
los trabajadores de planta — recursos/plantilla_op.html con los datos
reales. A diferencia de la cotización para el cliente
(core/presentar_cotizacion.py), este documento NO muestra ningún precio ni
valor de los productos: solo medidas, cantidades, y un recuento de qué
materiales hacen falta (textiles, estructuras, terminaciones y materiales
de caja), calculado desde la geometría de cada producto — nunca desde
core.precios.
"""

from pathlib import Path

from core.rutas import RECURSOS
from core.repositorio_ops import carpeta_html
from core.repositorio_cotizaciones import producto_desde_json
from core.precios import calcular_ml, parsear_valor_manual
from core.repositorio import TEXTILES_ANCHOS, ESTRUCTURAS_VALORES

RUTA_PLANTILLA = RECURSOS / "plantilla_op.html"


def _fmt_medida(valor: float) -> str:
    """1.5 -> '1,500' (formato chileno, 3 decimales, igual que la cotización)."""
    return f"{float(valor):.3f}".replace(".", ",")


def _fmt_cantidad(valor: float) -> str:
    """1234.5 -> '1.234,5' — separador de miles y coma decimal, sin
    decimales de sobra cuando el número es entero (formato chileno, pero
    para cantidades de material, no plata — no hay $)."""
    valor = round(valor, 2)
    if valor == int(valor):
        return f"{int(valor):,}".replace(",", ".")
    entero, _, decimales = f"{valor:,.2f}".partition(".")
    return entero.replace(",", ".") + "," + decimales.rstrip("0")


def _metrica_producto(interno: dict) -> tuple[float, str]:
    """(cantidad_de_metros, unidad) de un producto — M² para backlight
    (Alto×Ancho×Cantidad), ML para el resto (misma fórmula que
    core.precios, pero acá es una medida física, no un costo)."""
    if "tela" in interno:
        area = interno.get("alto", 0.0) * interno.get("ancho", 0.0) * interno.get("cantidad", 0)
        return area, "M²"
    ancho_tela = TEXTILES_ANCHOS.get(interno.get("textil", ""))
    _, ml = calcular_ml(interno, ancho_tela)
    return (ml or 0.0), "ML"


def _fila_producto(p: dict, interno: dict) -> tuple[str, float, str]:
    """Fila de la tabla de productos (sin precios). Devuelve el HTML de la
    fila, más (metros, unidad) para acumular en los totales."""
    cantidad = p.get("Cantidad", 0)
    tema = p.get("Tema", "").strip() or "—"
    medidas = f"{_fmt_medida(p.get('Ancho', 0))} × {_fmt_medida(p.get('Alto', 0))} m"
    metros, unidad = _metrica_producto(interno)

    if "Caja" in p:
        caja = p.get("Caja")
        con_caja = isinstance(caja, dict)
        if con_caja:
            nombre = f"Backlight + Caja · {p.get('Tela', '')}"
            detalle = caja.get("perfil", "")
        else:
            nombre = f"Backlight · {p.get('Tela', '')}"
            detalle = "Solo tela impresa"
        extras_html = ""
    else:
        nombre = p.get("producto", "")
        detalle = p.get("Tela", "")
        # Los ajustes manuales (montos escritos directo, ver
        # core.precios.parsear_valor_manual) no son un material real — no
        # se muestran acá, la OP es solo para producción.
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

    fila = f"""      <tr>
        <td>
          <div class="prod-nombre">{nombre}</div>
          <div class="prod-detalle">{detalle}</div>
          {extras_html}
        </td>
        <td>{medidas}</td>
        <td class="num">{cantidad}</td>
        <td>{tema}</td>
        <td class="num">{_fmt_cantidad(metros)} {unidad}</td>
      </tr>"""
    return fila, metros, unidad


def _bloque_valores(titulo: str, filas: list[tuple[str, str]]) -> str:
    """Bloque <div class="mat-bloque"> con nombre + cantidad (Textiles,
    Materiales de caja) — "" (nada) si la OP no usa nada de ese tipo, en
    vez de mostrar una tabla vacía."""
    if not filas:
        return ""
    cuerpo = "\n".join(f"        <tr><td>{nombre}</td><td>{valor}</td></tr>" for nombre, valor in filas)
    return f"""      <div class="mat-bloque">
        <h3>{titulo}</h3>
        <table>
{cuerpo}
        </table>
      </div>"""


def _bloque_lista(titulo: str, nombres: list[str]) -> str:
    """Bloque <div class="mat-bloque"> solo con nombres, sin cantidades
    (Estructuras, Terminaciones) — "" si no hay ninguna."""
    if not nombres:
        return ""
    cuerpo = "\n".join(f'        <div class="mat-item">{nombre}</div>' for nombre in sorted(nombres))
    return f"""      <div class="mat-bloque">
        <h3>{titulo}</h3>
{cuerpo}
      </div>"""


def _recuento_materiales(productos_raw: list[dict], productos_internos: list[dict]):
    """
    Recorre todos los productos de la OP y arma 4 recuentos:
    - textiles: {nombre_tela: {"ML": total, "M²": total}}
    - estructuras: {nombre: {"ML": total, "unidades": total}} — ML para las
      que cobran por valorML, unidades (Cantidad del producto) para las
      que cobran por valorUNIT.
    - terminaciones: {nombre: total_ML}
    - caja: {(material, tipo): cantidad} — Perfil/Traseras/Luces 1/Luces 2/FP
      de los productos backlight, sumado entre todos.
    Todo en cantidades físicas, nunca en plata (core.precios no se usa acá).
    """
    textiles: dict[str, dict[str, float]] = {}
    estructuras: dict[str, dict[str, float]] = {}
    terminaciones: dict[str, float] = {}
    caja: dict[tuple[str, str], float] = {}

    for p, interno in zip(productos_raw, productos_internos):
        metros, unidad = _metrica_producto(interno)

        if "tela" in interno:
            tela = interno.get("tela", "")
            slot = textiles.setdefault(tela, {"ML": 0.0, "M²": 0.0})
            slot[unidad] += metros

            cant = interno.get("cantidad", 0)
            ancho = interno.get("ancho", 0.0)
            alto = interno.get("alto", 0.0)
            ml_perfil = ((ancho * 2) + (alto * 2)) / 6 * cant

            caja_dict = p.get("Caja")
            if isinstance(caja_dict, dict):
                if caja_dict.get("perfil"):
                    clave = ("Perfil", caja_dict["perfil"])
                    caja[clave] = caja.get(clave, 0.0) + ml_perfil
                for campo, etiqueta in (("traseras", "Traseras"), ("luces_1", "Luces 1"), ("luces_2", "Luces 2")):
                    info = caja_dict.get(campo)
                    if info and info.get("tipo") and info.get("cantidad_total"):
                        clave = (etiqueta, info["tipo"])
                        caja[clave] = caja.get(clave, 0.0) + info["cantidad_total"]
                fp = caja_dict.get("fp")
                if fp and fp.get("tipo") and fp.get("cantidad_total"):
                    clave = ("FP", fp["tipo"])
                    caja[clave] = caja.get(clave, 0.0) + fp["cantidad_total"]
            elif isinstance(caja_dict, str) and caja_dict.strip() and caja_dict.strip().lower() != "sin caja":
                clave = ("Perfil", caja_dict.strip())
                caja[clave] = caja.get(clave, 0.0) + ml_perfil
        else:
            tela = interno.get("textil", "")
            slot = textiles.setdefault(tela, {"ML": 0.0, "M²": 0.0})
            slot[unidad] += metros

            cant = interno.get("cantidad", 0)
            # Los ajustes manuales (ver core.precios.parsear_valor_manual)
            # no son un material real, se excluyen del recuento.
            for nombre in interno.get("estructuras", []):
                if parsear_valor_manual(nombre) is not None:
                    continue
                valores = ESTRUCTURAS_VALORES.get(nombre)
                slot_e = estructuras.setdefault(nombre, {"ML": 0.0, "unidades": 0.0})
                if valores and "valorUNIT" in valores:
                    slot_e["unidades"] += cant
                else:
                    slot_e["ML"] += metros
            for nombre in interno.get("terminaciones", []):
                if parsear_valor_manual(nombre) is not None:
                    continue
                terminaciones[nombre] = terminaciones.get(nombre, 0.0) + metros

    return textiles, estructuras, terminaciones, caja


def _html_textiles(textiles: dict) -> str:
    filas = []
    for nombre, cant in sorted(textiles.items()):
        partes = []
        if cant["ML"]:
            partes.append(f"{_fmt_cantidad(cant['ML'])} ML")
        if cant["M²"]:
            partes.append(f"{_fmt_cantidad(cant['M²'])} M²")
        filas.append((nombre, " · ".join(partes) or "—"))
    return _bloque_valores("Textiles", filas)


def _html_estructuras(estructuras: dict) -> str:
    return _bloque_lista("Estructuras", list(estructuras.keys()))


def _html_terminaciones(terminaciones: dict) -> str:
    return _bloque_lista("Terminaciones", list(terminaciones.keys()))


def _html_caja(caja: dict) -> str:
    filas = []
    for (material, tipo), cant in sorted(caja.items()):
        unidad = "ML" if material in ("Perfil",) else ("planchas" if material == "Traseras" else "un.")
        filas.append((f"{material} · {tipo}", f"{_fmt_cantidad(cant)} {unidad}"))
    return _bloque_valores("Materiales de caja", filas)


def generar_html(op: dict) -> Path:
    """Genera el HTML de la OP y lo deja guardado en carpeta_html() (de
    core.repositorio_ops). Devuelve la ruta del archivo."""
    plantilla = RUTA_PLANTILLA.read_text(encoding="utf-8")

    numero = op.get("Cotizacion", "")
    productos_raw = op.get("productos", [])
    productos_internos = [producto_desde_json(p) for p in productos_raw]

    contacto = op.get("Contacto", "")
    email = op.get("Email", "")
    contacto_email = " · ".join(x for x in (contacto, email) if x)

    descripcion = op.get("Descripcion", "").strip()
    descripcion_bloque = (
        f'<div class="descripcion"><b>Descripción</b>\n    {descripcion}\n  </div>'
        if descripcion else ""
    )

    filas_html = []
    total_cantidad = 0
    total_ml = 0.0
    total_m2 = 0.0
    for p, interno in zip(productos_raw, productos_internos):
        fila, metros, unidad = _fila_producto(p, interno)
        filas_html.append(fila)
        total_cantidad += p.get("Cantidad", 0)
        if unidad == "ML":
            total_ml += metros
        else:
            total_m2 += metros

    partes_total_metros = []
    if total_ml:
        partes_total_metros.append(f"{_fmt_cantidad(total_ml)} ML")
    if total_m2:
        partes_total_metros.append(f"{_fmt_cantidad(total_m2)} M²")
    total_metros_txt = " · ".join(partes_total_metros) or "—"

    textiles, estructuras, terminaciones, caja = _recuento_materiales(productos_raw, productos_internos)

    bloques = [
        _html_textiles(textiles),
        _html_estructuras(estructuras),
        _html_terminaciones(terminaciones),
        _html_caja(caja),
    ]
    bloques = [b for b in bloques if b]  # solo los tipos de material que la OP realmente usa
    seccion_materiales = (
        f'  <div class="materiales">\n    <div class="mat-grid">\n'
        f'{chr(10).join(bloques)}\n    </div>\n  </div>'
        if bloques else ""
    )

    reemplazos = {
        "{{numero}}":           str(numero),
        "{{fecha_ingreso}}":    op.get("Fecha_ingreso", ""),
        "{{fecha_entrega}}":    op.get("Fecha_entrega", ""),
        "{{empresa}}":          op.get("Empresa", ""),
        "{{contacto_email}}":   contacto_email,
        "{{descripcion_bloque}}": descripcion_bloque,
        "{{filas_productos}}":  "\n".join(filas_html),
        "{{total_cantidad}}":   str(total_cantidad),
        "{{total_metros}}":     total_metros_txt,
        "{{seccion_materiales}}": seccion_materiales,
    }
    html = plantilla
    for placeholder, valor in reemplazos.items():
        html = html.replace(placeholder, str(valor))

    destino = carpeta_html() / f"{numero}.html"
    destino.write_text(html, encoding="utf-8")
    return destino
