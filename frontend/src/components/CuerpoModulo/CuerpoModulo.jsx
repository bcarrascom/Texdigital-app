import "./CuerpoModulo.css";

/* Las piezas del cuerpo de un módulo (lo que antes era su panel dentro de
   menu.html): la página en sí la arma pages/Modulos, que desliza de un módulo
   a otro con ←/→. Cada módulo solo declara su contenido:

       <Acciones>
         <Accion titulo="Nueva cotización" desc="..." onClick={...} />
       </Acciones>
       <SeccionModulo titulo="cotizaciones">
         <RejillaTarjetas vacio="Todavía no hay cotizaciones.">{tarjetas}</RejillaTarjetas>
       </SeccionModulo> */

/* Las tarjetas grandes de acción, apareciendo en escalón. */
export function Acciones({ children }) {
  return <div className="acciones aparecer">{children}</div>;
}

export function Accion({ titulo, desc, indice = 0, className = "", onClick }) {
  return (
    <button type="button" className={`accion ${className}`} style={{ "--i": indice }} onClick={onClick}>
      <span className="accion__titulo">{titulo}</span>
      {desc && <span className="accion__desc">{desc}</span>}
    </button>
  );
}

export function SeccionModulo({ titulo, children }) {
  return (
    <section className="modulo-seccion">
      {titulo && <h2 className="seccion-titulo">{titulo}</h2>}
      {children}
    </section>
  );
}

/* Rejilla de tarjetas .reg con aparición en escalón. `anchoTarjeta` cambia el
   mínimo de cada columna (p. ej. las de OPs, más anchas por la cuenta
   regresiva de entrega). */
export function RejillaTarjetas({ children, vacio, anchoTarjeta }) {
  const tarjetas = [].concat(children || []).filter(Boolean);
  if (!tarjetas.length) return <p className="rejilla-tarjetas__vacio">{vacio}</p>;
  return (
    <div className="rejilla-tarjetas aparecer" style={anchoTarjeta ? { "--ancho-tarjeta": anchoTarjeta } : undefined}>
      {children}
    </div>
  );
}

/* El escalón de aparición se corta acá: con muchas tarjetas, la última no
   puede tardar segundos en aparecer. */
const MAX_ESCALON = 12;
export const escalon = (i) => ({ "--i": Math.min(i, MAX_ESCALON) });
