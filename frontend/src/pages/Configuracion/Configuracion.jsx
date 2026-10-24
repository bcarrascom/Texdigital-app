import { useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { AnimatePresence, motion } from "motion/react";
import { rutas } from "@/router/rutas";
import { useAtajo } from "@/hooks/useAtajo";
import { useVolver } from "@/hooks/useVolver";
import Pagina from "@/components/Pagina/Pagina";
import IconoBuscar from "@/assets/svg/search.svg?react";
import { CATEGORIAS } from "./categorias";
import { Encabezado, IconoCategoria } from "./Ajustes";
import "./Configuracion.css";

/* Configuración: lo que no es de producción (proveedores, preferencias...).
   Se entra por el engranaje de arriba del menú. Como los Ajustes de macOS:
   la lista de categorías a la izquierda, con su buscador, y el contenido de
   la elegida a la derecha.

   La categoría va en la URL (/configuracion/proveedores), así un atajo puede
   abrir una puntual — p. ej. el botón "Proveedores" de Inventario. Cambiar
   de categoría REEMPLAZA la entrada del historial: "Volver" (o Escape) sale
   de Configuración de una, adonde se estaba antes. */

const FUNDIDO = { duration: 0.18, ease: [0.22, 1, 0.36, 1] };

/* Sin tildes ni mayúsculas, para que "version" encuentre "Versión". */
const normalizar = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export default function Configuracion() {
  const { categoria } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const volver = useVolver();
  useAtajo("escape", volver);
  const [buscar, setBuscar] = useState("");
  const lista = useRef(null);

  const actual = CATEGORIAS.find((c) => c.clave === categoria) || CATEGORIAS[0];
  const filtro = normalizar(buscar.trim());
  const visibles = filtro
    ? CATEGORIAS.filter((c) => normalizar(`${c.titulo} ${c.desc} ${c.palabras}`).includes(filtro))
    : CATEGORIAS;

  const elegir = (c) => navigate(rutas.configuracion(c.clave), { replace: true, state: location.state });

  /* ↑/↓ en la lista pasan de categoría, como en macOS. */
  function teclas(e) {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const i = visibles.findIndex((c) => c.clave === actual.clave);
    const siguiente = visibles[Math.min(visibles.length - 1, Math.max(0, i + (e.key === "ArrowDown" ? 1 : -1)))];
    if (!siguiente) return;
    elegir(siguiente);
    lista.current?.querySelector(`[data-clave="${siguiente.clave}"]`)?.focus();
  }

  const { Contenido } = actual;

  return (
    <Pagina tema="configuracion" titulo={`Configuración · ${actual.titulo}`} className="pag-configuracion">
      <aside className="ajustes-lateral">
        <button className="cab-btn cab-btn--fantasma ajustes-lateral__volver" type="button" onClick={volver}>← Volver</button>
        <label className="ajustes-buscar">
          <IconoBuscar aria-hidden="true" />
          <input type="search" placeholder="Buscar" aria-label="Buscar en Configuración" value={buscar}
                 onChange={(e) => setBuscar(e.target.value)}
                 onKeyDown={(e) => {
                   // Con algo escrito, Escape limpia la búsqueda en vez de salir.
                   if (e.key === "Escape" && buscar) { e.preventDefault(); e.stopPropagation(); setBuscar(""); }
                 }} />
        </label>
        <nav ref={lista} className="ajustes-lista" aria-label="Categorías" onKeyDown={teclas}>
          {visibles.map((c) => (
            <button key={c.clave} type="button" data-clave={c.clave} className="ajustes-lista__item"
                    aria-current={c.clave === actual.clave ? "page" : undefined} onClick={() => elegir(c)}>
              <IconoCategoria Icono={c.Icono} color={c.color} />
              <span>{c.titulo}</span>
            </button>
          ))}
          {!visibles.length && <p className="ajustes-lista__vacio">Sin resultados para “{buscar.trim()}”.</p>}
        </nav>
      </aside>

      <main className="ajustes-contenido">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={actual.clave} className="ajustes-pagina"
                      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={FUNDIDO}>
            <Encabezado categoria={actual} />
            <Contenido />
          </motion.div>
        </AnimatePresence>
      </main>
    </Pagina>
  );
}
