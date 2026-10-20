import { useEffect } from "react";
import { useLocation } from "react-router";
import { motion } from "motion/react";
import { api } from "@/services/api";

/* Envoltorio de TODA página: la transición de entrada/salida entre rutas
   (la coordina <AnimatePresence> en router/RutasAnimadas.jsx), el tema de
   color del módulo y el título de la ventana.

       <Pagina tema="despachos" titulo="Despacho OP 0042" className="pag-ver-despacho">
         <Cabecera ... />
         <main className="contenido">...</main>
       </Pagina>

   tema: "cotizaciones" | "ops" | "despachos" | "inventario" | undefined.
   Va en <html data-tema>, igual que en las pantallas viejas: así el fondo
   de body cambia con su propia transición de color (ver base.css).

   animarEntrada={false}: la página aparece ya en su lugar — la usa el menú
   cuando vuelve de un módulo, porque ahí la entrada la hace la contracción
   del color (context/ExpansionContext) y tiene que medir la caja quieta. */

const transicion = { duration: 0.28, ease: [0.22, 1, 0.36, 1] }; // --m-media, --ease-salida

export default function Pagina({ tema, titulo, className = "", animarEntrada = true, children }) {
  // navigate(ruta, { state: { deslizar: 1 | -1 } }): la página entra de
  // costado en vez de desde abajo — para pasar a la ficha siguiente/anterior.
  const deslizar = useLocation().state?.deslizar;
  const entrada = deslizar ? { opacity: 0, x: 48 * deslizar } : { opacity: 0, y: 16 };

  useEffect(() => {
    if (tema) document.documentElement.dataset.tema = tema;
    else delete document.documentElement.dataset.tema;
  }, [tema]);

  useEffect(() => {
    if (!titulo) return;
    document.title = `${titulo} · TexDigital`;
    api.poner_titulo(titulo);
  }, [titulo]);

  return (
    <motion.div
      className={`app ${className}`}
      initial={animarEntrada ? entrada : false}
      animate={{ opacity: 1, x: 0, y: 0 }}
      exit={{ opacity: 0, y: -8, transition: { ...transicion, duration: 0.16 } }}
      transition={transicion}
    >
      {children}
    </motion.div>
  );
}
