import { useApp } from "@/context/AppContext";
import { useAtajo } from "@/hooks/useAtajo";
import { useVolver } from "@/hooks/useVolver";
import Pagina from "@/components/Pagina/Pagina";
import "./PaginaModulo.css";

/* La página de un módulo (Inventario, Cotizaciones, OPs, Despachos) — lo que
   antes era su panel dentro de menu.html. Se llega desde el menú con la
   expansión de color (context/ExpansionContext), así que el fondo es el
   relleno del tema, igual que el color en que termina esa expansión.

       <PaginaModulo tema="cotizaciones" titulo="Cotizaciones" acciones={<button .../>}>
         <Acciones>
           <Accion titulo="Nueva cotización" desc="..." onClick={...} />
         </Acciones>
         <SeccionModulo titulo="cotizaciones">...</SeccionModulo>
       </PaginaModulo>

   `acciones`: botones extra de la cabecera, a la derecha de "Volver".
   Escape vuelve al menú, igual que el botón. */
export default function PaginaModulo({ tema, titulo, acciones, ancho, children }) {
  const { contexto } = useApp();
  const volver = useVolver();
  useAtajo("escape", volver);

  return (
    <Pagina tema={tema} titulo={titulo} className={`pagina-modulo pag-${tema}`}>
      <header className="modulo-cab">
        <button className="cab-btn cab-btn--fantasma" onClick={volver}>← Volver</button>
        {acciones}
        <span className="cabecera__sep" />
        {contexto.version && <span className="cabecera__version">v{contexto.version}</span>}
      </header>
      <main className="modulo-contenido">
        <div className="modulo-cuerpo" style={ancho ? { "--ancho-modulo": ancho } : undefined}>
          <h1 className="modulo-cuerpo__titulo">{titulo}</h1>
          {children}
        </div>
      </main>
    </Pagina>
  );
}

/* Las tarjetas grandes de acción ("Nueva cotización", "Historial", ...),
   apareciendo en escalón. */
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
