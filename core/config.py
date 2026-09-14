"""
core/config.py
Interruptores de "¿este módulo del menú ya se puede usar?" — un módulo en
False queda VISIBLE en el menú pero inutilizable (gris, subtítulo
"Próximamente", sin click, sin atajo de teclado) hasta que se vuelva a
poner en True. No hace falta tocar HTML ni JS para pausar o reactivar un
módulo — solo este diccionario.

Lo lee ui/api_app.py::obtener_contexto() (viaja en "modulos_habilitados")
y lo aplica menu.html en el arranque, antes de la primera pintada (ver
aplicarModulosHabilitados en el script de esa pantalla).

Uso típico: sacar un release con un módulo a medio construir sin
exponerlo, dejando el resto de la app intacta — ver core/repositorio_ops.py
y ui/api_ver_op.py para un ejemplo de módulo que SÍ depende de otro (ese
acoplamiento no cambia acá: el módulo sigue existiendo e importado, solo
queda inalcanzable desde el menú).
"""

MODULOS_HABILITADOS = {
    "inventario":   False,
    "cotizaciones": True,
    "ops":          True,
    "despachos":    False,
}

# Metros mínimos que un textil debería tener disponibles en Inventario sin
# que el menú principal muestre un aviso (ver core.repositorio_inventario.
# avisos_stock) — pedido de Bruno (2026-09-12). Por ahora es un número fijo
# acá: cuando exista un módulo de configuración editable desde la UI, este
# valor pasa a leerse (y guardarse) desde ahí, sin tocar avisos_stock().
# Variable mutable a propósito — quien la lea debe hacerlo por atributo de
# módulo (core.config.STOCK_MINIMO_ML), no importando el nombre suelto, para
# que un cambio en caliente (ej. desde ese futuro módulo) se vea de
# inmediato en vez de quedar pisado por una copia importada al arrancar.
STOCK_MINIMO_ML = 25

# Apaga por completo el ícono de aviso de stock del menú principal (ver
# core.repositorio_inventario.avisos_stock) sin tocar STOCK_MINIMO_ML — pedido
# de Bruno (2026-09-12) pensando en el futuro módulo de configuración: el
# usuario podría no querer estos avisos aunque el umbral le sirva para otra
# cosa. Mismo criterio de "variable mutable, leer por atributo de módulo"
# que STOCK_MINIMO_ML de arriba.
AVISOS_STOCK_HABILITADOS = True
