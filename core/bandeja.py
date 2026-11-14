"""
core/bandeja.py
La bandeja de salida de los correos automáticos (Bruno, 2026-11-13; ver
CLAUDE.md, "Bandeja de envíos").

Un correo automático (el aviso de cotización nueva, la OP nueva, la OP
recotizada) no se envía en el momento: se guarda primero, ya armado (el .eml,
con su PDF), en una carpeta de ESTE computador, y un hilo aparte lo envía.

  · Si no hay internet o el servidor no responde, el correo se queda en la
    bandeja y se reintenta cada REINTENTO_S segundos mientras la app esté
    abierta, y al volver a abrirla. No se pierde.
  · La carpeta es local (%APPDATA%\\SistemaGestion\\Bandeja) y no de la
    Dropbox: así lo reintenta solo el computador que lo creó y nunca sale
    dos veces (decisión de Bruno, 2026-11-11).
  · La pantalla no espera al servidor: guardar o aprobar es inmediato.

Cada correo son dos archivos: <id>.eml (el mensaje) y <id>.json:

    {"id", "creado", "destinatarios": [...] (a quién va de verdad),
     "meta": {"tipo", "numero", "para", "asunto", "prueba", "operacion"},
     "intentos", "error", "ultimo_intento"}

Quien quiera enterarse de cómo va cada uno (anotarlo en la OP, avisar en la
pantalla) se anota con al_cambiar(funcion(item, estado)); `estado` es
"pendiente", "error" o "enviado".
"""

import json
import threading
import time
import uuid
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path

from core import correos
from core.rutas import DATOS, _es_dev

REINTENTO_S = 120

_lock = threading.Lock()          # un solo envío a la vez
_despertar = threading.Event()
_hilo = None
_al_cambiar = []


def carpeta() -> Path:
    """La bandeja de este computador (la versión de desarrollo usa otra)."""
    p = DATOS / ("Bandeja-dev" if _es_dev() else "Bandeja")
    p.mkdir(parents=True, exist_ok=True)
    return p


def al_cambiar(funcion) -> None:
    """Anota `funcion(item, estado)`, que se llama cuando un correo entra a la
    bandeja ("pendiente"), falla un intento ("error") o sale ("enviado")."""
    if funcion not in _al_cambiar:
        _al_cambiar.append(funcion)


def _avisar(item: dict, estado: str) -> None:
    for funcion in list(_al_cambiar):
        try:
            funcion(item, estado)
        except Exception:   # anotarlo o avisarlo nunca puede trabar la bandeja
            pass


def _guardar(item: dict) -> None:
    (carpeta() / f"{item['id']}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")


def encolar(msg: EmailMessage, destinatarios: list[str], meta: dict) -> dict:
    """Deja el correo en la bandeja y despierta al hilo que envía. `meta`
    dice de qué es (tipo, numero…) para anotarlo donde corresponda."""
    item = {
        # Empieza por la hora con nanosegundos: así salen en el orden en que se
        # crearon (una OP nueva antes que su recotización, aunque sea el mismo segundo).
        "id": f"{datetime.now():%Y%m%d-%H%M%S}-{time.time_ns() % 10**9:09d}-{uuid.uuid4().hex[:4]}",
        "creado": datetime.now().isoformat(timespec="seconds"),
        "destinatarios": list(destinatarios),
        "meta": dict(meta),
        "intentos": 0, "error": None, "ultimo_intento": None,
    }
    (carpeta() / f"{item['id']}.eml").write_bytes(bytes(msg))
    _guardar(item)
    _avisar(item, "pendiente")
    _despertar.set()
    return item


def pendientes() -> list[dict]:
    """Los que esperan salir, del más viejo al más nuevo."""
    items = []
    for archivo in sorted(carpeta().glob("*.json")):
        try:
            items.append(json.loads(archivo.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return items


def _enviar_uno(item: dict) -> bool:
    eml = carpeta() / f"{item['id']}.eml"
    try:
        msg = BytesParser(policy=policy.default).parsebytes(eml.read_bytes())
        correos.enviar(msg, item["destinatarios"])
    except Exception as e:   # sin internet, sin contraseña, el .eml roto…
        item["intentos"] = item.get("intentos", 0) + 1
        item["error"] = str(e) if isinstance(e, correos.ErrorEnvio) else f"No se pudo enviar: {e}"
        item["ultimo_intento"] = datetime.now().isoformat(timespec="seconds")
        _guardar(item)
        _avisar(item, "error")
        return False
    # Salió: la copia en la carpeta Correos (Dropbox) y fuera de la bandeja.
    try:
        operacion = item["meta"].get("operacion") or item["meta"].get("tipo") or "aviso"
        item["archivo"] = correos.guardar_eml(msg, operacion).name
    except OSError:
        item["archivo"] = None
    item["enviado"] = datetime.now().isoformat(timespec="seconds")
    for ext in (".eml", ".json"):
        (carpeta() / f"{item['id']}{ext}").unlink(missing_ok=True)
    _avisar(item, "enviado")
    return True


def procesar() -> int:
    """Intenta enviar todo lo pendiente. Devuelve cuántos salieron."""
    with _lock:
        return sum(1 for item in pendientes() if _enviar_uno(item))


def despertar() -> None:
    """Que el hilo intente ahora, sin esperar el próximo reintento."""
    _despertar.set()


def _ciclo() -> None:
    while True:
        try:
            procesar()
        except Exception:
            pass
        # Con algo pendiente, se reintenta cada REINTENTO_S; si no, se espera
        # a que llegue un correo nuevo (encolar despierta al hilo).
        _despertar.wait(REINTENTO_S if pendientes() else None)
        _despertar.clear()


def iniciar() -> None:
    """Arranca el hilo que envía (una vez, al abrir la app): lo que quedó de
    antes sale apenas se pueda."""
    global _hilo
    if _hilo is None or not _hilo.is_alive():
        _hilo = threading.Thread(target=_ciclo, name="bandeja-correos", daemon=True)
        _hilo.start()
