"""
core/correos.py
Los correos que manda la app (pedido de Bruno, 2026-11-09; el plan entero
está en CLAUDE.md, "Correos automáticos").

Las cotizaciones tienen dos correos distintos (Bruno, 2026-11-11), cada uno
con su asunto, su mensaje y su lista:
  · al cliente: el botón "Enviar correo" de Ver cotización le manda el PDF, y
    el cliente responde a ese correo para aprobarla o pedir cambios. Los de
    "copia" (gente de Texdigital) reciben ese mismo correo, para revisarlo.
  · aviso de cotización nueva: al crear una cotización, la gente de Texdigital
    inscrita en "cotizaciones_nuevas" recibe el PDF. En el Resumen del
    cotizador se puede sacar a alguien o sumar otro correo solo esa vez.
Las demás áreas (OPs, Inventario, Despachos) por ahora solo guardan su lista.

Los correos automáticos (los que salen solos, como el aviso de cotización
nueva) se apagan con un switch general y uno por sección (Bruno, 2026-11-11;
ver automatico_activo). Los que se mandan a mano (el correo al cliente, el
correo de prueba) no dependen de esos switches.

Sale por SMTP desde la casilla de la app (sistema@texdigital.cl, en el
hosting de HostingPlus: mail.texdigital.cl, 465 con SSL o 587 con STARTTLS).
La contraseña NO va en la Dropbox ni en el código: se guarda en cada
computador, en el Administrador de credenciales de Windows o el Llavero del
Mac (core.credenciales), desde Configuración › Correos. Sin contraseña en
este computador, no se envía nada. Cada correo que sale deja además una
copia .eml en la carpeta Correos (Dropbox/SGTD/Correos/AAAA/MM; con --dev,
en DropboxDev), que se abre con Outlook o con el Correo de Windows.

Modo de prueba (encendido de fábrica): el correo no va a los destinatarios
de verdad sino a la dirección de prueba (brosky.spam@gmail.com), con
"[Prueba]" en el asunto y a quién iba al principio del mensaje. En la
versión de desarrollo (desde el código, con DropboxDev) está siempre
encendido: sus cotizaciones de prueba tienen correos de clientes inventados.

Los ajustes van en Dropbox/SGTD/Conf/correos.json (globales, ver
core.ajustes_globales):

    {"version": 1,
     "cuenta": {"remitente", "nombre", "servidor", "puerto"},
     "prueba": {"activo", "direccion"},
     "cotizaciones": {"al_cliente": bool, "asunto", "mensaje", "copia": [{"correo", "nombre"}]},
     "cotizaciones_nuevas": {"asunto", "mensaje", "para": [{"correo", "nombre"}]},
     "ops": {"asunto", "mensaje"},              (OP nueva, con el PDF; a areas.ops)
     "ops_recotizada": {"asunto", "mensaje"},   (OP recotizada; a areas.ops)
     "areas": {"ops" | "inventario" | "despachos": [{"correo", "nombre"}]},
     "automaticos": {"activo", "cotizaciones", "ops", "inventario", "despachos"}}   (bool)

Cada envío queda anotado en la cotización, en "Correos" (una lista):

    {"fecha": "2026-11-09T10:32:05", "para": [...], "copia": [...], "asunto",
     "huella", "prueba": bool, "archivo"}

"huella" es el SHA-256 del documento que se adjuntó (el HTML del que sale el
PDF). Si al volver a enviar sale la misma huella, la cotización no cambió
desde el último envío y la pantalla lo advierte.
"""

import hashlib
import html as _html
import re
import smtplib
import socket
import ssl
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import format_datetime, formataddr, make_msgid, parsedate_to_datetime
from pathlib import Path

from core import ajustes_globales, credenciales
from core.precios import formatear_clp
from core.repositorio import cargar_clientes, correo_valido, formatear_rut
from core.rutas import DATOS, _detectar_dropbox, _es_dev
from core.titulo_impresion import titulo_impresion

NOMBRE = "correos"
VERSION_FORMATO = 1

