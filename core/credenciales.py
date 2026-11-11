"""
core/credenciales.py
Guarda una contraseña en el almacén seguro del sistema, de este computador:
el Administrador de credenciales de Windows o el Llavero del Mac. Lo usa la
contraseña del correo de la app (ver core/correos.py): no va en la Dropbox
ni en el código, se escribe una vez en cada computador desde Configuración ›
Correos (decisión del 2026-11-10).

Sin librerías: en Windows, las funciones Cred* de advapi32 con ctypes; en el
Mac, la herramienta `security` que trae macOS. En otro sistema no hay dónde
guardarla (NoDisponible).
"""

import subprocess
import sys


class NoDisponible(Exception):
    """Este sistema no tiene dónde guardar la contraseña."""


# ── Windows ────────────────────────────────────────────────────────────────

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _CRED_TYPE_GENERIC = 1
    _CRED_PERSIST_LOCAL_MACHINE = 2
    _ERROR_NOT_FOUND = 1168

    class _CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
        ]

    _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _advapi32.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIAL), wintypes.DWORD]
    _advapi32.CredWriteW.restype = wintypes.BOOL
    _advapi32.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                    ctypes.POINTER(ctypes.POINTER(_CREDENTIAL))]
    _advapi32.CredReadW.restype = wintypes.BOOL
    _advapi32.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    _advapi32.CredDeleteW.restype = wintypes.BOOL
    _advapi32.CredFree.argtypes = [ctypes.c_void_p]

    def _guardar(servicio: str, cuenta: str, secreto: str) -> None:
        datos = secreto.encode("utf-8")
        blob = (ctypes.c_ubyte * len(datos)).from_buffer_copy(datos) if datos else None
        cred = _CREDENTIAL(Type=_CRED_TYPE_GENERIC, TargetName=f"{servicio}/{cuenta}", UserName=cuenta,
                           CredentialBlobSize=len(datos), Persist=_CRED_PERSIST_LOCAL_MACHINE,
                           CredentialBlob=ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte)) if blob else None)
        if not _advapi32.CredWriteW(ctypes.byref(cred), 0):
            raise OSError(ctypes.get_last_error(), "No se pudo guardar la contraseña en Windows.")

    def _leer(servicio: str, cuenta: str) -> str | None:
        p = ctypes.POINTER(_CREDENTIAL)()
        if not _advapi32.CredReadW(f"{servicio}/{cuenta}", _CRED_TYPE_GENERIC, 0, ctypes.byref(p)):
            if ctypes.get_last_error() == _ERROR_NOT_FOUND:
                return None
            raise OSError(ctypes.get_last_error(), "No se pudo leer la contraseña de Windows.")
        try:
            c = p.contents
            return ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize).decode("utf-8") if c.CredentialBlobSize else ""
        finally:
            _advapi32.CredFree(p)

    def _borrar(servicio: str, cuenta: str) -> None:
        if not _advapi32.CredDeleteW(f"{servicio}/{cuenta}", _CRED_TYPE_GENERIC, 0):
            if ctypes.get_last_error() != _ERROR_NOT_FOUND:
                raise OSError(ctypes.get_last_error(), "No se pudo borrar la contraseña de Windows.")

# ── Mac ────────────────────────────────────────────────────────────────────

elif sys.platform == "darwin":

    def _security(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["security", *args], capture_output=True, text=True)

    def _guardar(servicio: str, cuenta: str, secreto: str) -> None:
        r = _security("add-generic-password", "-U", "-s", servicio, "-a", cuenta, "-w", secreto)
        if r.returncode != 0:
            raise OSError(r.returncode, "No se pudo guardar la contraseña en el Llavero.")

    def _leer(servicio: str, cuenta: str) -> str | None:
        r = _security("find-generic-password", "-s", servicio, "-a", cuenta, "-w")
        return r.stdout.rstrip("\n") if r.returncode == 0 else None

    def _borrar(servicio: str, cuenta: str) -> None:
        _security("delete-generic-password", "-s", servicio, "-a", cuenta)

else:

    def _guardar(servicio, cuenta, secreto):
        raise NoDisponible("Este sistema no tiene dónde guardar la contraseña.")

    def _leer(servicio, cuenta):
        return None

    def _borrar(servicio, cuenta):
        return None


def guardar(servicio: str, cuenta: str, secreto: str) -> None:
    _guardar(servicio, cuenta, secreto)


def leer(servicio: str, cuenta: str) -> str | None:
    """La contraseña guardada, o None si no hay."""
    try:
        return _leer(servicio, cuenta)
    except OSError:
        return None


def borrar(servicio: str, cuenta: str) -> None:
    _borrar(servicio, cuenta)
