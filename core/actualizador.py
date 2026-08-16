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
import re
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
API_RELEASES = f"https://api.github.com/repos/{REPO_GITHUB}/releases"
API_ULTIMO_RELEASE = f"{API_RELEASES}/latest"
# Variable de entorno que activa incluir_prerelease en buscar_actualizacion()
# desde ui/actualizador.py — ver docstring de esa función. Nunca se activa
# en un uso normal (nadie la define al abrir la app desde el acceso
# directo/ícono), solo sirve para probar el updater contra una beta antes
# de publicarla como "Latest".
VAR_ENTORNO_PRERELEASE = "SGTD_ACTUALIZAR_PRERELEASE"
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
    """'v1.2.3' -> (1, 2, 3, 1, 0); '1.2.3-beta.2' -> (1, 2, 3, 0, 2).
    Ignora lo que no sea numérico.

    Los dos últimos elementos implementan la precedencia de semver para
    sufijos (-beta.N, -dev, -rc1...):
    - El primero castiga TENER sufijo: a igual versión numérica, algo con
      sufijo compara como más viejo que lo mismo sin sufijo
      (1.4.0-beta.1 < 1.4.0) — si no, promover una beta a versión final
      sin cambiar el número (1.4.0-beta.1 -> 1.4.0, en vez de saltar a
      1.4.1) nunca se detectaría como actualización para quien ya tiene
      la beta instalada: ambas colapsaban a la misma tupla.
    - El segundo desempata ENTRE sufijos del mismo número, tomando el
      último grupo de dígitos del sufijo (1.4.0-beta.2 > 1.4.0-beta.1) —
      si no, probar el updater beta-a-beta (ver incluir_prerelease) tendría
      el mismo problema: dos betas seguidas colapsarían a la misma tupla.
    """
    texto = texto.strip().lstrip("vV")
    if "-" in texto:
        cuerpo, sufijo = texto.split("-", 1)
        tiene_sufijo = 0
        grupos_sufijo = re.findall(r"\d+", sufijo)
        num_sufijo = int(grupos_sufijo[-1]) if grupos_sufijo else 0
    else:
        cuerpo = texto
        tiene_sufijo = 1
        num_sufijo = 0
    partes = [p for p in cuerpo.split(".") if p.isdigit()]
    numeros = tuple(int(p) for p in partes) or (0,)
    return numeros + (tiene_sufijo, num_sufijo)


def _nombre_os() -> str:
    return {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")


def _asset_para_este_os(assets: list[dict]) -> dict | None:
    objetivo = _nombre_os()
    for asset in assets:
        if objetivo in asset.get("name", "").lower():
            return asset
    return None


def buscar_actualizacion(incluir_prerelease: bool = False) -> dict | None:
    """
    Devuelve {"tag", "url", "nombre"} del release de GitHub si hay una
    versión más nueva que la actual. Devuelve None si ya se tiene la
    versión más reciente (o si se está corriendo desde código fuente, ver
    docstring del módulo) — en cambio, cualquier error real (sin internet,
    GitHub caído, el release no trae paquete para este OS, respuesta
    inesperada) se deja propagar como excepción, para que quien llama
    (ui/actualizador.py) pueda mostrar un error de verdad en vez de
    confundirlo con "ya estás al día".

    Por default (incluir_prerelease=False) consulta /releases/latest, que
    de por sí SOLO devuelve el último release marcado "Latest" en GitHub —
    nunca uno marcado "Pre-release" (confirmado: con dos betas publicadas
    como Pre-release, este endpoint sigue devolviendo la última release
    estable de verdad). Esto es intencional: en un uso normal, la app
    nunca debe ofrecer instalar una beta hecha para probar.

    incluir_prerelease=True (ver VAR_ENTORNO_PRERELEASE, activado desde
    ui/actualizador.py) consulta /releases en cambio (trae también los
    Pre-release) y toma el primero — solo para poder probar el updater
    contra una beta antes de publicarla como Latest.
    """
    if not getattr(sys, "frozen", False):
        return None

    url = API_RELEASES if incluir_prerelease else API_ULTIMO_RELEASE
    req = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_CONSULTA, context=_contexto_ssl()) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if incluir_prerelease:
        if not data:
            return None
        data = data[0]

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


