import IconoGeneral from "@/assets/svg/cog.svg?react";
import IconoProveedores from "@/assets/svg/truck.svg?react";
import IconoTextiles from "@/assets/svg/spiral.svg?react";
import IconoEstructuras from "@/assets/svg/wrench.svg?react";
import IconoTerminaciones from "@/assets/svg/scissors.svg?react";
import IconoCajas from "@/assets/svg/box.svg?react";
import IconoReglas from "@/assets/svg/percent.svg?react";
import IconoClientes from "@/assets/svg/users.svg?react";
import IconoProductos from "@/assets/svg/package.svg?react";
import General from "./General";
import Proveedores from "./Proveedores";
import Textiles from "./Textiles";
import Cajas from "./Cajas";
import Reglas from "./Reglas";
import ClientesContactos from "./ClientesContactos";
import Productos from "./Productos";
import { Estructuras, Terminaciones } from "./ListaPrecios";

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
    clave: "textiles", titulo: "Textiles", Icono: IconoTextiles, color: "#AF52DE", Contenido: Textiles,
    desc: "Cuánto se cobra por metro de cada textil: un valor fijo o el valor de venta del rollo. Vale para todos los que cotizan.",
    palabras: "precio precios valor metro cobro cobrar telas rollos cotizar",
  },
  {
    clave: "productos", titulo: "Productos", Icono: IconoProductos, color: "#FF9F0A", Contenido: Productos,
    desc: "Los productos que se eligen en el cotizador: agregar, renombrar o quitar.",
    palabras: "producto productos bandera pendon lienzo vela catalogo cotizar",
  },
  {
    clave: "estructuras", titulo: "Estructuras", Icono: IconoEstructuras, color: "#3478F6", Contenido: Estructuras,
    desc: "Cuánto se cobra por cada estructura. Vale para todos los que cotizan.",
    palabras: "precio precios valor cobro asta base estaca panel araña cotizar",
  },
  {
    clave: "terminaciones", titulo: "Terminaciones", Icono: IconoTerminaciones, color: "#E8772E", Contenido: Terminaciones,
    desc: "Cuánto se cobra por cada terminación. Vale para todos los que cotizan.",
    palabras: "precio precios valor cobro basta bolsillos ojetillos fundas cotizar",
  },
  {
    clave: "cajas", titulo: "Backlight", Icono: IconoCajas, color: "#C9A227", Contenido: Cajas,
    desc: "Los márgenes del corte de la tela y lo que vale cada pieza de una caja: luces, fuentes, perfiles, traseras, armado y pintura.",
    palabras: "precio precios valor backlight caja cajas luces fuente poder perfil trasera armado pintura corte margen costura area visual caja terminada",
  },
  {
    clave: "reglas", titulo: "Reglas de cobro", Icono: IconoReglas, color: "#E5484D", Contenido: Reglas,
    desc: "El IVA, el mínimo que se cobra por textil y el descuento por volumen. Cada cotización guarda las suyas.",
    palabras: "iva impuesto minimo mínimo descuento volumen tramos porcentaje reglas",
  },
  {
    clave: "clientes", titulo: "Clientes y contactos", Icono: IconoClientes, color: "#30B0C7", Contenido: ClientesContactos,
    desc: "Los clientes y contactos que sugiere el cotizador: agregar, corregir sus datos o eliminarlos.",
    palabras: "cliente clientes empresa rut razon social contacto contactos correo email descuento condicion pago",
  },
  {
    clave: "proveedores", titulo: "Proveedores", Icono: IconoProveedores, color: "#2E9D5B", Contenido: Proveedores,
    desc: "Los proveedores que se sugieren al cargar rollos de tela y materiales.",
    palabras: "proveedor compras rollos materiales inventario",
  },
];
