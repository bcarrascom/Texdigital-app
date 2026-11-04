"""
core/orden.py
El orden de las listas que se eligen o se editan en Configuración (textiles,
estructuras, terminaciones, productos, perfiles, luces, traseras, clientes,
contactos, proveedores): alfabético, siempre (pedido de Bruno, 2026-11-04).

Sin mayúsculas ni tildes ("Ñ" junto a "N", "Ciré" junto a "Cire"), y los
números por su valor, no letra a letra: "Popelina 155" antes que
"Popelina 1550" y "PERFIL 60 MM" antes que "PERFIL 100 MM".

Se ordena al LEER (core.repositorio, core.catalogo), así cualquier lista
que sale de ahí ya viene en orden y lo que se agrega cae en su lugar.
"""

import re
import unicodedata


def clave(texto) -> list:
    """La clave de orden de un nombre: los trozos de texto sin tildes ni
    mayúsculas, y los de dígitos como números (siempre en las posiciones
    impares de re.split, así nunca se compara un número con un texto)."""
    s = "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if not unicodedata.combining(c))
    return [int(p) if i % 2 else p for i, p in enumerate(re.split(r"(\d+)", s.casefold()))]


def alfabetico(items, por=None) -> list:
    """`items` en orden alfabético (ver arriba). `por`: de dónde sale el
    nombre de cada uno, si no son textos (p. ej. lambda c: c["empresa"])."""
    return sorted(items, key=lambda x: clave(por(x) if por else x))
