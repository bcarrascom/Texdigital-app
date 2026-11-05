"""
core/actualizador.py
Actualización del build empaquetado. La app busca sola al abrir, en segundo
plano, y el usuario decide cuándo instalar (ver ui/api_actualizacion.py: el
botón "Actualizar a vX" del menú y Configuración › General).

buscar_actualizacion() consulta el último release publicado en GitHub y lo
compara contra la VERSION embebida. Si hay una más nueva, aplicar_actualizacion()
descarga el paquete de este sistema operativo, lo deja extraído junto a la
instalación, y lanza un script separado que: espera a que este proceso
termine, aparta la carpeta de instalación, pone la nueva en su lugar, y
vuelve a abrir la app — el llamador debe cerrar la app enseguida después
(ver ui/api_actualizacion.py, que usa ui.panel_produccion.salir_app()).

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
    (ui/api_actualizacion.py) pueda mostrar un error de verdad en vez de
    confundirlo con "ya estás al día".

    Por default (incluir_prerelease=False) consulta /releases/latest, que
    de por sí SOLO devuelve el último release marcado "Latest" en GitHub —
    nunca uno marcado "Pre-release" (confirmado: con dos betas publicadas
    como Pre-release, este endpoint sigue devolviendo la última release
    estable de verdad). Esto es intencional: en un uso normal, la app
    nunca debe ofrecer instalar una beta hecha para probar.

    incluir_prerelease=True consulta /releases en cambio (trae también los
    Pre-release) y toma la versión más nueva que ya tenga paquete para este
    SO — una que todavía se está subiendo (el workflow crea el release y
    después sube los archivos) se salta en vez de dar error. Solo lo pide
    Configuración › General › Versiones de prueba, con contraseña (ver
    ui/api_actualizacion.py): desde v2.1.2, ni siquiera una beta instalada
    busca betas sola (pedido de Bruno, 2026-11-05).
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
        candidatos = [
            r for r in data
            if not r.get("draft") and r.get("tag_name")
            and _asset_para_este_os(r.get("assets", []))
        ]
        if not candidatos:
            return None
        data = max(candidatos, key=lambda r: _version_tupla(r["tag_name"]))

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
    corre la descarga (ver ui/api_actualizacion.py, que solo lo anota y la
    pantalla lo va leyendo)."""
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


# Lo que macOS deja solo en una carpeta y no es parte del paquete.
_IGNORADOS = {"__MACOSX", ".DS_Store"}


def _extraer(archivo: Path, destino: Path) -> Path | None:
    """En macOS, el .zip se abre con `ditto` y no con zipfile (confirmado a
    mano, rc9 en un Mac, 2026-11-04): el .app trae symlinks (Python.framework,
    Contents/Frameworks <-> Resources) que `zip -y` guarda como symlinks, y
    zipfile los escribe como archivos de texto con la ruta adentro. El .app
    queda roto y no abre nunca más, sin ningún mensaje. `ditto` (el de
    Finder) conserva symlinks, permisos y atributos."""
    destino.mkdir(parents=True, exist_ok=True)
    if archivo.suffix == ".zip" and sys.platform == "darwin":
        r = subprocess.run(["/usr/bin/ditto", "-x", "-k", str(archivo), str(destino)],
                           capture_output=True, text=True, timeout=TIMEOUT_DESCARGA)
        if r.returncode:
            raise RuntimeError(f"No se pudo abrir el paquete descargado ({r.stderr.strip() or r.returncode}).")
    elif archivo.suffix == ".zip":
        with zipfile.ZipFile(archivo) as z:
            z.extractall(destino)
    else:
        with tarfile.open(archivo) as t:
            t.extractall(destino)
    contenido = [c for c in destino.iterdir() if c.name not in _IGNORADOS]
    return contenido[0] if len(contenido) == 1 else None


