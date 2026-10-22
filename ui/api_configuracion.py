"""
ui/api_configuracion.py
API de las páginas de Configuración que no son de un módulo en particular:
los precios (textiles, estructuras, terminaciones, cajas — ver
core.precios_textiles y core.precios_componentes) y las reglas de cobro
(core.reglas_cobro).
Proveedores sigue en ui/api_inventario.py: es la misma lista que usan los
formularios de Inventario.
"""

from core import precios_componentes, precios_textiles, reglas_cobro
from core import repositorio_inventario as _repo_inv
from core import repositorio_materiales as _repo_mat


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

    # ── Estructuras y terminaciones ──────────────────────────────────────

    def obtener_precios_componentes(self, tipo: str) -> dict:
        """tipo: "estructuras" o "terminaciones".

            {"filas": [{"nombre", "valor", "unidad", "por_materiales": None | "asociados" | "mismo_nombre"}],
             "solo_lectura": bool}
        """
        motivos = _repo_mat.estructuras_cobradas_por_materiales() if tipo == "estructuras" else {}
        filas = [{**f, "por_materiales": motivos.get(f["nombre"])} for f in precios_componentes.cargar_lista(tipo)]
        return {"filas": filas, "solo_lectura": precios_componentes.solo_lectura(tipo)}

    def guardar_precios_componentes(self, tipo: str, filas: list) -> dict:
        return precios_componentes.guardar_lista(tipo, filas)

    # ── Cajas de Backlight ───────────────────────────────────────────────

    def obtener_precios_cajas(self) -> dict:
        """{"cajas": {sección: {clave: valor}, "pintura_por_ml"}, "solo_lectura"}
        ("fp" con los watts como texto: así viaja un objeto a JavaScript)."""
        cajas = precios_componentes.cajas()
        cajas["fp"] = {str(k): v for k, v in cajas["fp"].items()}
        return {"cajas": cajas, "solo_lectura": precios_componentes.solo_lectura("cajas")}

    def guardar_precios_cajas(self, cajas: dict) -> dict:
        return precios_componentes.guardar_cajas(cajas or {})

    # ── Reglas de cobro ──────────────────────────────────────────────────

    def obtener_reglas_cobro(self) -> dict:
        return {"reglas": reglas_cobro.cargar(), "por_defecto": reglas_cobro.POR_DEFECTO,
                "solo_lectura": reglas_cobro.solo_lectura()}

    def guardar_reglas_cobro(self, reglas: dict) -> dict:
        return reglas_cobro.guardar(reglas or {})
