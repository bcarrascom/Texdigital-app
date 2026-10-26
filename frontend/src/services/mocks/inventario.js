/* Mocks de Inventario (ui/api_inventario.py). Datos inventados, guardados en
   memoria. Las 9 cifras de plata (metricas_rollo / metricas_material en
   Python) salen acá de una cuenta simplificada: sirven para mirar las
   pantallas, no para llevar la contabilidad. Cada entrada de historial tiene
   la forma de la real (_agregar_registro / _agregar_historial). */

import reportesCerrados from "./reportesInventario.json";

const hoy = () => new Date().toLocaleDateString("es-CL", { day: "2-digit", month: "2-digit", year: "numeric" }).replace(/-/g, "/");
const isoADma = (iso) => iso.split("-").reverse().join("/");
let siguienteEntrada = 1;
const idEntrada = () => `e${siguienteEntrada++}`;

/* Las 9 claves que mandan las dos tablas: unitarias + derivados. */
function metricas({ costo, valor, inicial, restante }) {
  const vendido = inicial - restante;
  return {
    gasto_unitario: costo, gasto_mes: costo != null ? Math.round(costo * vendido * 0.4) : null, gasto_total: costo != null ? Math.round(costo * inicial) : null,
    valor_unitario: valor, valor_restante: valor != null ? Math.round(valor * restante) : null, valor_vendido: valor != null ? Math.round(valor * vendido) : null,
    ganancia_unitaria: valor != null && costo != null ? valor - costo : null,
    ganancia_mes: valor != null && costo != null ? Math.round((valor - costo) * vendido * 0.4) : null,
    ganancia_total: valor != null && costo != null ? Math.round((valor - costo) * vendido) : null,
  };
}

/* ── Rollos ─────────────────────────────────────────────────────────────── */

const uso = (tipo, fecha, anterior, nuevo, extra = {}) =>
  ({ id: idEntrada(), tipo, fecha, metros_restantes_anterior: anterior, metros_restantes_nuevo: nuevo, descripcion: "", ...extra });

let siguienteRollo = 32;
export const rollos = [
  { id: "R-031", nombre_textil: "Tela backlit", ancho: 3, metros_iniciales: 50, metros_restantes: 12.5, estado: "activo", proveedor: "Textiles del Sur", fecha: "02/10/2026", precio_compra: 380000, valor: 14000,
    usos: [
      uso("consumo", "05/10/2026", 50, 41.2, { numero_op: 9008, cliente: "Clínica Norte", tema: "Señalética interior", obs: "" }),
      uso("ajuste", "09/10/2026", 41.2, 39.7, { descripcion: "Recorte con error de medida." }),
      uso("consumo", "14/10/2026", 39.7, 24.5, { numero_op: 9011, cliente: "Café del Puerto", tema: "Menú de pared", obs: "Urgente" }),
      uso("consumo", "18/10/2026", 24.5, 12.5, { numero_op: 9012, cliente: "Tiendas Ejemplo SpA", tema: "Campaña verano", obs: "" }),
    ] },
  { id: "R-030", nombre_textil: "Lona mate", ancho: 3.2, metros_iniciales: 50, metros_restantes: 40, estado: "activo", proveedor: "Lonas Chile", fecha: "28/09/2026", precio_compra: 250000, valor: 9000,
    usos: [uso("consumo", "01/10/2026", 50, 40, { numero_op: 9005, cliente: "Tiendas Ejemplo SpA", tema: "Vitrinas otoño" })] },
  { id: "R-029", nombre_textil: "Poliéster satinado", ancho: 1.5, metros_iniciales: 100, metros_restantes: 3, estado: "activo", proveedor: "Textiles del Sur", fecha: "15/09/2026", precio_compra: 0, valor: 7500, usos: [] },
  { id: "R-027", nombre_textil: "Felpa gruesa", ancho: 1.4, metros_iniciales: 60, metros_restantes: 22, estado: "inactivo", proveedor: "", fecha: "01/08/2026", precio_compra: 0, valor: 11000,
    usos: [uso("activacion", "20/09/2026", 22, 22, { estado_nuevo: "inactivo", descripcion: "Tela con manchas de humedad, revisar con el proveedor." })] },
  { id: "R-025", nombre_textil: "Poliéster satinado", ancho: 1.5, metros_iniciales: 100, metros_restantes: 64, estado: "inactivo", proveedor: "Importadora Andes", fecha: "20/07/2026", precio_compra: 420000, valor: 7500, usos: [] },
];

