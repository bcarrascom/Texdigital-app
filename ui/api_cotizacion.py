"""
ui/api_cotizacion.py
Lógica de nueva-cotizacion.html — instanciada una sola vez por
ui.api_app.ApiApp (ver docstring de ese módulo). La más grande de las 5:
fusiona lo que antes eran seis pantallas Tkinter distintas en una sola,
donde CADA producto elige su tipo (estándar/backlight) — habilitando
cotizaciones mixtas.

Esquema del producto tal como lo manda/espera el JS ("p", ver
productoVacio() en nueva-cotizacion.html) — DISTINTO del esquema interno
que usa core/precios.py y core/repositorio_cotizaciones.py:
  tipo: "estandar" | "backlight"
  producto, textil, impresion, estructuras[], terminaciones[]   (estándar)
  tela, perfil, luces_1, luces_2, terminaciones_caja             (backlight)
  ancho, alto, cantidad   — STRINGS con coma decimal, no float/int
  tema, obs, forzar, calc
_producto_a_interno()/_interno_a_producto_frontend() convierten entre los
dos — mismo rol que mapear_producto()/producto_desde_json() (esquema
interno ↔ JSON guardado), pero para el esquema del NAVEGADOR.
"""

import re
import webbrowser
from datetime import datetime

from core.repositorio import (
    PRODUCTOS, TEXTILES, TEXTILES_ANCHOS,
    ESTRUCTURAS_LEGADO, TERMINACIONES_LEGADO,
    ESTRUCTURAS_LEGADO_VALORES, TERMINACIONES_LEGADO_VALORES,
    PERFILES, LUCES, FUENTES_PODER,
    cargar_clientes, cargar_contactos, guardar_cliente, guardar_contacto,
)
from core.calculo_cajas import calcular_caja
from core.precios import costo_producto, costo_cotizacion
from core.repositorio_cotizaciones import (
    cargar_cotizacion, guardar_cotizacion as _guardar_cotizacion_repo,
    mapear_producto, producto_desde_json, siguiente_numero, numero_en_uso,
)
from core.repositorio_pendientes import (
    guardar_pendiente, cargar_pendiente, eliminar_pendiente, nuevo_id,
)
from core.repositorio_inventario import calcular_faltantes
from core.presentar_cotizacion import generar_html

SIN_CAJA = "Sin caja"

# Telas backlight: mismo recorte curado que ui/cotizador_backlight.py
# (_NOMBRES_TELAS_BACKLIGHT) — no CUALQUIER textil sirve para backlight
# (necesita ser translúcido), así que no se reusa la lista completa de
# TEXTILES acá.
_TELAS_BACKLIGHT = [
    "Popelina 155", "Popelina 310", "Pearl 155", "Pearl 310", "Pearl 160 HP",
]


def _num(v, default=0.0) -> float:
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return default


