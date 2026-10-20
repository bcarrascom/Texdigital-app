import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router";
import { AnimatePresence } from "motion/react";
import { api } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { useVolver } from "@/hooks/useVolver";

import Menu from "@/pages/Menu/Menu";
import Cotizaciones from "@/pages/Cotizaciones/Cotizaciones";
import IndiceDesarrollo from "@/pages/IndiceDesarrollo/IndiceDesarrollo";
import PendienteMigrar from "@/pages/PendienteMigrar/PendienteMigrar";
import VerCotizacion from "@/pages/VerCotizacion/VerCotizacion";
import VerDespacho from "@/pages/VerDespacho/VerDespacho";

/* Rutas que, entre sí, son la MISMA página: pasar de una a otra no desmonta
   la página (no hay transición del router), la página anima su propio
   contenido. Es lo que permite el slide entre cotizaciones con ←/→, donde
   la vieja y la nueva tienen que estar montadas al mismo tiempo. */
const MISMA_PAGINA = [/^\/cotizaciones\/\d+$/];

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

        {/* Módulos */}
        <Route path="/inventario" element={
          <RequiereModulo clave="inventario"><PendienteMigrar tema="inventario" titulo="Inventario" /></RequiereModulo>} />
        <Route path="/cotizaciones" element={
          <RequiereModulo clave="cotizaciones"><Cotizaciones /></RequiereModulo>} />
        <Route path="/ops" element={
          <RequiereModulo clave="ops"><PendienteMigrar tema="ops" titulo="Órdenes de Producción" /></RequiereModulo>} />
        <Route path="/despachos" element={
          <RequiereModulo clave="despachos"><PendienteMigrar tema="despachos" titulo="Despachos" /></RequiereModulo>} />

        <Route path="/cotizaciones/:numero" element={<VerCotizacion />} />
        <Route path="/despachos/:numero" element={<VerDespacho />} />
        <Route path="*" element={<PendienteMigrar />} />
      </Routes>
    </AnimatePresence>
  );
}

/* Un módulo apagado en core/config.py::MODULOS_HABILITADOS (típicamente uno
   sin terminar al sacar un release) no se abre ni llegando por URL: vuelve
   al menú. Un dato que no llegó nunca apaga un módulo (`!== false`). */
function RequiereModulo({ clave, children }) {
  const { contexto } = useApp();
  if (contexto.modulos_habilitados?.[clave] === false) return <Navigate to="/" replace />;
  return children;
}
