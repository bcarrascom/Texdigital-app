"""
core/titulo_impresion.py
Arma el <title> de los documentos imprimibles (ver core/presentar_cotizacion.py
y core/presentar_op.py, que lo meten en {{titulo}} de sus plantillas).

No es solo el rótulo de la pestaña: al imprimir con "Guardar como PDF", el
navegador propone el TÍTULO DEL DOCUMENTO como nombre del archivo. O sea
que este string es, en la práctica, el nombre con el que el PDF termina en
el disco del usuario — por eso el formato es "1003 • Cubre alarma Empresa
Ejemplo" y no "Cotización N° 1003 · TEXDIGITAL": el número adelante para
que la carpeta se ordene sola, y el trabajo + el cliente para reconocer el
archivo sin abrirlo.

El HTML que queda en carpeta_html() sigue llamándose {numero}.html — es un
archivo de trabajo que se regenera y se pisa en cada impresión, no el que
el usuario guarda.
"""

import html
import re

# Windows no admite estos caracteres en un nombre de archivo. El navegador
# los reemplaza solo al armar el nombre del PDF, pero deja un "_" por cada
# uno; sacarlos acá deja un nombre limpio (un nombre de trabajo con una
# barra, "Cubre alarma / cenefa", no tiene por qué llegar así al archivo).
_PROHIBIDOS = re.compile(r'[\/:*?"<>|\x00-\x1f]')


def _limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", _PROHIBIDOS.sub(" ", str(texto or ""))).strip()


def titulo_impresion(numero, nombre_trabajo="", cliente="") -> str:
    """'{numero} • {nombre_trabajo} {cliente}', ya escapado para meterlo
    dentro de <title>. Las partes vacías no dejan espacios de más: una
    cotización sin nombre de trabajo queda '1003 Empresa Ejemplo', y si no
    hay ni trabajo ni cliente queda solo el número."""
    numero = _limpiar(numero)
    resto = " ".join(p for p in (_limpiar(nombre_trabajo), _limpiar(cliente)) if p)
    if numero and resto:
        titulo = f"{numero} • {resto}"
    else:
        titulo = numero or resto or "TEXDIGITAL"
    return html.escape(titulo, quote=False)
