/* Lo que comparten las pantallas de Despachos sobre direcciones (ver
   core/repositorio.py: direcciones.json). La dirección es POR PRODUCTO, y la
   que queda puesta en una OP es una COPIA hecha al asignarla, no una
   referencia viva: editar o borrar una dirección guardada no toca las OPs. */

export const REGION_DEFECTO = "Región Metropolitana";

/* "Av. Providencia 1234, Providencia" */
export function direccionTexto(d) {
  if (!d) return "—";
  const linea1 = [d.calle, d.numero].filter(Boolean).join(" ");
  return [linea1, d.comuna].filter(Boolean).join(", ") || "—";
}

/* El texto con que se elige un cliente en el <datalist>: empresa Y RUT en una
   sola cadena, así el filtro nativo del navegador busca por cualquiera. */
export const etiquetaCliente = (c) => [c?.empresa, c?.rut].filter(Boolean).join(" — ");

/* Para comparar RUTs escritos distinto ("76.123.456-7" / "761234567"). */
export const claveRut = (s) => String(s || "").replace(/[^a-z0-9]/gi, "").toLowerCase();
