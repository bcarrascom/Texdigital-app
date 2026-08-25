"""
ui/api_ver_cotizacion.py
Lógica de ver-cotizacion.html — instanciada una sola vez por
ui.api_app.ApiApp (ver docstring de ese módulo). Ya no navega por su
cuenta: eliminar_cotizacion/aprobar_cotizacion devuelven éxito/fracaso y
es ApiApp quien decide a dónde ir después.
"""

import webbrowser

from core.repositorio_cotizaciones import (
    cargar_cotizacion,
    eliminar_cotizacion as _eliminar_cotizacion,
    listar_cotizaciones,
    producto_desde_json,
    recalcular_descuentos,
)
from core.precios import costo_producto, costo_cotizacion, ml_o_area_facturable_por_producto
from core.presentar_cotizacion import generar_html
from ui.dialogo_aprobar import promover_a_op


def _iso_a_dma(iso: str) -> str:
    """"2026-08-23" -> "23/08/2026" (los <input type=date> del HTML dan
    ISO; promover_a_op/el resto del sistema usa dd/mm/aaaa)."""
    anio, mes, dia = iso.split("-")
    return f"{dia}/{mes}/{anio}"


def _producto_a_json_pantalla(p_json: dict, p_interno: dict, costo: dict) -> dict:
    """Producto en el shape que espera ver-cotizacion.html — mismos
    campos independiente del tipo, vacíos los que no correspondan."""
    es_bl = "tela" in p_interno
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
        "ml":            None if es_bl else costo["ml_o_area"],
        "m2":            costo["ml_o_area"] if es_bl else None,
        "total":         costo["total"],
    }


class ApiVerCotizacion:

    def contexto_extra(self, numero) -> dict:
        return {"numero": int(numero) if numero is not None else None}

    def numero_adyacente(self, numero, direccion: str) -> int | None:
        """Flechas ←/→ de ver-cotizacion.html: el número de la cotización
        siguiente/anterior en el mismo orden en que ya se listan hoy en el
        menú (listar_cotizaciones(): más nueva primero) — con vuelta (de
        la más antigua salta a la más nueva y viceversa). None si `numero`
        no está en la lista o no hay ninguna otra cotización guardada."""
        numeros = [c["numero"] for c in listar_cotizaciones()]
        numero = int(numero) if numero is not None else None
        if numero not in numeros or len(numeros) < 2:
            return None
        i = numeros.index(numero)
        paso = 1 if direccion == "siguiente" else -1
        return numeros[(i + paso) % len(numeros)]

    def obtener_cotizacion(self, numero) -> dict | None:
        datos = cargar_cotizacion(int(numero))
        if datos is None:
            return None
        datos = recalcular_descuentos(datos)  # deja Neto/NetoTotal/IVA/Total al día

        productos_json = datos.get("productos", [])
        productos_internos = [producto_desde_json(p) for p in productos_json]
        facturables = ml_o_area_facturable_por_producto(productos_internos)
        costos = [
            costo_producto(p, ml_o_area_facturable=f)
            for p, f in zip(productos_internos, facturables)
        ]

        impresion     = sum(c["costo_impresion"] for c in costos)
        estructuras   = sum(c.get("costo_estructuras", 0.0) for c in costos)
        terminaciones = sum(c.get("costo_terminaciones", 0.0) for c in costos)

        despacho = datos.get("Despacho")
        instalacion = datos.get("Instalacion")
        descuento_pct = datos.get("Descuento", 0.0) or 0.0
        totales = costo_cotizacion(productos_internos, descuento_pct,
                                    despacho=despacho or 0.0, instalacion=instalacion or 0.0)

        # Mismo criterio que core.presentar_cotizacion.generar_html: si
        # ganó el descuento automático por volumen, se muestra SU %, no el
        # manual del contacto (que en ese caso no fue el que se aplicó).
        # descuento_textil_pct puede salir con muchos decimales (es un %
        # derivado de un monto en pesos, ver core.precios.descuento_textil)
        # — se redondea a 1 decimal para mostrar, la pantalla lo interpola
        # directo sin formatear (ver ver-cotizacion.html).
        if totales["fuente_descuento"] == "textil":
            descuento_pct_mostrado = round(totales["descuento_textil_pct"], 1)
        else:
            descuento_pct_mostrado = descuento_pct

        return {
            "numero":       datos.get("Cotizacion"),
            "nombre":       datos.get("Nombre", ""),
            "empresa":      datos.get("Empresa", ""),
            "rut":          datos.get("RUT", ""),
            "razon_social": datos.get("Razon Social", ""),
            "contacto":     datos.get("Contacto", ""),
            "email":        datos.get("Email", ""),
            "condicion":    datos.get("Condicion de pago", ""),
            "fecha":        datos.get("Fecha", ""),
            "descripcion":  datos.get("Descripcion", ""),
            "totales": {
                "impresion":       impresion or None,
                "estructuras":     estructuras or None,
                "terminaciones":   terminaciones or None,
                "despacho":        despacho,
                "instalacion":     instalacion,
                "neto":            totales["neto"],
                "descuento_pct":   descuento_pct_mostrado,
                "descuento_monto": totales["descuento"],
                "fuente_descuento": totales["fuente_descuento"],
                "neto_total":      totales["neto_total"],
                "iva_pct":         19,
                "iva":             totales["iva"],
                "total":           totales["total"],
            },
            "productos": [
                _producto_a_json_pantalla(pj, pi, c)
                for pj, pi, c in zip(productos_json, productos_internos, costos)
            ],
        }

    def eliminar_cotizacion(self, numero) -> bool:
        return _eliminar_cotizacion(int(numero))

    def imprimir_cotizacion(self, numero) -> None:
        datos = cargar_cotizacion(int(numero))
        if datos is None:
            return
        datos = recalcular_descuentos(datos)
        ruta_html = generar_html(datos)
        webbrowser.open(ruta_html.as_uri())

    def aprobar_cotizacion(self, numero, ingreso, entrega) -> bool:
        datos = cargar_cotizacion(int(numero))
        if datos is None:
            return False
        promover_a_op(datos, _iso_a_dma(ingreso), _iso_a_dma(entrega))
        return True
