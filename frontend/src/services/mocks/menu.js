/* Mocks del menú principal (ui/api_menu.py::ApiMenu.obtener_resumen). Las
   listas de Despachos salen del estado de mocks/despachos.js. */

import { resumenDespachos } from "./despachos";

const hoyMas = (dias) => {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  return d.toLocaleDateString("es-CL", { day: "2-digit", month: "2-digit", year: "numeric" }).replace(/-/g, "/");
};

const ops = [
  { numero: 9012, empresa: "Tiendas Ejemplo SpA", nombre: "Pendones liquidación", fecha_entrega: hoyMas(5) },
  { numero: 9011, empresa: "Café del Puerto", nombre: "Toldo terraza", fecha_entrega: hoyMas(-2) },
  { numero: 9008, empresa: "Clínica Norte", nombre: "Backlight recepción", fecha_entrega: hoyMas(-6) },
];

export default {
  obtener_resumen: () => ({
    pendientes: [
      { id: "p-1", nombre_trabajo: "Vitrinas navidad", completos: 2, total: 5 },
    ],
    cotizaciones: [["Tiendas Ejemplo SpA", "Vitrinas verano"], ["Café del Puerto", "Menú mural"],
      ["Gimnasio Activo", "Lienzos sala"], ["Clínica Norte", "Señalética pasillos"],
      ["Librería Central", "Backlight entrada"], ["Hotel Mirador", "Pendones lobby"],
      ["Constructora Andes", "Malla fachada"], ["Pastelería Dulce", "Toldo vitrina"],
      ["Óptica Visión", "Vinilo vidrios"], ["Colegio San Marcos", "Telón acto"]]
      .map(([empresa, nombre], i) => ({ numero: 9015 - i, empresa, nombre, fecha: `${18 - i}/10/2026` })),
    ops,
    ...resumenDespachos(),
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
  // Actualizaciones (ui/api_actualizacion.py): hay una nueva, y "instalar"
  // simula la descarga. Con ?actualizacion=al_dia|error|recien en la URL,
  // arranca en ese estado.
  estado_actualizacion: () => {
    const e = { ...actualizacion, recien_actualizado: recienActualizado };
    recienActualizado = false;
    return e;
  },
  buscar_actualizacion: () => {
    actualizacion = { fase: "buscando", version: "2.1.0" };
    setTimeout(() => { actualizacion = { fase: "disponible", version: "2.1.0", nueva: "v2.1.1" }; }, 1500);
    return actualizacion;
  },
  instalar_actualizacion: () => {
    actualizacion = { fase: "descargando", version: "2.1.0", nueva: "v2.1.1", progreso: 0 };
    const id = setInterval(() => {
      const progreso = actualizacion.progreso + 9;
      actualizacion = progreso >= 100
        ? { fase: "listo", version: "2.1.0", nueva: "v2.1.1" }
        : { ...actualizacion, progreso };
      if (progreso >= 100) clearInterval(id);
    }, 300);
    return actualizacion;
  },
};

const inicio = new URLSearchParams(location.search).get("actualizacion");
let recienActualizado = inicio === "recien";
let actualizacion = {
  al_dia: { fase: "al_dia", version: "2.1.0" },
  error: { fase: "error", version: "2.1.0", error: "No se pudo conectar con el servidor de actualizaciones. Revisa la conexión a internet." },
}[inicio] || { fase: "disponible", version: "2.1.0", nueva: "v2.1.1" };
