"""
ui/api_configuracion.py
API de las páginas de Configuración que no son de un módulo en particular:
los precios (textiles, estructuras, terminaciones, cajas — ver
core.precios_textiles y core.precios_componentes), las reglas de cobro
(core.reglas_cobro), qué textiles, estructuras y terminaciones existen
(core.catalogo), y las listas de clientes y contactos (core.repositorio).
Proveedores sigue en ui/api_inventario.py: es la misma lista que usan los
formularios de Inventario.
"""

from core import catalogo, corte_backlight, precios_componentes, precios_textiles, reglas_cobro
from core import repositorio as _repo
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
        catalogo.refrescar()
        ajustes = precios_textiles.cargar()
        inventario = precios_textiles._inventario_habilitado()
        resumen = _repo_inv.resumen_valores_por_textil() if inventario else {}
        del_catalogo = {t["nombre"]: t for t in catalogo.textiles()}
        for t in ajustes["textiles"]:
            c = del_catalogo.get(t["nombre"], {})
            t.update(rollos=resumen.get(t["nombre"]), backlight=c.get("backlight", False),
                     agregado=c.get("agregado", False), anteriores=c.get("anteriores", []))
        return {**ajustes, "inventario": inventario, "solo_lectura": precios_textiles.solo_lectura(),
                "catalogo_solo_lectura": catalogo.solo_lectura()}

    def agregar_textil(self, datos: dict) -> dict:
        """datos: {nombre, ancho, backlight, valor} — ver core.catalogo.agregar_textil."""
        d = datos or {}
        return catalogo.agregar_textil(d.get("nombre"), d.get("ancho"), bool(d.get("backlight")), d.get("valor"))

    def editar_textil(self, nombre_actual: str, datos: dict) -> dict:
        """datos: {nombre, ancho, backlight} — ver core.catalogo.editar_textil."""
        d = datos or {}
        return catalogo.editar_textil(nombre_actual, d.get("nombre"), d.get("ancho"), bool(d.get("backlight")))

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

            {"filas": [{"nombre", "valor", "unidad", "agregado",
                        "materiales": [{"nombre", "falta"}]}],   ← los asociados, si tiene
             "solo_lectura": bool, "catalogo_solo_lectura": bool}
        """
        catalogo.refrescar()
        asociados = _repo_mat.materiales_de_estructuras() if tipo == "estructuras" else {}
        agregados = {c["nombre"] for c in catalogo.componentes(tipo) if c["agregado"]}
        filas = [{**f, "materiales": asociados.get(f["nombre"], []), "agregado": f["nombre"] in agregados}
                 for f in precios_componentes.cargar_lista(tipo)]
        return {"filas": filas, "solo_lectura": precios_componentes.solo_lectura(tipo),
                "catalogo_solo_lectura": catalogo.solo_lectura()}

    def guardar_precios_componentes(self, tipo: str, filas: list) -> dict:
        return precios_componentes.guardar_lista(tipo, filas)

    def agregar_componente(self, tipo: str, datos: dict) -> dict:
        """datos: {nombre, unidad: "un." | "ML", valor} — ver core.catalogo.agregar_componente."""
        d = datos or {}
        return catalogo.agregar_componente(tipo, d.get("nombre"), d.get("unidad"), d.get("valor"))

    # ── Cajas de Backlight ───────────────────────────────────────────────

    def obtener_precios_cajas(self) -> dict:
        """Configuración › Backlight:

            {"cajas": {sección: {clave: valor}, "pintura_por_ml"}, "solo_lectura",
             "materiales_perfiles": {perfil: [{"nombre", "falta"}]},   ← asociados en Inventario
             "margenes_cm": {"caja_terminada", "area_visual"}, "margenes_solo_lectura"}

        ("fp" con los watts como texto: así viaja un objeto a JavaScript)."""
        cajas = precios_componentes.cajas()
        cajas["fp"] = {str(k): v for k, v in cajas["fp"].items()}
        asociados = _repo_mat.materiales_de_estructuras()
        return {"cajas": cajas, "solo_lectura": precios_componentes.solo_lectura("cajas"),
                "materiales_perfiles": {p: asociados[p] for p in cajas["perfiles"] if p in asociados},
                "margenes_cm": {k: round(v * 100, 2) for k, v in corte_backlight.cargar().items()},
                "margenes_solo_lectura": corte_backlight.solo_lectura()}

    def guardar_precios_cajas(self, cajas: dict) -> dict:
        return precios_componentes.guardar_cajas(cajas or {})

    def guardar_margenes_corte(self, margenes_cm: dict) -> dict:
        """margenes_cm: {"caja_terminada", "area_visual"} en cm."""
        d = margenes_cm or {}
        def a_metros(v):
            try:
                return float(str(v).replace(",", ".")) / 100
            except (TypeError, ValueError):
                return None
        return corte_backlight.guardar({k: a_metros(d.get(k)) for k in corte_backlight.POR_DEFECTO})

    # ── Productos ────────────────────────────────────────────────────────

    def obtener_productos(self) -> list[dict]:
        """[{"nombre", "agregado", "anteriores", "materiales": [{"nombre", "falta"}]}]
        en el orden del cotizador — con los materiales de Inventario asociados."""
        catalogo.refrescar()
        asociados = _repo_mat.materiales_de_productos()
        return [{**p, "materiales": asociados.get(p["nombre"], [])} for p in catalogo.productos_detalle()]

    def obtener_materiales_backlight(self) -> list[dict]:
        """[{"nombre": "Backlight" | "Backlight + Caja", "materiales": [...]}]:
        los materiales asociados a los nombres reservados de Inventario, que no
        son productos del cotizador pero se muestran junto a ellos."""
        asociados = _repo_mat.materiales_de_productos()
        return [{"nombre": n, "materiales": asociados.get(n, [])}
                for n in (_repo_mat.PRODUCTO_BACKLIGHT, _repo_mat.PRODUCTO_BACKLIGHT_CAJA)]

    def agregar_producto(self, datos: dict) -> dict:
        return catalogo.agregar_producto((datos or {}).get("nombre"))

    def renombrar_producto(self, actual: str, datos: dict) -> dict:
        return catalogo.renombrar_producto(actual, (datos or {}).get("nombre"))

    def quitar_producto(self, nombre: str) -> dict:
        return catalogo.quitar_producto(nombre)

    # ── Clientes y contactos ─────────────────────────────────────────────

    def obtener_clientes(self) -> list[dict]:
        """[{"empresa", "rut", "razon_social", "direcciones": n}] por nombre."""
        direcciones: dict[str, int] = {}
        for d in _repo.cargar_direcciones():
            rut = _repo.formatear_rut(d.get("rut", ""))
            direcciones[rut] = direcciones.get(rut, 0) + 1
        clientes = [{"empresa": c.get("empresa", ""), "rut": c.get("rut", ""), "razon_social": c.get("razon_social", ""),
                     "direcciones": direcciones.get(_repo.formatear_rut(c.get("rut", "")), 0) if c.get("rut") else 0}
                    for c in _repo.cargar_clientes()]
        return sorted(clientes, key=lambda c: c["empresa"].casefold())

    def crear_cliente(self, datos: dict) -> dict:
        return _repo.crear_cliente(datos or {})

    def editar_cliente(self, empresa_actual: str, datos: dict) -> dict:
        return _repo.editar_cliente(empresa_actual, datos or {})

    def eliminar_cliente(self, empresa: str) -> dict:
        return _repo.eliminar_cliente(empresa)

    def obtener_contactos(self) -> list[dict]:
        """[{"contacto", "email", "descuento", "condicion"}] por nombre."""
        contactos = [{"contacto": c.get("contacto", ""), "email": c.get("email", ""),
                      "descuento": c.get("descuento", "") or "0", "condicion": c.get("condicion", "")}
                     for c in _repo.cargar_contactos()]
        return sorted(contactos, key=lambda c: c["contacto"].casefold())

    def crear_contacto(self, datos: dict) -> dict:
        return _repo.crear_contacto(datos or {})

    def editar_contacto(self, nombre_actual: str, datos: dict) -> dict:
        return _repo.editar_contacto(nombre_actual, datos or {})

    def eliminar_contacto(self, nombre: str) -> dict:
        return _repo.eliminar_contacto(nombre)

    # ── Reglas de cobro ──────────────────────────────────────────────────

    def obtener_reglas_cobro(self) -> dict:
        return {"reglas": reglas_cobro.cargar(), "por_defecto": reglas_cobro.POR_DEFECTO,
                "solo_lectura": reglas_cobro.solo_lectura()}

    def guardar_reglas_cobro(self, reglas: dict) -> dict:
        return reglas_cobro.guardar(reglas or {})
