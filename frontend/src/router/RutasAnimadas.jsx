import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router";
import { AnimatePresence } from "motion/react";
import { api } from "@/services/api";
import { useVolver } from "@/hooks/useVolver";

import Inicio from "@/pages/Inicio/Inicio";
import PendienteMigrar from "@/pages/PendienteMigrar/PendienteMigrar";
import VerDespacho from "@/pages/VerDespacho/VerDespacho";

/* Las rutas, con transición entre páginas: <AnimatePresence mode="wait">
   deja que la página que se va termine su animación de salida (ver
   components/Pagina) antes de montar la que llega. El `key` por pathname
   es lo que le hace notar que cambió de página. */
export default function RutasAnimadas() {
  const location = useLocation();
  const volver = useVolver();

  // La X nativa de la ventana: Python pregunta en qué ruta estamos para
  // decidir entre cerrar la app o volver (ver ApiApp._al_cerrar_nativo).
  useEffect(() => { api.notificar_ruta(location.pathname); }, [location.pathname]);
  useEffect(() => {
    window.TD = window.TD || {};
    window.TD.volver = volver;
  }, [volver]);

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Inicio />} />
        <Route path="/despachos/:numero" element={<VerDespacho />} />
        <Route path="*" element={<PendienteMigrar />} />
      </Routes>
    </AnimatePresence>
  );
}