# Los primeros 4 bytes de un ejecutable de macOS: Mach-O de 32/64 bits, en
# los dos órdenes de bytes, o binario universal.
_MACH_O = {b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xfe\xed\xfa\xce", b"\xca\xfe\xba\xbe"}


def _revisar_app_mac(app: Path, exe_nombre: str) -> None:
    """Antes de cerrar nada: que el .app extraído tenga su ejecutable como un
    ejecutable de verdad, y sus symlinks como symlinks (ver _extraer). Si
    no, RuntimeError: la app sigue abierta y la instalada no se toca."""
    exe = app / "Contents" / "MacOS" / exe_nombre
    if not (exe.is_file() and os.access(exe, os.X_OK)):
        raise RuntimeError("El paquete descargado no trae el ejecutable de la app.")
    with open(exe, "rb") as f:
        if f.read(4) not in _MACH_O:
            raise RuntimeError("El ejecutable del paquete descargado no es un programa de macOS.")
    if not any(c.is_symlink() for c in app.rglob("*")):
        raise RuntimeError("El paquete descargado perdió sus enlaces internos al abrirse.")


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


# Carpeta de trabajo del script de reemplazo: nunca la de la instalación
# (ver OJO 3 en _lanzar_actualizador_windows), ni su carpeta temporal, que
# el script borra al final.
_CWD_SCRIPT = tempfile.gettempdir()


def _respaldo_de(instalada: Path) -> Path:
    """Donde se aparta la instalación vieja mientras se pone la nueva."""
    return instalada.with_name(instalada.name + ".anterior")


def _lanzar_actualizador_windows(instalada: Path, nueva: Path, tmp: Path, exe_nombre: str) -> None:
    # PowerShell en vez de un .bat con tasklist/find: esperar un PID por
    # substring de texto es frágil (puede matchear otra cosa en la salida
    # de tasklist y quedar pegado en loop). Wait-Process espera el proceso
    # real por su PID, sin parsing de texto de por medio.
    #
    # OJO — confirmado a mano (v1.4.0 -> v1.4.1): justo después de que el
    # proceso viejo termina, Windows a veces todavía tiene los .dll/.pyd de
    # _internal/ tomados un instante más (antivirus, liberación de handles
    # no instantánea). Antes se BORRABA la carpeta vieja, y un borrado que
    # falla a medias deja una instalación rota sin vuelta atrás. Ahora se
    # APARTA con Rename-Item (renombrar una carpeta con un archivo tomado
    # adentro falla entero, nunca a medias), reintentando: si no se puede
    # apartar, no se tocó nada y se vuelve a abrir la versión instalada; si
    # se apartó pero la nueva no llega a su lugar, se devuelve la vieja.
    # Nunca queda la app sin abrir ni a medio instalar. Como la nueva se
    # extrae junto a la instalada (ver aplicar_actualizacion), Move-Item no
    # cruza de disco (no puede mover carpetas entre unidades).
    #
    # OJO 2 — confirmado a mano (v1.4.2 -> v1.4.3): el script se borra su
    # carpeta temporal al final siempre, así que sin un log a una ruta FIJA
    # (ver ruta_log_actualizador) no queda rastro de qué falló.
    #
    # OJO 3 — confirmado a mano (v2.1.0-rc3 -> rc4): abierta con doble clic,
    # la app tiene como carpeta de trabajo la de la instalación, y el script
    # la heredaba: PowerShell mismo la tenía "en uso" y Rename-Item fallaba
    # los 30 intentos. El script arranca en la carpeta temporal del sistema
    # (ver _CWD_SCRIPT) y abre la app con la suya (-WorkingDirectory).
    log = _ps1_literal(ruta_log_actualizador())
    respaldo = _respaldo_de(instalada)
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
        f"$respaldo = '{_ps1_literal(respaldo)}'\n"
        f"$exe = '{_ps1_literal(instalada / exe_nombre)}'\n"
        "if (Test-Path -LiteralPath $respaldo) {\n"
        "    Remove-Item -LiteralPath $respaldo -Recurse -Force -ErrorAction SilentlyContinue\n"
        "}\n"
        "$apartada = $false\n"
        "$intentos = 0\n"
        "while ((-not $apartada) -and ($intentos -lt 30)) {\n"
        "    try {\n"
        f"        Rename-Item -LiteralPath $destino -NewName '{_ps1_literal(respaldo.name)}' -ErrorAction Stop\n"
        "        $apartada = $true\n"
        '        Log "Carpeta vieja apartada (intento ${intentos})"\n'
        "    } catch {\n"
        '        Log "Rename-Item intento ${intentos}: FALLO - $($_.Exception.Message)"\n'
        "        Start-Sleep -Seconds 1\n"
        "    }\n"
        "    $intentos++\n"
        "}\n"
        "if (-not $apartada) {\n"
        '    Log "ABORTADO: la carpeta vieja no se pudo apartar. No se toco nada; se abre la version instalada."\n'
        "    Start-Process -FilePath $exe -WorkingDirectory $destino\n"
        "} else {\n"
        "    try {\n"
        f"        Move-Item -LiteralPath '{_ps1_literal(nueva)}' -Destination $destino -ErrorAction Stop\n"
        '        Log "Move-Item OK"\n'
        "        Start-Process -FilePath $exe -WorkingDirectory $destino -ArgumentList '--actualizado'\n"
        '        Log "Start-Process lanzado"\n'
        "        Remove-Item -LiteralPath $respaldo -Recurse -Force -ErrorAction SilentlyContinue\n"
        "    } catch {\n"
        '        Log "Move-Item FALLO - $($_.Exception.Message). Se devuelve la version anterior."\n'
        "        if (Test-Path -LiteralPath $destino) {\n"
        "            Remove-Item -LiteralPath $destino -Recurse -Force -ErrorAction SilentlyContinue\n"
        "        }\n"
        f"        Rename-Item -LiteralPath $respaldo -NewName '{_ps1_literal(instalada.name)}' -ErrorAction SilentlyContinue\n"
        "        Start-Process -FilePath $exe -WorkingDirectory $destino\n"
        "    }\n"
        "}\n"
        f"Remove-Item -LiteralPath '{_ps1_literal(nueva.parent)}' -Recurse -Force -ErrorAction SilentlyContinue\n"
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
        cwd=_CWD_SCRIPT,
    )