# Con qué nombre se guarda la contraseña en el almacén del sistema (la
# cuenta es el correo de la app): "SistemaGestion-correo/sistema@texdigital.cl".
SERVICIO_CREDENCIAL = "SistemaGestion-correo"

ESPERA_SMTP_S = 30

AREAS = ("ops", "inventario", "despachos")
SECCIONES = ("cuenta", "prueba", "cotizaciones", "cotizaciones_nuevas", "ops", "ops_recotizada", "automaticos")
PLANTILLAS = ("cotizaciones", "cotizaciones_nuevas", "ops", "ops_recotizada")   # las que tienen asunto y mensaje
# Las partes del programa que mandan correos automáticos, cada una con su switch.
PARTES_AUTOMATICAS = ("cotizaciones",) + AREAS

VARIABLES_COTIZACION = {
    "numero":   "El N° de la cotización",
    "cliente":  "La empresa",
    "contacto": "El contacto (o la empresa, si no tiene)",
    "trabajo":  "El nombre del trabajo",
    "total":    "El total con IVA",
    "fecha":    "La fecha de la cotización",
}

VARIABLES_OP = {
    "numero":   "El N° de la OP",
    "cliente":  "La empresa",
    "contacto": "El contacto (o la empresa, si no tiene)",
    "trabajo":  "El nombre del trabajo",
    "ingreso":  "La fecha de ingreso",
    "entrega":  "La fecha de entrega",
}

POR_DEFECTO = {
    "cuenta": {"remitente": "sistema@texdigital.cl", "nombre": "Texdigital",
               "servidor": "mail.texdigital.cl", "puerto": 465},
    "prueba": {"activo": True, "direccion": "brosky.spam@gmail.com"},
    "cotizaciones": {
        # El correo al cliente ("Enviar correo"), apagado hasta que Bruno lo
        # habilite: primero se prueban los avisos a Texdigital (2026-11-12).
        "al_cliente": False,
        "asunto": "Cotización {numero} - {cliente}",
        "mensaje": ("Hola {contacto}:\n\n"
                    "Te enviamos la cotización N° {numero}, por un total de {total} (IVA incluido). "
                    "Va adjunta en PDF.\n\n"
                    "Para aprobarla o pedirnos cambios, basta con responder este correo.\n\n"
                    "Saludos,\nTexdigital"),
        "copia": [],
    },
    "cotizaciones_nuevas": {
        "asunto": "Nueva cotización {numero} - {cliente}",
        "mensaje": ("Se creó la cotización N° {numero} de {cliente} ({trabajo}), "
                    "por un total de {total} (IVA incluido).\n\n"
                    "Va adjunta en PDF.\n\n"
                    "Correo automático del Sistema de Gestión."),
        "para": [],
    },
    # Los correos de las OPs, a los de "Reciben las OPs" (areas.ops).
    "ops": {
        "asunto": "OP {numero} - {cliente}",
        "mensaje": ("Se aprobó la cotización N° {numero} de {cliente} ({trabajo}) y pasó a OP.\n\n"
                    "Ingreso: {ingreso}\nEntrega: {entrega}\n\n"
                    "Va adjunta la OP en PDF.\n\n"
                    "Correo automático del Sistema de Gestión."),
    },
    "ops_recotizada": {
        "asunto": "OP {numero} recotizada - {cliente}",
        "mensaje": ("La OP {numero} de {cliente} ({trabajo}) se recotizó: volvió a Cotizaciones "
                    "y ya no está en producción.\n\n"
                    "No sigan trabajando en ella hasta que se apruebe de nuevo.\n\n"
                    "Correo automático del Sistema de Gestión."),
    },
    "areas": {a: [] for a in AREAS},
    "automaticos": {"activo": True, **{p: True for p in ("cotizaciones", "ops", "inventario", "despachos")}},
}


# ── Ajustes ────────────────────────────────────────────────────────────────

def _lista_correos(valor) -> list[dict]:
    filas = []
    for x in valor if isinstance(valor, list) else []:
        if isinstance(x, str):
            x = {"correo": x}
        if isinstance(x, dict):
            filas.append({"correo": " ".join(str(x.get("correo") or "").split()),
                          "nombre": " ".join(str(x.get("nombre") or "").split())})
    return filas


