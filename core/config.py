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
    "inventario":   True,
    "cotizaciones": True,
    "ops":          True,
    "despachos":    False,
}
