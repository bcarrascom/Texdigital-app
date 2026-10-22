import { useLayoutEffect, useState } from "react";
import { useAnimate } from "motion/react";
import "./Pista.css";

/* Slide entre dos "fichas" como si estuvieran físicamente una al lado de la
   otra (entre cotizaciones con ←/→, entre módulos, ...). Cuando cambia el
   `elemento` (según su `clave`), la pista pone el viejo y el nuevo lado a
   lado y se desliza ENTERA — no cada uno por su lado: así viajan pegados,
   sin que uno arranque un cuadro antes que el otro. Al terminar queda solo
   el nuevo.

       <Pista elemento={cot} clave={(c) => c.numero} direccion={1}
              onTerminar={() => setDeslizando(false)}
              render={(c, saliendo) => <VistaCotizacion cot={c} />} />

     direccion   1: el nuevo entra por la derecha · -1: por la izquierda
     render      (elemento, saliendo) → contenido de una ficha; `saliendo`
                 es true para la que se va (p. ej. para apagarle algo)

   El contenido de cada ficha conserva su estado al quedar sola en la pista
   (va con key por clave). Si llega el mismo elemento con datos nuevos (misma
   clave), se actualiza en el lugar, sin slide. */

const SLIDE = { duration: 0.35, ease: [0.65, 0, 0.35, 1] };   // simétrica: arranca y frena suave

export default function Pista({ elemento, clave, direccion = 1, render, onTerminar, transicion = SLIDE, className = "" }) {
  const [mostrado, setMostrado] = useState(elemento);
  const [anterior, setAnterior] = useState(null);
  const [pista, animar] = useAnimate();

  // Cambió el elemento: el que se estaba mostrando pasa a ser "el que sale".
  // (Ajuste de estado durante el render a partir de una prop, el patrón que
  // recomienda React para esto — no hace falta un efecto.)
  if (elemento !== mostrado) {
    if (clave(elemento) !== clave(mostrado)) setAnterior(mostrado);
    setMostrado(elemento);
  }

  const enPar = !!anterior && clave(anterior) !== clave(mostrado);

  useLayoutEffect(() => {
    if (!enPar) return;
    const ida = direccion > 0;
    const reducido = matchMedia("(prefers-reduced-motion: reduce)").matches;
    // La posición de partida se fija a mano ANTES del primer cuadro: si no,
    // yendo hacia la izquierda se vería un instante la pista sin correr.
    pista.current.style.transform = `translateX(${ida ? 0 : -100}%)`;
    const animacion = animar(pista.current, { x: ida ? ["0%", "-100%"] : ["-100%", "0%"] },
                             reducido ? { duration: 0 } : transicion);
    animacion.then(() => {
      setAnterior(null);
      onTerminar?.();
    });
    return () => animacion.stop();
  }, [enPar]);  // solo al empezar un paso, no en cada render del mismo

  // Ya sin el viejo, la pista vuelve a su lugar en el mismo cuadro en que se
  // lo saca (useLayoutEffect: antes de pintar). Las dos cosas hacen falta:
  // motion recuerda el último `x` que animó y lo volvería a escribir encima
  // si solo se toca el estilo, pero su reset recién llega al cuadro
  // siguiente — y ese único cuadro mostraba la ficha fuera de lugar.
  useLayoutEffect(() => {
    if (anterior || !pista.current) return;
    animar(pista.current, { x: "0%" }, { duration: 0 });
    pista.current.style.transform = "none";
  }, [anterior, pista, animar]);

  const fichas = enPar ? (direccion > 0 ? [anterior, mostrado] : [mostrado, anterior]) : [mostrado];

  return (
    <div className={`pista-ventana ${className}`}>
      <div ref={pista} className="pista">
        {fichas.map((f) => {
          const saliendo = enPar && f === anterior;
          return (
            <div key={clave(f)} className="pista__ficha" aria-hidden={saliendo || undefined}>
              {render(f, saliendo)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