def prueba_forzada() -> bool:
    """La versión de desarrollo nunca le escribe a un cliente de verdad."""
    return _es_dev()


def cargar() -> dict:
    """Los ajustes, con los valores de fábrica en lo que falte."""
    guardado = ajustes_globales.leer(NOMBRE)
    a = {k: (dict(v) if isinstance(v, dict) else v) for k, v in POR_DEFECTO.items()}
    for seccion in SECCIONES:
        if isinstance(guardado.get(seccion), dict):
            a[seccion] = {**POR_DEFECTO[seccion], **guardado[seccion]}
    a["cotizaciones"]["copia"] = _lista_correos(a["cotizaciones"].get("copia"))
    a["cotizaciones_nuevas"]["para"] = _lista_correos(a["cotizaciones_nuevas"].get("para"))
    areas = guardado.get("areas") if isinstance(guardado.get("areas"), dict) else {}
    a["areas"] = {k: _lista_correos(areas.get(k)) for k in AREAS}
    a["cotizaciones"]["al_cliente"] = bool(a["cotizaciones"].get("al_cliente"))
    a["automaticos"] = {k: bool(v) for k, v in a["automaticos"].items()}
    if prueba_forzada():
        a["prueba"]["activo"] = True
    return a


def al_cliente_activo(a: dict | None = None) -> bool:
    """Si se le pueden enviar cotizaciones al cliente ("Enviar correo")."""
    return bool((a or cargar())["cotizaciones"].get("al_cliente"))


def automatico_activo(parte: str, a: dict | None = None) -> bool:
    """Si los correos automáticos de esta parte del programa ("cotizaciones",
    "ops"…) están encendidos: el switch general y el de la parte."""
    auto = (a or cargar())["automaticos"]
    return bool(auto.get("activo")) and bool(auto.get(parte, True))


def solo_lectura() -> bool:
    return ajustes_globales.es_mas_nuevo(NOMBRE, VERSION_FORMATO)


def _validar_lista(filas: list[dict], clave: str, errores: dict) -> None:
    vistos = set()
    for i, f in enumerate(filas):
        c = f["correo"].lower()
        if not correo_valido(c):
            errores[f"{clave}:{i}"] = "El correo no es válido."
        elif c in vistos:
            errores[f"{clave}:{i}"] = "Ese correo ya está en la lista."
        vistos.add(c)


def validar(a: dict) -> dict:
    """{campo: mensaje}; vacío si está todo bien. Las claves de las listas
    son "<lista>:<índice>" (p. ej. "areas.ops:2")."""
    e = {}
    cuenta, prueba, cot = a["cuenta"], a["prueba"], a["cotizaciones"]
    if not correo_valido(cuenta.get("remitente")):
        e["cuenta.remitente"] = "El correo no es válido."
    if not str(cuenta.get("nombre") or "").strip():
        e["cuenta.nombre"] = "Falta el nombre que ve el cliente."
    if not str(cuenta.get("servidor") or "").strip():
        e["cuenta.servidor"] = "Falta el servidor."
    try:
        puerto = int(cuenta.get("puerto"))
    except (TypeError, ValueError):
        puerto = 0
    if not 0 < puerto < 65536:
        e["cuenta.puerto"] = "Un número entre 1 y 65535."
    if prueba.get("activo") and not correo_valido(prueba.get("direccion")):
        e["prueba.direccion"] = "El correo no es válido."
    for seccion in PLANTILLAS:
        if not str(a[seccion].get("asunto") or "").strip():
            e[f"{seccion}.asunto"] = "Falta el asunto."
        if not str(a[seccion].get("mensaje") or "").strip():
            e[f"{seccion}.mensaje"] = "Falta el mensaje."
    _validar_lista(cot["copia"], "cotizaciones.copia", e)
    _validar_lista(a["cotizaciones_nuevas"]["para"], "cotizaciones_nuevas.para", e)
    for area in AREAS:
        _validar_lista(a["areas"][area], f"areas.{area}", e)
    return e


