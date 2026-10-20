import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

/* Avisos flotantes (esquina inferior derecha).

       const aviso = useAvisos();
       aviso("Guía 123 generada.");                 // tipo "info", 3,5 s
       aviso("No se pudo guardar.", "error", 8000);

   Python también los dispara (ApiApp._aviso → window.TD.aviso). */

const AvisosContext = createContext(null);

export function AvisosProvider({ children }) {
  const [avisos, setAvisos] = useState([]);
  const siguienteId = useRef(0);

  const aviso = useCallback((texto, tipo = "info", ms = 3500) => {
    const id = siguienteId.current++;
    setAvisos((lista) => [...lista, { id, texto, tipo }]);
    setTimeout(() => setAvisos((lista) => lista.filter((a) => a.id !== id)), ms);
  }, []);

  useEffect(() => {
    window.TD = window.TD || {};
    window.TD.aviso = aviso;
  }, [aviso]);

  return (
    <AvisosContext.Provider value={aviso}>
      {children}
      <div className="pila-avisos">
        <AnimatePresence>
          {avisos.map((a) => (
            <motion.div
              key={a.id}
              layout
              className={`aviso aviso--${a.tipo}`}
              role={a.tipo === "error" ? "alert" : "status"}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: 24 }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            >
              {a.texto}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </AvisosContext.Provider>
  );
}

export function useAvisos() {
  const aviso = useContext(AvisosContext);
  if (!aviso) throw new Error("useAvisos() fuera de <AvisosProvider>");
  return aviso;
}