const conMetricasRollo = (r) => ({ ...r, ...metricas({ costo: r.precio_compra ? Math.round(r.precio_compra / r.metros_iniciales) : null,
  valor: r.valor, inicial: r.metros_iniciales, restante: r.metros_restantes }) });
const rolloPorId = (id) => rollos.find((x) => x.id === id);
const devolverRollo = (r) => (r ? structuredClone(conMetricasRollo(r)) : null);

/* ── Materiales ─────────────────────────────────────────────────────────── */

const entrada = (tipo, fecha, anterior, nuevo, extra = {}) =>
  ({ id: idEntrada(), tipo, fecha, cantidad_anterior: anterior, cantidad_nueva: nuevo, descripcion: "", ...extra });

let siguienteMaterial = 5;
const materiales = [
  { id: "M-01", nombre: "Silicona", tipo: "metro", cantidad: 180, valor: 1200, proveedor: "Ferretería Central",
    tipo_consumo: "perimetro", consumo_parametros: { n: 1 }, productos_asociados: ["Backlight"], estructuras_asociadas: [],
    historial: [
      entrada("restock", "10/09/2026", 0, 200, { proveedor: "Ferretería Central", costo_total: 90000, costo_unitario: 450 }),
      entrada("precio", "12/09/2026", 200, 200, { valor_anterior: 1000, valor_nuevo: 1200, descripcion: "Subió el costo del proveedor." }),
      entrada("consumo", "05/10/2026", 200, 186.4, { numero_op: 9008, cliente: "Clínica Norte" }),
      entrada("ajuste", "15/10/2026", 186.4, 180, { descripcion: "Cartucho vencido." }),
    ] },
  { id: "M-02", nombre: "Perfil 10 cm", tipo: "metro", cantidad: 36, valor: 8500, proveedor: "Aluminios Ltda.",
    tipo_consumo: "metro_lineal_salto", consumo_parametros: { paso: 3, n: 1 }, productos_asociados: [], estructuras_asociadas: ["Bastidor 10 cm"],
    historial: [entrada("restock", "01/10/2026", 0, 40, { proveedor: "Aluminios Ltda.", costo_total: 368000, costo_unitario: 9200 }),
                entrada("consumo", "14/10/2026", 40, 36, { numero_op: 9011, cliente: "Café del Puerto" })] },
  { id: "M-03", nombre: "Ojetillos", tipo: "unidad", cantidad: 1200, valor: null, proveedor: "",
    historial: [entrada("restock", "22/08/2026", 0, 1500, { proveedor: "Ferretería Central", costo_total: 52500, costo_unitario: 35 }),
                entrada("ajuste", "30/08/2026", 1500, 1200, { descripcion: "Recuento físico." })] },
  { id: "M-04", nombre: "Cinta doble faz", tipo: "unidad", cantidad: 14, valor: 3500, proveedor: "Librería Central", historial: [] },
];

let proveedores = ["Aluminios Ltda.", "Ferretería Central", "Importadora Andes", "Lonas Chile", "Librería Central", "Textiles del Sur"];

const conMetricasMaterial = (m) => {
  const restocks = m.historial.filter((h) => h.tipo === "restock");
  const inicial = restocks.reduce((s, h) => s + (h.cantidad_nueva - h.cantidad_anterior), 0) || m.cantidad;
  return { ...m, ...metricas({ costo: restocks.at(-1)?.costo_unitario ?? null, valor: m.valor, inicial, restante: m.cantidad }) };
};
const materialPorId = (id) => materiales.find((x) => x.id === id);
const devolverMaterial = (m) => (m ? structuredClone(conMetricasMaterial(m)) : null);

/* ── Reportes mensuales ────────────────────────────────────────────────────
   Los tres cerrados son los mismos que se escriben en la Dropbox de
   desarrollo; el del mes en curso es una copia del último, a medio mes. */