def guardar(datos: dict) -> dict:
    """{"ok": True} o {"ok": False, "errores": {campo: mensaje}}."""
    d = datos or {}
    a = cargar()
    for seccion in SECCIONES:
        if isinstance(d.get(seccion), dict):
            a[seccion] = {**a[seccion], **d[seccion]}
    a["cuenta"] = {k: (" ".join(str(v).split()) if isinstance(v, str) else v) for k, v in a["cuenta"].items()}
    a["prueba"]["activo"] = bool(a["prueba"].get("activo"))
    a["automaticos"] = {k: bool(v) for k, v in a["automaticos"].items() if k == "activo" or k in PARTES_AUTOMATICAS}
    a["prueba"]["direccion"] = str(a["prueba"].get("direccion") or "").strip()
    for seccion in PLANTILLAS:
        a[seccion]["asunto"] = " ".join(str(a[seccion].get("asunto") or "").split())
        a[seccion]["mensaje"] = str(a[seccion].get("mensaje") or "").strip()
    a["cotizaciones"]["copia"] = _lista_correos(a["cotizaciones"].get("copia"))
    a["cotizaciones"]["al_cliente"] = bool(a["cotizaciones"].get("al_cliente"))
    a["cotizaciones_nuevas"]["para"] = _lista_correos(a["cotizaciones_nuevas"].get("para"))
    if isinstance(d.get("areas"), dict):
        a["areas"] = {k: _lista_correos(d["areas"].get(k, a["areas"][k])) for k in AREAS}
    errores = validar(a)
    if errores:
        return {"ok": False, "errores": errores}
    try:
        a["cuenta"]["puerto"] = int(a["cuenta"]["puerto"])
        ajustes_globales.guardar(NOMBRE, a, VERSION_FORMATO)
    except ajustes_globales.AjusteMasNuevo:
        return {"ok": False, "errores": {"general": "Estos ajustes los guardó una versión más nueva de la app."}}
    return {"ok": True}


def correos_guardados(a: dict | None = None) -> list[dict]:
    """[{"correo", "nombre"}]: todos los correos de Texdigital inscritos en
    alguna lista (cotizaciones nuevas, copia de las cotizaciones, áreas), sin
    repetir. Es de donde se elige al sumar a alguien solo una vez."""
    a = a or cargar()
    vistos, lista = set(), []
    for filas in (a["cotizaciones_nuevas"]["para"], a["cotizaciones"]["copia"], *a["areas"].values()):
        for f in filas:
            clave = f["correo"].lower()
            if correo_valido(clave) and clave not in vistos:
                vistos.add(clave)
                lista.append(dict(f))
    return lista


# ── Carpeta de los correos guardados ───────────────────────────────────────

def carpeta() -> Path:
    """Dropbox/SGTD/Correos (sin Dropbox, la carpeta de datos local)."""
    dropbox = _detectar_dropbox()
    p = (dropbox / "SGTD" / "Correos") if dropbox else (DATOS / "Correos")
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Plantillas ─────────────────────────────────────────────────────────────

_VARIABLE = re.compile(r"\{(\w+)\}")


def rellenar(texto: str, valores: dict) -> str:
    """Cambia cada {variable} conocida por su valor; una que no se conoce
    queda escrita tal cual (así se nota en la vista previa)."""
    return _VARIABLE.sub(lambda m: str(valores[m.group(1)]) if m.group(1) in valores else m.group(0), texto or "")


def valores_op(datos: dict) -> dict:
    empresa = datos.get("Empresa", "")
    return {
        "numero":   datos.get("Cotizacion", ""),
        "cliente":  empresa,
        "contacto": datos.get("Contacto", "") or empresa,
        "trabajo":  datos.get("Nombre", ""),
        "ingreso":  datos.get("Fecha_ingreso", ""),
        "entrega":  datos.get("Fecha_entrega", ""),
    }


