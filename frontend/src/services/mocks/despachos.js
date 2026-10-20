/* Mocks de Despachos (ui/api_ver_despacho.py). Datos inventados, guardados
   en memoria: se pierden al recargar. */

const direccionA = { calle: "Av. Providencia", numero: "1234", comuna: "Providencia", region: "Metropolitana" };
const direccionB = { calle: "Los Carrera", numero: "560", comuna: "Concepción", region: "Biobío" };

const despachos = {
  42: {
    numero: 42,
    nombre: "Campaña verano",
    empresa: "Tiendas Ejemplo SpA",
    rut: "76.123.456-7",
    contacto: "María Pérez",
    email: "maria@ejemplo.cl",
    fecha_completada: "15-10-2026",
    estado_despacho: "parcial",
    estado_asignacion: "asignada",
    instalacion: true,
    productos: [
      { nombre: "Pendón roller", tema: "Verano 2027", cantidad: 10, cantidad_despachada: 4, pendiente: 6, direccion: direccionA },
      { nombre: "Backlight · Tela backlit", tema: "Vitrina", cantidad: 2, cantidad_despachada: 0, pendiente: 2, direccion: direccionA },
      { nombre: "Lienzo", tema: "Fachada", cantidad: 1, cantidad_despachada: 0, pendiente: 1, direccion: direccionB },
    ],
    productos_sin_direccion: 0,
    guias: [
      { numero_guia: "42-1", fecha: "16-10-2026", items: [{ producto: "Pendón roller", cantidad: 4 }] },
    ],
  },
};

export default {
  obtener_despacho: (numero) => structuredClone(despachos[numero] ?? despachos[42]),

  generar_guia_despacho(numero, items, observaciones) {
    const op = despachos[numero] ?? despachos[42];
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
};
