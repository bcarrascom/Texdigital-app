"""
core/version.py
Versión de la app embebida en el build empaquetado. El workflow de
release (.github/workflows/release.yml) sobreescribe VERSION con el tag
de git justo antes de correr PyInstaller, así que en un build publicado
esto y el tag siempre coinciden. El valor de acá abajo solo se usa
corriendo desde código fuente (donde la auto-actualización nunca se
activa, ver core/actualizador.py).
"""

VERSION = "0.0.0-dev"
