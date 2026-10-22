/* Mocks de ver-OP e historial (ui/api_ver_op.py, ui/api_historial_ops.py).
   Datos inventados, guardados en memoria. Las activas son las mismas que
   lista el mock del menú (9012, 9011, 9008). Fechas en dd/mm/aaaa, como las
   manda Python. */

const dma = (dias) => {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  return [d.getDate(), d.getMonth() + 1, d.getFullYear()].map((x, i) => String(x).padStart(i < 2 ? 2 : 4, "0")).join("/");
};

const estandar = (producto, textil, extra) => ({
  tipo: "estandar", producto, textil, impresion: "Cara única", estructuras: [], terminaciones: [],
  tela: "", caja: "", tema: "", obs: "", ancho: 0.85, alto: 2, cantidad: 4, ml: 8, m2: null, ...extra,
});
const backlight = (tela, caja, extra) => ({
  tipo: "backlight", producto: "", textil: "", impresion: "", estructuras: [], terminaciones: [],
  tela, caja, tema: "", obs: "", ancho: 2.4, alto: 1.2, cantidad: 2, ml: null, m2: 5.76, ...extra,
});

const OPS = [
  { numero: 9012, nombre: "Campaña verano", empresa: "Tiendas Ejemplo SpA", ingreso: -3, entrega: 5, estado: "activa",
    despacho: true, instalacion: true, tiene_backlight: true,
    productos: [estandar("Pendón roller", "Poliéster satinado", { estructuras: ["Roller 85"], tema: "Verano 2027" }),
                backlight("Tela backlit", "PERFIL 100 MM SIMPLE", { tema: "Vitrina", obs: "Entregar armada" }),
                estandar("Lienzo", "Lona mate", { ancho: 6, alto: 3, cantidad: 1, ml: 18, terminaciones: ["Ojetillos"], tema: "Fachada" })] },
  { numero: 9011, nombre: "Menú de pared", empresa: "Café del Puerto", ingreso: -8, entrega: -2, estado: "activa",
    despacho: false, instalacion: false, tiene_backlight: false,
    productos: [estandar("Lienzo", "Lona mate", { ancho: 1.2, alto: 0.8, cantidad: 2, ml: 2.4 })] },
  { numero: 9008, nombre: "Señalética interior", empresa: "Clínica Norte", ingreso: -12, entrega: 1, estado: "activa",
    despacho: true, instalacion: false, tiene_backlight: true,
    productos: [backlight("Tela backlit", "Sin caja", { cantidad: 6, m2: 17.28 }), backlight("Tela backlit premium", "PERFIL 60 MM", { ancho: 1, alto: 1, m2: 2 })] },
  { numero: 9005, nombre: "Vitrinas otoño", empresa: "Tiendas Ejemplo SpA", ingreso: -20, entrega: -9, estado: "entregada",
    despacho: true, instalacion: false, tiene_backlight: false,
    productos: [estandar("Bandera", "Poliéster satinado", { cantidad: 10, ml: 20 })] },
  { numero: 9003, nombre: "Feria del libro", empresa: "Librería Central", ingreso: -25, entrega: -15, estado: "entregada_atrasada",
    despacho: false, instalacion: true, tiene_backlight: false,
    productos: [estandar("Telón", "Felpa gruesa", { ancho: 3, alto: 2.5, cantidad: 1, ml: 3 }),
                estandar("Pendón roller", "Poliéster satinado"), estandar("Cojín", "Felpa gruesa"), estandar("Bandera", "Poliéster satinado")] },
  { numero: 8990, nombre: "Inauguración", empresa: "Hotel Mirador", ingreso: -45, entrega: -38, estado: "cancelada",
    despacho: false, instalacion: false, tiene_backlight: false, productos: [estandar("Lienzo", "Lona mate")] },
].map(({ ingreso, entrega, ...o }) => ({
  contacto: "María Pérez", email: "maria@ejemplo.cl", descripcion: "Trabajo de prueba para mirar el diseño.",
  fecha_ingreso: dma(ingreso), fecha_entrega: dma(entrega), direccion: null, op_inser: false, ...o,
}));

const buscar = (numero) => OPS.find((o) => o.numero === Number(numero));
const NUMEROS = OPS.map((o) => o.numero).sort((a, b) => b - a);
const mesDe = (fechaDMA) => fechaDMA.split("/").slice(1).map(Number);   // [mes, año]

export default {
  obtener_op: (numero) => structuredClone(buscar(numero) ?? null),

  op_adyacente(numero, direccion) {
    const i = NUMEROS.indexOf(Number(numero));
    if (i === -1) return null;
    return NUMEROS[(i + (direccion === "siguiente" ? 1 : -1) + NUMEROS.length) % NUMEROS.length];
  },

  imprimir_op: (numero) => console.info("[mock] imprimir_op", numero),
  recotizar_op: (numero) => { console.info("[mock] recotizar_op", numero); return buscar(numero)?.estado === "activa"; },
  completar_op(numero) {
    const op = buscar(numero);
    if (op?.estado !== "activa") return false;
    op.estado = "entregada";
    return true;
  },
  guardar_op_inser(numero, marcado) {
    const op = buscar(numero);
    if (op) op.op_inser = !!marcado;
    return !!op;
  },

  // La "carpeta" de un año/mes: en Python, por mes de ingreso.
  obtener_historial: (anio, mes) => structuredClone(OPS.filter((o) => {
    const [m, a] = mesDe(o.fecha_ingreso);
    return a === Number(anio) && m === Number(mes);
  })),

  buscar_historial({ texto = "", cliente = "", material = "" } = {}) {
    const t = texto.toLowerCase(), c = cliente.toLowerCase(), mat = material.toLowerCase();
    return structuredClone(OPS.filter((o) =>
      (!t || String(o.numero).includes(t) || o.nombre.toLowerCase().includes(t))
      && (!c || o.empresa.toLowerCase().includes(c))
      && (!mat || o.productos.some((p) => [p.textil, p.tela, p.caja, ...p.estructuras].some((x) => x?.toLowerCase().includes(mat))))));
  },
};
