/* Mocks de nueva cotización (ui/api_cotizacion.py). Las cifras salen de una
   fórmula INVENTADA: sirven para mirar la pantalla, no para cotizar. En la
   app, todo número sale de core/precios.py. */

const TEXTILES_ANCHOS = { "Poliéster satinado": 1.5, "Lona mate": 3.2, "Felpa gruesa": 1.4, "Tela backlit": 3 };

const catalogos = {
  productos: ["Pendón roller", "Lienzo", "Bandera", "Telón", "Cojín"],
  textiles: ["Poliéster satinado", "Lona mate", "Felpa gruesa", "Tela sin precio"],
  textiles_sin_precio: ["Tela sin precio"],
  textiles_anchos: TEXTILES_ANCHOS,
  telas_backlight: ["Tela backlit", "Tela backlit premium"],
  estructuras: ["Roller 85", "Roller 100", "Bastidor", "Ojetillos"],
  terminaciones: ["Bolsillo", "Dobladillo", "Velcro", "Ojetillos"],
  estructuras_unit: ["Roller 85", "Roller 100"],
  terminaciones_unit: ["Ojetillos"],
  perfiles: ["Perfil 4 cm", "Perfil 10 cm"],
  luces: ["M12", "M24", "sin luces"],
  clientes: [
    { empresa: "Tiendas Ejemplo SpA", rut: "76.123.456-7", razon_social: "Tiendas Ejemplo SpA Limitada" },
    { empresa: "Café del Puerto", rut: "77.890.123-4", razon_social: "Café del Puerto Ltda." },
  ],
  contactos: [
    { contacto: "María Pérez", email: "maria@ejemplo.cl", descuento: "10", condicion: "30 días" },
    { contacto: "Juan Soto", email: "juan@cafe.cl", descuento: "0", condicion: "Contado" },
  ],
};

const n = (v) => parseFloat(String(v ?? "").replace(",", ".")) || 0;
const MONTO = /^\$?\s*[\d.,]+$/;
const montoDe = (item, porUnidad) => (MONTO.test(item) ? n(item.replace(/[$.\s]/g, "")) : porUnidad);

function calcular(p) {
  const ancho = n(p.ancho), alto = n(p.alto), cant = parseInt(p.cantidad, 10) || 0;
  if (!(ancho > 0 && alto > 0 && cant > 0)) return null;
  const nombre = p.tipo === "backlight" ? p.tela : p.textil;
  const ancho_max = TEXTILES_ANCHOS[nombre] ?? null;
  const corto = Math.min(ancho, alto);
  const error = ancho_max != null && corto > ancho_max
    ? `El lado corto (${corto.toFixed(2)} m) excede el ancho máximo del textil (${ancho_max.toFixed(2)} m).`
    : null;

  if (p.tipo === "backlight") {
    const m2 = Math.round(ancho * alto * cant * 100) / 100;
    const conCaja = p.perfil && p.perfil !== "Sin caja";
    const total = Math.round(m2 * (p.tela ? 45000 : 0) + (conCaja ? 60000 * cant : 0) + 4000 * cant);
    return {
      m2, watts: conCaja ? Math.round(ancho * alto * 40) : 0,
      materiales: conCaja ? [
        { material: p.perfil, tipo: "perfil", cantidad_x_caja: 2 * (ancho + alto), cantidad_total: 2 * (ancho + alto) * cant },
        { material: p.luces_1, tipo: "luces", cantidad_x_caja: Math.ceil(alto * 4), cantidad_total: Math.ceil(alto * 4) * cant },
      ] : [],
      materiales_inventario: [{ nombre: "Silicona", consumo: 2 * (ancho + alto) * cant, unidad: "m", monto: 4000 * cant }],
      costo_materiales: 4000 * cant, ancho_max, error,
      valor_unitario: Math.round(total / cant), total,
    };
  }

  const ml = Math.round((p.textil ? Math.max(ancho, alto) * cant : 0) * 100) / 100;
  const costo_impresion = Math.round(ml * 9000 * (p.impresion === "Tiro y retiro" ? 1.8 : 1));
  const detalle = (items, porUnidad) => Object.fromEntries(items.map((x) => [x, montoDe(x, porUnidad) * cant]));
  const detalle_estructuras = detalle(p.estructuras, 15000);
  const detalle_terminaciones = detalle(p.terminaciones, 2500);
  const costo_extras = [...Object.values(detalle_estructuras), ...Object.values(detalle_terminaciones)].reduce((a, b) => a + b, 0);
  const total = costo_impresion + costo_extras;
  // "Lona mate" se cobra por rollo y, pasado 10 ML, ningún rollo alcanza (ver avisoTextil).
  const precio_textil = p.textil === "Lona mate"
    ? { textil: p.textil, cobro: "rollo", valor: ml > 10 ? 9500 : 9000, origen: ml > 10 ? "sin_rollo" : "rollo", rollo: ml > 10 ? null : "0030" }
    : null;
  return {
    ml, costo_impresion, costo_extras, detalle_estructuras, detalle_terminaciones,
    total, valor_unitario: Math.round(total / cant), ancho_max, error, precio_textil,
  };
}