function reporteEnCurso() {
  const ahora = new Date();
  const base = structuredClone(reportesCerrados[reportesCerrados.length - 1]);
  return { ...base, anio: ahora.getFullYear(), mes: ahora.getMonth() + 1, cerrado: false,
           generado: `${hoy()} ${ahora.toTimeString().slice(0, 5)}` };
}
/* Las cuatro formas del valor vendido (ver core/reportes_inventario.py): acá,
   inventadas a partir del valor_vendido, con un 5 % de descuento y 19 % de IVA. */
function conFormas(x) {
  if (!x || typeof x !== "object") return x;
  if (Array.isArray(x)) return x.map(conFormas);
  const y = Object.fromEntries(Object.entries(x).map(([k, v]) => [k, conFormas(v)]));
  if (typeof x.valor_vendido === "number") {
    const v = x.valor_vendido / 0.95;
    y.valores_vendidos = { sin_iva: Math.round(v), sin_iva_con_descuento: x.valor_vendido,
                           con_iva: Math.round(v * 1.19), con_iva_con_descuento: Math.round(x.valor_vendido * 1.19) };
  }
  return y;
}
const todosLosReportes = () => [conFormas(reporteEnCurso()), ...reportesCerrados.slice().reverse()];

export default {
  abrir_reportes_inventario: () => todosLosReportes().map(({ anio, mes, cerrado }) => ({ anio, mes, cerrado })),
  obtener_reporte_inventario: (anio, mes) =>
    structuredClone(todosLosReportes().find((r) => r.anio === Number(anio) && r.mes === Number(mes)) || null),

  listar_rollos: () => structuredClone(rollos.map(conMetricasRollo)),
  obtener_rollo: (id) => devolverRollo(rolloPorId(id)),
  listar_materiales: () => structuredClone(materiales.map(conMetricasMaterial)),
  obtener_material: (id) => devolverMaterial(materialPorId(id)),
  cargar_textiles_inventario: () => ["Felpa gruesa", "Lona mate", "Poliéster satinado", "Tela backlit"],
  cargar_proveedores: () => [...proveedores],
  cargar_nombres_materiales: () => materiales.map((m) => m.nombre),
  cargar_productos_catalogo: () => ["Backlight", "Backlight + Caja", "Pendón", "Telón", "Bandera", "Lienzo"],
  cargar_perfiles_catalogo: () => ["PERFIL 60 MM", "PERFIL 100 MM DOBLE"],
  cargar_estructuras_catalogo: () => ["Bastidor 10 cm", "Bastidor 5 cm", "Tubo de aluminio", "Pie metálico", "PERFIL 60 MM", "PERFIL 100 MM DOBLE"],
  valor_sugerido_textil: (textil) => rollos.find((r) => r.nombre_textil === textil)?.valor ?? 8000,

  crear_rollo(nombre_textil, ancho, metros, precio_compra, valor, proveedor) {
    const r = { id: `R-0${siguienteRollo++}`, nombre_textil, ancho, metros_iniciales: metros, metros_restantes: metros,
                estado: "activo", proveedor, fecha: hoy(), precio_compra, valor, usos: [] };
    rollos.unshift(r);
    return devolverRollo(r);
  },
  editar_rollo(id, nombre_textil, ancho, precio_compra, valor, proveedor) {
    const r = rolloPorId(id);
    if (r && r.valor !== valor) {
      r.usos.push(uso("precio", hoy(), r.metros_restantes, r.metros_restantes, { valor_anterior: r.valor, valor_nuevo: valor }));
    }
    if (r) Object.assign(r, { nombre_textil, ancho, precio_compra, valor, proveedor });
    return devolverRollo(r);
  },
  cambiar_estado_rollo(id, activo) {
    const r = rolloPorId(id);
    if (r) r.estado = activo ? "activo" : "inactivo";
    return devolverRollo(r);
  },
  ajustar_restante_rollo(id, nuevo, descripcion) {
    const r = rolloPorId(id);
    if (!r) return null;
    r.usos.push(uso("ajuste", hoy(), r.metros_restantes, nuevo, { descripcion }));
    r.metros_restantes = nuevo;
    return devolverRollo(r);
  },
  ajustar_estado_rollo(id, activo, descripcion) {
    const r = rolloPorId(id);
    if (!r) return null;
    r.estado = activo ? "activo" : "inactivo";
    r.usos.push(uso("activacion", hoy(), r.metros_restantes, r.metros_restantes, { estado_nuevo: r.estado, descripcion }));
    return devolverRollo(r);
  },
  /* Deshace la entrada más reciente: vuelve los metros (o el estado) a como estaban. */
  eliminar_ajuste_rollo(id, idAjuste) {
    const r = rolloPorId(id);
    const ultima = r?.usos.at(-1);
    if (!ultima || ultima.id !== idAjuste) return null;
    r.usos.pop();
    r.metros_restantes = ultima.metros_restantes_anterior;
    if (ultima.tipo === "activacion") r.estado = ultima.estado_nuevo === "activo" ? "inactivo" : "activo";
    return devolverRollo(r);
  },
  decomisionar_rollo(id) {
    const i = rollos.findIndex((x) => x.id === id);
    if (i >= 0) rollos.splice(i, 1);
    return i >= 0;
  },

  ingresar_material(nombre, cantidad, tipo, proveedor, costo_total, costo_unitario, _tc, _cp, _pa, _ea, fecha, valor) {
    let m = materiales.find((x) => x.nombre.toLowerCase() === nombre.toLowerCase());
    if (!m) {
      m = { id: `M-0${siguienteMaterial++}`, nombre, tipo, cantidad: 0, valor, proveedor, historial: [] };
      materiales.push(m);
    }
    m.historial.push(entrada("restock", fecha ? isoADma(fecha) : hoy(), m.cantidad, m.cantidad + cantidad, {
      proveedor, costo_total: costo_total ?? (costo_unitario != null ? costo_unitario * cantidad : null),
      costo_unitario: costo_unitario ?? (costo_total != null ? Math.round(costo_total / cantidad) : null),
    }));
    m.cantidad += cantidad;
    return devolverMaterial(m);
  },
  editar_material(id, nombre, tipo, valor, proveedor, tipo_consumo, consumo_parametros, productos_asociados, estructuras_asociadas) {
    const m = materialPorId(id);
    if (!m) return null;
    if (valor !== m.valor) m.historial.push(entrada("precio", hoy(), m.cantidad, m.cantidad, { valor_anterior: m.valor, valor_nuevo: valor }));
    Object.assign(m, { nombre, tipo, valor, proveedor, tipo_consumo, consumo_parametros, productos_asociados, estructuras_asociadas });
    return devolverMaterial(m);
  },
  ajustar_cantidad_material(id, nueva, descripcion) {
    const m = materialPorId(id);
    if (!m) return null;
    m.historial.push(entrada("ajuste", hoy(), m.cantidad, nueva, { descripcion }));
    m.cantidad = nueva;
    return devolverMaterial(m);
  },
  ajustar_valor_material(id, nuevo, descripcion) {
    const m = materialPorId(id);
    if (!m) return null;
    m.historial.push(entrada("precio", hoy(), m.cantidad, m.cantidad, { valor_anterior: m.valor, valor_nuevo: nuevo, descripcion }));
    m.valor = nuevo;
    return devolverMaterial(m);
  },
  eliminar_ultimo_historial_material(id, idEntrada_) {
    const m = materialPorId(id);
    const ultima = m?.historial.at(-1);
    if (!ultima || ultima.id !== idEntrada_) return null;
    m.historial.pop();
    m.cantidad = ultima.cantidad_anterior;
    if (ultima.tipo === "precio") m.valor = ultima.valor_anterior;
    return devolverMaterial(m);
  },
  eliminar_material(id) {
    const i = materiales.findIndex((x) => x.id === id);
    if (i >= 0) materiales.splice(i, 1);
    return i >= 0;
  },

  guardar_proveedor(nombre) {
    if (nombre && !proveedores.includes(nombre)) proveedores = [...proveedores, nombre].sort((a, b) => a.localeCompare(b, "es"));
  },
  editar_proveedor(actual, nuevo) {
    if (proveedores.includes(nuevo)) return false;
    proveedores = proveedores.map((p) => (p === actual ? nuevo : p)).sort((a, b) => a.localeCompare(b, "es"));
    return true;
  },
  eliminar_proveedor(nombre) {
    proveedores = proveedores.filter((p) => p !== nombre);
    return true;
  },
};