def _ent(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def _iso_a_dma(iso: str) -> str:
    if not iso:
        return ""
    try:
        anio, mes, dia = iso.split("-")
        return f"{dia}/{mes}/{anio}"
    except ValueError:
        return ""


def _dma_a_iso(dma: str) -> str:
    if not dma:
        return ""
    try:
        dia, mes, anio = dma.split("/")
        return f"{anio}-{mes}-{dia}"
    except ValueError:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# Frontend (p) ↔ interno (core/precios.py, core/calculo_cajas.py)
# ══════════════════════════════════════════════════════════════════════════════

def _empaquetar_caja(tabla: dict, perfil: str) -> dict:
    """Arma el dict que se guarda como datos["caja"] a partir del resultado
    de calcular_caja() — mismo shape que ui.cotizador_backlight.
    _valor_caja_guardado(), reescrito acá como función pura (sin estado de
    ventana Tkinter de por medio)."""
    filas_por_material = {f["material"]: f for f in tabla["filas"]}

    def _sub(material):
        f = filas_por_material[material]
        return {"tipo": f["tipo"], "cantidad_x_caja": f["cantidad_x_caja"],
                "cantidad_total": f["cantidad_total"]}

    fp_sub = _sub("FP")
    fp_sub["watts_unidad"] = tabla["fp"]["watts_unidad"] if tabla["fp"] else None

    return {
        "perfil": perfil,
        "watts": tabla["watts"],
        "lado_corto": tabla["lado_corto"],
        "lado_largo": tabla["lado_largo"],
        "mts_lineales_x_caja": tabla["mts_lineales_x_caja"],
        "traseras": _sub("Traseras"),
        "luces_1": _sub("Luces 1"),
        "luces_2": _sub("Luces 2"),
        "fp": fp_sub,
        "obs": "",
    }


def _producto_a_interno(p: dict) -> dict:
    """Convierte un producto del frontend (p) al esquema interno que usan
    core.precios.costo_producto / core.repositorio_cotizaciones.
    mapear_producto — el mismo que ya usan ui/cotizacion.py y
    ui/cotizador_backlight.py."""
    ancho = _num(p.get("ancho"))
    alto = _num(p.get("alto"))
    cantidad = _ent(p.get("cantidad"), 1)
    tema = (p.get("tema") or "").strip()
    obs = (p.get("obs") or "").strip()

    if p.get("tipo") == "backlight":
        perfil = p.get("perfil") or SIN_CAJA
        caja = SIN_CAJA
        if perfil != SIN_CAJA and ancho > 0 and alto > 0:
            luces1 = p.get("luces_1") or ""
            luces2 = p.get("luces_2") or "sin luces"
            tabla = calcular_caja(ancho, alto, cantidad or 1, perfil, luces1, luces2, LUCES, FUENTES_PODER)
            caja = _empaquetar_caja(tabla, perfil)
        return {
            "tela": p.get("tela", ""), "caja": caja,
            "ancho": ancho, "alto": alto, "cantidad": cantidad,
            "tema": tema, "obs": obs,
        }

    return {
        "producto": (p.get("producto") or "").strip(),
        "textil": (p.get("textil") or "").strip(),
        "estructuras": list(p.get("estructuras") or []),
        "terminaciones": list(p.get("terminaciones") or []),
        "impresion": p.get("impresion") or "Cara única",
        "ancho": ancho, "alto": alto, "cantidad": cantidad,
        "tema": tema, "obs": obs,
    }


def _interno_a_frontend(interno: dict) -> dict:
    """Inversa aproximada de _producto_a_interno — para pre-llenar
    estado.productos al editar una cotización guardada o retomar una
    pendiente vieja (formato Tkinter). "calc" queda en None a propósito:
    la pantalla lo recalcula sola al construir el carril (ver
    construirCarril()/recalcular() en nueva-cotizacion.html — cada panel
    llama a calcular_producto() apenas se arma, no hace falta mandarlo
    precalculado)."""
    base = {
        "tipo": "estandar", "producto": "", "textil": "", "impresion": "Cara única",
        "estructuras": [], "terminaciones": [],
        "tela": "", "perfil": SIN_CAJA, "luces_1": "M12", "luces_2": "sin luces",
        "terminaciones_caja": "CAJA TERMINADA",
        "ancho": "", "alto": "", "cantidad": "1", "tema": "", "obs": "",
        "forzar": False, "calc": None,
    }
    ancho = interno.get("ancho", 0.0)
    alto = interno.get("alto", 0.0)
    cantidad = interno.get("cantidad", 1)

    if "tela" in interno:
        caja = interno.get("caja")
        con_caja = isinstance(caja, dict)
        base.update({
            "tipo": "backlight",
            "tela": interno.get("tela", ""),
            "perfil": (caja.get("perfil") if con_caja else caja) or SIN_CAJA,
            "luces_1": (caja.get("luces_1") or {}).get("tipo", "M12") if con_caja else "M12",
            "luces_2": (caja.get("luces_2") or {}).get("tipo", "sin luces") if con_caja else "sin luces",
            "ancho": str(ancho), "alto": str(alto), "cantidad": str(cantidad),
            "tema": interno.get("tema", ""), "obs": interno.get("obs", ""),
        })
        return base

    base.update({
        "tipo": "estandar",
        "producto": interno.get("producto", ""),
        "textil": interno.get("textil", ""),
        "impresion": interno.get("impresion", "Cara única"),
        "estructuras": list(interno.get("estructuras", [])),
        "terminaciones": list(interno.get("terminaciones", [])),
        "ancho": str(ancho), "alto": str(alto), "cantidad": str(cantidad),
        "tema": interno.get("tema", ""), "obs": interno.get("obs", ""),
    })
    return base


def _error_medida(interno: dict, ancho: float, alto: float) -> tuple[str | None, float | None]:
    """(error, ancho_max) — mismo criterio que ui/cotizacion.py y
    ui/cotizador_backlight.py: el lado corto no puede exceder el ancho
    máximo de impresión del textil/tela elegido."""
    nombre = interno.get("tela") if "tela" in interno else interno.get("textil")
    ancho_max = TEXTILES_ANCHOS.get(nombre or "")
    if ancho_max is None:
        return None, None
    lado_corto = min(ancho, alto)
    if lado_corto > ancho_max:
        return (
            f"El lado corto ({lado_corto:.2f} m) excede el ancho máximo "
            f"del textil ({ancho_max:.2f} m).",
            ancho_max,
        )
    return None, ancho_max


class ApiCotizacion:

    # ── Contexto / arranque ──────────────────────────────────────────────────

    def contexto_extra(self, editar=None, pendiente=None) -> dict:
        editar = int(editar) if editar else None
        pendiente = pendiente or None

        ctx = {
            "fecha_iso": datetime.now().strftime("%Y-%m-%d"),
            "numero_sugerido": str(siguiente_numero()),
            "numero_editando": None,
            "estado": None,
        }

        if editar is not None:
            datos = cargar_cotizacion(editar)
            if datos is not None:
                ctx["estado"] = self._estado_desde_json(datos)
                ctx["numero_sugerido"] = str(datos.get("Cotizacion", ""))
                # El propio número de la cotización que se está editando no
                # cuenta como choque contra sí mismo — ver numero_disponible.
                ctx["numero_editando"] = ctx["numero_sugerido"]
        elif pendiente is not None:
            datos = cargar_pendiente(pendiente)
            if datos is not None:
                ctx["estado"] = self._estado_desde_pendiente(datos)

        return ctx

    def _estado_desde_json(self, datos: dict) -> dict:
        productos_json = datos.get("productos", [])
        return {
            "id": None,
            "nombre_trabajo": datos.get("Nombre", ""),
            "despacho": datos.get("Despacho"),
            "instalacion": datos.get("Instalacion"),
            "cliente": {
                "empresa": datos.get("Empresa", ""),
                "rut": datos.get("RUT", ""),
                "razon_social": datos.get("Razon Social", ""),
                "contacto": datos.get("Contacto", ""),
                "email": datos.get("Email", ""),
                "descuento": str(datos.get("Descuento", 0) or 0),
                "condicion": datos.get("Condicion de pago", ""),
                "fecha": _dma_a_iso(datos.get("Fecha", "")),
                "numero": str(datos.get("Cotizacion", "")),
                "descripcion": datos.get("Descripcion", ""),
            },
            "productos": [_interno_a_frontend(producto_desde_json(p)) for p in productos_json],
            "actual": 0,
        }

    def _estado_desde_pendiente(self, datos: dict) -> dict:
        if "cliente" in datos:
            # Formato nuevo (esta misma pantalla) — guardar_progreso() lo
            # guarda tal cual lo manda el JS, así que ya calza el shape.
            return datos
        # Formato viejo (ui/cotizacion.py, ui/cotizador_backlight.py):
        # "productos" es una lista con huecos (None = todavía sin llenar) y
        # cada entrada ya viene en esquema JSON (mapear_producto), no en
        # esquema frontend — convertir lo que haya y avisar que puede
        # faltar algo (el "producto_parcial" de a medio llenar del formato
        # viejo no tiene equivalente acá, se pierde ese detalle puntual).
        productos = [
            _interno_a_frontend(producto_desde_json(p)) if p is not None
            else _interno_a_frontend({"producto": "", "textil": "", "estructuras": [],
                                       "terminaciones": [], "impresion": "Cara única",
                                       "ancho": 0.0, "alto": 0.0, "cantidad": 1,
                                       "tema": "", "obs": ""})
            for p in datos.get("productos", [])
        ] or [_interno_a_frontend({"producto": "", "textil": "", "estructuras": [],
                                    "terminaciones": [], "impresion": "Cara única",
                                    "ancho": 0.0, "alto": 0.0, "cantidad": 1,
                                    "tema": "", "obs": ""})]
        return {
            "id": datos.get("id"),
            "nombre_trabajo": datos.get("nombre_trabajo", ""),
            "despacho": datos.get("despacho"),
            "instalacion": datos.get("instalacion"),
            "cliente": {
                "empresa": "", "rut": "", "razon_social": "", "contacto": "", "email": "",
                "descuento": "0", "condicion": "", "fecha": "", "numero": "", "descripcion": "",
            },
            "productos": productos,
            "actual": 0,
        }

    def obtener_catalogos(self) -> dict:
        return {
            "productos": PRODUCTOS,
            "textiles": TEXTILES,
            "textiles_anchos": TEXTILES_ANCHOS,
            "telas_backlight": _TELAS_BACKLIGHT,
            "estructuras": ESTRUCTURAS_LEGADO,
            "terminaciones": TERMINACIONES_LEGADO,
            # Nombres que se cobran POR UNIDAD (valorUNIT) — las que son por
            # ML necesitan el ancho del textil para convertirse en metros
            # lineales, así que en un producto sin textil solo se pueden
            # agregar estas (ver nueva-cotizacion.html::agregar()).
            "estructuras_unit": [
                n for n in ESTRUCTURAS_LEGADO if "valorUNIT" in ESTRUCTURAS_LEGADO_VALORES.get(n, {})
            ],
            "terminaciones_unit": [
                n for n in TERMINACIONES_LEGADO if "valorUNIT" in TERMINACIONES_LEGADO_VALORES.get(n, {})
            ],
            "perfiles": PERFILES,
            "luces": [l["corto"] for l in LUCES],
            "clientes": [
                {"empresa": c.get("empresa", ""), "rut": c.get("rut", ""),
                 "razon_social": c.get("razon_social", "")}
                for c in cargar_clientes()
            ],
            "contactos": [
                {"contacto": c.get("contacto", ""), "email": c.get("email", ""),
                 "descuento": c.get("descuento", ""), "condicion": c.get("condicion", "")}
                for c in cargar_contactos()
            ],
        }

    # ── Cálculo en vivo ───────────────────────────────────────────────────────

    def calcular_producto(self, p: dict) -> dict | None:
        ancho = _num(p.get("ancho"), 0.0)
        alto = _num(p.get("alto"), 0.0)
        cantidad = _ent(p.get("cantidad"), 0)
        if not (ancho > 0 and alto > 0 and cantidad > 0):
            return None

        interno = _producto_a_interno(p)
        error, ancho_max = _error_medida(interno, ancho, alto)
        costo = costo_producto(interno)

        if p.get("tipo") == "backlight":
            materiales = []
            perfil = p.get("perfil") or SIN_CAJA
            if perfil != SIN_CAJA:
                luces1 = p.get("luces_1") or ""
                luces2 = p.get("luces_2") or "sin luces"
                tabla = calcular_caja(ancho, alto, cantidad, perfil, luces1, luces2, LUCES, FUENTES_PODER)
                materiales = [
                    {"material": f["material"], "tipo": f["tipo"],
                     "cantidad_x_caja": f["cantidad_x_caja"], "cantidad_total": f["cantidad_total"]}
                    for f in tabla["filas"]
                ]
                watts = tabla["watts"]
            else:
                watts = 0
            return {
                "m2": costo["ml_o_area"],
                "watts": watts,
                "materiales": materiales,
                "ancho_max": ancho_max,
                "error": error,
                "valor_unitario": costo["valor_unitario"],
                "total": costo["total"],
            }

        return {
            "ml": costo["ml_o_area"],
            "costo_impresion": costo["costo_impresion"],
            "costo_extras": costo["costo_estructuras"] + costo["costo_terminaciones"],
            "detalle_estructuras": costo["detalle_estructuras"],
            "detalle_terminaciones": costo["detalle_terminaciones"],
            "total": costo["total"],
            "valor_unitario": costo["valor_unitario"],
            "ancho_max": ancho_max,
            "error": error,
        }

    def numero_disponible(self, numero, propio=None) -> bool:
        """Chequeo en vivo del campo N° de cotización (nueva-cotizacion.html
        — gatea el botón "bajar a productos", ver revisarDatos()): False si
        ya pertenece a otra cotización u OP. `propio` es el número con el
        que esta pantalla arrancó (editando una cotización existente,
        ctx.numero_editando) — no cuenta como choque contra sí mismo."""
        try:
            numero = int(numero)
        except (TypeError, ValueError):
            return False
        propio = int(propio) if propio not in (None, "") else None
        return not numero_en_uso(numero, excluir=propio)

    def verificar_materiales(self, productos: list) -> list[dict]:
        """Aviso "Materiales insuficientes" del resumen y diálogo previo a
        Guardar/Guardar y abrir (ver nueva-cotizacion.html) — solo mira
        productos con medidas/cantidad ya cargadas (los vacíos no piden
        tela todavía). No bloquea nada acá: guardar una cotización con
        stock insuficiente sigue permitido, el único bloqueo real es al
        aprobarla (ver ApiVerCotizacion.aprobar_cotizacion)."""
        productos_internos = [
            _producto_a_interno(p) for p in productos
            if _num(p.get("ancho")) > 0 and _num(p.get("alto")) > 0 and _ent(p.get("cantidad")) > 0
        ]
        return calcular_faltantes(productos_internos)

    # ── Guardado ──────────────────────────────────────────────────────────────

    def guardar_progreso(self, estado: dict) -> dict:
        id_ = estado.get("id") or nuevo_id()
        estado = dict(estado)
        estado["id"] = id_
        guardar_pendiente(estado)
        ahora = datetime.now()
        return {"id": id_, "guardado_en": ahora.strftime("%d/%m/%Y %H:%M")}

    def guardar_cotizacion(self, estado: dict, abrir: bool = False) -> dict:
        cliente = estado.get("cliente") or {}
        numero_str = str(cliente.get("numero", ""))
        if not re.fullmatch(r"\d{4}", numero_str):
            return {"error": "El N° de cotización tiene que tener 4 dígitos."}
        empresa = (cliente.get("empresa") or "").strip()
        if not empresa:
            return {"error": "Falta la Empresa."}

        numero = int(numero_str)
        productos_frontend = estado.get("productos") or []
        productos_internos = [_producto_a_interno(p) for p in productos_frontend]

        despacho = estado.get("despacho")
        instalacion = estado.get("instalacion")
        descuento_pct = _num(cliente.get("descuento"), 0.0)
        totales = costo_cotizacion(productos_internos, descuento_pct,
                                    despacho=despacho or 0.0, instalacion=instalacion or 0.0)

        fecha = _iso_a_dma(cliente.get("fecha", "")) or datetime.now().strftime("%d/%m/%Y")
        json_dict = {
            "Cotizacion": numero,
            "Nombre": estado.get("nombre_trabajo", ""),
            "Fecha": fecha,
            "Empresa": empresa,
            "RUT": cliente.get("rut", ""),
            "Razon Social": cliente.get("razon_social", ""),
            "Contacto": cliente.get("contacto", ""),
            "Email": cliente.get("email", ""),
            "Descuento": descuento_pct,
            "Condicion de pago": cliente.get("condicion", ""),
            "Descripcion": cliente.get("descripcion", ""),
            "productos": [mapear_producto(p) for p in productos_internos],
            "Neto": totales["neto"],
            "NetoTotal": totales["neto_total"],
            "IVA": totales["iva"],
            "Total": totales["total"],
        }
        if despacho is not None:
            json_dict["Despacho"] = despacho
        if instalacion is not None:
            json_dict["Instalacion"] = instalacion

        _guardar_cotizacion_repo(json_dict)

        if estado.get("id"):
            eliminar_pendiente(estado["id"])

        if abrir:
            ruta_html = generar_html(json_dict)
            webbrowser.open(ruta_html.as_uri())

        return {"numero": numero}

    def guardar_cliente(self, empresa, rut, razon_social) -> bool:
        return guardar_cliente(empresa, rut, razon_social)

    def guardar_contacto(self, contacto, email, descuento, condicion) -> None:
        guardar_contacto(contacto, email, descuento, condicion)
