"""
ui/api_configuracion.py
API de las páginas de Configuración que no son de un módulo en particular —
por ahora, Textiles (cómo se cobra cada textil, ver core.precios_textiles).
Proveedores sigue en ui/api_inventario.py: es la misma lista que usan los
formularios de Inventario.
"""

from core import precios_textiles
from core import repositorio_inventario as _repo_inv


class ApiConfiguracion:

    def obtener_precios_textiles(self) -> dict:
        """Los ajustes de Configuración › Textiles, con un resumen de los
        rollos de cada textil (cuántos, y entre qué valores):

            {"modo", "inventario": bool, "solo_lectura": bool,
             "textiles": [{"nombre", "ancho", "cobro", "valor",
                           "rollos": {"rollos", "sin_valor", "minimo", "maximo"} | None}]}
        """
        ajustes = precios_textiles.cargar()
        inventario = precios_textiles._inventario_habilitado()
        resumen = _repo_inv.resumen_valores_por_textil() if inventario else {}
        for t in ajustes["textiles"]:
            t["rollos"] = resumen.get(t["nombre"])
        return {**ajustes, "inventario": inventario, "solo_lectura": precios_textiles.solo_lectura()}

    def guardar_precios_textiles(self, datos: dict) -> dict:
        return precios_textiles.guardar(datos or {})

    def fijar_valor_rollos(self, nombre_textil: str, valor) -> dict:
        """{"ok": True, "cambiados": n} o {"ok": False, "error": ...}."""
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            return {"ok": False, "error": "El valor tiene que ser un monto mayor que 0."}
        if valor <= 0:
            return {"ok": False, "error": "El valor tiene que ser un monto mayor que 0."}
        return {"ok": True, "cambiados": _repo_inv.fijar_valor_rollos(nombre_textil, valor)}
