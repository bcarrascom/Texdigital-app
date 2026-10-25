/* Todas las rutas de la app en un solo lugar. Las páginas nunca escriben
   una URL a mano: usan estas funciones, así cambiar una ruta es tocar una
   línea.

       navigate(rutas.verDespacho(42));             // → "/despachos/42"
       navigate(rutas.inventario({ buscar: "X" }));  // → "/inventario?buscar=X"

   Equivalencia con las pantallas viejas (recursos/pantallas/*.html) y el
   nombre de pantalla que espera ApiApp.obtener_contexto(): */

/* "?clave=valor" con solo los parámetros que tienen valor. */
function consulta(params = {}) {
  const definidos = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return definidos.length ? "?" + new URLSearchParams(definidos).toString() : "";
}

export const rutas = {
  inicio:               () => "/",                                   // menu
  desarrollo:           () => "/dev",                                // (temporal, ver IndiceDesarrollo)

  // Módulos (antes eran paneles dentro de menu.html)
  inventario:           (params) => "/inventario" + consulta(params), // ?vista=materiales · ?buscar=textil · ?nuevo_textil=textil
  cotizaciones:         () => "/cotizaciones",
  ops:                  () => "/ops",
  despachos:            () => "/despachos",

  nuevaCotizacion:      () => "/cotizaciones/nueva",                 // nueva-cotizacion
  editarCotizacion:     (numero) => `/cotizaciones/${numero}/editar`,// nueva-cotizacion (editar)
  retomarPendiente:     (id) => `/cotizaciones/pendientes/${id}`,    // nueva-cotizacion (pendiente)
  verCotizacion:        (numero) => `/cotizaciones/${numero}`,       // ver-cotizacion
  historialOps:         () => "/ops/historial",                      // historial-ops
  verOp:                (numero) => `/ops/${numero}`,                // ver-op
  gestionarDirecciones: () => "/despachos/direcciones",              // gestionar-direcciones
  verDespacho:          (numero) => `/despachos/${numero}`,          // ver-despacho
  asignarDespacho:      (numero) => `/despachos/${numero}/asignar`,  // asignar-despacho
  verRollo:             (id) => `/inventario/rollos/${id}`,          // ver-rollo
  verMaterial:          (id) => `/inventario/materiales/${id}`,      // ver-material
  reportesInventario:   (params) => "/inventario/reportes" + consulta(params), // ?anio=2026&mes=9

  // Configuración (no es un módulo de producción: se entra por el engranaje del menú)
  configuracion:        (categoria) => "/configuracion" + (categoria ? `/${categoria}` : ""),
};

/* Los módulos del menú, en el orden en que aparecen. `clave` es la misma de
   core/config.py::MODULOS_HABILITADOS y del tema de color (data-tema). */
export const MODULOS = [
  { clave: "inventario",   titulo: "Inventario",            ruta: () => rutas.inventario() },
  { clave: "cotizaciones", titulo: "Cotizaciones",          ruta: rutas.cotizaciones },
  { clave: "ops",          titulo: "Órdenes de Producción", ruta: rutas.ops },
  { clave: "despachos",    titulo: "Despachos",             ruta: rutas.despachos },
];
