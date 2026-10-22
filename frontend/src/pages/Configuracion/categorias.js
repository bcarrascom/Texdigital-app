import IconoGeneral from "@/assets/svg/cog.svg?react";
import IconoProveedores from "@/assets/svg/truck.svg?react";
import General from "./General";
import Proveedores from "./Proveedores";

/* Las categorías de Configuración, en el orden de la barra lateral. Sumar
   una es agregar una entrada acá (y su componente):

     clave      la de la URL: /configuracion/<clave>
     titulo     en la barra lateral y en el encabezado
     desc       debajo del título, en el encabezado
     palabras   lo que además encuentra el buscador de la barra lateral
     Icono      dibujo de Lucide (assets/svg), en blanco sobre `color`
     Contenido  lo que va debajo del encabezado */
export const CATEGORIAS = [
  {
    clave: "general", titulo: "General", Icono: IconoGeneral, color: "#8E8E93", Contenido: General,
    desc: "La versión de la app, las actualizaciones, el tamaño del texto y el manual de uso.",
    palabras: "versión actualizar actualizaciones texto tamaño letra escala zoom manual ayuda",
  },
  {
    clave: "proveedores", titulo: "Proveedores", Icono: IconoProveedores, color: "#2E9D5B", Contenido: Proveedores,
    desc: "Los proveedores que se sugieren al cargar rollos de tela y materiales.",
    palabras: "proveedor compras rollos materiales inventario",
  },
];
