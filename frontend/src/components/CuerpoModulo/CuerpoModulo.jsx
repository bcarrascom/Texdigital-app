import { useRef, useState } from "react";
import { useLocation, useSearchParams } from "react-router";
import { useAtajo } from "@/hooks/useAtajo";
import IconoBuscar from "@/assets/svg/search.svg?react";
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

/* `accesorio` va a la derecha del título (p. ej. el buscador). */
export function SeccionModulo({ titulo, accesorio, children }) {
  const h2 = titulo && <h2 className="seccion-titulo">{titulo}</h2>;
  return (
    <section className="modulo-seccion">
      {accesorio ? <div className="modulo-seccion__cab">{h2}{accesorio}</div> : h2}
      {children}
    </section>
  );
}

/* Lo escrito en el buscador del módulo, guardado en la URL (?q=): al volver
   de una ficha, el listado sigue filtrado como se lo dejó (mismo criterio
   que pages/HistorialOps). El valor vive acá y se copia a la URL, no al
   revés: leído de la URL, el campo perdería letras al escribir rápido.

       const [busqueda, setBusqueda] = useBusqueda(); */
export function useBusqueda() {
  const [params, setParams] = useSearchParams();
  const { state } = useLocation();
  const [texto, setTexto] = useState(() => params.get("q") || "");
  function cambiar(valor) {
    setTexto(valor);
    setParams((p) => {
      const nuevos = new URLSearchParams(p);
      if (valor) nuevos.set("q", valor);
      else nuevos.delete("q");
      return nuevos;
    }, { replace: true, state });
  }
  return [texto, cambiar];
}

/* Sin tildes ni mayúsculas, como los buscadores de Configuración. */
const normalizar = (s) => String(s ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

/* ¿Calza `texto` con los `campos`? Cada palabra tiene que aparecer en
   alguno ("tiendas pendones" encuentra el trabajo "Pendones" de Tiendas
   Ejemplo); sin texto, calza todo. */
export function coincide(texto, campos) {
  const donde = campos.map(normalizar).join("\n");
  return normalizar(texto).split(/\s+/).filter(Boolean).every((palabra) => donde.includes(palabra));
}

/* Ctrl+F (⌘F) lo enfoca. Dentro del campo, ←/→ mueven el cursor en vez de
   pasar al módulo vecino (ver pages/Modulos), y Escape primero lo borra. */
export function Buscador({ valor, onCambiar, placeholder }) {
  const entrada = useRef(null);
  useAtajo("mod+f", () => { entrada.current?.focus(); entrada.current?.select(); });
  function alPresionar(e) {
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") e.stopPropagation();
    if (e.key === "Escape" && valor) { e.preventDefault(); e.stopPropagation(); onCambiar(""); }
  }
  return (
    <label className="modulo-buscar">
      <IconoBuscar aria-hidden="true" />
      <input ref={entrada} type="search" placeholder={placeholder} aria-label={placeholder} value={valor}
             onChange={(e) => onCambiar(e.target.value)} onKeyDown={alPresionar} />
    </label>
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
