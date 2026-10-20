import { HashRouter } from "react-router";
import { MotionConfig } from "motion/react";
import { AvisosProvider } from "@/context/AvisosContext";
import { AppProvider } from "@/context/AppContext";
import { ExpansionProvider } from "@/context/ExpansionContext";
import RutasAnimadas from "@/router/RutasAnimadas";

/* HashRouter (#/despachos/42) y no BrowserRouter: el servidor interno de
   pywebview solo sirve archivos, no sabe devolver index.html para una ruta
   que no existe en disco. El día que haya versión web con un servidor
   propio, se cambia por BrowserRouter acá y nada más. */
export default function App() {
  return (
    // reducedMotion="user": respeta "reducir movimiento" del sistema
    // operativo, igual que el @media de base.css.
    <MotionConfig reducedMotion="user">
      <HashRouter>
        <AvisosProvider>
          <AppProvider>
            <ExpansionProvider>
              <RutasAnimadas />
            </ExpansionProvider>
          </AppProvider>
        </AvisosProvider>
      </HashRouter>
    </MotionConfig>
  );
}
