/* Mocks de Inventario (ui/api_inventario.py). Datos inventados, guardados en
   memoria. Las 9 cifras de plata (metricas_rollo / metricas_material en
   Python) salen acá de una cuenta simplificada: sirven para mirar las
   tablas, no para llevar la contabilidad. */

const hoy = () => new Date().toLocaleDateString("es-CL", { day: "2-digit", month: "2-digit", year: "numeric" }).replace(/-/g, "/");

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

let siguienteRollo = 32;
const rollos = [
  { id: "R-031", nombre_textil: "Tela backlit", ancho: 3, metros_iniciales: 50, metros_restantes: 12.5, estado: "activo", proveedor: "Textiles del Sur", fecha: "02/10/2026", precio_compra: 380000, valor: 14000 },
  { id: "R-030", nombre_textil: "Lona mate", ancho: 3.2, metros_iniciales: 50, metros_restantes: 40, estado: "activo", proveedor: "Lonas Chile", fecha: "28/09/2026", precio_compra: 250000, valor: 9000 },
  { id: "R-029", nombre_textil: "Poliéster satinado", ancho: 1.5, metros_iniciales: 100, metros_restantes: 3, estado: "activo", proveedor: "Textiles del Sur", fecha: "15/09/2026", precio_compra: 0, valor: 7500 },
  { id: "R-027", nombre_textil: "Felpa gruesa", ancho: 1.4, metros_iniciales: 60, metros_restantes: 22, estado: "inactivo", proveedor: "", fecha: "01/08/2026", precio_compra: 0, valor: 11000 },
  { id: "R-025", nombre_textil: "Poliéster satinado", ancho: 1.5, metros_iniciales: 100, metros_restantes: 64, estado: "inactivo", proveedor: "Importadora Andes", fecha: "20/07/2026", precio_compra: 420000, valor: 7500 },
];

const materiales = [
  { id: "M-01", nombre: "Silicona", tipo: "metro", cantidad: 180, valor: 1200, proveedor: "Ferretería Central",
    historial: [{ tipo: "restock", fecha: "10/09/2026", proveedor: "Ferretería Central", costo_unitario: 450, cantidad: 200 }] },
  { id: "M-02", nombre: "Perfil 10 cm", tipo: "metro", cantidad: 36, valor: 8500, proveedor: "Aluminios Ltda.",
    historial: [{ tipo: "restock", fecha: "01/10/2026", proveedor: "Aluminios Ltda.", costo_unitario: 9200, cantidad: 40 }] },
  { id: "M-03", nombre: "Ojetillos", tipo: "unidad", cantidad: 1200, valor: null, proveedor: "",
    historial: [{ tipo: "restock", fecha: "22/08/2026", proveedor: "Ferretería Central", costo_unitario: 35, cantidad: 1500 }] },
  { id: "M-04", nombre: "Cinta doble faz", tipo: "unidad", cantidad: 14, valor: 3500, proveedor: "Librería Central", historial: [] },
];

let proveedores = ["Aluminios Ltda.", "Ferretería Central", "Importadora Andes", "Lonas Chile", "Librería Central", "Textiles del Sur"];

const conMetricasRollo = (r) => ({ ...r, ...metricas({ costo: r.precio_compra ? Math.round(r.precio_compra / r.metros_iniciales) : null,
  valor: r.valor, inicial: r.metros_iniciales, restante: r.metros_restantes }) });
const conMetricasMaterial = (m) => {
  const ultimo = m.historial.filter((h) => h.tipo === "restock").at(-1);
  const inicial = m.historial.reduce((s, h) => s + (h.cantidad || 0), 0) || m.cantidad;
  return { ...m, ...metricas({ costo: ultimo?.costo_unitario ?? null, valor: m.valor, inicial, restante: m.cantidad }) };
};

export default {
  listar_rollos: () => structuredClone(rollos.map(conMetricasRollo)),
  listar_materiales: () => structuredClone(materiales.map(conMetricasMaterial)),
  cargar_textiles_inventario: () => ["Felpa gruesa", "Lona mate", "Poliéster satinado", "Tela backlit"],
  cargar_proveedores: () => [...proveedores],
  cargar_nombres_materiales: () => materiales.map((m) => m.nombre),
  valor_sugerido_textil: (textil) => rollos.find((r) => r.nombre_textil === textil)?.valor ?? 8000,

  crear_rollo(nombre_textil, ancho, metros, precio_compra, valor, proveedor) {
    const r = { id: `R-0${siguienteRollo++}`, nombre_textil, ancho, metros_iniciales: metros, metros_restantes: metros,
                estado: "activo", proveedor, fecha: hoy(), precio_compra, valor };
    rollos.unshift(r);
    return conMetricasRollo(r);
  },
  cambiar_estado_rollo(id, activo) {
    const r = rollos.find((x) => x.id === id);
    if (r) r.estado = activo ? "activo" : "inactivo";
    return r ? conMetricasRollo(r) : null;
  },
  ingresar_material(nombre, cantidad, tipo, proveedor, costo_total, costo_unitario, _tc, _cp, _pa, _ea, _f, valor) {
    let m = materiales.find((x) => x.nombre.toLowerCase() === nombre.toLowerCase());
    if (!m) {
      m = { id: `M-0${materiales.length + 1}`, nombre, tipo, cantidad: 0, valor, proveedor, historial: [] };
      materiales.push(m);
    }
    m.cantidad += cantidad;
    m.historial.push({ tipo: "restock", fecha: hoy(), proveedor, cantidad,
                       costo_unitario: costo_unitario ?? (costo_total != null ? Math.round(costo_total / cantidad) : null) });
    return conMetricasMaterial(m);
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