def _lanzar_actualizador_unix(instalada: Path, nueva: Path, tmp: Path, exe_nombre: str) -> None:
    if sys.platform == "darwin":
        abrir = f'open "{instalada}"'
        abrir_nueva = f'open "{instalada}" --args --actualizado'
        proceso = f"{instalada}/Contents/MacOS/"
    else:
        abrir = f'"{instalada}/{exe_nombre}" &'
        abrir_nueva = f'"{instalada}/{exe_nombre}" --actualizado &'
        proceso = f"{instalada}/{exe_nombre}"

    # Mismo cuidado que _lanzar_actualizador_windows (ver ahí el porqué,
    # incluido el log persistente): la instalación vieja se APARTA con mv
    # (atómico en el mismo disco) en vez de borrarse, y vuelve a su lugar
    # si la nueva no llega. Además, la vieja solo se borra si la nueva sigue
    # CORRIENDO 10 s después de abrirla: una que no arranca (rc9 en un Mac,
    # ver _extraer) se cambia por la vieja, que vuelve a abrirse.
    log = ruta_log_actualizador()
    respaldo = _respaldo_de(instalada)
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
        f'RESPALDO="{respaldo}"\n'
        'rm -rf "$RESPALDO"\n'
        "apartada=0\n"
        "intentos=0\n"
        'while [ $apartada -eq 0 ] && [ $intentos -lt 30 ]; do\n'
        '    if mv "$DESTINO" "$RESPALDO" 2>/dev/null; then\n'
        "        apartada=1\n"
        '        log "Carpeta vieja apartada (intento $intentos)"\n'
        "    else\n"
        '        log "mv intento $intentos: FALLO"\n'
        "        sleep 1\n"
        "    fi\n"
        "    intentos=$((intentos + 1))\n"
        "done\n"
        "if [ $apartada -eq 0 ]; then\n"
        '    log "ABORTADO: la carpeta vieja no se pudo apartar. No se toco nada; se abre la version instalada."\n'
        f"    {abrir}\n"
        f'elif mv "{nueva}" "$DESTINO"; then\n'
        '    log "mv OK"\n'
        # En macOS los permisos ya vienen bien (ditto) y no se tocan.
        + ("" if sys.platform == "darwin" else '    chmod -R +x "$DESTINO" 2>/dev/null\n') +
        f"    {abrir_nueva}\n"
        "    sleep 10\n"
        f"    if pgrep -f '{proceso}' >/dev/null 2>&1; then\n"
        '        log "Relanzado: la version nueva esta corriendo"\n'
        '        rm -rf "$RESPALDO"\n'
        "    else\n"
        '        log "La version nueva no quedo corriendo. Se devuelve la anterior."\n'
        '        rm -rf "$DESTINO"\n'
        '        mv "$RESPALDO" "$DESTINO"\n'
        f"        {abrir}\n"
        "    fi\n"
        "else\n"
        '    log "mv FALLO. Se devuelve la version anterior."\n'
        '    rm -rf "$DESTINO"\n'
        '    mv "$RESPALDO" "$DESTINO"\n'
        f"    {abrir}\n"
        "fi\n"
        f'rm -rf "{nueva.parent}"\n'
        f'rm -rf "{tmp}"\n'
        'log "=== Fin ==="\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    subprocess.Popen(["/bin/sh", str(script)], start_new_session=True, cwd=_CWD_SCRIPT)


