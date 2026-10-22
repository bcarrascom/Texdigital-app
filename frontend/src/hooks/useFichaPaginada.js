import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { useAtajo } from "@/hooks/useAtajo";

/* Una ficha (cotización, OP, ...) por número de ruta, con ←/→ para pasar a la
   vecina. La pasada REEMPLAZA la entrada del historial: "Volver" desde
   cualquiera de ellas vuelve adonde se entró, no retrocede de a una. Los
   datos de la vecina se piden ANTES de navegar, así el slide (components/
   Pista) arranca con la ficha ya llena.

       const { ficha, direccion, deslizando, alTerminarSlide, actualizar } =
         useFichaPaginada({ numero, cargar: cargarOp, adyacente: api.op_adyacente, ruta: rutas.verOp });

     ficha       undefined mientras carga · null si no existe · el objeto
     direccion   1 / -1: por qué lado entra la nueva (para la Pista)
     deslizando  true durante el paso (para bloquear botones)
     actualizar  (fn) cambia la ficha actual en el lugar (p. ej. tras
                 guardar algo de ella), sin volver a pedirla

   La página tiene que estar en MISMA_PAGINA (router/RutasAnimadas.jsx) para
   que el router no la desmonte al cambiar de número. */
export function useFichaPaginada({ numero, cargar, adyacente, ruta }) {
  const navigate = useNavigate();
  const location = useLocation();
  const cache = useRef(new Map());   // número → ficha ya pedida
  const [ficha, setFicha] = useState(undefined);
  const [deslizando, setDeslizando] = useState(false);
  const pidiendo = useRef(false);

  useEffect(() => {
    if (cache.current.has(numero)) {
      setFicha(cache.current.get(numero));
      return;
    }
    let vigente = true;
    cargar(numero).then((f) => {
      cache.current.set(numero, f);
      if (vigente) setFicha(f);
    });
    return () => { vigente = false; };
  }, [numero]);  // `cargar` es estable por pantalla

  async function paginar(sentido) {
    if (deslizando || pidiendo.current || !ficha) return;  // una a la vez
    pidiendo.current = true;
    try {
      const vecina = await adyacente(numero, sentido);
      if (vecina == null || vecina === numero) return;
      if (!cache.current.has(vecina)) cache.current.set(vecina, await cargar(vecina));
      setDeslizando(true);
      navigate(ruta(vecina), {
        replace: true,
        state: { ...location.state, deslizar: sentido === "siguiente" ? 1 : -1 },
      });
    } finally {
      pidiendo.current = false;
    }
  }
  useAtajo("arrowleft", () => paginar("anterior"));
  useAtajo("arrowright", () => paginar("siguiente"));

  const actualizar = useCallback((fn) => {
    setFicha((f) => {
      if (!f) return f;
      const nueva = fn(f);
      cache.current.set(numero, nueva);
      return nueva;
    });
  }, [numero]);

  return {
    ficha,
    direccion: location.state?.deslizar ?? 1,
    deslizando,
    alTerminarSlide: () => setDeslizando(false),
    actualizar,
  };
}
