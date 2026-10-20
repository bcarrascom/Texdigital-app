import { useCallback, useEffect, useRef, useState } from "react";

/* Un índice que va pasando solo de 0 a n−1 (con vuelta), y que se congela
   mientras el usuario mira algo puntual.

       const { indice, mirar, soltar } = useCarrusel(productos.length);
       <Ficha onMouseEnter={() => mirar(i)} onMouseLeave={soltar} />

   Al soltar, el ciclo se retoma recién después de `reanudarMs`: si se
   retomara al instante, pasar el mouse por encima de camino a otra cosa
   haría saltar el carrusel. Con "reducir movimiento" no avanza solo. */
export function useCarrusel(n, { cicloMs = 5200, reanudarMs = 3000 } = {}) {
  const [indice, setIndice] = useState(0);
  const [pausado, setPausado] = useState(false);
  const reanudar = useRef(null);

  useEffect(() => {
    if (pausado || n < 2) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const t = setInterval(() => setIndice((i) => (i + 1) % n), cicloMs);
    return () => clearInterval(t);
  }, [pausado, n, cicloMs]);

  useEffect(() => () => clearTimeout(reanudar.current), []);

  const mirar = useCallback((i) => {
    clearTimeout(reanudar.current);
    setPausado(true);
    setIndice(i);
  }, []);

  const soltar = useCallback(() => {
    clearTimeout(reanudar.current);
    reanudar.current = setTimeout(() => setPausado(false), reanudarMs);
  }, [reanudarMs]);

  return { indice: n ? indice % n : 0, mirar, soltar };
}
