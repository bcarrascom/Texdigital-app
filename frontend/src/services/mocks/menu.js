/* Mocks del menú principal (ui/api_menu.py::ApiMenu.obtener_resumen). */

const hoyMas = (dias) => {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  return d.toLocaleDateString("es-CL", { day: "2-digit", month: "2-digit", year: "numeric" }).replace(/-/g, "/");
};

const ops = [
  { numero: 9012, empresa: "Tiendas Ejemplo SpA", fecha_entrega: hoyMas(5) },
  { numero: 9011, empresa: "Café del Puerto", fecha_entrega: hoyMas(-2) },
  { numero: 9008, empresa: "Clínica Norte", fecha_entrega: hoyMas(-6) },
];

export default {
  obtener_resumen: () => ({
    pendientes: [
      { id: "p-1", nombre_trabajo: "Vitrinas navidad", completos: 2, total: 5 },
    ],
    cotizaciones: [
      { numero: 9015, empresa: "Tiendas Ejemplo SpA", fecha: "18/10/2026" },
      { numero: 9014, empresa: "Café del Puerto", fecha: "17/10/2026" },
      { numero: 9013, empresa: "Gimnasio Activo", fecha: "15/10/2026" },
    ],
    ops,
    despachos: [
      { numero: 42, nombre: "Campaña verano", asignados: 1, total: 3 },
    ],
    despachos_asignados: [],
    rollos: [
      { id: "R-031", nombre_textil: "Tela backlit", metros_restantes: 12.5, metros_iniciales: 50 },
      { id: "R-030", nombre_textil: "Lona mate", metros_restantes: 40, metros_iniciales: 50 },
      { id: "R-028", nombre_textil: "Poliéster satinado", metros_restantes: 3, metros_iniciales: 100 },
    ],
    avisos_inventario: [
      { textil: "Poliéster satinado", severidad: "roja", metros: 3 },
      { textil: "Tela backlit", severidad: "roja", metros: 12.5 },
      { textil: "Lona mate", severidad: "amarilla", metros: 40 },
    ],
    avisos_produccion: ops.slice(1),
  }),
  buscar_actualizacion: () => window.TD?.aviso?.("Todavía no está conectado el buscador de actualizaciones.", "info"),
};
