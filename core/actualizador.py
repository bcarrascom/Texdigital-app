"""
core/actualizador.py
Auto-actualización del build empaquetado.

Al iniciar, compara la VERSION embebida contra el último release publicado
en GitHub. Si hay una más nueva, descarga el paquete de este sistema
operativo, lo deja listo en una carpeta temporal y lanza un script
separado que: espera a que este proceso termine, reemplaza la carpeta de
instalación por la nueva, y vuelve a abrir la app. Este proceso termina
justo después de lanzar ese script (ver main.py).

Como toda la persistencia real (cotizaciones, OPs, clientes, catálogos)
vive en Dropbox y no en la carpeta del programa, reemplazar los archivos
de la app entre un inicio y el siguiente no pone en riesgo ningún dato.

Nunca se activa corriendo desde código fuente (sys.frozen es False) — solo
tiene sentido para el build empaquetado que se distribuye por GitHub
Releases.
"""

import json
import os
import shutil
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
TIMEOUT_CONSULTA = 6
TIMEOUT_DESCARGA = 120


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
    versión más nueva que la actual y trae un paquete para este OS. Si no
    hay ninguna más nueva, o falla la consulta (sin internet, GitHub
    caído, etc.), devuelve None sin lanzar excepciones — la app debe
    poder arrancar igual.
    """
    if not getattr(sys, "frozen", False):
        return None

    try:
        req = urllib.request.Request(
            API_ULTIMO_RELEASE, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_CONSULTA) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    tag = data.get("tag_name", "")
    if not tag or _version_tupla(tag) <= _version_tupla(VERSION):
        return None

    asset = _asset_para_este_os(data.get("assets", []))
    if asset is None:
        return None

    return {"tag": tag, "url": asset["browser_download_url"], "nombre": asset["name"]}


def _descargar(url: str, destino: Path) -> None:
    req = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_DESCARGA) as resp, open(destino, "wb") as f:
        shutil.copyfileobj(resp, f)


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


def aplicar_actualizacion(release: dict) -> bool:
    """
    Descarga el release, lo deja extraído, y lanza el script que hace el
    reemplazo real una vez que este proceso termine. Devuelve True si
    quedó todo listo (el llamador debe cerrar la app de inmediato después);
    False si algo falló (sin internet a mitad de descarga, etc.) — en ese
    caso no se tocó nada y la app debe seguir abriendo normalmente.
    """
    tmp = Path(tempfile.mkdtemp(prefix="sgtd_update_"))
    try:
        paquete = tmp / release["nombre"]
        _descargar(release["url"], paquete)
        nueva = _extraer(paquete, tmp / "nueva")
        if nueva is None:
            raise RuntimeError("el paquete descargado no tiene la carpeta esperada")

        instalada = _carpeta_instalada()
        exe_nombre = Path(sys.executable).name

        if sys.platform == "win32":
            _lanzar_actualizador_windows(instalada, nueva, tmp, exe_nombre)
        else:
            _lanzar_actualizador_unix(instalada, nueva, tmp, exe_nombre)
        return True
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        return False
