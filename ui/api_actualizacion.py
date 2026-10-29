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

import sys
import threading
import urllib.error

from core import actualizador
from core.version import VERSION

# Lo que tarda la pantalla en mostrar "Listo" antes de que la app se cierre.
ESPERA_ANTES_DE_CERRAR = 2.0


def _mensaje(error: Exception) -> str:
    if isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError)):
        return "No se pudo conectar con el servidor de actualizaciones. Revisa la conexión a internet."
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

    def buscar(self) -> dict:
        """Empieza a buscar (si no se está buscando o instalando ya)."""
        with self._lock:
            if self._estado["fase"] in ("no_disponible", "buscando", "descargando", "listo"):
                return dict(self._estado)
            self._estado = {"fase": "buscando", "version": VERSION}
        threading.Thread(target=self._buscar, daemon=True).start()
        return self.estado()

    def _buscar(self) -> None:
        try:
            release = actualizador.buscar_actualizacion()
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
