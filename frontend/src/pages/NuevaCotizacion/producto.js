import { aNumero } from "@/utils/formato";

/* Reglas de un producto de la cotización, sin nada de pantalla. El objeto es
   EXACTAMENTE lo que se manda a Python (calcular_productos, guardar_progreso,
   guardar_cotizacion — ver ui/api_cotizacion.py): si algo no está acá, no se
   guarda. `calc` es lo que devuelve Python (costos, ML/M², error...). */

export const SIN_CAJA = "Sin caja";
export const CAJA_TERMINADA = "CAJA TERMINADA";

export function productoVacio(tipo = "estandar") {
  return {
    tipo,
    producto: "", textil: "", impresion: "Cara única",
    estructuras: [], terminaciones: [],
    tela: "", perfil: SIN_CAJA, luces_1: "", luces_2: "sin luces",
    terminaciones_caja: CAJA_TERMINADA,
    ancho: "", alto: "", cantidad: "1", tema: "", obs: "", forzar: false,
    calc: null,
  };
}

/* Los <select> de backlight tienen que tener en el estado un valor que esté
   entre sus opciones: si no, el navegador muestra la primera opción pero a
   Python le llega "" y el cálculo se hace sin luces — sin aviso de ningún
   tipo, parece que anduviera todo bien. Y con perfil, el margen de costura
   es siempre caja terminada (el switch ni se muestra, ver PanelProducto). */
export function normalizar(p, cat) {
  const luces = cat.luces || [];
  const n = { ...p };
  if (luces.length && !luces.includes(n.luces_1)) n.luces_1 = luces[0];
  if (luces.length && !luces.includes(n.luces_2)) n.luces_2 = luces.includes("sin luces") ? "sin luces" : luces[0];
  if (![SIN_CAJA, ...(cat.perfiles || [])].includes(n.perfil)) n.perfil = SIN_CAJA;
  if (n.perfil !== SIN_CAJA) n.terminaciones_caja = CAJA_TERMINADA;
  return n;
}

/* "Sin tocar" = ningún campo se movió del default — el tipo no cuenta (es
   justo lo que se le va a pisar) ni calc. Sirve para propagar el tipo
   backlight/estándar a los productos que siguen: las cotizaciones mixtas
   existen pero son la excepción. */
export function esVacio(p, cat) {
  const limpio = normalizar(productoVacio(p.tipo), cat);
  return Object.keys(limpio).every((clave) =>
    clave === "tipo" || clave === "calc" || JSON.stringify(p[clave]) === JSON.stringify(limpio[clave]));
}

/* Completo = su panel dejaría avanzar. El textil/tela NO es obligatorio por
   sí solo: un backlight sin tela vale si tiene una caja de verdad, y un
   estándar sin textil vale si tiene alguna estructura o terminación (si no,
   no tendría nada que cobrar). */
export function completo(p) {
  const base = aNumero(p.ancho) > 0 && aNumero(p.alto) > 0 && parseInt(p.cantidad, 10) > 0;
  if (!base) return false;
  if (p.calc?.error && !p.forzar) return false;
  if (p.tipo === "backlight") return !!p.tela || (!!p.perfil && p.perfil !== SIN_CAJA);
  const conExtras = p.estructuras.length > 0 || p.terminaciones.length > 0;
  return !!p.producto.trim() && (!!p.textil.trim() || conExtras);
}

/* Un monto escrito a mano ("$10.000") en vez de un ítem del catálogo. */
export const esMonto = (texto) => /^\$?\s*[\d.,]+$/.test(texto);

/* Todo lo que, si cambia, cambia el cálculo: el producto sin `calc`. */
export const firma = (productos) => JSON.stringify(productos.map(({ calc, ...resto }) => resto));
