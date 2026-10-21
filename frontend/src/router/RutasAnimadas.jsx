import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router";
import { AnimatePresence } from "motion/react";
import { api } from "@/services/api";
import { useVolver } from "@/hooks/useVolver";
import { MODULOS } from "@/router/rutas";

import Menu from "@/pages/Menu/Menu";
import Modulos from "@/pages/Modulos/Modulos";
import IndiceDesarrollo from "@/pages/IndiceDesarrollo/IndiceDesarrollo";
import PendienteMigrar from "@/pages/PendienteMigrar/PendienteMigrar";
import NuevaCotizacion from "@/pages/NuevaCotizacion/NuevaCotizacion";
import VerCotizacion from "@/pages/VerCotizacion/VerCotizacion";
import VerDespacho from "@/pages/VerDespacho/VerDespacho";

/* Rutas que, entre sí, son la MISMA página: pasar de una a otra no desmonta
   la página (no hay transición del router), la página anima su propio
   contenido. Es lo que permite los slides con ←/→ (components/Pista), donde
   la vieja y la nueva tienen que estar montadas al mismo tiempo. */
const MISMA_PAGINA = [
  /^\/cotizaciones\/\d+$/,                      // entre cotizaciones (VerCotizacion)
  /^\/(inventario|cotizaciones|ops|despachos)$/,  // entre módulos (Modulos)
];

/* Las rutas, con transición entre páginas: <AnimatePresence mode="wait">
   deja que la página que se va termine su animación de salida (ver
   components/Pagina) antes de montar la que llega. El `key` por pathname
   es lo que le hace notar que cambió de página. */
export default function RutasAnimadas() {
  const location = useLocation();
  const clave = MISMA_PAGINA.find((patron) => patron.test(location.pathname))?.source ?? location.pathname;
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
      <Routes location={location} key={clave}>
        <Route path="/" element={<Menu />} />
        <Route path="/dev" element={<IndiceDesarrollo />} />

        {/* Módulos: una sola página para los cuatro (ver pages/Modulos) */}
        {MODULOS.map((m) => <Route key={m.clave} path={`/${m.clave}`} element={<Modulos />} />)}

        <Route path="/cotizaciones/nueva" element={<NuevaCotizacion />} />
        <Route path="/cotizaciones/:numero/editar" element={<NuevaCotizacion modo="editar" />} />
        <Route path="/cotizaciones/pendientes/:id" element={<NuevaCotizacion modo="pendiente" />} />
        <Route path="/cotizaciones/:numero" element={<VerCotizacion />} />
        <Route path="/despachos/:numero" element={<VerDespacho />} />
        <Route path="*" element={<PendienteMigrar />} />
      </Routes>
    </AnimatePresence>
  );
}
