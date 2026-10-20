/* Mocks del contrato común de ui/api_app.py — lo que toda página usa. */

export default {
  obtener_contexto: () => ({
    version: "0.0.0-mock",
    escala_ui: 1,
    hoy_iso: new Date().toISOString().slice(0, 10),
    fecha: new Date().toLocaleDateString("es-CL").replace(/\//g, "-"),
    modulos_habilitados: { cotizaciones: true, ops: true, despachos: true, inventario: true },
    stock_minimo_ml: 25,
  }),
  guardar_preferencia: () => true,
  abrir_manual: () => console.info("[mock] abrir_manual"),
  notificar_ruta: () => {},
  poner_titulo: () => {},
};