def ruta_log_actualizador() -> Path:
    """Log persistente del script de reemplazo (ver
    _lanzar_actualizador_windows) — a diferencia de todo lo demás que usa
    ese script, este archivo NO vive en la carpeta temporal de la
    descarga (que el script borra sola al final, éxito o no), así que
    sobrevive para poder revisarlo después de un intento fallido."""
    return Path(tempfile.gettempdir()) / "SistemaGestion_actualizador.log"


def _lanzar_actualizador_windows(instalada: Path, nueva: Path, tmp: Path, exe_nombre: str) -> None:
    # PowerShell en vez de un .bat con tasklist/find: esperar un PID por
    # substring de texto es frágil (puede matchear otra cosa en la salida
    # de tasklist y quedar pegado en loop). Wait-Process espera el proceso
    # real por su PID, sin parsing de texto de por medio.
    #
    # OJO — confirmado a mano (v1.4.0 -> v1.4.1): justo después de que el
    # proceso viejo termina, Windows a veces todavía tiene los .dll/.pyd de
    # _internal/ tomados un instante más (antivirus escaneando el borrado,
    # liberación de handles no instantánea) — un solo intento de
    # Remove-Item con -ErrorAction SilentlyContinue puede fallar EN
    # SILENCIO y dejar la carpeta vieja a medio borrar. Si eso pasa,
    # Move-Item con -Destination apuntando a una carpeta que TODAVÍA EXISTE
    # no la reemplaza — la mueve ADENTRO (mismo comportamiento que "mv" a
    # un directorio existente), dejando "Sistema de Gestion\Sistema de
    # Gestion\" anidado, con el .exe viejo todavía en el lugar que se
    # relanza. Por eso: reintentar el borrado con verificación, y si sigue
    # sin poder borrarse después de varios intentos, ABORTAR sin tocar
    # nada más — nunca hacer el Move-Item si el destino sigue existiendo.
    #
    # OJO 2 — confirmado a mano (v1.4.2 -> v1.4.3): con eso ya arreglado,
    # el "abortar sin tocar nada" puede ser justo lo que pasó y no hay
    # forma de saberlo — el propio script se borra su carpeta temporal al
    # final SIEMPRE (haya funcionado o no), así que no queda ningún rastro
    # de qué falló. Se agrega un log a una ruta FIJA fuera de esa carpeta
    # (ver ruta_log_actualizador) para poder revisar qué pasó realmente:
    # si Remove-Item nunca soltó la carpeta vieja (y por qué), si el
    # script ni siquiera llegó a correr, etc.
    log = _ps1_literal(ruta_log_actualizador())
    ps1 = tmp / "actualizar.ps1"
    ps1.write_text(
        f"$log = '{log}'\n"
        "function Log($msg) {\n"
        '    Add-Content -LiteralPath $log -Value "$(Get-Date -Format \'yyyy-MM-dd HH:mm:ss\') $msg" -Encoding UTF8 -ErrorAction SilentlyContinue\n'
        "}\n"
        f'Log "=== Actualizando (PID viejo {os.getpid()}) ==="\n'
        f"Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue\n"
        'Log "Wait-Process termino"\n'
        "Start-Sleep -Seconds 1\n"
        f"$destino = '{_ps1_literal(instalada)}'\n"
        "$intentos = 0\n"
        "while ((Test-Path -LiteralPath $destino) -and ($intentos -lt 30)) {\n"
        "    try {\n"
        "        Remove-Item -LiteralPath $destino -Recurse -Force -ErrorAction Stop\n"
        '        Log "Remove-Item intento ${intentos}: OK"\n'
        "    } catch {\n"
        '        Log "Remove-Item intento ${intentos}: FALLO - $($_.Exception.Message)"\n'
        "    }\n"
        "    if (Test-Path -LiteralPath $destino) { Start-Sleep -Seconds 1 }\n"
        "    $intentos++\n"
        "}\n"
        "if (-not (Test-Path -LiteralPath $destino)) {\n"
        f'    Log "Carpeta vieja borrada tras $intentos intento(s), moviendo la nueva..."\n'
        "    try {\n"
        f"        Move-Item -LiteralPath '{_ps1_literal(nueva)}' -Destination $destino -Force -ErrorAction Stop\n"
        '        Log "Move-Item OK"\n'
        f"        Start-Process -FilePath '{_ps1_literal(instalada / exe_nombre)}'\n"
        '        Log "Start-Process lanzado"\n'
        "    } catch {\n"
        '        Log "Move-Item FALLO - $($_.Exception.Message)"\n'
        "    }\n"
        "} else {\n"
        '    Log "ABORTADO: la carpeta vieja sigue sin poder borrarse tras $intentos intentos. No se toco nada."\n'
        "}\n"
        f"Remove-Item -LiteralPath '{_ps1_literal(tmp)}' -Recurse -Force -ErrorAction SilentlyContinue\n"
        'Log "=== Fin ==="\n',
        # utf-8-sig (con BOM): Windows PowerShell 5.1 (no pwsh) sin BOM
        # interpreta un .ps1 no-ASCII con el codepage activo del sistema,
        # no UTF-8 — sin esto, cualquier caracter acentuado en el script
        # (o en una ruta con tildes) puede llegar corrupto o, peor, hacer
        # que el parser tropiece. Confirmado a mano: sin BOM, "FALLÓ" en
        # un mensaje de Log salía como "FALLÃ“" al correr el script.
        encoding="utf-8-sig",
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

    # Mismo cuidado que _lanzar_actualizador_windows (ver ahí el porqué,
    # incluido el log persistente — confirmado a mano que sin loguear
    # cada paso a una ruta fija, un intento fallido no deja ningún rastro
    # de qué pasó, porque el propio script se borra su carpeta temporal
    # al final haya funcionado o no): si "rm -rf" no llegara a borrar
    # instalada del todo (poco probable en Unix, pero posible por
    # permisos/montajes), "mv nueva instalada" con el destino todavía
    # existiendo la mueve ADENTRO en vez de reemplazarla — se verifica y
    # reintenta antes de mover, y si sigue sin poder borrarse, se aborta
    # sin tocar nada más.
    log = ruta_log_actualizador()
    script = tmp / "actualizar.sh"
    script.write_text(
        "#!/bin/sh\n"
        f'LOG="{log}"\n'
        'log() { echo "$(date "+%Y-%m-%d %H:%M:%S") $1" >> "$LOG" 2>/dev/null; }\n'
        f"PID={os.getpid()}\n"
        f'log "=== Actualizando (PID viejo $PID) ==="\n'
        'while kill -0 "$PID" 2>/dev/null; do sleep 1; done\n'
        'log "Proceso viejo terminado"\n'
        "sleep 1\n"
        f'DESTINO="{instalada}"\n'
        "intentos=0\n"
        'while [ -e "$DESTINO" ] && [ $intentos -lt 30 ]; do\n'
        '    rm -rf "$DESTINO"\n'
        '    if [ -e "$DESTINO" ]; then\n'
        '        log "rm -rf intento $intentos: sigue existiendo"\n'
        "        sleep 1\n"
        "    else\n"
        '        log "rm -rf intento $intentos: OK"\n'
        "    fi\n"
        "    intentos=$((intentos + 1))\n"
        "done\n"
        'if [ ! -e "$DESTINO" ]; then\n'
        '    log "Carpeta vieja borrada tras $intentos intento(s), moviendo la nueva..."\n'
        f'    if mv "{nueva}" "$DESTINO"; then\n'
        '        log "mv OK"\n'
        '        chmod -R +x "$DESTINO" 2>/dev/null\n'
        f"        {comando_relanzar}\n"
        '        log "Relanzado"\n'
        "    else\n"
        '        log "mv FALLO"\n'
        "    fi\n"
        "else\n"
        '    log "ABORTADO: la carpeta vieja sigue sin poder borrarse tras $intentos intentos. No se toco nada."\n'
        "fi\n"
        f'rm -rf "{tmp}"\n'
        'log "=== Fin ==="\n',
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
