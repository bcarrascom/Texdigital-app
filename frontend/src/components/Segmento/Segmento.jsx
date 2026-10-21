import { Fragment, useId, useLayoutEffect, useRef, useState } from "react";

/* Switch segmentado de DOS opciones, con textos de cualquier largo:

       <Segmento valor={p.impresion} onCambiar={(v) => ...} etiqueta="Impresión"
                 opciones={[{ valor: "Cara única" }, { valor: "Tiro y retiro" }]} />

       opciones   [{ valor, etiqueta?, titulo? }, ...] — sin etiqueta, se
                  muestra el valor; la etiqueta puede ser un ícono (con el
                  texto en `titulo`, el tooltip)
       vertical   las opciones apiladas en vez de lado a lado
       bloque     ocupa todo el ancho y reparte el espacio entre las dos
       className  clases extra (p. ej. "segmento--iconos")

   La píldora que marca la opción elegida es un elemento propio, MEDIDO sobre
   esa opción (no la mitad del switch): con textos de distinto largo, al
   cambiar de opción se desliza Y cambia de tamaño, siempre calzada. Se vuelve
   a medir si cambia el tamaño de algo (otro texto, la escala A− / A+).

   Son <input type=radio> de verdad: se manejan con las flechas del teclado y
   son accesibles. Pero es un switch, no un grupo de radios cualquiera: un
   click en CUALQUIER punto —incluida la opción ya elegida— pasa a la otra. El
   click nativo del label marcaría la que se tocó y, junto con este toggle,
   terminaría alternando dos veces; por eso se apaga y el cambio lo maneja
   solo el click del grupo. */
export default function Segmento({ opciones, valor, onCambiar, etiqueta, vertical = false, bloque = false, className = "" }) {
  const nombre = useId();
  const grupo = useRef(null);
  const etiquetas = useRef([]);
  const [pildora, setPildora] = useState(null);   // { x, y, ancho, alto } en px, relativa al grupo
  const elegida = Math.max(0, opciones.findIndex((o) => o.valor === valor));
  const otra = () => opciones.find((o) => o.valor !== valor)?.valor ?? opciones[0].valor;

  useLayoutEffect(() => {
    const medir = () => {
      const el = etiquetas.current[elegida];
      if (!el) return;
      setPildora((antes) => {
        const nueva = { x: el.offsetLeft, y: el.offsetTop, ancho: el.offsetWidth, alto: el.offsetHeight };
        // Sin cambios no se re-renderiza (el ResizeObserver avisa seguido).
        return antes && Object.keys(nueva).every((k) => antes[k] === nueva[k]) ? antes : nueva;
      });
    };
    medir();
    const observador = new ResizeObserver(medir);
    observador.observe(grupo.current);
    etiquetas.current.forEach((el) => el && observador.observe(el));
    return () => observador.disconnect();
  }, [elegida, opciones.length]);

  /* La primera vez la píldora aparece directo en su lugar; recién después
     de esa primera medida se anima (si no, se vería viajar desde la esquina). */
  const [animar, setAnimar] = useState(false);
  useLayoutEffect(() => {
    if (!pildora || animar) return;
    const t = requestAnimationFrame(() => setAnimar(true));
    return () => cancelAnimationFrame(t);
  }, [pildora, animar]);

  const clases = ["segmento", vertical && "segmento--vertical", bloque && "segmento--bloque", className].filter(Boolean).join(" ");

  return (
    <div ref={grupo} className={clases} role="group" aria-label={etiqueta} onClick={() => onCambiar(otra())}>
      {pildora && (
        <span
          className="segmento__pildora"
          data-animar={animar || undefined}
          aria-hidden="true"
          style={{ width: pildora.ancho, height: pildora.alto, transform: `translate(${pildora.x}px, ${pildora.y}px)` }}
        />
      )}
      {opciones.map((o, k) => {
        const id = `${nombre}-${k}`;
        return (
          <Fragment key={o.valor}>
            <input type="radio" id={id} name={nombre} checked={k === elegida} onChange={() => onCambiar(o.valor)}
                   // El click lo resuelve el grupo (ver arriba): que no suba dos veces.
                   onClick={(e) => e.stopPropagation()} />
            <label ref={(el) => { etiquetas.current[k] = el; }} htmlFor={id} title={o.titulo}
                   onClick={(e) => e.preventDefault()}>
              {o.etiqueta ?? o.valor}
            </label>
          </Fragment>
        );
      })}
    </div>
  );
}
