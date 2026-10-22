/* Mocks de Despachos (ui/api_ver_despacho.py, api_asignar_despacho.py,
   api_gestionar_direcciones.py y lo de Despachos en api_menu.py). Datos
   inventados, guardados en memoria: se pierden al recargar. El resumen del
   menú (mocks/menu.js) lee de acá las dos listas del módulo, así entregar o
   eliminar se ve al volver a pedirlo. */

const RM = "Región Metropolitana";
const direccionA = { rut: "76.123.456-7", empresa: "Tiendas Ejemplo SpA", calle: "Av. Providencia", numero: "1234", comuna: "Providencia", region: RM };
const direccionB = { rut: "76.123.456-7", empresa: "Tiendas Ejemplo SpA", calle: "Los Carrera", numero: "560", comuna: "Concepción", region: "Región del Biobío" };

let siguienteDireccion = 5;
let direcciones = [
  { id: "d1", ...direccionA, alias: "Casa matriz", referencia: "Piso 3" },
  { id: "d2", ...direccionB, alias: "", referencia: "" },
  { id: "d3", rut: "77.555.111-2", empresa: "Café del Puerto", alias: "", calle: "Blanco", numero: "1100", comuna: "Valparaíso", region: "Región de Valparaíso", referencia: "Local 4" },
  { id: "d4", rut: "65.432.100-K", empresa: "Clínica Norte", alias: "Bodega", calle: "Av. Recoleta", numero: "3200", comuna: "Recoleta", region: RM, referencia: "" },
];

const clientes = [
  { empresa: "Tiendas Ejemplo SpA", rut: "76.123.456-7" },
  { empresa: "Café del Puerto", rut: "77.555.111-2" },
  { empresa: "Clínica Norte", rut: "65.432.100-K" },
  { empresa: "Librería Central", rut: "78.900.200-3" },
];

const REGIONES = ["Región de Arica y Parinacota", "Región de Tarapacá", "Región de Antofagasta", "Región de Atacama", "Región de Coquimbo", "Región de Valparaíso", RM, "Región del Libertador General Bernardo O'Higgins", "Región del Maule", "Región de Ñuble", "Región del Biobío", "Región de La Araucanía", "Región de Los Ríos", "Región de Los Lagos", "Región de Aysén del General Carlos Ibáñez del Campo", "Región de Magallanes y de la Antártica Chilena"];   // las de core/repositorio.py

const producto = (nombre, tema, cantidad, direccion = null) =>
  ({ nombre, tema, cantidad, cantidad_despachada: 0, pendiente: cantidad, direccion });

/* Las OPs que están en Despachos. `asignacion`: "pendiente" mientras falte
   dirección en algún producto (ver _sincronizar_carpeta). */
const ops = {
  42: {
    numero: 42, nombre: "Campaña verano", empresa: "Tiendas Ejemplo SpA", rut: "76.123.456-7",
    contacto: "María Pérez", email: "maria@ejemplo.cl", fecha_completada: "15-10-2026",
    estado_despacho: "parcial", instalacion: true,
    productos: [
      { ...producto("Pendón roller", "Verano 2027", 10, direccionA), cantidad_despachada: 4, pendiente: 6 },
      producto("Backlight · Tela backlit", "Vitrina", 2, direccionA),
      producto("Lienzo", "Fachada", 1, direccionB),
    ],
    guias: [{ numero_guia: "42-1", fecha: "16-10-2026", items: [{ producto: "Pendón roller", cantidad: 4 }] }],
  },
  9011: {
    numero: 9011, nombre: "Menú de pared", empresa: "Café del Puerto", rut: "77.555.111-2", contacto: "Jorge Soto",
    estado_despacho: "pendiente", instalacion: false,
    productos: [producto("Backlight · Tela backlit", "Menú", 1, direcciones[2])], guias: [],
  },
  9008: {
    numero: 9008, nombre: "Señalética interior", empresa: "Clínica Norte", rut: "65.432.100-K", contacto: "Ana Rivas",
    estado_despacho: "pendiente", instalacion: true,
    productos: [producto("Letrero", "Recepción", 2, direcciones[3]), producto("Pendón", "Pasillos", 6, { ...direccionA, comuna: "Las Condes" })], guias: [],
  },
  9015: {
    numero: 9015, nombre: "Vitrinas navidad", empresa: "Tiendas Ejemplo SpA", rut: "76.123.456-7", contacto: "María Pérez",
    estado_despacho: "pendiente", instalacion: false,
    productos: [producto("Pendón roller", "Navidad", 8, direccionA), producto("Lienzo", "Fachada", 1), producto("Backlight · Tela backlit", "Vitrina", 3)], guias: [],
  },
  9013: {
    numero: 9013, nombre: "Feria del libro", empresa: "Librería Central", rut: "78.900.200-3", contacto: "Pablo Díaz",
    estado_despacho: "pendiente", instalacion: false,
    productos: [producto("Pendón", "Stand", 4), producto("Telón", "Escenario", 1)], guias: [],
  },
};
const completa = (o) => o.productos.length > 0 && o.productos.every((p) => p.direccion);

