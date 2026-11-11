import { useLayoutEffect, useRef, useState } from "react";
import "./NavFlotante.css";

/* Menú de secciones de una página (p. ej. Configuración › Correos): un botón
   por sección, con su ícono y su nombre, y una píldora que se desliza a la
   elegida. Idea de Bruno (2026-11-11), con el aspecto del switch segmentado
   de la app (components/Segmento): caja gris con borde, píldora grafito y el
   texto de la elegida en blanco. Queda pegado arriba al bajar por la página.

       <NavFlotante etiqueta="Secciones de Correos" valor={seccion} onCambiar={setSeccion}
                    items={[{ clave: "cotizaciones", etiqueta: "Cotizaciones", Icono, aviso: false }, ...]} />

   `aviso`: un punto rojo en el botón (p. ej. un dato inválido en esa sección).
   La píldora se mide sobre el botón elegido, así que calza con nombres de
   cualquier largo y se vuelve a medir si algo cambia de tamaño (A− / A+).
   Se anima con CSS (--m-media), así respeta "reducir movimiento" del sistema.
   ←/→ pasan de sección con el foco en el menú. */

export default function NavFlotante({ items, valor, onCambiar, etiqueta }) {
  const contenedor = useRef(null);
  const botones = useRef([]);
  const [pildora, setPildora] = useState(null);   // { x, ancho } en px
  const [animar, setAnimar] = useState(false);    // la primera medida no se anima
  const elegido = Math.max(0, items.findIndex((x) => x.clave === valor));

  useLayoutEffect(() => {
    const medir = () => {
      const b = botones.current[elegido];
      if (!b) return;
      setPildora({ x: b.offsetLeft, ancho: b.offsetWidth });
    };
    medir();
    const obs = new ResizeObserver(medir);
    obs.observe(contenedor.current);
    botones.current.forEach((b) => b && obs.observe(b));
    return () => obs.disconnect();
  }, [elegido, items.length]);

  useLayoutEffect(() => {
    if (pildora && !animar) requestAnimationFrame(() => setAnimar(true));
  }, [pildora, animar]);

  function teclas(e) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    e.stopPropagation();
    const i = (elegido + (e.key === "ArrowRight" ? 1 : -1) + items.length) % items.length;
    onCambiar(items[i].clave);
    botones.current[i]?.focus();
  }

  return (
    <div className="nav-flotante" ref={contenedor} role="tablist" aria-label={etiqueta} onKeyDown={teclas}>
      {pildora && (
        <span className="nav-flotante__pildora" aria-hidden="true" data-animar={animar || undefined}
              style={{ width: pildora.ancho, transform: `translateX(${pildora.x}px)` }} />
      )}
      {items.map(({ clave, etiqueta: texto, Icono, aviso }, i) => (
        <button key={clave} ref={(el) => { botones.current[i] = el; }} type="button" role="tab"
                className="nav-flotante__item" aria-selected={i === elegido} tabIndex={i === elegido ? 0 : -1}
                onClick={() => onCambiar(clave)}>
          <Icono className="nav-flotante__icono" aria-hidden="true" />
          <span>{texto}</span>
          {aviso && <span className="nav-flotante__punto" title="Hay algo que revisar" />}
        </button>
      ))}
    </div>
  );
}
