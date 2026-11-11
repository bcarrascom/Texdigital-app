"""
core/pdf.py
Pasa a PDF un documento HTML de la app (la cotización, la OP, la guía de
despacho: ver core/presentar_*.py), sin abrir ninguna ventana. Lo usa el
envío por correo (core/correos.py), que adjunta el PDF.

Se imprime con Edge (o Chrome) sin ventana, `--headless --print-to-pdf`: es
el mismo motor que usa la gente al apretar "Guardar como PDF", así que el
documento sale igual que impreso a mano, con el CSS de impresión de la
plantilla (@media print, @page carta). Edge viene con todo Windows 10/11.
En el Mac solo funciona si hay Chrome o Edge instalado; si no, el PDF no se
puede armar y quien llama avisa (falta hacerlo con el WebKit del sistema,
ver CLAUDE.md, "Correos automáticos").
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


class PdfNoDisponible(Exception):
    """No se pudo armar el PDF: no hay navegador o falló al imprimir."""


def _candidatos() -> list[Path]:
    if sys.platform == "win32":
        bases = [os.environ.get(v, "") for v in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
        relativos = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"]
        return [Path(b) / r for r in relativos for b in bases if b]
    if sys.platform == "darwin":
        return [Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    return [Path("/usr/bin/microsoft-edge"), Path("/usr/bin/google-chrome"), Path("/usr/bin/chromium")]


def navegador() -> Path | None:
    """El ejecutable con que se imprime, o None si no hay ninguno."""
    return next((p for p in _candidatos() if p.is_file()), None)


def html_a_pdf(ruta_html: Path, destino: Path, *, espera_s: int = 60) -> Path:
    """Imprime `ruta_html` a `destino` (se pisa si existe) y devuelve
    `destino`. Lanza PdfNoDisponible si no se pudo."""
    exe = navegador()
    if exe is None:
        raise PdfNoDisponible("No se encontró Microsoft Edge ni Google Chrome para armar el PDF.")
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()
    # Un perfil aparte: con el Edge de la persona abierto, el proceso nuevo
    # le pasaría el trabajo al que ya corre (y no imprimiría nada).
    with tempfile.TemporaryDirectory(prefix="SistemaGestion_pdf_") as perfil:
        comando = [
            str(exe), "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--no-pdf-header-footer", f"--user-data-dir={perfil}",
            f"--print-to-pdf={destino}", Path(ruta_html).resolve().as_uri(),
        ]
        opciones = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        try:
            subprocess.run(comando, capture_output=True, timeout=espera_s, check=False, **opciones)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise PdfNoDisponible(f"No se pudo armar el PDF: {e}") from e
    if not destino.is_file() or destino.stat().st_size == 0:
        raise PdfNoDisponible("El navegador no generó el PDF.")
    return destino