/* Comuna (o región fuera de la Metropolitana) de cada producto, sin repetir
   — como ui/api_menu.py::_ubicaciones. */
function ubicaciones(o) {
  const lista = [];
  o.productos.forEach((p) => {
    const lugar = p.direccion && (p.direccion.region === RM ? p.direccion.comuna : p.direccion.region);
    if (lugar && !lista.includes(lugar)) lista.push(lugar);
  });
  return lista;
}

/* Las dos listas del módulo, como las arma ApiMenu.obtener_resumen. */
export function resumenDespachos() {
  const todas = Object.values(ops).sort((a, b) => b.numero - a.numero);
  return {
    despachos: todas.filter((o) => !completa(o)).map((o) => ({
      numero: o.numero, nombre: o.nombre, asignados: o.productos.filter((p) => p.direccion).length, total: o.productos.length,
    })),
    despachos_asignados: todas.filter(completa).map((o) => ({
      numero: o.numero, nombre: o.nombre, empresa: o.empresa, estado_despacho: o.estado_despacho, ubicaciones: ubicaciones(o),
    })),
  };
}

const opDe = (numero) => ops[numero] ?? ops[42];

export default {
  // ── Ver despacho ──
  obtener_despacho: (numero) => {
    const o = opDe(numero);
    return structuredClone({ ...o, estado_asignacion: completa(o) ? "asignada" : "pendiente",
                             productos_sin_direccion: o.productos.filter((p) => !p.direccion).length });
  },
  generar_guia_despacho(numero, items, observaciones) {
    const op = opDe(numero);
    items.forEach(({ indice_producto, cantidad }) => {
      const p = op.productos[indice_producto];
      p.cantidad_despachada += cantidad;
      p.pendiente = Math.max(0, p.cantidad - p.cantidad_despachada);
    });
    const guia = {
      numero_guia: `${op.numero}-${op.guias.length + 1}`,
      fecha: new Date().toLocaleDateString("es-CL").replace(/\//g, "-"),
      observaciones,
      items: items.map(({ indice_producto, cantidad }) => ({ producto: op.productos[indice_producto].nombre, cantidad })),
    };
    op.guias.push(guia);
    op.estado_despacho = op.productos.every((p) => p.pendiente === 0) ? "despachado" : "parcial";
    return guia;
  },
  reimprimir_guia: (numero_guia) => {
    console.info("[mock] reimprimir_guia", numero_guia);
    return true;
  },

  // ── Módulo ──
  marcar_despacho_entregado(numero) {
    if (!ops[numero]) return false;
    delete ops[numero];
    return true;
  },
  eliminar_despachos: (numeros) => numeros.filter((n) => ops[n] && delete ops[n]).length,

  // ── Asignar despacho ──
  obtener_asignacion_despacho(numero) {
    const o = ops[numero];
    return o ? structuredClone({ numero: o.numero, nombre: o.nombre, empresa: o.empresa, rut: o.rut, contacto: o.contacto,
                                 instalacion: o.instalacion, productos: o.productos.map(({ nombre, tema, cantidad, direccion }) => ({ nombre, tema, cantidad, direccion })) })
             : null;
  },
  cargar_todas_direcciones: () => structuredClone(direcciones),
  cargar_clientes_direccion: () => structuredClone(clientes),
  cargar_regiones: () => [...REGIONES],
  guardar_direccion_nueva(direccion) {
    const d = { id: `d${siguienteDireccion++}`, alias: "", ...direccion };
    direcciones.push(d);
    return structuredClone(d);
  },
  asignar_direccion_productos(numero, indices, direccion) {
    indices.forEach((i) => { ops[numero].productos[i].direccion = structuredClone(direccion); });
  },
  quitar_direccion_productos(numero, indices) {
    indices.forEach((i) => { ops[numero].productos[i].direccion = null; });
  },

  // ── Gestionar direcciones ──
  listar_direcciones_gestion: () => structuredClone(direcciones),
  cargar_clientes_gestion: () => structuredClone(clientes),
  guardar_direccion_gestion(direccion) {
    if (direccion.id) {
      direcciones = direcciones.map((d) => (d.id === direccion.id ? { ...d, ...direccion } : d));
      return structuredClone(direcciones.find((d) => d.id === direccion.id));
    }
    const d = { ...direccion, id: `d${siguienteDireccion++}` };
    direcciones.push(d);
    return structuredClone(d);
  },
  eliminar_direccion_gestion(id) {
    const antes = direcciones.length;
    direcciones = direcciones.filter((d) => d.id !== id);
    return direcciones.length < antes;
  },
};