def valores_cotizacion(datos: dict) -> dict:
    empresa = datos.get("Empresa", "")
    return {
        "numero":   datos.get("Cotizacion", ""),
        "cliente":  empresa,
        "contacto": datos.get("Contacto", "") or empresa,
        "trabajo":  datos.get("Nombre", ""),
        "total":    formatear_clp(datos.get("Total") or 0),
        "fecha":    datos.get("Fecha", ""),
    }


# ── La cotización al cliente ───────────────────────────────────────────────

def _cliente_guardado(datos: dict) -> dict | None:
    """El cliente de Configuración de esta cotización: por RUT y, si no
    calza, por nombre."""
    clientes = cargar_clientes()
    rut = formatear_rut(datos.get("RUT", "") or "")
    if rut:
        c = next((c for c in clientes if formatear_rut(c.get("rut", "")) == rut), None)
        if c:
            return c
    empresa = (datos.get("Empresa", "") or "").strip().lower()
    return next((c for c in clientes if c.get("empresa", "").strip().lower() == empresa), None)


def destinatarios_sugeridos(datos: dict) -> list[dict]:
    """[{"origen": "contacto" | "cliente", "nombre", "correo"}], sin repetir
    correos: el del contacto que quedó en la cotización y el del cliente en
    Configuración › Clientes y contactos."""
    sugeridos = []
    if correo_valido(datos.get("Email")):
        sugeridos.append({"origen": "contacto", "nombre": datos.get("Contacto", "") or "Contacto",
                          "correo": datos["Email"].strip()})
    cliente = _cliente_guardado(datos)
    if cliente and correo_valido(cliente.get("email")):
        if all(s["correo"].lower() != cliente["email"].strip().lower() for s in sugeridos):
            sugeridos.append({"origen": "cliente", "nombre": cliente.get("empresa", ""),
                              "correo": cliente["email"].strip()})
    return sugeridos


def nombre_adjunto(datos: dict) -> str:
    """El mismo nombre con que se guarda al imprimir: "1004 • Trabajo Cliente.pdf"."""
    titulo = _html.unescape(titulo_impresion(datos.get("Cotizacion", ""), datos.get("Nombre", ""), datos.get("Empresa", "")))
    return f"{titulo}.pdf"


def huella(ruta_html: Path) -> str:
    return hashlib.sha256(Path(ruta_html).read_bytes()).hexdigest()


def ultimo_envio(datos: dict) -> dict | None:
    envios = datos.get("Correos")
    return envios[-1] if isinstance(envios, list) and envios else None


def _texto_a_html(texto: str) -> str:
    parrafos = [p for p in re.split(r"\n\s*\n", texto.strip()) if p.strip()]
    cuerpo = "".join(f"<p>{_html.escape(p).replace(chr(10), '<br>')}</p>" for p in parrafos)
    return ('<!doctype html><html><body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;'
            f'line-height:1.5;color:#222">{cuerpo}</body></html>')


def armar_mensaje(*, ajustes: dict, para: list[str], copia: list[str], asunto: str, mensaje: str,
                  adjunto: Path | None = None, nombre_adjunto: str = "") -> tuple[EmailMessage, list[str]]:
    """El correo listo para salir, y a quién va de verdad (en modo de prueba,
    solo a la dirección de prueba). Sin `adjunto`, va sin PDF."""
    cuenta, prueba = ajustes["cuenta"], ajustes["prueba"]
    msg = EmailMessage()
    msg["From"] = formataddr((cuenta["nombre"], cuenta["remitente"]))
    msg["Date"] = format_datetime(datetime.now().astimezone())
    msg["Message-ID"] = make_msgid(domain=cuenta["remitente"].split("@")[-1])
    if prueba.get("activo"):
        reales = [prueba["direccion"]]
        msg["To"] = prueba["direccion"]
        msg["Subject"] = f"[Prueba] {asunto}"
        msg["X-Destinatarios-Originales"] = ", ".join(para + copia)
        aviso = f"(Correo de prueba. Iba a: {', '.join(para)}"
        aviso += f"; con copia a: {', '.join(copia)})" if copia else ")"
        mensaje = f"{aviso}\n\n{mensaje}"
    else:
        reales = para + copia
        msg["To"] = ", ".join(para)
        if copia:
            msg["Cc"] = ", ".join(copia)
        msg["Subject"] = asunto
    msg.set_content(mensaje)
    msg.add_alternative(_texto_a_html(mensaje), subtype="html")
    if adjunto is not None:
        msg.add_attachment(Path(adjunto).read_bytes(), maintype="application", subtype="pdf", filename=nombre_adjunto)
    return msg, reales


