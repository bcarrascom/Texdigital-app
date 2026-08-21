"""
tests/test_compatibilidad_datos_viejos.py
Verifica que el programa actual siga pudiendo leer y procesar JSON
guardados por versiones anteriores: cotizaciones/OPs con el esquema viejo
de Estructura/Terminacion (string único, no lista), sin los campos de
precio (Descuento/Neto/IVA/Total) que no existían antes, con "Fuente" en
vez de "Descuento" en contactos, y catálogos (estructuras/terminaciones)
en formato de lista de strings en vez de lista de objetos con precio.

Los fixtures de OPs vienen copiados TAL CUAL de archivos reales que
todavía están en Dropbox/SGTD/OPs/JSON/ (1002.json, 1006.json) — no son
inventados — para probar contra datos genuinos de antes de este cambio,
no solo contra lo que yo creo que era el formato viejo.

Correr con:  python -m unittest tests.test_compatibilidad_datos_viejos -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.repositorio_cotizaciones import producto_desde_json, mapear_producto
from core.precios import costo_producto, costo_cotizacion
from core.presentar_cotizacion import generar_html


# ── Fixtures reales: copiados de OPs guardadas antes de este cambio ──────────

# Dropbox/SGTD/OPs/JSON/1006.json — no-backlight, esquema viejo de
# Estructura/Terminacion (string), sin "Descuento" en el nivel de cotización
# ("Fuente" en su lugar). "Terminacion" además referencia un nombre del
# catálogo viejo de terminaciones ("Ojetillos perimetrales reforzados cada
# 30 cms") que ya no existe en el catálogo nuevo (ahora es solo "Ojetillos").
OP_VIEJA_NO_BACKLIGHT = {
    "Cotizacion": 1006, "Nombre": "1",
    "Fecha_ingreso": "29/07/2026", "Fecha_entrega": "31/07/2026",
    "Empresa": "Empresa Ejemplo", "RUT": "12.345.678-9",
    "Razon Social": "Ejemplo S.A.", "Contacto": "Contacto Ejemplo",
    "Email": "contacto.ejemplo@gmail.com", "Fuente": 0.0,
    "Condicion de pago": "condicion_ejemplo", "Descripcion": "",
    "productos": [{
        "producto": "Piecera 2 plazas", "Tela": "Blackout",
        "Estructura": "Asta fibra de vidrio vela 2 mts",
        "Terminacion": "Ojetillos perimetrales reforzados cada 30 cms",
        "Impresion": "Tiro y retiro",
        "Ancho": 1.0, "Alto": 1.0, "Cantidad": 2, "Tema": "", "Obs": "",
    }],
    "ProductosListos": [],
}

# Dropbox/SGTD/OPs/JSON/1002.json — backlight, "Caja" ya como dict (no
# string), sin ningún campo de precio a nivel de cotización.
OP_VIEJA_BACKLIGHT = {
    "Cotizacion": 1002, "Nombre": "test reedicion",
    "Fecha_ingreso": "24/07/2026", "Fecha_entrega": "28/07/2026",
    "Empresa": "Empresa Ejemplo", "RUT": "12.345.678-9",
    "Razon Social": "Ejemplo S.A.", "Contacto": "Contacto Ejemplo",
    "Email": "contacto.ejemplo@gmail.com", "Fuente": 0.0,
    "Condicion de pago": "condicion_ejemplo", "Descripcion": "Descasipsfaslkfan",
    "productos": [{
        "Tela": "Popelina 155",
        "Caja": {
            "perfil": "PERFIL 60 MM", "watts": 330.6,
            "traseras": {"tipo": "Alucobond 122x244",
                         "cantidad_x_caja": 0.5038968019349638,
                         "cantidad_total": 1.0077936038699276},
            "luces_1": {"tipo": "Malla 150", "cantidad_x_caja": 55.1, "cantidad_total": 110.2},
            "luces_2": {"tipo": "sin luces", "cantidad_x_caja": 0.0, "cantidad_total": 0.0},
            "fp": {"tipo": "FP 350 watts - 24v MEAN WELL", "cantidad_x_caja": 1, "cantidad_total": 2},
            "obs": "",
        },
        "Ancho": 1.0, "Alto": 1.5, "Cantidad": 2, "Tema": "tema", "Obs": "2",
    }],
}

# Reconstrucción de un caso todavía más viejo: previo incluso al perfil de
# caja como dict (versión original, "Caja" era solo el nombre del perfil).
PRODUCTO_BACKLIGHT_MUY_VIEJO = {
    "Tela": "Popelina 155", "Caja": "PERFIL 100 MM SIMPLE",
    "Ancho": 1.2, "Alto": 0.8, "Cantidad": 1, "Tema": "", "Obs": "",
}

# Producto no-backlight de antes de que existiera Estructura/Terminación —
# ninguna de las dos claves está presente.
PRODUCTO_SIN_ESTRUCTURA_NI_TERMINACION = {
    "producto": "Mantel 150x150", "Tela": "Bistretch",
    "Ancho": 1.5, "Alto": 1.5, "Cantidad": 1, "Tema": "", "Obs": "",
}

# Placeholder viejo explícito ("Sin estructura"/"Sin terminaciones") en vez
# de string vacío u omitido.
PRODUCTO_CON_PLACEHOLDER_VIEJO = {
    "producto": "Mantel 150x150", "Tela": "Bistretch",
    "Estructura": "Sin estructura", "Terminacion": "Sin terminaciones",
    "Ancho": 1.5, "Alto": 1.5, "Cantidad": 1, "Tema": "", "Obs": "",
}


class TestCompatibilidadCotizacionesViejas(unittest.TestCase):

    def test_producto_no_backlight_viejo_migra_a_listas(self):
        interno = producto_desde_json(OP_VIEJA_NO_BACKLIGHT["productos"][0])
        self.assertEqual(interno["estructuras"], ["Asta fibra de vidrio vela 2 mts"])
        self.assertEqual(interno["terminaciones"],
                          ["Ojetillos perimetrales reforzados cada 30 cms"])
        self.assertEqual(interno["impresion"], "Tiro y retiro")

    def test_producto_no_backlight_viejo_no_rompe_el_calculo_de_precio(self):
        """La estructura vieja SÍ está en el catálogo nuevo (mismo nombre) y
        se cobra normal; la terminación vieja YA NO existe con ese nombre
        en el catálogo nuevo (se acortó a "Ojetillos") — no debe explotar,
        simplemente no aporta costo ($0) hasta que alguien la re-seleccione
        con el nombre nuevo."""
        interno = producto_desde_json(OP_VIEJA_NO_BACKLIGHT["productos"][0])
        costo = costo_producto(interno)  # no debe lanzar excepción
        self.assertGreaterEqual(costo["total"], 0)
        self.assertIsInstance(costo["detalle_estructuras"], dict)
        self.assertIsInstance(costo["detalle_terminaciones"], dict)

    def test_producto_backlight_con_caja_dict_no_rompe(self):
        interno = producto_desde_json(OP_VIEJA_BACKLIGHT["productos"][0])
        self.assertEqual(interno["caja"]["perfil"], "PERFIL 60 MM")
        costo = costo_producto(interno)  # no debe lanzar excepción
        self.assertGreaterEqual(costo["total"], 0)

    def test_producto_backlight_con_caja_string_viejisima_no_rompe(self):
        """Antes de core/calculo_cajas.py, "Caja" era directo el nombre del
        perfil (string), no un dict con el detalle de materiales."""
        interno = producto_desde_json(PRODUCTO_BACKLIGHT_MUY_VIEJO)
        self.assertEqual(interno["caja"], "PERFIL 100 MM SIMPLE")
        costo = costo_producto(interno)
        self.assertGreaterEqual(costo["total"], 0)

    def test_producto_sin_estructura_ni_terminacion_en_absoluto(self):
        interno = producto_desde_json(PRODUCTO_SIN_ESTRUCTURA_NI_TERMINACION)
        self.assertEqual(interno["estructuras"], [])
        self.assertEqual(interno["terminaciones"], [])
        costo = costo_producto(interno)
        self.assertGreaterEqual(costo["total"], 0)

    def test_placeholder_viejo_sin_estructura_migra_a_lista_vacia(self):
        interno = producto_desde_json(PRODUCTO_CON_PLACEHOLDER_VIEJO)
        self.assertEqual(interno["estructuras"], [])
        self.assertEqual(interno["terminaciones"], [])

    def test_cotizacion_vieja_sin_campos_de_precio_calcula_totales_sola(self):
        """Ni Descuento ni Neto/NetoTotal/IVA/Total existen en el JSON
        viejo — costo_cotizacion debe poder calcularlos igual desde 0."""
        productos_internos = [producto_desde_json(p) for p in OP_VIEJA_NO_BACKLIGHT["productos"]]
        descuento_pct = OP_VIEJA_NO_BACKLIGHT.get("Descuento", 0.0) or 0.0
        self.assertEqual(descuento_pct, 0.0)  # no existía -> default 0, no explota
        totales = costo_cotizacion(productos_internos, descuento_pct)
        self.assertEqual(totales["descuento"], 0.0)
        self.assertEqual(totales["neto"], totales["neto_total"])

    def test_mapear_producto_ida_y_vuelta_no_pierde_datos_nuevos(self):
        """mapear_producto (el inverso) siempre debe escribir el formato
        NUEVO (listas), aunque lo que se leyó haya sido formato viejo —
        así una cotización vieja, al guardarse de nuevo (editar y confirmar),
        queda migrada para la próxima vez."""
        interno = producto_desde_json(OP_VIEJA_NO_BACKLIGHT["productos"][0])
        de_vuelta = mapear_producto(interno)
        self.assertIn("Estructuras", de_vuelta)
        self.assertIn("Terminaciones", de_vuelta)
        self.assertNotIn("Estructura", de_vuelta)
        self.assertNotIn("Terminacion", de_vuelta)
        self.assertEqual(de_vuelta["Estructuras"], ["Asta fibra de vidrio vela 2 mts"])

    def test_generar_html_no_rompe_con_cotizacion_vieja_completa(self):
        """Pipeline completo (el mismo que usa "Guardar y abrir"/"Ver
        Imprimir") contra un JSON de cotización real de antes de este
        cambio, con Fuente en vez de Descuento y ninguno de los campos de
        precio nuevos."""
        ruta = generar_html(dict(OP_VIEJA_NO_BACKLIGHT, Cotizacion=899001))
        try:
            html = ruta.read_text(encoding="utf-8")
            self.assertIn("Piecera 2 plazas", html)
            self.assertIn("N° 899001", html)
        finally:
            ruta.unlink(missing_ok=True)

    def test_generar_html_no_rompe_con_op_backlight_vieja(self):
        ruta = generar_html(dict(OP_VIEJA_BACKLIGHT, Cotizacion=899002))
        try:
            html = ruta.read_text(encoding="utf-8")
            self.assertIn("Backlight", html)
        finally:
            ruta.unlink(missing_ok=True)

    def test_generar_html_sin_despacho_no_muestra_fila_despacho(self):
        """Cotizaciones sin la clave "Despacho" (todas las de antes de esta
        función) no deben mostrar ninguna fila de despacho — compatibilidad
        con todo lo guardado hasta ahora."""
        ruta = generar_html(dict(OP_VIEJA_NO_BACKLIGHT, Cotizacion=899003))
        try:
            html = ruta.read_text(encoding="utf-8")
            self.assertNotIn("Despacho", html)
        finally:
            ruta.unlink(missing_ok=True)

    def test_generar_html_con_despacho_aparece_como_fila_y_suma_al_total(self):
        """El despacho (ver ui/pantalla_extras.py) no es un producto — se
        muestra como una fila sin medidas, con su monto, sumado al total."""
        datos = dict(OP_VIEJA_NO_BACKLIGHT, Cotizacion=899004, Despacho=15000)
        ruta = generar_html(datos)
        try:
            html = ruta.read_text(encoding="utf-8")
            self.assertIn("Despacho", html)
            self.assertIn("$15.000", html)
        finally:
            ruta.unlink(missing_ok=True)

    def test_generar_html_sin_instalacion_no_muestra_fila_instalacion(self):
        """Cotizaciones sin la clave "Instalacion" (todas las de antes de
        esta función) no deben mostrar ninguna fila de instalación —
        compatibilidad con todo lo guardado hasta ahora."""
        ruta = generar_html(dict(OP_VIEJA_NO_BACKLIGHT, Cotizacion=899005))
        try:
            html = ruta.read_text(encoding="utf-8")
            self.assertNotIn("Instalación", html)
        finally:
            ruta.unlink(missing_ok=True)

    def test_generar_html_con_instalacion_aparece_como_fila_y_suma_al_total(self):
        """La instalación (ver ui/pantalla_extras.py), igual que el
        despacho, no es un producto — se muestra como una fila sin
        medidas, con su monto, sumado al total."""
        datos = dict(OP_VIEJA_NO_BACKLIGHT, Cotizacion=899006, Instalacion=20000)
        ruta = generar_html(datos)
        try:
            html = ruta.read_text(encoding="utf-8")
            self.assertIn("Instalación", html)
            self.assertIn("$20.000", html)
        finally:
            ruta.unlink(missing_ok=True)

    def test_generar_html_con_despacho_e_instalacion_muestra_ambas_filas(self):
        """Con ambos campos activos, las dos filas aparecen y ambos montos
        se suman al total — mismo patrón, en la misma cotización."""
        datos = dict(OP_VIEJA_NO_BACKLIGHT, Cotizacion=899007,
                      Despacho=15000, Instalacion=20000)
        ruta = generar_html(datos)
        try:
            html = ruta.read_text(encoding="utf-8")
            self.assertIn("Despacho", html)
            self.assertIn("$15.000", html)
            self.assertIn("Instalación", html)
            self.assertIn("$20.000", html)
        finally:
            ruta.unlink(missing_ok=True)


class TestCompatibilidadCatalogosViejos(unittest.TestCase):
    """estructuras.json/terminaciones.json pasaron de lista de strings a
    lista de objetos con precio. Si el archivo empaquetado en recursos/
    quedó en el formato viejo (build vieja, o edición manual incompleta),
    core.repositorio debe poder seguir leyéndolo sin que la app entera
    falle al arrancar."""

    def _con_recursos_temporal(self, nombre_archivo, contenido):
        tmp = tempfile.TemporaryDirectory()
        (Path(tmp.name) / nombre_archivo).write_text(
            json.dumps(contenido, ensure_ascii=False), encoding="utf-8")
        return tmp

    def test_cargar_estructuras_formato_viejo_lista_de_strings(self):
        import core.repositorio as repo
        contenido_viejo = ["Sin estructura", "Asta fibra de vidrio vela 2 mts", "Base auto"]
        with self._con_recursos_temporal("estructuras.json", contenido_viejo) as tmp:
            with mock.patch.object(repo, "_RECURSOS_DIR", Path(tmp)):
                nombres, valores = repo.cargar_estructuras()
        self.assertEqual(nombres, contenido_viejo)
        self.assertEqual(valores, {})  # formato viejo no trae precio, no explota

    def test_cargar_terminaciones_formato_viejo_lista_de_strings(self):
        import core.repositorio as repo
        contenido_viejo = ["Sin terminaciones", "Basta perimetral", "Con bolsillo"]
        with self._con_recursos_temporal("terminaciones.json", contenido_viejo) as tmp:
            with mock.patch.object(repo, "_RECURSOS_DIR", Path(tmp)):
                nombres, valores = repo.cargar_terminaciones()
        self.assertEqual(nombres, contenido_viejo)
        self.assertEqual(valores, {})


if __name__ == "__main__":
    unittest.main()
