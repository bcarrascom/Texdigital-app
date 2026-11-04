import { useLayoutEffect, useState } from "react";

/* Lo que Inventario recuerda mientras no se sale del módulo (pedido de Bruno,
   2026-11-04): el scroll de cada tabla y su búsqueda, orden y modo de los
   inactivos. Así, abrir un rollo o un material (o pasar a la otra tabla) y
   volver deja la lista donde estaba, en vez de arriba de todo con cientos de
   rollos por recorrer.

   "Volver" desde un rollo es un paso atrás en el historial (ver useVolver):
   se vuelve a la MISMA entrada, con la misma location.key. Entrar al módulo
   desde el menú o desde otro módulo (←/→) es una entrada nueva, con otra
   key: ahí se olvida todo. */

const vacia = () => ({ clave: null, scroll: {}, tablas: {} });
let memoria = vacia();

/* Al montar Inventario: si es otra entrada del historial, se empieza de cero.
   Se puede llamar más de una vez (StrictMode): siempre da lo mismo. */
export function entrarAlModulo(clave) {
  if (memoria.clave !== clave) memoria = { ...vacia(), clave };
}

/* Ya adentro, cambiar de tabla (?vista=) reemplaza la entrada del historial
   y le da otra key: la memoria la sigue, sin olvidar nada. */
export function seguirClave(clave) {
  memoria.clave = clave;
}

/* Lo que está elegido en una tabla ({buscar, orden...}), para leerlo desde
   otra página (↑/↓ en la ficha de un rollo). */
export const recordado = (tabla) => memoria.tablas[tabla] || {};

/* Un useState que además queda guardado para la vuelta. `tabla`: "rollos" o
   "materiales"; `campo`: "buscar", "orden"... */
export function useRecordado(tabla, campo, inicial) {
  const guardar = (v) => { memoria.tablas[tabla] = { ...memoria.tablas[tabla], [campo]: v }; return v; };
  // El inicial también queda guardado: es lo que se ve (ver `recordado`).
  const [valor, setValor] = useState(() => guardar(memoria.tablas[tabla]?.[campo] ?? inicial));
  const fijar = (nuevo) => setValor((anterior) => guardar(typeof nuevo === "function" ? nuevo(anterior) : nuevo));
  return [valor, fijar];
}

/* El scroll de la página del módulo (.modulo-contenido, ver
   components/CuerpoModulo) mientras se ve esta tabla. Se restaura al montarla,
   antes de pintar: sus filas ya están, así que la lista tiene su alto. */
export function useScrollRecordado(tabla, ref) {
  useLayoutEffect(() => {
    const caja = ref.current?.closest(".modulo-contenido");
    if (!caja) return;
    caja.scrollTop = memoria.scroll[tabla] ?? 0;
    const guardar = () => { memoria.scroll[tabla] = caja.scrollTop; };
    caja.addEventListener("scroll", guardar, { passive: true });
    return () => caja.removeEventListener("scroll", guardar);
  }, [tabla, ref]);
}
