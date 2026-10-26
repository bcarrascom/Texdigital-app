import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { AnimatePresence, motion } from "motion/react";
import { rutas } from "@/router/rutas";
import { useAtajo } from "@/hooks/useAtajo";
import { useVolver } from "@/hooks/useVolver";
import Pagina from "@/components/Pagina/Pagina";
import Dialogo from "@/components/Dialogo/Dialogo";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import IconoBuscar from "@/assets/svg/search.svg?react";
import { CATEGORIAS } from "./categorias";
import { Encabezado, IconoCategoria } from "./Ajustes";
import { CambiosPendientes } from "./cambiosPendientes";
import "./Configuracion.css";

/* Configuración: lo que no es de producción (proveedores, preferencias...).
   Se entra por el engranaje de arriba del menú. Como los Ajustes de macOS:
   la lista de categorías a la izquierda, con su buscador, y el contenido de
   la elegida a la derecha.

   La categoría va en la URL (/configuracion/proveedores), así un atajo puede
   abrir una puntual — p. ej. el botón "Proveedores" de Inventario. Cambiar
   de categoría REEMPLAZA la entrada del historial: "Volver" (o Escape) sale
   de Configuración de una, adonde se estaba antes.

   Si la página abierta tiene cambios sin guardar (ver cambiosPendientes.js),
   salir de ella —Volver, Escape, la X de la ventana u otra categoría— abre
   primero DialogoSalir: Guardar, No guardar o Cancelar. */

const FUNDIDO = { duration: 0.18, ease: [0.22, 1, 0.36, 1] };

/* Sin tildes ni mayúsculas, para que "version" encuentre "Versión". */
const normalizar = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export default function Configuracion() {
  const { categoria } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const volverDirecto = useVolver();
  const [buscar, setBuscar] = useState("");
  const lista = useRef(null);

  // Lo que la página abierta tiene sin guardar, y la salida que espera respuesta.
  const pendiente = useRef(null);
  const registrar = useCallback((info) => { pendiente.current = info; }, []);
  const [salida, setSalida] = useState(null);   // { accion, ...pendiente } mientras se pregunta
  const intentar = (accion) => {
    if (pendiente.current) { setSalida({ accion, ...pendiente.current }); return true; }
    accion();
    return false;
  };
  const volver = () => intentar(volverDirecto);
  useAtajo("escape", volver);

  /* La X de la ventana llama a TD.volver (ver RutasAnimadas): con cambios
     pendientes, se pregunta acá en vez de salir. */
  const volverRef = useRef(volverDirecto);
  volverRef.current = volverDirecto;
  useEffect(() => {
    window.TD = window.TD || {};
    window.TD.interceptarVolver = () => {
      if (!pendiente.current) return false;
      setSalida({ accion: () => volverRef.current(), ...pendiente.current });
      return true;
    };
    return () => { delete window.TD.interceptarVolver; };
  }, []);

  const actual = CATEGORIAS.find((c) => c.clave === categoria) || CATEGORIAS[0];
  const filtro = normalizar(buscar.trim());
  const visibles = filtro
    ? CATEGORIAS.filter((c) => normalizar(`${c.titulo} ${c.desc} ${c.palabras}`).includes(filtro))
    : CATEGORIAS;

  const elegir = (c) => {
    if (c.clave === actual.clave) return;
    intentar(() => navigate(rutas.configuracion(c.clave), { replace: true, state: location.state }));
  };

  /* ↑/↓ en la lista pasan de categoría, como en macOS. */
  function teclas(e) {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const i = visibles.findIndex((c) => c.clave === actual.clave);
    const siguiente = visibles[Math.min(visibles.length - 1, Math.max(0, i + (e.key === "ArrowDown" ? 1 : -1)))];
    if (!siguiente) return;
    elegir(siguiente);
    if (!pendiente.current) lista.current?.querySelector(`[data-clave="${siguiente.clave}"]`)?.focus();
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
            <CambiosPendientes.Provider value={registrar}>
              <Contenido />
            </CambiosPendientes.Provider>
          </motion.div>
        </AnimatePresence>
      </main>

      <DialogoSalir salida={salida} onCerrar={() => setSalida(null)}
                    onSalir={() => { const { accion } = salida; setSalida(null); pendiente.current = null; accion(); }} />
    </Pagina>
  );
}

/* ¿Guardar los cambios antes de salir? Con la lista de TODOS los cambios
   (pedido de Bruno). Si alguno no es válido, Guardar no se puede: dice por qué. */
function DialogoSalir({ salida, onCerrar, onSalir }) {
  const [guardando, setGuardando] = useState(false);
  async function guardar() {
    if (guardando || salida.error) return;
    setGuardando(true);
    try {
      if (await salida.guardar()) onSalir();
    } finally {
      setGuardando(false);
    }
  }
  return (
    <Dialogo abierto={!!salida} onCerrar={onCerrar} className="dlg--desenfoque dlg-salir">
      {salida && (
        <>
          <h2 className="dlg__titulo">¿Guardar los cambios?</h2>
          <p className="dlg__texto">
            {salida.cambios.length === 1 ? "Hay un cambio sin guardar:" : `Hay ${salida.cambios.length} cambios sin guardar:`}
          </p>
          <ul className="dlg-salir__lista">
            {salida.cambios.map((c, k) => <li key={k}>{c}</li>)}
          </ul>
          {salida.error && (
            <p className="ajustes-nota ajustes-nota--aviso dlg-salir__nota" role="alert">
              <IconoAviso aria-hidden="true" /><span>No se puede guardar: {salida.error}</span>
            </p>
          )}
          <div className="dlg__acciones">
            <button className="btn btn--fantasma btn--chico" type="button" disabled={guardando} onClick={onCerrar}>Cancelar</button>
            <button className="btn btn--secundario btn--chico" type="button" disabled={guardando} onClick={onSalir}>No guardar</button>
            <button className="btn btn--primario btn--chico" type="button" data-autofoco={salida.error ? undefined : ""}
                    disabled={guardando || !!salida.error} onClick={guardar}>Guardar</button>
          </div>
        </>
      )}
    </Dialogo>
  );
}
