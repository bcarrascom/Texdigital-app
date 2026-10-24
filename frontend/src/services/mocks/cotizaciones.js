/* Mocks de ver-cotización (ui/api_ver_cotizacion.py). Datos inventados. La
   9013 simula falta de stock al aprobar; las demás aprueban. La 9015 trae
   precios que cambiaron desde que se hizo (core/lista_precios.py). Los
   números son los mismos que lista el mock del menú (9015 … 9006). */

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

function cotizacion(numero) {
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
      neto, descuento_pct: 10, descuento_monto: descuento, fuente_descuento: "contacto",
      neto_total: netoTotal, iva_pct: 19, iva, total: netoTotal + iva,
    },
    productos: i % 2 ? productos.slice(0, 2) : productos,
    cambios_precios: numero === 9015 ? cambios9015 : null,
  };
}

export default {
  obtener_cotizacion: (numero) => cotizacion(Number(numero)),

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

  actualizar_precios_cotizacion: () => { cambios9015 = null; return true; },
  mantener_precios_cotizacion: () => { cambios9015 = null; return true; },
  eliminar_cotizacion: (numero) => console.info("[mock] eliminar_cotizacion", numero),
  imprimir_cotizacion: (numero) => console.info("[mock] imprimir_cotizacion", numero),
};
