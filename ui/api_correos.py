"""
ui/api_correos.py
API de los correos (ver core/correos.py): Configuración › Correos y el botón
"Enviar correo" de Ver cotización.

Los correos salen por SMTP desde la casilla de la app, con la contraseña
guardada en este computador (ver core/correos.py). Cada uno deja una copia
.eml en la carpeta Correos.
"""

import os
import subprocess
import sys
import tempfile
from datetime import datetime
from email.utils import formataddr
from pathlib import Path

from core import correos
from core.pdf import PdfNoDisponible, html_a_pdf
from core.precios import formatear_clp
from core.presentar_cotizacion import generar_html
from core.repositorio import cargar_clientes, cargar_contactos, correo_valido
from core.repositorio_cotizaciones import cargar_cotizacion, guardar_cotizacion, recalcular_descuentos


def _abrir(ruta: Path) -> None:
    """Abre un archivo o carpeta con el programa del sistema."""
    if sys.platform == "win32":
        os.startfile(str(ruta))
    else:
        subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(ruta)])


def _lista(valor) -> list[str]:
    """["a@b.cl", ...] desde una lista o un texto separado por comas o ;."""
    if isinstance(valor, str):
        valor = valor.replace(";", ",").split(",")
    return [c.strip() for c in (valor or []) if str(c).strip()]


def _documento(numero):
    """(datos guardados, datos con los montos al día, HTML del documento),
    o None si la cotización no existe. Los montos se recalculan como al
    imprimir (ver ApiVerCotizacion.imprimir_cotizacion), sin guardarlos."""
    datos = cargar_cotizacion(int(numero))
    if datos is None:
        return None
    doc = recalcular_descuentos(dict(datos), guardar=False)
    return datos, doc, generar_html(doc)


def _enviar_con_pdf(ajustes, datos, ruta_html, *, para, copia, asunto, mensaje, nombre_eml):
    """Arma el PDF del documento, lo envía y deja la copia .eml en la
    carpeta Correos. Devuelve (a quién salió de verdad, ruta del .eml).
    Levanta PdfNoDisponible o correos.ErrorEnvio si no sale."""
    with tempfile.TemporaryDirectory(prefix="SistemaGestion_correo_") as tmp:
        pdf = html_a_pdf(ruta_html, Path(tmp) / "cotizacion.pdf")
        msg, reales = correos.armar_mensaje(
            ajustes=ajustes, para=para, copia=copia, asunto=asunto, mensaje=mensaje,
            adjunto=pdf, nombre_adjunto=correos.nombre_adjunto(datos),
        )
    correos.enviar(msg, reales, ajustes)
    return reales, correos.guardar_eml(msg, nombre_eml)


def resumen_envio(registro: dict | None) -> dict | None:
    """Lo que la pantalla muestra de un envío anotado en la cotización."""
    if not registro:
        return None
    try:
        fecha = datetime.fromisoformat(registro.get("fecha", ""))
        fecha_texto = fecha.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        fecha_texto = registro.get("fecha", "")
    return {"fecha": fecha_texto, "para": registro.get("para", []), "copia": registro.get("copia", []),
            "asunto": registro.get("asunto", ""), "prueba": bool(registro.get("prueba")),
            # Los de antes del 2026-11-10 no salieron: solo quedaron como archivo.
            "simulado": bool(registro.get("simulado"))}


def estado_envio(datos: dict) -> str:
    """Si el cliente tiene la cotización tal como está hoy (pedido de Bruno,
    2026-11-11; Ver cotización lo muestra arriba de la hoja):

        "sin_enviar"   nunca se le envió
        "con_cambios"  se le envió, pero el documento cambió desde entonces
        "al_dia"       el último envío es este mismo documento

    `datos` con los montos al día (recalcular_descuentos), como se imprime:
    la huella es la del HTML, la misma que anota enviar_correo_cotizacion.
    Los envíos simulados (de antes del 2026-11-10) no salieron: no cuentan."""
    envios = [e for e in (datos.get("Correos") or []) if isinstance(e, dict) and not e.get("simulado")]
    if not envios:
        return "sin_enviar"
    return "al_dia" if envios[-1].get("huella") == correos.huella(generar_html(datos)) else "con_cambios"


