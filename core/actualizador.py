"""
core/actualizador.py
Actualización del build empaquetado, disparada a mano desde el botón
"Actualizar" del menú principal (ver ui/actualizador.py) — no hay ningún
chequeo automático al iniciar.

buscar_actualizacion() consulta el último release publicado en GitHub y lo
compara contra la VERSION embebida. Si hay una más nueva, aplicar_actualizacion()
descarga el paquete de este sistema operativo, lo deja extraído, y lanza un
script separado que: espera a que este proceso termine, reemplaza la carpeta
de instalación por la nueva, y vuelve a abrir la app — el llamador debe
cerrar la app enseguida después (ver ui/actualizador.py, que usa
ui.panel_produccion.salir_app()).

Como toda la persistencia real (cotizaciones, OPs, clientes, catálogos)
vive en Dropbox y no en la carpeta del programa, reemplazar los archivos
de la app entre un inicio y el siguiente no pone en riesgo ningún dato.

Nunca hace nada corriendo desde código fuente (sys.frozen es False) — solo
tiene sentido para el build empaquetado que se distribuye por GitHub
Releases (corriendo desde código fuente, sys.executable es el intérprete
de Python, no hay ninguna carpeta de instalación que reemplazar).
"""

import json
import os
import shutil
import ssl
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from core.version import VERSION

REPO_GITHUB = "bcarrascom/Texdigital-app"
API_ULTIMO_RELEASE = f"https://api.github.com/repos/{REPO_GITHUB}/releases/latest"
TIMEOUT_CONSULTA = 8
TIMEOUT_DESCARGA = 120
TAMANO_CHUNK = 262144  # 256 KiB