# ── Historial: la copia de cada correo que salió ──────────────────────────
# Bruno (2026-11-13): cada correo que envía la app queda en
# SGTD/Correos/<año>/<mes>/, con el nombre "<asunto> - <operación>.eml", y
# Configuración › Correos › Historial de correos los muestra mes a mes.
# La operación va también en la cabecera X-Operacion de la copia (no en el
# correo que sale): el historial la lee de ahí.

OPERACIONES = {
    "cotizacion_cliente": "envío al cliente",
    "cotizacion_nueva": "cotización nueva",
    "op_nueva": "aprobación",
    "op_reenviada": "reenvío de OP",
    "op_recotizada": "recotización",
    "prueba": "prueba",
}
_NO_VA_EN_NOMBRE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _nombre_archivo(asunto: str, operacion: str) -> str:
    """"<asunto> - <operación>", sin los caracteres que Windows no acepta."""
    nombre = _NO_VA_EN_NOMBRE.sub(" ", f"{asunto} - {operacion}" if asunto else operacion)
    nombre = re.sub(r"\s+", " ", nombre).strip()[:150].rstrip(". ")
    return nombre or "Correo"


def guardar_eml(msg: EmailMessage, operacion: str) -> Path:
    """Deja la copia en Correos/AAAA/MM/<asunto> - <operación>.eml (con
    " (2)", " (3)"… si ya hay uno igual). `operacion`: una clave de
    OPERACIONES o el texto mismo."""
    texto = OPERACIONES.get(operacion, operacion)
    del msg["X-Operacion"]
    msg["X-Operacion"] = texto
    ahora = datetime.now()
    destino = carpeta() / f"{ahora:%Y}" / f"{ahora:%m}"
    destino.mkdir(parents=True, exist_ok=True)
    base = _nombre_archivo(str(msg["Subject"] or ""), texto)
    ruta, n = destino / f"{base}.eml", 2
    while ruta.exists():
        ruta, n = destino / f"{base} ({n}).eml", n + 1
    ruta.write_bytes(bytes(msg))
    return ruta


def meses_historial() -> list[dict]:
    """Los meses con correos guardados, del más nuevo al más viejo:
    [{"anio", "mes", "cantidad"}]."""
    meses = []
    for d_anio in carpeta().iterdir():
        if not (d_anio.is_dir() and d_anio.name.isdigit()):
            continue
        for d_mes in d_anio.iterdir():
            if d_mes.is_dir() and d_mes.name.isdigit():
                cantidad = sum(1 for _ in d_mes.glob("*.eml"))
                if cantidad:
                    meses.append({"anio": int(d_anio.name), "mes": int(d_mes.name), "cantidad": cantidad})
    return sorted(meses, key=lambda m: (m["anio"], m["mes"]), reverse=True)


def _operacion_por_nombre(nombre: str) -> str:
    """Las copias de antes del 2026-11-13 ("2026-11-10 18.36.28 Cotización
    1004.eml") no tienen X-Operacion: se saca del nombre."""
    m = re.match(r"\d{4}-\d\d-\d\d \d\d\.\d\d\.\d\d (.+)\.eml$", nombre)
    t = m.group(1) if m else ""
    if t.startswith("Cotización nueva"):
        return OPERACIONES["cotizacion_nueva"]
    if t.startswith("Cotización"):
        return OPERACIONES["cotizacion_cliente"]
    if t.startswith("OP"):
        return OPERACIONES["op_recotizada" if t.endswith("recotizada") else "op_nueva"]
    return ""


def _direcciones(valor) -> list[str]:
    return [c.strip() for c in str(valor or "").split(",") if c.strip()]


