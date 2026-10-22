import { useLayoutEffect, useRef, useState } from "react";
import "@/components/Dialogo/Dialogo.css";   // la base de todo <dialog> de la app
import "./DialogoMorph.css";

/* Diálogo que NACE del botón que lo abre: el botón (p. ej. el "+" redondo de
   Inventario) se deforma hasta ser el diálogo — posición, tamaño, radio y
   color viajan juntos, del círculo del botón al rectángulo blanco final — y
   al cerrar se encoge de vuelta hasta él. Se animan top/left/width/height de
   verdad (no un transform/scale): así el contenido nunca se ve estirado.

       const mas = useRef(null);
       <button ref={mas} onClick={() => setAbierto(true)}>+</button>
       <DialogoMorph abierto={abierto} origen={mas} onCerrar={() => setAbierto(false)}>
         <form>...</form>
       </DialogoMorph>

   El contenido se vuelve a montar en cada apertura (arranca limpio). Escape y
   un click en el fondo cierran; un hijo con data-autofoco recibe el foco.
   `anchoRem`: ancho final del diálogo (30rem por defecto, nunca más del 90%
   de la ventana). */

const MARGEN = 12;        // px libres alrededor del diálogo, como mínimo

function rectDe(el) {
  const r = el.getBoundingClientRect();
  return { top: r.top, left: r.left, ancho: r.width, alto: r.height };
}

function aplicar(dlg, { top, left, ancho, alto }, radio) {
  Object.assign(dlg.style, { top: `${top}px`, left: `${left}px`, width: `${ancho}px`, height: `${alto}px`, borderRadius: radio });
}

/* El alto que necesita el contenido con el ancho final, vía scrollHeight: el
   max-height del contenido se saca un instante (sin transición) para medir el
   alto natural, y se restaura antes de que se vea. */
function altoNecesario(dlg, ancho) {
  const contenido = dlg.querySelector(".dlg-morph__contenido");
  const cs = getComputedStyle(dlg);
  const previo = { transition: dlg.style.transition, width: dlg.style.width, maxHeight: contenido.style.maxHeight };
  dlg.style.transition = "none";
  dlg.style.width = `${ancho}px`;
  contenido.style.maxHeight = "none";
  const alto = contenido.scrollHeight + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom)
    + parseFloat(cs.borderTopWidth) + parseFloat(cs.borderBottomWidth) + 1;
  Object.assign(dlg.style, { transition: previo.transition, width: previo.width });
  contenido.style.maxHeight = previo.maxHeight;
  return alto;
}

/* Centrado sobre el botón de origen, pero sin salirse de la ventana. */
function rectFinal(dlg, origen, anchoRem) {
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  const ancho = Math.min(window.innerWidth * 0.9, anchoRem * rem);
  const alto = Math.min(window.innerHeight - 2 * MARGEN, altoNecesario(dlg, ancho));
  const centrado = (inicio, tamOrigen, tam, limite) =>
    Math.min(Math.max(inicio + tamOrigen / 2 - tam / 2, MARGEN), limite - tam - MARGEN);
  return {
    top: centrado(origen.top, origen.alto, alto, window.innerHeight),
    left: centrado(origen.left, origen.ancho, ancho, window.innerWidth),
    ancho, alto,
  };
}

export default function DialogoMorph({ abierto, origen, onCerrar, anchoRem = 30, className = "", children }) {
  const ref = useRef(null);
  const [aperturas, setAperturas] = useState(0);
  const [montado, setMontado] = useState(false);   // el contenido sigue montado mientras se encoge

  if (abierto && !montado) {
    setMontado(true);
    setAperturas((n) => n + 1);
  }

  useLayoutEffect(() => {
    const dlg = ref.current;
    const boton = origen?.current;
    if (abierto && montado && !dlg.open) {
      const desde = boton ? rectDe(boton) : rectDe(dlg);
      dlg.removeAttribute("data-abierto");
      aplicar(dlg, desde, "999px");
      // Arranca con el color REAL del botón y termina en el blanco del
      // diálogo: el fondo viaja en la misma transición (ver el CSS).
      if (boton) dlg.style.background = getComputedStyle(boton).backgroundColor;
      dlg.showModal();
      void dlg.getBoundingClientRect();   // el punto de partida ya aplicado, antes de animar
      const hasta = rectFinal(dlg, desde, anchoRem);
      requestAnimationFrame(() => {
        aplicar(dlg, hasta, "");
        dlg.style.background = "";
        dlg.setAttribute("data-abierto", "");
        dlg.querySelector("[data-autofoco]")?.focus({ preventScroll: true });
      });
    } else if (!abierto && dlg.open) {
      // Camino inverso: se encoge hasta el botón y RECIÉN ahí se cierra.
      dlg.removeAttribute("data-abierto");
      if (boton) {
        aplicar(dlg, rectDe(boton), "999px");
        dlg.style.background = getComputedStyle(boton).backgroundColor;
      }
      let listo = false;
      const terminar = () => {
        if (listo) return;
        listo = true;
        dlg.close();
        dlg.style.background = "";
        setMontado(false);
      };
      const alTerminar = (e) => { if (e.target === dlg && e.propertyName === "width") terminar(); };
      dlg.addEventListener("transitionend", alTerminar);
      const seguro = setTimeout(terminar, 800);   // por si la transición no llega a dispararse
      return () => { dlg.removeEventListener("transitionend", alTerminar); clearTimeout(seguro); };
    }
  }, [abierto, montado]);

  return (
    <dialog
      ref={ref}
      className={`dlg-morph ${className}`}
      onCancel={(e) => { e.preventDefault(); onCerrar(); }}   // Escape
      onClick={(e) => { if (e.target === ref.current) onCerrar(); }}   // el fondo
    >
      <div className="dlg-morph__contenido" key={aperturas}>
        {montado && children}
      </div>
    </dialog>
  );
}