def _contexto_ssl() -> ssl.SSLContext | None:
    """Contexto SSL con el bundle de certificados de certifi, si está
    disponible. El build empaquetado con PyInstaller en macOS no siempre
    encuentra el bundle de certificados que usaría una instalación normal
    de Python (falta el paso "Install Certificates.command"), lo que hace
    fallar toda request HTTPS con "certificate verify failed: unable to
    get local issuer certificate". Devuelve None (contexto por defecto de
    Python) si certifi no está disponible."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def _version_tupla(texto: str) -> tuple:
    """'v1.2.3' o '1.2.3-dev' -> (1, 2, 3). Ignora lo que no sea numérico."""
    cuerpo = texto.strip().lstrip("vV").split("-")[0]
    partes = [p for p in cuerpo.split(".") if p.isdigit()]
    return tuple(int(p) for p in partes) or (0,)


def _nombre_os() -> str:
    return {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")


def _asset_para_este_os(assets: list[dict]) -> dict | None:
    objetivo = _nombre_os()
    for asset in assets:
        if objetivo in asset.get("name", "").lower():
            return asset
    return None


def buscar_actualizacion() -> dict | None:
    """
    Devuelve {"tag", "url", "nombre"} del release de GitHub si hay una
    versión más nueva que la actual. Devuelve None si ya se tiene la
    versión más reciente (o si se está corriendo desde código fuente, ver
    docstring del módulo) — en cambio, cualquier error real (sin internet,
    GitHub caído, el release no trae paquete para este OS, respuesta
    inesperada) se deja propagar como excepción, para que quien llama
    (ui/actualizador.py) pueda mostrar un error de verdad en vez de
    confundirlo con "ya estás al día".
    """
    if not getattr(sys, "frozen", False):
        return None

    req = urllib.request.Request(
        API_ULTIMO_RELEASE, headers={"Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_CONSULTA, context=_contexto_ssl()) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    tag = data.get("tag_name", "")
    if not tag:
        raise RuntimeError("El último release de GitHub no trae un tag válido.")
    if _version_tupla(tag) <= _version_tupla(VERSION):
        return None

    asset = _asset_para_este_os(data.get("assets", []))
    if asset is None:
        raise RuntimeError(
            f"El release {tag} no trae un paquete para este sistema operativo ({_nombre_os()}).")

    return {"tag": tag, "url": asset["browser_download_url"], "nombre": asset["name"]}


def _descargar(url: str, destino: Path, on_progreso=None) -> None:
    """on_progreso(bytes_leidos, bytes_total) — bytes_total es 0 si el
    servidor no informó Content-Length. Se llama en el mismo hilo que
    corre la descarga (quien la use desde Tkinter debe marshalear a la UI
    con .after(), ver ui/actualizador.py)."""
    req = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_DESCARGA, context=_contexto_ssl()) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        leidos = 0
        with open(destino, "wb") as f:
            while True:
                chunk = resp.read(TAMANO_CHUNK)
                if not chunk:
                    break
                f.write(chunk)
                leidos += len(chunk)
                if on_progreso:
                    on_progreso(leidos, total)


def _extraer(archivo: Path, destino: Path) -> Path | None:
    destino.mkdir(parents=True, exist_ok=True)
    if archivo.suffix == ".zip":
        with zipfile.ZipFile(archivo) as z:
            z.extractall(destino)
    else:
        with tarfile.open(archivo) as t:
            t.extractall(destino)
    contenido = list(destino.iterdir())
    return contenido[0] if len(contenido) == 1 else None


def _carpeta_instalada() -> Path:
    """Carpeta (Windows/Linux) o .app (macOS) que hay que reemplazar."""
    ejecutable = Path(sys.executable).resolve()
    if sys.platform == "darwin":
        return ejecutable.parents[2]  # .../Nombre.app/Contents/MacOS/bin -> Nombre.app
    return ejecutable.parent


def _ps1_literal(texto: str) -> str:
    """Escapa un valor para usarlo entre comillas simples en PowerShell
    (comilla simple literal -> se duplica)."""
    return str(texto).replace("'", "''")


def _lanzar_actualizador_windows(instalada: Path, nueva: Path, tmp: Path, exe_nombre: str) -> None:
    # PowerShell en vez de un .bat con tasklist/find: esperar un PID por
    # substring de texto es frágil (puede matchear otra cosa en la salida
    # de tasklist y quedar pegado en loop). Wait-Process espera el proceso
    # real por su PID, sin parsing de texto de por medio.
    ps1 = tmp / "actualizar.ps1"
    ps1.write_text(
        f"Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue\n"
        "Start-Sleep -Seconds 1\n"
        f"Remove-Item -LiteralPath '{_ps1_literal(instalada)}' -Recurse -Force -ErrorAction SilentlyContinue\n"
        f"Move-Item -LiteralPath '{_ps1_literal(nueva)}' -Destination '{_ps1_literal(instalada)}' -Force\n"
        f"Start-Process -FilePath '{_ps1_literal(instalada / exe_nombre)}'\n",
        encoding="utf-8",
    )
    # CREATE_NO_WINDOW (consola oculta) y no DETACHED_PROCESS (sin consola):
    # powershell.exe necesita algún tipo de consola para iniciar aunque sea
    # no interactivo — con DETACHED_PROCESS el proceso muere en silencio al
    # arrancar y el reemplazo nunca ocurre.
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    if hasattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB"):
        # Necesario si el proceso actual corre dentro de un Job Object
        # (terminales/CI que matan a todos los hijos al cerrar la shell);
        # sin esto el script de actualización moriría con nosotros antes
        # de poder hacer el reemplazo. Inofensivo si no hay Job Object.
        flags |= subprocess.CREATE_BREAKAWAY_FROM_JOB
    subprocess.Popen(
        [
            "powershell", "-NoProfile", "-WindowStyle", "Hidden",
            "-ExecutionPolicy", "Bypass", "-File", str(ps1),
        ],
        creationflags=flags,
        close_fds=True,
    )


def _lanzar_actualizador_unix(instalada: Path, nueva: Path, tmp: Path, exe_nombre: str) -> None:
    if sys.platform == "darwin":
        comando_relanzar = f'open "{instalada}"'
    else:
        comando_relanzar = f'"{instalada}/{exe_nombre}" &'

    script = tmp / "actualizar.sh"
    script.write_text(
        "#!/bin/sh\n"
        f"PID={os.getpid()}\n"
        'while kill -0 "$PID" 2>/dev/null; do sleep 1; done\n'
        "sleep 1\n"
        f'rm -rf "{instalada}"\n'
        f'mv "{nueva}" "{instalada}"\n'
        f'chmod -R +x "{instalada}" 2>/dev/null\n'
        f"{comando_relanzar}\n"
        'rm -- "$0"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    subprocess.Popen(["/bin/sh", str(script)], start_new_session=True)


def aplicar_actualizacion(release: dict, on_progreso=None) -> None:
    """
    Descarga el release, lo deja extraído, y lanza el script que hace el
    reemplazo real una vez que este proceso termine. Si termina sin lanzar
    excepción, quedó todo listo y el llamador debe cerrar la app de
    inmediato (ver ui/actualizador.py, que usa
    ui.panel_produccion.salir_app()) — si lanza una excepción, no se tocó
    nada y la app debe seguir abierta con normalidad.
    """
    tmp = Path(tempfile.mkdtemp(prefix="sgtd_update_"))
    try:
        paquete = tmp / release["nombre"]
        _descargar(release["url"], paquete, on_progreso=on_progreso)
        nueva = _extraer(paquete, tmp / "nueva")
        if nueva is None:
            raise RuntimeError("El paquete descargado no tiene la carpeta esperada.")

        instalada = _carpeta_instalada()
        exe_nombre = Path(sys.executable).name

        if sys.platform == "win32":
            _lanzar_actualizador_windows(instalada, nueva, tmp, exe_nombre)
        else:
            _lanzar_actualizador_unix(instalada, nueva, tmp, exe_nombre)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