def leer_copia(ruta: Path) -> dict | None:
    """Lo que el historial muestra de una copia. Solo lee las cabeceras (el
    principio del archivo, no el PDF)."""
    try:
        with open(ruta, "rb") as f:
            inicio = f.read(65536)
        cab = BytesParser(policy=policy.default).parsebytes(inicio, headersonly=True)
        asunto = str(cab["Subject"] or "")
        originales = cab["X-Destinatarios-Originales"]
    except (OSError, ValueError, TypeError):
        return None
    prueba = originales is not None or asunto.startswith("[Prueba] ")
    try:
        fecha = parsedate_to_datetime(str(cab["Date"])).astimezone().replace(tzinfo=None)
    except (TypeError, ValueError):
        fecha = datetime.fromtimestamp(ruta.stat().st_mtime)
    return {
        "archivo": ruta.relative_to(carpeta()).as_posix(),
        "fecha": fecha.isoformat(timespec="seconds"),
        "asunto": asunto.removeprefix("[Prueba] "),
        "operacion": str(cab["X-Operacion"] or "") or _operacion_por_nombre(ruta.name),
        "para": _direcciones(originales) if prueba and originales else _direcciones(cab["To"]),
        "copia": [] if prueba else _direcciones(cab["Cc"]),
        "prueba": prueba,
    }


def historial(anio: int, mes: int) -> list[dict]:
    """Los correos que salieron ese mes, del más nuevo al más viejo."""
    d = carpeta() / f"{int(anio):04d}" / f"{int(mes):02d}"
    if not d.is_dir():
        return []
    copias = [c for c in (leer_copia(r) for r in d.glob("*.eml")) if c]
    return sorted(copias, key=lambda c: c["fecha"], reverse=True)


def ruta_copia(archivo: str) -> Path | None:
    """La ruta de una copia del historial ("2026/11/….eml"), solo si está
    dentro de la carpeta Correos."""
    raiz = carpeta().resolve()
    ruta = (raiz / str(archivo)).resolve()
    if ruta.suffix.lower() != ".eml" or raiz not in ruta.parents or not ruta.is_file():
        return None
    return ruta


# ── La contraseña (en este computador) y el envío ──────────────────────────

class ErrorEnvio(Exception):
    """No se pudo enviar: el mensaje ya viene listo para mostrarlo."""


def contrasena(remitente: str | None = None) -> str | None:
    """La contraseña de la casilla guardada en este computador, o None."""
    return credenciales.leer(SERVICIO_CREDENCIAL, (remitente or cargar()["cuenta"]["remitente"]).lower())


def _conectar(cuenta: dict, clave: str) -> smtplib.SMTP:
    """Una conexión ya autenticada. Lanza ErrorEnvio con un mensaje para
    la persona (no el error técnico)."""
    servidor, puerto = cuenta["servidor"], int(cuenta["puerto"])
    try:
        import certifi
        contexto = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        contexto = ssl.create_default_context()
    try:
        if puerto == 465:
            smtp = smtplib.SMTP_SSL(servidor, puerto, timeout=ESPERA_SMTP_S, context=contexto)
        else:
            smtp = smtplib.SMTP(servidor, puerto, timeout=ESPERA_SMTP_S)
            smtp.starttls(context=contexto)
    except (socket.gaierror, socket.timeout, TimeoutError, ConnectionError, OSError, smtplib.SMTPException) as e:
        raise ErrorEnvio(f"No se pudo conectar con {servidor} (puerto {puerto}). Revisa la conexión a internet "
                         "y el servidor en Configuración › Correos.") from e
    try:
        smtp.login(cuenta["remitente"], clave)
    except smtplib.SMTPAuthenticationError as e:
        smtp.close()
        raise ErrorEnvio(f"El servidor no aceptó la contraseña de {cuenta['remitente']}. "
                         "Vuelve a escribirla en Configuración › Correos.") from e
    except (smtplib.SMTPException, OSError) as e:
        smtp.close()
        raise ErrorEnvio(f"No se pudo entrar a la casilla {cuenta['remitente']}.") from e
    return smtp


