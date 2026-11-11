/* Mocks de ver-cotización (ui/api_ver_cotizacion.py). Datos inventados. La
   9013 simula falta de stock al aprobar; las demás aprueban. La 9015 trae
   precios que cambiaron desde que se hizo (core/lista_precios.py). Los
   números son los mismos que lista el mock del menú (9015 … 9006). */

import ejemplos from "./cotizacionesDescuentos.json";
import { montoManual } from "@/components/Descuentos/Descuentos";

/* Qué devuelve lista_precios.cambios() para la 9015, hasta que se decide. */
let cambios9015 = {
  firma: "mock",
  componentes: [
    { tipo: "Textil", nombre: "Poliéster satinado", antes: 9500, ahora: 10800, unidad: "/ML", formato: "pesos" },
    { tipo: "Terminación", nombre: "Bolsillo", antes: 1200, ahora: 1400, unidad: "/un.", formato: "pesos" },
    { tipo: "Material", nombre: "Ojetillos", antes: 35, ahora: 42, unidad: "/un.", formato: "pesos" },
  ],
  productos: [
    { indice: 0, nombre: "Pendón roller", antes: 389000, ahora: 417000 },
    { indice: 2, nombre: "Lienzo", antes: 268000, ahora: 291400 },
  ],
  total: { antes: 1282239, ahora: 1338601 },
};

const NUMEROS = Array.from({ length: 10 }, (_, i) => 9015 - i);
const EMPRESAS = ["Tiendas Ejemplo SpA", "Café del Puerto", "Gimnasio Activo", "Clínica Norte",
  "Librería Central", "Hotel Mirador", "Constructora Andes", "Pastelería Dulce", "Óptica Visión", "Colegio San Marcos"];

const productos = [
  { tipo: "estandar", producto: "Pendón roller", textil: "Poliéster satinado", impresion: "Sublimación",
    estructuras: ["Roller 85"], terminaciones: ["Bolsillo"], tela: "", caja: "", tema: "Verano 2027", obs: "",
    ancho: 0.85, alto: 2, cantidad: 10, ml: 20, m2: null, total: 389000 },
  { tipo: "backlight", producto: "", textil: "", impresion: "", estructuras: [], terminaciones: [],
    tela: "Tela backlit", caja: "Caja 10 cm", tema: "Vitrina", obs: "Entregar armada",
    ancho: 2.4, alto: 1.2, cantidad: 2, ml: null, m2: 5.76, total: 512000 },
  { tipo: "estandar", producto: "Lienzo", textil: "Lona mate", impresion: "Látex",
    estructuras: [], terminaciones: ["Ojetillos", "Dobladillo"], tela: "", caja: "", tema: "Fachada", obs: "",
    ancho: 6, alto: 3, cantidad: 1, ml: 18, m2: null, total: 268000 },
];

/* 9014 … 9010: las 5 cotizaciones de prueba de los descuentos (DropboxDev
   1000 … 1004, tal cual las devuelve obtener_cotizacion): sin descuento, gana
   el del contacto, gana el de volumen, volumen por varios textiles y backlight. */
const CON_DESCUENTOS = { 9014: 0, 9013: 1, 9012: 2, 9011: 3, 9010: 4 };

/* Descuentos puestos a mano por cotización (guardar_descuentos_cotizacion),
   recalculados acá con la misma regla de core.precios: el manual reemplaza
   al automático de su línea y el del pedido va sobre lo que queda. */
const manuales = {};

const lineaConManual = (l, m) => {
  if (m === undefined || m === null) {
    const a = l.automatico;
    return { ...l, manual: null, monto: a.monto, pct: a.pct, razon: a.razon, total: l.precio - a.monto };
  }
  const monto = montoManual(m, l.precio);
  return { ...l, manual: m, monto, pct: l.precio ? (monto / l.precio) * 100 : 0, razon: "manual", total: l.precio - monto };
};

function conManuales(cot) {
  const man = manuales[cot.numero];
  if (!man) return cot;
  const productos = cot.productos.map((p, i) => ({ ...p, descuento: lineaConManual(p.descuento, man.productos?.[i]) }));
  const d = { ...cot.descuento };
  for (const k of ["despacho", "instalacion"]) if (d[k]) d[k] = lineaConManual(d[k], man[k]);
  const lineas = productos.reduce((s, p) => s + p.descuento.monto, 0) + (d.despacho?.monto || 0) + (d.instalacion?.monto || 0);
  const base = cot.totales.neto - lineas;
  const montoPedido = montoManual(man.pedido, base) || 0;
  d.pedido = { manual: man.pedido || null, base, monto: montoPedido, pct: base > 0 ? (montoPedido / base) * 100 : 0 };
  d.hay_manuales = true;
  const descuento = lineas + montoPedido, netoTotal = cot.totales.neto - descuento, iva = netoTotal * 0.19;
  return { ...cot, productos, descuento: d,
           totales: { ...cot.totales, descuento_monto: descuento, neto_total: netoTotal, iva, total: netoTotal + iva } };
}

