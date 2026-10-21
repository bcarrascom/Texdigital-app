import { AnimatePresence, motion } from "motion/react";
import "./TituloDeslizante.css";

/* Título de cabecera para las pantallas que pasan de una ficha a otra con
   ←/→ (ver-cotización, ver-OP): al cambiar, el viejo sale hacia arriba
   desvaneciéndose y el nuevo aparece subiendo desde abajo (todo el
   movimiento en un solo sentido, como un contador que gira) recién cuando
   el slide del contenido ya terminó.

       <Cabecera titulo={<TituloDeslizante texto={titulo} clave={cot.numero} esperar={0.35} />} />

     clave     lo que cambia entre fichas. El texto solo no alcanza: al
               terminar de cargar la primera, el texto se completa (con la
               empresa) y eso no tiene que animarse.
     esperar   segundos hasta que termina el slide del contenido */

const SALE = { duration: 0.16, ease: [0.55, 0, 1, 0.45] };
const ENTRA = { duration: 0.28, ease: [0.22, 1, 0.36, 1] };

export default function TituloDeslizante({ texto, clave, esperar = 0.35 }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={clave}
        className="cabecera__titulo-texto"
        initial={{ y: "110%", opacity: 0 }}
        // mode="wait": entra cuando terminó de salir, así que de la espera
        // total se descuenta lo que tardó la salida.
        animate={{ y: 0, opacity: 1, transition: { ...ENTRA, delay: Math.max(0, esperar - SALE.duration) } }}
        exit={{ y: "-110%", opacity: 0, transition: SALE }}
      >
        {texto}
      </motion.span>
    </AnimatePresence>
  );
}