def guardar_contrasena(clave: str) -> None:
    """Prueba la contraseña contra el servidor y, si entra, la guarda en
    este computador. Lanza ErrorEnvio si no entra."""
    cuenta = cargar()["cuenta"]
    if not clave:
        raise ErrorEnvio("Escribe la contraseña.")
    smtp = _conectar(cuenta, clave)
    try:
        smtp.quit()
    except smtplib.SMTPException:
        pass
    try:
        credenciales.guardar(SERVICIO_CREDENCIAL, cuenta["remitente"].lower(), clave)
    except (OSError, credenciales.NoDisponible) as e:
        raise ErrorEnvio("La contraseña es correcta, pero no se pudo guardar en este computador.") from e


def olvidar_contrasena() -> None:
    credenciales.borrar(SERVICIO_CREDENCIAL, cargar()["cuenta"]["remitente"].lower())


# Quién se entera cada vez que sale un correo (ver al_enviar). La ventana de
# la app se anota para mostrar la animación "Correo enviado": así sale con
# CADA correo, venga de donde venga (Bruno, 2026-11-12).
_al_enviar = []


def al_enviar(funcion) -> None:
    """Anota `funcion(msg, destinatarios)`, que se llama después de cada
    correo que sale (con a quién salió de verdad)."""
    if funcion not in _al_enviar:
        _al_enviar.append(funcion)


def enviar(msg: EmailMessage, destinatarios: list[str], ajustes: dict | None = None) -> None:
    """Manda `msg` a `destinatarios` (los de verdad, ver armar_mensaje).
    Lanza ErrorEnvio si no sale. Si sale, avisa a los de al_enviar."""
    ajustes = ajustes or cargar()
    cuenta = ajustes["cuenta"]
    clave = contrasena(cuenta["remitente"])
    if not clave:
        raise ErrorEnvio("Falta la contraseña del correo de la app en este computador: "
                         "escríbela en Configuración › Correos.")
    smtp = _conectar(cuenta, clave)
    try:
        rechazados = smtp.send_message(msg, from_addr=cuenta["remitente"], to_addrs=destinatarios)
    except smtplib.SMTPRecipientsRefused as e:
        raise ErrorEnvio(f"El servidor rechazó {', '.join(e.recipients)}: revisa el correo.") from e
    except (smtplib.SMTPException, OSError) as e:
        raise ErrorEnvio("El servidor cortó el envío. Prueba de nuevo en un rato.") from e
    finally:
        try:
            smtp.quit()
        except (smtplib.SMTPException, OSError):
            pass
    for funcion in list(_al_enviar):
        try:
            funcion(msg, destinatarios)
        except Exception:   # la animación nunca puede hacer fallar un envío
            pass
    if rechazados:
        raise ErrorEnvio(f"Salió, pero el servidor rechazó {', '.join(rechazados)}.")


def mensaje_de_prueba(ajustes: dict | None = None) -> tuple[EmailMessage, list[str]]:
    """El correo de "Enviar un correo de prueba": va a la dirección de prueba
    (o, con el modo de prueba apagado, a la misma casilla de la app)."""
    ajustes = ajustes or cargar()
    cuenta, prueba = ajustes["cuenta"], ajustes["prueba"]
    para = prueba["direccion"] if prueba.get("activo") else cuenta["remitente"]
    msg = EmailMessage()
    msg["From"] = formataddr((cuenta["nombre"], cuenta["remitente"]))
    msg["To"] = para
    msg["Date"] = format_datetime(datetime.now().astimezone())
    msg["Message-ID"] = make_msgid(domain=cuenta["remitente"].split("@")[-1])
    msg["Subject"] = "Correo de prueba del Sistema de Gestión"
    texto = (f"Este correo lo mandó la app desde {cuenta['remitente']}, para probar que el envío funciona.\n\n"
             "Si llegó, ya se pueden enviar cotizaciones por correo.")
    msg.set_content(texto)
    msg.add_alternative(_texto_a_html(texto), subtype="html")
    return msg, [para]
