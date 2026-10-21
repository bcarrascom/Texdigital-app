import { useState } from "react";
import IconoOrden from "@/assets/svg/arrow-down.svg?react";
import IconoDeshacer from "@/assets/svg/trash-2.svg?react";
import "./Ficha.css";

/* El historial de un rollo o un material como timeline: la vida de esa ficha
   en el tiempo, más reciente primero (se puede invertir con el botón de
   arriba). La tarjeta del movimiento más reciente trae el botón para
   deshacerlo — solo esa: deshacer una del medio dejaría el historial
   inconsistente.

       <Historial entradas={rollo.usos} vacio="Todavía no hay..."
                  vista={(u) => ({ chip: "Ajuste", cambio: "40 → 38 m", ... })}
                  onDeshacer={(u) => ...} />

   `vista(entrada)` dice cómo se ve cada una:
     chip         texto del chip (Ajuste, Consumo, ...)
     variante     color del chip y del punto (consumo, restock, precio, activo,
                  inactivo) — sin variante, el color del tema
     neto         "+25 un." (opcional, pegado al chip)
     cambio       "104 → 129 un."
     descripcion  texto libre (opcional)
     datos        [[etiqueta, valor]] debajo (opcional; valor puede ser un nodo)

   El orden de las entradas que llega es el de Python: la última es la más
   nueva (siempre se agrega al final). */
export default function Historial({ entradas = [], vista, onDeshacer, vacio }) {
  const [reciente, setReciente] = useState(true);
  const idMasReciente = entradas.length ? entradas[entradas.length - 1].id : null;
  const lista = reciente ? entradas.slice().reverse() : entradas;
  const texto = reciente ? "Más reciente primero" : "Más antiguo primero";

  return (
    <section>
      <div className="seccion-cab">
        <h2 className="seccion-titulo">Historial</h2>
        <button className="btn-orden-timeline" type="button" aria-pressed={!reciente} title={texto} aria-label={texto}
                onClick={() => setReciente((r) => !r)}>
          <IconoOrden aria-hidden="true" />
        </button>
      </div>
      {lista.length ? (
        <div className="timeline">
          {lista.map((e) => (
            <Tarjeta key={e.id} {...vista(e)} onDeshacer={e.id === idMasReciente && onDeshacer ? () => onDeshacer(e) : null} />
          ))}
        </div>
      ) : <p className="estado-vacio">{vacio}</p>}
    </section>
  );
}

function Tarjeta({ chip, variante, neto, cambio, fecha, descripcion, datos = [], onDeshacer }) {
  const conDatos = datos.filter(([, v]) => v);
  return (
    <div className="timeline__item">
      <div className={`timeline__punto${variante ? ` timeline__punto--${variante}` : ""}`} />
      <div className="timeline__card">
        <div className="timeline__cab">
          <span className={`chip-tipo${variante ? ` chip-tipo--${variante}` : ""}`}>{chip}</span>
          {neto && <span className="timeline__neto">{neto}</span>}
          <span className="timeline__cambio">{cambio}</span>
          <span className="timeline__fecha">{fecha}</span>
          {onDeshacer && (
            <button className="timeline__deshacer" type="button" title="Deshacer este movimiento" onClick={onDeshacer}>
              <IconoDeshacer aria-hidden="true" />
            </button>
          )}
        </div>
        {/* Sin descripción no hay párrafo: una línea sola se ve más compacta que un "—" colgando. */}
        {descripcion && <p className="timeline__descripcion">{descripcion}</p>}
        {conDatos.length > 0 && (
          <div className="timeline__datos">
            {conDatos.map(([et, v]) => (
              <div key={et} className="dato"><span className="dato__et">{et}</span><span className="dato__val">{v}</span></div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* El número de OP de un consumo: lleva a esa OP. */
export function EnlaceOp({ numero, onAbrir }) {
  return <button type="button" className="timeline__op" title="Abrir esta OP" onClick={onAbrir}>#{numero}</button>;
}
