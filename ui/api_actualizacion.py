"""
ui/api_actualizacion.py
Buscar e instalar versiones nuevas desde la app (ver core/actualizador.py)
— instanciada una sola vez por ui.api_app.ApiApp.

Al abrir la app se busca sola, en segundo plano (ApiApp.__init__). La
pantalla no espera nada: pregunta `estado()` y, mientras se busca o se
descarga, lo vuelve a preguntar seguido (ver frontend/src/hooks/
useActualizacion.js). El estado es uno solo para toda la app:

    fase        "no_disponible"  corriendo desde el código fuente
                "buscando" | "al_dia" | "disponible" | "error"
                "descargando"    (con "progreso", 0-100 o None)
                "listo"          la app se cierra y vuelve a abrir sola
    version     la instalada
    nueva       el tag de la que hay para instalar ("v2.1.1")
    error       qué falló, para mostrar
    recien_actualizado  la app se abrió recién actualizada (una sola vez)
"""

import hashlib
import sys
import threading
import urllib.error

from core import actualizador
from core.version import VERSION

# Lo que tarda la pantalla en mostrar "Listo" antes de que la app se cierre.
ESPERA_ANTES_DE_CERRAR = 2.0

# Las versiones de prueba (tags con guion, p. ej. v2.2.0-rc1) no se ofrecen
# solas: se buscan a mano en Configuración › General, con esta contraseña
# (pedido de Bruno, 2026-11-05). Va su sha256 y no el texto, para que no
# salga a la vista en el código.
_CONTRASENA_BETAS = "1b0df68dfd2fa3db8b0533634c7fe9794cf9e351b91373cc1dfbeb76ab248a9e"


def _mensaje(error: Exception) -> str:
    if isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError)):
        return "No se pudo conectar con el servidor de actualizaciones. Revisa la conexión a internet."
    if isinstance(error, PermissionError) and sys.platform == "darwin":
        # En el Escritorio, Documentos o Descargas, macOS pide permiso la
        # primera vez; si se negó, se da en Ajustes del Sistema.
        return ("macOS no dejó escribir en la carpeta de la app. Dale permiso en Ajustes del Sistema › "
                "Privacidad y seguridad › Archivos y carpetas › Sistema de Gestion, y vuelve a intentarlo.")
    if isinstance(error, PermissionError):
        return ("No se pudo escribir en la carpeta de la app. Puede que esté en una carpeta "
                "protegida; muévela al Escritorio o a Documentos.")
    return str(error) or type(error).__name__


class ApiActualizacion:

    def __init__(self, recien_actualizado: bool = False):
        self._lock = threading.Lock()
        self._release = None
        self._recien_actualizado = recien_actualizado
        frozen = getattr(sys, "frozen", False)
        self._estado = {"fase": "al_dia" if frozen else "no_disponible", "version": VERSION}

    def _poner(self, **cambios) -> None:
        with self._lock:
            self._estado = {"version": VERSION, **cambios}

    def estado(self) -> dict:
        with self._lock:
            estado = dict(self._estado)
            estado["recien_actualizado"] = self._recien_actualizado
            self._recien_actualizado = False
        return estado

    def buscar(self, betas: bool = False) -> dict:
        """Empieza a buscar (si no se está buscando o instalando ya). Con
        `betas`, también las versiones de prueba (ver buscar_betas)."""
        with self._lock:
            if self._estado["fase"] in ("no_disponible", "buscando", "descargando", "listo"):
                return dict(self._estado)
            self._estado = {"fase": "buscando", "version": VERSION}
        threading.Thread(target=self._buscar, args=(betas,), daemon=True).start()
        return self.estado()

    def buscar_betas(self, contrasena) -> dict:
        """Configuración › General › Versiones de prueba: con la contraseña,
        busca también las betas. {"ok": False, "error"} si no es la correcta
        (y no busca nada); si es, {"ok": True, "estado"}."""
        if hashlib.sha256(str(contrasena or "").encode("utf-8")).hexdigest() != _CONTRASENA_BETAS:
            return {"ok": False, "error": "Esa no es la contraseña."}
        return {"ok": True, "estado": self.buscar(betas=True)}

    def _buscar(self, betas: bool = False) -> None:
        try:
            release = actualizador.buscar_actualizacion(incluir_prerelease=betas)
        except Exception as e:
            self._poner(fase="error", error=_mensaje(e))
            return
        self._release = release
        if release:
            self._poner(fase="disponible", nueva=release["tag"])
        else:
            self._poner(fase="al_dia")

    def instalar(self) -> dict:
        """Baja la versión encontrada y deja todo listo para el reemplazo;
        después cierra la app (el script de core.actualizador la vuelve a
        abrir ya actualizada)."""
        with self._lock:
            if self._estado["fase"] != "disponible" or not self._release:
                return dict(self._estado)
            self._estado = {"fase": "descargando", "version": VERSION,
                            "nueva": self._release["tag"], "progreso": 0}
        threading.Thread(target=self._instalar, args=(self._release,), daemon=True).start()
        return self.estado()

    def _instalar(self, release: dict) -> None:
        def progreso(leidos, total):
            with self._lock:
                self._estado["progreso"] = round(leidos / total * 100) if total else None

        try:
            actualizador.aplicar_actualizacion(release, on_progreso=progreso)
        except Exception as e:
            # No se tocó nada: "Reintentar" vuelve a buscar (ver buscar).
            self._poner(fase="error", error=_mensaje(e))
            return
        self._poner(fase="listo", nueva=release["tag"])
        from ui.panel_produccion import salir_app
        threading.Timer(ESPERA_ANTES_DE_CERRAR, salir_app).start()
