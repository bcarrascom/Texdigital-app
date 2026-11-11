"""
core/correos.py
Los correos que manda la app (pedido de Bruno, 2026-11-09; el plan entero
está en CLAUDE.md, "Correos automáticos").

Lo primero es la cotización al cliente: el botón "Enviar correo" de Ver
cotización le manda el PDF con un asunto y un mensaje, y el cliente responde
a ese correo para aprobarla o pedir cambios. Las demás áreas (OPs,
Inventario, Despachos) por ahora solo guardan su lista de correos.

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
     "cotizaciones": {"asunto", "mensaje", "copia": [{"correo", "nombre"}]},
     "areas": {"ops" | "inventario" | "despachos": [{"correo", "nombre"}]}}

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
from email.message import EmailMessage
from email.utils import format_datetime, formataddr, make_msgid
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

VARIABLES_COTIZACION = {
    "numero":   "El N° de la cotización",
    "cliente":  "La empresa",
    "contacto": "El contacto (o la empresa, si no tiene)",
    "trabajo":  "El nombre del trabajo",
    "total":    "El total con IVA",
    "fecha":    "La fecha de la cotización",
}

POR_DEFECTO = {
    "cuenta": {"remitente": "sistema@texdigital.cl", "nombre": "Texdigital",
               "servidor": "mail.texdigital.cl", "puerto": 465},
    "prueba": {"activo": True, "direccion": "brosky.spam@gmail.com"},
    "cotizaciones": {
        "asunto": "Cotización {numero} - {cliente}",
        "mensaje": ("Hola {contacto}:\n\n"
                    "Te enviamos la cotización N° {numero}, por un total de {total} (IVA incluido). "
                    "Va adjunta en PDF.\n\n"
                    "Para aprobarla o pedirnos cambios, basta con responder este correo.\n\n"
                    "Saludos,\nTexdigital"),
        "copia": [],
    },
    "areas": {a: [] for a in AREAS},
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
    for seccion in ("cuenta", "prueba", "cotizaciones"):
        if isinstance(guardado.get(seccion), dict):
            a[seccion] = {**POR_DEFECTO[seccion], **guardado[seccion]}
    a["cotizaciones"]["copia"] = _lista_correos(a["cotizaciones"].get("copia"))
    areas = guardado.get("areas") if isinstance(guardado.get("areas"), dict) else {}
    a["areas"] = {k: _lista_correos(areas.get(k)) for k in AREAS}
    if prueba_forzada():
        a["prueba"]["activo"] = True
    return a


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
    if not str(cot.get("asunto") or "").strip():
        e["cotizaciones.asunto"] = "Falta el asunto."
    if not str(cot.get("mensaje") or "").strip():
        e["cotizaciones.mensaje"] = "Falta el mensaje."
    _validar_lista(cot["copia"], "cotizaciones.copia", e)
    for area in AREAS:
        _validar_lista(a["areas"][area], f"areas.{area}", e)
    return e


def guardar(datos: dict) -> dict:
    """{"ok": True} o {"ok": False, "errores": {campo: mensaje}}."""
    d = datos or {}
    a = cargar()
    for seccion in ("cuenta", "prueba", "cotizaciones"):
        if isinstance(d.get(seccion), dict):
            a[seccion] = {**a[seccion], **d[seccion]}
    a["cuenta"] = {k: (" ".join(str(v).split()) if isinstance(v, str) else v) for k, v in a["cuenta"].items()}
    a["prueba"]["activo"] = bool(a["prueba"].get("activo"))
    a["prueba"]["direccion"] = str(a["prueba"].get("direccion") or "").strip()
    a["cotizaciones"]["asunto"] = " ".join(str(a["cotizaciones"].get("asunto") or "").split())
    a["cotizaciones"]["mensaje"] = str(a["cotizaciones"].get("mensaje") or "").strip()
    a["cotizaciones"]["copia"] = _lista_correos(a["cotizaciones"].get("copia"))
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
                  adjunto: Path, nombre_adjunto: str) -> tuple[EmailMessage, list[str]]:
    """El correo listo para salir, y a quién va de verdad (en modo de prueba,
    solo a la dirección de prueba)."""
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
    msg.add_attachment(Path(adjunto).read_bytes(), maintype="application", subtype="pdf", filename=nombre_adjunto)
    return msg, reales


def guardar_eml(msg: EmailMessage, nombre: str) -> Path:
    """Deja el correo en Correos/AAAA/MM/<fecha hora> <nombre>.eml."""
    ahora = datetime.now()
    destino = carpeta() / f"{ahora:%Y}" / f"{ahora:%m}"
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / f"{ahora:%Y-%m-%d %H.%M.%S} {nombre}.eml"
    ruta.write_bytes(bytes(msg))
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


def enviar(msg: EmailMessage, destinatarios: list[str], ajustes: dict | None = None) -> None:
    """Manda `msg` a `destinatarios` (los de verdad, ver armar_mensaje).
    Lanza ErrorEnvio si no sale."""
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
