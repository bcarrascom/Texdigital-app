import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import IconoAlerta from "@/assets/svg/circle-alert.svg?react";

/* Aviso de menú: el círculo arriba de la caja de un módulo y la tarjeta que
   se despliega al hacerle click. Lo usan el aviso de stock (Inventario,
   core.repositorio_inventario.avisos_stock) y el de producción (OPs
   atrasadas, core.repositorio_ops.avisos_ops): misma cáscara, distinto
   contenido (`render`). Si hay varios ítems, rotan solos mientras la tarjeta
   está abierta; ←/→ los pasan a mano.

   Teclado, con el ícono enfocado (se llega con ↑ desde el módulo, ver Menu):
     Enter      tarjeta cerrada → la abre; abierta → aprieta su botón de acción
     ↓          vuelve al módulo que corona (cerrando la tarjeta)
     Escape     cierra la tarjeta */

const ROTACION_MS = 4000;
const FUNDIDO = { duration: 0.18 };

export default function AvisoMenu({
  tema, titulo, color, items, texto, render, etiquetaAccion, onAccion,
  abierto, onAbrir, onCerrar, onBajar, botonRef,
}) {
  const raiz = useRef(null);
  const [indice, setIndice] = useState(0);
  const [reinicio, setReinicio] = useState(0);  // cambia → la rotación automática arranca de cero
  const n = items.length;
  const actual = items[indice % n];

  useEffect(() => { if (abierto) setIndice(0); }, [abierto]);

  useEffect(() => {
    if (!abierto || n <= 1) return;
    const t = setInterval(() => setIndice((i) => (i + 1) % n), ROTACION_MS);
    return () => clearInterval(t);
  }, [abierto, n, reinicio]);

  // Mientras está abierta: Escape, ←/→ y click afuera.
  useEffect(() => {
    if (!abierto) return;
    const mover = (delta) => {
      setIndice((i) => (i + delta + n) % n);
      setReinicio((r) => r + 1);
    };
    const tecla = (e) => {
      if (e.key === "Escape") onCerrar();
      else if (e.key === "ArrowLeft" && n > 1) { e.preventDefault(); mover(-1); }
      else if (e.key === "ArrowRight" && n > 1) { e.preventDefault(); mover(1); }
    };
    const clickAfuera = (e) => { if (!raiz.current?.contains(e.target)) onCerrar(); };
    document.addEventListener("keydown", tecla);
    document.addEventListener("click", clickAfuera);
    return () => {
      document.removeEventListener("keydown", tecla);
      document.removeEventListener("click", clickAfuera);
    };
  }, [abierto, n, onCerrar]);

  if (!n) return null;

  const accionar = () => {
    onCerrar();
    onAccion(actual);
  };

  return (
    // data-tema: el aviso no vive dentro de su .modulo (ver Menu.css), así que
    // necesita el tema propio para que su botón salga del color del módulo.
    <div ref={raiz} className="aviso-menu" data-tema={tema} data-abierto={abierto || undefined}
         style={{ "--color-aviso": color }}>
      <button
        ref={botonRef}
        className="aviso-menu__icono" type="button" title={titulo} aria-expanded={abierto}
        onClick={(e) => { e.stopPropagation(); abierto ? onCerrar() : onAbrir(); }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            // Se intercepta a mano: el Enter nativo de un <button> dispararía
            // el onClick, que siempre alterna abrir/cerrar.
            e.preventDefault();
            abierto ? accionar() : onAbrir();
          } else if (e.key === "ArrowDown") {
            e.preventDefault();
            if (abierto) onCerrar();
            onBajar();
          }
        }}
      >
        <IconoAlerta aria-hidden="true" />
      </button>

      <div className="aviso-menu__tarjeta">
        <p className="aviso-menu__texto">{typeof texto === "function" ? texto(actual) : texto}</p>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={indice % n} className="aviso-menu__contenido"
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={FUNDIDO}>
            {render(actual)}
          </motion.div>
        </AnimatePresence>
        {n > 1 && (
          <div className="aviso-menu__puntos">
            {items.map((_, j) => (
              <span key={j} className="aviso-menu__punto" data-activo={j === indice % n || undefined} />
            ))}
          </div>
        )}
        <button className="btn btn--primario btn--chico aviso-menu__accion" type="button" onClick={accionar}>
          {typeof etiquetaAccion === "function" ? etiquetaAccion(actual) : etiquetaAccion}
        </button>
      </div>
    </div>
  );
}
