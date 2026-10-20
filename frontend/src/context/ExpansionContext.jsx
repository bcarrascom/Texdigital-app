import { createContext, useCallback, useContext, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "motion/react";

/* La expansión del color al entrar a un módulo desde el menú (y la
   contracción al volver). Antes vivía dentro de menu.html porque el módulo
   y su panel eran la misma página; ahora el módulo es OTRA ruta, así que
   este div tiene que sobrevivir al cambio de página: vive acá, por encima
   del router, no dentro de ninguna página.

     abrir(caja, modulo, ruta)  la caja del módulo crece hasta pasarse de
                                los bordes de la ventana, recién ahí se
                                navega, y se desvanece sobre la página nueva.
     contraer(caja, alTerminar) al revés: arranca cubriendo la pantalla y se
                                encoge hasta la caja del módulo del que se
                                había salido (lo llama el menú al montarse).

   Arranca calcada de la caja (relleno, borde y radio) y termina PASADA de
   los bordes: el borde también crece y se va de pantalla, que es lo que le
   da el contorno definido a la animación. */

const ExpansionContext = createContext(null);

const EXPANSION = { duration: 0.39, ease: [0.5, 0, 0.2, 1] };  // --m-expansion, --ease-expandir
const DESVANECER = { duration: 0.16, ease: "linear" };         // --m-rapida
// Cuánto esperar después de navegar antes de desvanecerse: la salida de la
// página anterior (ver components/Pagina) tiene que haber terminado.
const ESPERA_PAGINA_MS = 200;

function rectDe(caja) {
  const r = caja.getBoundingClientRect();
  const est = getComputedStyle(caja);
  return {
    geometria: { top: r.top, left: r.left, width: r.width, height: r.height,
                 borderRadius: parseFloat(est.borderTopLeftRadius) || 0 },
    colores: { background: est.backgroundColor, borderColor: est.borderTopColor,
               borderWidth: est.borderTopWidth },
  };
}

function pantallaCompleta() {
  const w = window.innerWidth, h = window.innerHeight;
  return { top: -0.06 * h, left: -0.06 * w, width: 1.12 * w, height: 1.12 * h, borderRadius: 0 };
}

/* Cambia el tema de <html> sin la transición de fondo de body (base.css):
   la expansión ya está tapando todo, el fundido no se vería y solo
   retrasaría que el fondo quede del color correcto. */
function temaInstantaneo(tema) {
  const body = document.body;
  const previa = body.style.transition;
  body.style.transition = "none";
  document.documentElement.dataset.tema = tema;
  void body.offsetWidth;
  body.style.transition = previa;
}

export function ExpansionProvider({ children }) {
  const navigate = useNavigate();
  const [anim, setAnim] = useState(null);   // { id, tipo, colores, desde, hasta, fase, alTerminar }
  const moduloAbierto = useRef(null);
  const siguienteId = useRef(0);

  const desvanecer = useCallback(() => {
    setAnim((a) => a && { ...a, fase: "desvaneciendo", alTerminar: () => setAnim(null) });
  }, []);

  const abrir = useCallback((caja, modulo, ruta) => {
    if (anim) return;  // una a la vez: un doble click no arranca otra encima
    const { geometria, colores } = rectDe(caja);
    moduloAbierto.current = { modulo };
    setAnim({
      id: siguienteId.current++, tipo: "abrir", colores, desde: geometria, hasta: pantallaCompleta(), fase: "moviendo",
      alTerminar: () => {
        temaInstantaneo(modulo);
        navigate(ruta);
        setTimeout(desvanecer, ESPERA_PAGINA_MS);
      },
    });
  }, [anim, navigate, desvanecer]);

  const contraer = useCallback((caja, alTerminar) => {
    const { geometria, colores } = rectDe(caja);
    moduloAbierto.current = null;
    setAnim({
      id: siguienteId.current++, tipo: "contraer", colores, desde: pantallaCompleta(), hasta: geometria, fase: "moviendo",
      alTerminar: () => {
        desvanecer();
        alTerminar?.();
      },
    });
  }, [desvanecer]);

  const valor = {
    abrir,
    contraer,
    // true mientras crece (el menú se desdibuja por detrás, ver Menu.css)
    expandiendo: anim?.tipo === "abrir" && anim.fase === "moviendo",
    // Qué módulo quedó "abierto" (el menú lo usa para saber hacia qué caja
    // contraer al volver).
    moduloAbierto: () => moduloAbierto.current?.modulo ?? null,
  };

  return (
    <ExpansionContext.Provider value={valor}>
      {children}
      {anim && (
        <motion.div
          key={anim.id}
          className="expansion"
          style={anim.colores}
          initial={{ ...anim.desde, opacity: 1 }}
          animate={anim.fase === "desvaneciendo" ? { ...anim.hasta, opacity: 0 } : { ...anim.hasta, opacity: 1 }}
          transition={anim.fase === "desvaneciendo" ? DESVANECER : EXPANSION}
          onAnimationComplete={() => anim.alTerminar?.()}
        />
      )}
    </ExpansionContext.Provider>
  );
}

export function useExpansion() {
  const valor = useContext(ExpansionContext);
  if (!valor) throw new Error("useExpansion() fuera de <ExpansionProvider>");
  return valor;
}