class ApiCorreos:

    # ── Configuración › Correos ──────────────────────────────────────────

    def obtener_ajustes_correos(self) -> dict:
        clientes, contactos = cargar_clientes(), cargar_contactos()
        return {
            "ajustes": correos.cargar(),
            "por_defecto": {"asunto": correos.POR_DEFECTO["cotizaciones"]["asunto"],
                            "mensaje": correos.POR_DEFECTO["cotizaciones"]["mensaje"],
                            "nuevas": {"asunto": correos.POR_DEFECTO["cotizaciones_nuevas"]["asunto"],
                                       "mensaje": correos.POR_DEFECTO["cotizaciones_nuevas"]["mensaje"]}},
            "variables": [{"clave": k, "texto": v} for k, v in correos.VARIABLES_COTIZACION.items()],
            "solo_lectura": correos.solo_lectura(),
            "contrasena_guardada": bool(correos.contrasena()),
            "prueba_forzada": correos.prueba_forzada(),
            "con_correo": {
                "clientes": sum(1 for c in clientes if correo_valido(c.get("email"))), "clientes_total": len(clientes),
                "contactos": sum(1 for c in contactos if correo_valido(c.get("email"))), "contactos_total": len(contactos),
            },
        }

    def guardar_ajustes_correos(self, datos: dict) -> dict:
        return correos.guardar(datos or {})

    def abrir_carpeta_correos(self) -> None:
        _abrir(correos.carpeta())

    def guardar_contrasena_correo(self, clave: str) -> dict:
        """Prueba la contraseña contra el servidor y la guarda en este
        computador. {"ok": True} o {"ok": False, "error": ...}."""
        try:
            correos.guardar_contrasena(str(clave or ""))
        except correos.ErrorEnvio as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    def olvidar_contrasena_correo(self) -> None:
        correos.olvidar_contrasena()

    def enviar_correo_de_prueba(self) -> dict:
        """{"ok": True, "a": [...]} o {"ok": False, "error": ...}."""
        msg, para = correos.mensaje_de_prueba()
        try:
            correos.enviar(msg, para)
        except correos.ErrorEnvio as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "a": para}

    # ── Enviar una cotización ────────────────────────────────────────────

    def preparar_correo_cotizacion(self, numero) -> dict | None:
        """Lo que muestra el panel de "Enviar correo": el cliente, a quién
        se le puede mandar, el asunto y el mensaje ya rellenados, y si la
        cotización cambió desde el último envío."""
        r = _documento(numero)
        if r is None:
            return None
        datos, doc, ruta_html = r
        ajustes = correos.cargar()
        valores = correos.valores_cotizacion(doc)
        ultimo = correos.ultimo_envio(datos)
        cuenta = ajustes["cuenta"]
        return {
            "numero": datos.get("Cotizacion"),
            "empresa": datos.get("Empresa", ""),
            "rut": datos.get("RUT", ""),
            "razon_social": datos.get("Razon Social", ""),
            "contacto": datos.get("Contacto", ""),
            "trabajo": datos.get("Nombre", ""),
            "total": formatear_clp(doc.get("Total") or 0),
            "sugeridos": correos.destinatarios_sugeridos(datos),
            "copia": [f["correo"] for f in ajustes["cotizaciones"]["copia"]],
            "asunto": correos.rellenar(ajustes["cotizaciones"]["asunto"], valores),
            "mensaje": correos.rellenar(ajustes["cotizaciones"]["mensaje"], valores),
            "adjunto": correos.nombre_adjunto(datos),
            "ultimo": resumen_envio(ultimo),
            "envios": len(datos.get("Correos") or []),
            "sin_cambios": bool(ultimo and ultimo.get("huella") == correos.huella(ruta_html)),
            "remitente": formataddr((cuenta["nombre"], cuenta["remitente"])),
            "prueba": ajustes["prueba"],
            "prueba_forzada": correos.prueba_forzada(),
            # Sin contraseña en este computador no se puede enviar: el panel lo dice.
            "contrasena_guardada": bool(correos.contrasena(cuenta["remitente"])),
        }

    def ver_pdf_cotizacion(self, numero) -> dict:
        """Arma el PDF que se adjuntaría y lo abre, para revisarlo."""
        r = _documento(numero)
        if r is None:
            return {"ok": False, "error": "La cotización ya no existe."}
        datos, _, ruta_html = r
        destino = Path(tempfile.gettempdir()) / "SistemaGestion" / correos.nombre_adjunto(datos)
        try:
            html_a_pdf(ruta_html, destino)
        except PdfNoDisponible as e:
            return {"ok": False, "error": str(e)}
        _abrir(destino)
        return {"ok": True}

    def enviar_correo_cotizacion(self, numero, datos: dict) -> dict:
        """datos: {"para": [...], "copia": [...], "asunto", "mensaje"}.

        {"ok": True, "prueba", "a": [a quién salió], "archivo", "ultimo"} o
        {"ok": False, "errores": {campo: mensaje}} / {"ok": False, "error": ...}.
        Si no sale, no se anota nada en la cotización."""
        if not correos.al_cliente_activo():
            return {"ok": False, "error": "Los correos a clientes están desactivados (Configuración › Correos)."}
        d = datos or {}
        para, copia = _lista(d.get("para")), _lista(d.get("copia"))
        asunto = " ".join(str(d.get("asunto") or "").split())
        mensaje = str(d.get("mensaje") or "").strip()
        errores = {}
        if not para:
            errores["para"] = "Falta a quién enviarlo."
        malos = [c for c in para + copia if not correo_valido(c)]
        if malos:
            errores["para" if any(c in para for c in malos) else "copia"] = f"«{malos[0]}» no es un correo válido."
        if not asunto:
            errores["asunto"] = "Falta el asunto."
        if not mensaje:
            errores["mensaje"] = "Falta el mensaje."
        if errores:
            return {"ok": False, "errores": errores}

        r = _documento(numero)
        if r is None:
            return {"ok": False, "error": "La cotización ya no existe."}
        guardados, _, ruta_html = r
        ajustes = correos.cargar()
        try:
            reales, archivo = _enviar_con_pdf(ajustes, guardados, ruta_html, para=para, copia=copia, asunto=asunto,
                                              mensaje=mensaje, nombre_eml=f"Cotización {guardados.get('Cotizacion')}")
        except (PdfNoDisponible, correos.ErrorEnvio) as e:
            return {"ok": False, "error": str(e)}

        registro = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "para": para, "copia": copia, "asunto": asunto,
            "huella": correos.huella(ruta_html),
            "prueba": bool(ajustes["prueba"].get("activo")),
            "archivo": archivo.name,
        }
        guardados.setdefault("Correos", []).append(registro)
        guardar_cotizacion(guardados)
        return {"ok": True, "prueba": registro["prueba"], "a": reales, "archivo": str(archivo),
                "ultimo": resumen_envio(registro)}

    # ── Aviso de cotización nueva (a la gente de Texdigital) ─────────────
    # Bruno (2026-11-11): al crear una cotización, los inscritos en
    # "Cotizaciones nuevas" (Configuración › Correos) reciben el PDF, con su
    # propio asunto y mensaje. Es otro correo que el del cliente. En el
    # Resumen del cotizador se ve la lista: cada correo se puede sacar, y se
    # puede sumar otro de los guardados en la app (o uno escrito), solo esa vez.

    def correo_al_crear(self) -> dict:
        """Lo que el bloque del Resumen necesita: la lista de inscritos, los
        demás correos guardados en la app (para sumar uno), el modo de prueba
        y si hay contraseña en este computador."""
        ajustes = correos.cargar()
        inscritos = ajustes["cotizaciones_nuevas"]["para"]
        ya = {f["correo"].lower() for f in inscritos}
        return {
            # Con los correos automáticos de cotizaciones apagados, el Resumen no muestra el aviso.
            "activo": correos.automatico_activo("cotizaciones", ajustes),
            "inscritos": inscritos,
            "guardados": [f for f in correos.correos_guardados(ajustes) if f["correo"].lower() not in ya],
            "prueba": ajustes["prueba"],
            "contrasena_guardada": bool(correos.contrasena(ajustes["cuenta"]["remitente"])),
        }

    def enviar_aviso_cotizacion_nueva(self, numero, para) -> dict:
        """Manda el aviso de la cotización recién creada, con el asunto y el
        mensaje de Configuración y el PDF. {"ok": True, "prueba", "a": [...]}
        o {"ok": False, "error"}. Queda anotado en la cotización, en
        "AvisoCreacion" (no en "Correos": esos son los envíos al cliente)."""
        if not correos.automatico_activo("cotizaciones"):
            return {"ok": False, "apagado": True, "error": "Los correos automáticos de cotizaciones están apagados."}
        para = _lista(para)
        if not para:
            return {"ok": False, "error": "Falta a quién enviarlo."}
        malos = [c for c in para if not correo_valido(c)]
        if malos:
            return {"ok": False, "error": f"«{malos[0]}» no es un correo válido."}
        r = _documento(numero)
        if r is None:
            return {"ok": False, "error": "La cotización ya no existe."}
        guardados, doc, ruta_html = r
        ajustes = correos.cargar()
        plantilla, valores = ajustes["cotizaciones_nuevas"], correos.valores_cotizacion(doc)
        try:
            reales, archivo = _enviar_con_pdf(
                ajustes, guardados, ruta_html, para=para, copia=[],
                asunto=correos.rellenar(plantilla["asunto"], valores),
                mensaje=correos.rellenar(plantilla["mensaje"], valores),
                nombre_eml=f"Cotización nueva {guardados.get('Cotizacion')}")
        except (PdfNoDisponible, correos.ErrorEnvio) as e:
            return {"ok": False, "error": str(e)}
        prueba = bool(ajustes["prueba"].get("activo"))
        guardados["AvisoCreacion"] = {"fecha": datetime.now().isoformat(timespec="seconds"),
                                      "para": para, "prueba": prueba, "archivo": archivo.name}
        guardar_cotizacion(guardados)
        return {"ok": True, "prueba": prueba, "a": reales}
