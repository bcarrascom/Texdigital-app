/* Todas las rutas de la app en un solo lugar. Las páginas nunca escriben
   una URL a mano: usan estas funciones, así cambiar una ruta es tocar una
   línea.

       navigate(rutas.verDespacho(42));      // → "/despachos/42"
       <Link to={rutas.historialOps()}>      // → "/ops/historial"

   Equivalencia con las pantallas viejas (recursos/pantallas/*.html) y el
   nombre de pantalla que espera ApiApp.obtener_contexto(): */

export const rutas = {
  inicio:               () => "/",                                   // menu
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
};
