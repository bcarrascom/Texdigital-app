import { useLayoutEffect, useRef } from "react";

/* Un módulo del menú: la caja (la pieza visual, clickeable) y, DETRÁS de
   ella, el mazo de tarjetas que asoma al pasar el mouse o enfocarla (todo
   por CSS, ver Menu.css: .modulo:hover / :focus-within).

   Orden de pintado (ver z-index en Menu.css):
     .modulo            posicionador, sin pintura
       .modulo__caja    relleno, borde, título              (z-index 2)
       .modulo__lista   las tarjetas, escondidas detrás     (z-index 1)

   `tarjetas`: null mientras carga, [] si no hay nada (muestra `vacio`). */

const COLUMNAS = 2;

/* --i ordena el escalonado y el z-index del mazo; --fila, la posición de
   reposo (cuánto hay que subir cada tarjeta para esconderla). */
export const varsMazo = (i) => ({ "--i": i, "--fila": Math.floor(i / COLUMNAS) });

export default function Modulo({ clave, titulo, meta, deshabilitado, indice, tarjetas, vacio, registrarCaja, onAbrir }) {
  const seccion = useRef(null);
  const caja = useRef(null);
  const rejilla = useRef(null);

  /* Cada tarjeta guarda la misma proporción alto/ancho que la caja de su
     módulo. El ancho lo decide la rejilla (2 columnas), así que lo único que
     hay que calcular es el alto. No alcanza con `aspect-ratio`: el reposo del
     mazo necesita saber el alto de cada fila para esconderlas detrás de la
     caja. Se recalcula cuando cambia la caja (ventana, escala A− / A+). */
  useLayoutEffect(() => {
    const ajustar = () => {
      const r = caja.current.getBoundingClientRect();
      if (!r.width || !r.height) return;
      const gap = parseFloat(getComputedStyle(rejilla.current).columnGap) || 0;
      const ancho = (r.width - gap * (COLUMNAS - 1)) / COLUMNAS;
      seccion.current.style.setProperty("--reg-alto", (ancho * (r.height / r.width)).toFixed(2) + "px");
    };
    ajustar();
    const observador = new ResizeObserver(ajustar);
    observador.observe(caja.current);
    return () => observador.disconnect();
  }, []);

  return (
    <section ref={seccion} className="modulo" data-tema={clave}
             data-deshabilitado={deshabilitado || undefined} style={{ "--i": indice }}>
      <button
        ref={(el) => { caja.current = el; registrarCaja(el); }}
        className="modulo__caja" type="button" disabled={deshabilitado} onClick={onAbrir}
      >
        <span className="modulo__titulo">{titulo}</span>
        <span className="modulo__meta">{deshabilitado ? "Próximamente" : meta ?? "—"}</span>
        <span className="modulo__flecha" aria-hidden="true">→</span>
      </button>
      <div className="modulo__lista">
        <div ref={rejilla} className="modulo__rejilla">
          {tarjetas && (tarjetas.length ? tarjetas : <p className="modulo__vacio">{vacio}</p>)}
        </div>
      </div>
    </section>
  );
}
