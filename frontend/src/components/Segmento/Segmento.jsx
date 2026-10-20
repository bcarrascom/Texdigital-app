import { useId } from "react";

/* Switch segmentado de DOS opciones (.segmento en base.css): una pastilla que
   se desliza de una a la otra. Son <input type=radio> de verdad, así que se
   maneja con las flechas del teclado y es accesible.

       <Segmento valor={p.impresion} onCambiar={(v) => ...} etiqueta="Impresión"
                 opciones={[{ valor: "Cara única" }, { valor: "Tiro y retiro" }]} />

   Es un switch, no un grupo de radios cualquiera: un click en CUALQUIER punto
   —incluida la opción ya elegida— pasa a la otra. El click nativo del label
   marcaría la que se tocó y, junto con este toggle, terminaría alternando
   dos veces; por eso se apaga y el cambio lo maneja solo el click del grupo. */
export default function Segmento({ opciones, valor, onCambiar, etiqueta, vertical = false, bloque = false }) {
  const nombre = useId();
  const otra = () => opciones.find((o) => o.valor !== valor)?.valor ?? opciones[0].valor;

  return (
    <div className={`segmento${vertical ? " segmento--vertical" : ""}${bloque ? " segmento--bloque" : ""}`}
         role="group" aria-label={etiqueta} onClick={() => onCambiar(otra())}>
      {opciones.map((o, k) => (
        <SegmentoOpcion key={o.valor} id={`${nombre}-${k}`} nombre={nombre} opcion={o}
                        marcada={o.valor === valor} onElegir={() => onCambiar(o.valor)} />
      ))}
    </div>
  );
}

function SegmentoOpcion({ id, nombre, opcion, marcada, onElegir }) {
  return (
    <>
      <input type="radio" id={id} name={nombre} checked={marcada} onChange={onElegir}
             // El click lo resuelve el grupo (ver arriba): que no suba dos veces.
             onClick={(e) => e.stopPropagation()} />
      <label htmlFor={id} onClick={(e) => e.preventDefault()}>{opcion.etiqueta ?? opcion.valor}</label>
    </>
  );
}
