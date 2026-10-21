/* Mocks del contrato común de ui/api_app.py — lo que toda página usa. */

import { contextoNuevaCotizacion } from "./nuevaCotizacion";

/* Lo que cada pantalla suma al contexto común (ApiApp.obtener_contexto con
   `pantalla`, ver ui/api_app.py). */
const CONTEXTO_PANTALLA = {
  "nueva-cotizacion": contextoNuevaCotizacion,
};

export default {
  obtener_contexto: (pantalla, argumentos) => ({
    version: "0.0.0-mock",
    escala_ui: 1,
    hoy_iso: new Date().toISOString().slice(0, 10),
    fecha: new Date().toLocaleDateString("es-CL").replace(/\//g, "-"),
    modulos_habilitados: { inventario: true, cotizaciones: true, ops: true, despachos: false },  // igual que core/config.py
    stock_minimo_ml: 25,
    ...(CONTEXTO_PANTALLA[pantalla]?.(argumentos) || {}),
  }),
  guardar_preferencia: () => true,
  abrir_manual: () => console.info("[mock] abrir_manual"),
  // En la app abre ventanas aparte (p. ej. el panel de producción).
  ir: (destino) => window.TD?.aviso?.(`[mock] abriría "${destino}" en su propia ventana.`, "info"),
  notificar_ruta: () => {},
  poner_titulo: () => {},
};