function cotizacion(numero) {
  if (numero in CON_DESCUENTOS) return conManuales({ ...ejemplos[CON_DESCUENTOS[numero]], numero });
  const i = Math.max(0, NUMEROS.indexOf(numero));
  const neto = 1169000, descuento = 116900, netoTotal = neto - descuento, iva = Math.round(netoTotal * 0.19);
  return {
    numero,
    nombre: "Campaña verano",
    empresa: EMPRESAS[i],
    rut: "76.123.456-7",
    razon_social: `${EMPRESAS[i]} Limitada`,
    contacto: "María Pérez",
    email: "maria@ejemplo.cl",
    condicion: "30 días",
    fecha: `${18 - i}/10/2026`,
    descripcion: "Material gráfico para la temporada de verano: pendones, backlight de vitrina y lienzo de fachada.",
    totales: {
      impresion: 812000, estructuras: 241000, terminaciones: 116000, despacho: 25000, instalacion: null,
      neto, descuento_pct: 10, descuento_monto: descuento, fuente_descuento: "normal",
      neto_total: netoTotal, iva_pct: 19, iva, total: netoTotal + iva,
    },
    descuento: {
      aplicado: "contacto", contacto: { pct: 10, monto: descuento },
      volumen: { monto: 0, grupos: [{ nombre: "Poliéster satinado", m2: 17, pct: 0, base: 0, monto: 0, en_minimo: [] }] },
      tramo_desde: 10, minimo: { ml: 2, m2: 2 }, hay_manuales: false,
      despacho: { nombre: "Despacho", precio: 25000, monto: 2500, total: 22500, pct: 10, razon: "contacto", manual: null,
                  automatico: { monto: 2500, pct: 10, razon: "contacto" } },
      instalacion: null,
      pedido: { manual: null, base: neto - descuento, monto: 0, pct: 0 },
    },
    productos: (i % 2 ? productos.slice(0, 2) : productos).map((p) => ({
      ...p, descuento: { nombre: p.producto || p.tela, precio: p.total, monto: p.total * 0.1, total: p.total * 0.9,
                         pct: 10, razon: "contacto", manual: null, automatico: { monto: p.total * 0.1, pct: 10, razon: "contacto" },
                         en_minimo: false, minimo: null },
    })),
    cambios_precios: numero === 9015 ? cambios9015 : null,
  };
}

/* Si el cliente la tiene (ui/api_correos.estado_envio): 9014 cambió desde el
   último envío, 9013 está al día y el resto nunca se envió. */
const ENVIADAS = {
  9014: { estado: "con_cambios", fecha: "05/11/2026 16:40" },
  9013: { estado: "al_dia", fecha: "10/11/2026 11:02" },
};
function conCorreo(cot) {
  const e = ENVIADAS[cot.numero];
  return {
    ...cot,
    estado_correo: e?.estado || "sin_enviar",
    ultimo_correo: e ? { fecha: e.fecha, para: [cot.email || "cliente@ejemplo.cl"], copia: [],
                         asunto: `Cotización ${cot.numero} - ${cot.empresa}`, prueba: true, simulado: false } : null,
  };
}

export default {
  obtener_cotizacion: (numero) => conCorreo(cotizacion(Number(numero))),

  cotizacion_adyacente(numero, direccion) {
    const i = NUMEROS.indexOf(Number(numero));
    if (i === -1) return null;
    return NUMEROS[(i + (direccion === "siguiente" ? 1 : -1) + NUMEROS.length) % NUMEROS.length];
  },

  verificar_materiales_cotizacion: (numero) => (Number(numero) === 9013
    ? [{ textil: "Tela backlit", faltante: 3.5, necesario: 16, disponible: 12.5 }]
    : []),

  materiales_manuales_pendientes: () => [{ id: "m-1", nombre: "Cinta doble faz", tipo: "unidad" }],

  aprobar_cotizacion: (numero, ingreso, entrega, consumos) => {
    console.info("[mock] aprobar_cotizacion", numero, ingreso, entrega, consumos);
    return { ok: true };
  },

  /* Solo las 9014 … 9010 (las de los descuentos) los recalculan. */
  guardar_descuentos_cotizacion(numero, cambios) {
    const man = (manuales[numero] ||= { productos: {} });
    for (const [i, m] of Object.entries(cambios.productos || {})) man.productos[i] = m;
    for (const k of ["despacho", "instalacion", "pedido"]) if (k in cambios) man[k] = cambios[k];
    return cotizacion(Number(numero));
  },
  restablecer_descuentos_cotizacion(numero) {
    delete manuales[numero];
    return cotizacion(Number(numero));
  },

  actualizar_precios_cotizacion: () => { cambios9015 = null; return true; },
  mantener_precios_cotizacion: () => { cambios9015 = null; return true; },
  eliminar_cotizacion: (numero) => console.info("[mock] eliminar_cotizacion", numero),
  imprimir_cotizacion: (numero) => console.info("[mock] imprimir_cotizacion", numero),
};