def aplicar_actualizacion(release: dict, on_progreso=None) -> None:
    """
    Descarga el release, lo deja extraído, y lanza el script que hace el
    reemplazo real una vez que este proceso termine. Si termina sin lanzar
    excepción, quedó todo listo y el llamador debe cerrar la app de
    inmediato (ver ui/api_actualizacion.py, que usa
    ui.panel_produccion.salir_app()) — si lanza una excepción, no se tocó
    nada y la app debe seguir abierta con normalidad.

    El paquete se baja a la carpeta temporal, pero se extrae JUNTO a la
    instalación ("<carpeta>.nueva"): así el script la pone en su lugar sin
    cruzar de disco, y si no se puede escribir ahí, falla acá, con la app
    todavía abierta, y no a mitad del reemplazo.
    """
    instalada = _carpeta_instalada()
    # Un .app abierto sin moverlo de donde se descomprimió corre desde una
    # copia de solo lectura que arma macOS (App Translocation): no hay nada
    # que reemplazar ahí.
    if sys.platform == "darwin" and "/AppTranslocation/" in str(instalada):
        raise RuntimeError("Para poder actualizarla, mueve la app a la carpeta Aplicaciones con el Finder y ábrela desde ahí.")
    tmp = Path(tempfile.mkdtemp(prefix="sgtd_update_"))
    extraida = instalada.with_name(instalada.name + ".nueva")
    try:
        paquete = tmp / release["nombre"]
        _descargar(release["url"], paquete, on_progreso=on_progreso)
        shutil.rmtree(extraida, ignore_errors=True)
        nueva = _extraer(paquete, extraida)
        if nueva is None:
            raise RuntimeError("El paquete descargado no tiene la carpeta esperada.")

        exe_nombre = Path(sys.executable).name
        if sys.platform == "darwin":
            _revisar_app_mac(nueva, exe_nombre)

        if sys.platform == "win32":
            _lanzar_actualizador_windows(instalada, nueva, tmp, exe_nombre)
        else:
            _lanzar_actualizador_unix(instalada, nueva, tmp, exe_nombre)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(extraida, ignore_errors=True)
        raise