/* Lo que ApiCotizacion.contexto_extra suma al contexto de la pantalla. */
export function contextoNuevaCotizacion({ editar, pendiente } = {}) {
  const ctx = { fecha_iso: new Date().toISOString().slice(0, 10), numero_sugerido: "9016", numero_editando: null, estado: null };
  if (editar || pendiente) {
    ctx.estado = {
      id: pendiente || null,
      nombre_trabajo: "Vitrinas navidad",
      despacho: 25000, instalacion: null,
      cliente: {
        empresa: "Tiendas Ejemplo SpA", rut: "76.123.456-7", razon_social: "Tiendas Ejemplo SpA Limitada",
        contacto: "María Pérez", email: "maria@ejemplo.cl", descuento: "10", condicion: "30 días",
        fecha: ctx.fecha_iso, numero: editar ? String(editar) : "", descripcion: "Vitrinas de temporada",
      },
      productos: [
        { tipo: "estandar", producto: "Pendón roller", textil: "Poliéster satinado", impresion: "Cara única",
          estructuras: ["Roller 85"], terminaciones: [], ancho: "0.85", alto: "2", cantidad: "4", tema: "Navidad", obs: "" },
        { tipo: "backlight", tela: "Tela backlit", perfil: "Perfil 10 cm", luces_1: "M12", luces_2: "sin luces",
          ancho: "2.4", alto: "1.2", cantidad: "2", tema: "Vitrina", obs: "" },
        { tipo: "estandar", producto: "", textil: "", ancho: "", alto: "", cantidad: "1" },
      ],
    };
    if (editar) ctx.numero_editando = String(editar);
  }
  return ctx;
}

const tomados = new Set(["9014", "9015"]);

export default {
  obtener_catalogos: () => structuredClone(catalogos),
  calcular_productos: (productos) => productos.map(calcular),
  numero_disponible: (numero, propio) => numero === propio || !tomados.has(String(numero)),
  verificar_materiales: (productos) => (productos.some((p) => p.tipo === "backlight" && n(p.ancho) * n(p.alto) * (parseInt(p.cantidad, 10) || 0) > 5)
    ? [{ textil: "Tela backlit", faltante: 3.5, necesario: 16, disponible: 12.5 }] : []),
  guardar_progreso: (estado) => {
    console.info("[mock] guardar_progreso", estado);
    return { id: estado.id || "p-mock", guardado_en: new Date().toLocaleString("es-CL").slice(0, 16) };
  },
  guardar_cotizacion: (estado, abrir) => {
    console.info("[mock] guardar_cotizacion", estado, { abrir });
    return { numero: Number(estado.cliente.numero) };
  },
  guardar_cliente: (empresa, rut) => (catalogos.clientes.some((c) => c.rut === rut && c.empresa !== empresa)
    ? { ok: false, error: "Ese RUT ya está registrado a nombre de otra empresa: revisa el RUT." } : { ok: true }),
  guardar_contacto: () => undefined,
};
