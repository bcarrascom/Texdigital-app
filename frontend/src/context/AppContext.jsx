import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, enMock } from "@/services/api";
import { useAtajo } from "@/hooks/useAtajo";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";

/* Contexto común de la app (versión, módulos habilitados, fecha de hoy,
   etc. — ver ApiApp.obtener_contexto en ui/api_app.py), pedido UNA vez al
   arrancar en vez de en cada pantalla, más la escala de texto A− / A+. */

const AppContext = createContext(null);

/* La palanca del usuario contra las pantallas chicas de alta resolución. Se
   guarda en Python (guardar_preferencia), no en localStorage: así sobrevive
   a reinstalaciones y la comparten todas las ventanas. */
const PASOS = [0.85, 0.925, 1, 1.1, 1.25, 1.4, 1.6];
const indiceDe = (valor) => {
  const i = PASOS.indexOf(valor);
  return i >= 0 ? i : PASOS.indexOf(1);
};

export function AppProvider({ children }) {
  const aviso = useAvisos();
  const [contexto, setContexto] = useState(null);
  const [iEscala, setIEscala] = useState(PASOS.indexOf(1));

  useEffect(() => {
    api.obtener_contexto()
      .then((ctx) => {
        setContexto(ctx || {});
        setIEscala(indiceDe(ctx?.escala_ui ?? 1));
      })
      .catch((err) => {
        console.error(err);
        aviso("Error al iniciar la app: " + err.message, "error", 8000);
        setContexto({});
      });
  }, [aviso]);

  useEffect(() => {
    document.documentElement.style.setProperty("--ui-escala", PASOS[iEscala]);
  }, [iEscala]);

  const moverEscala = useCallback((delta) => {
    setIEscala((i) => {
      const nuevo = Math.min(PASOS.length - 1, Math.max(0, i + delta));
      if (nuevo !== i) api.guardar_preferencia("escala_ui", PASOS[nuevo]);
      return nuevo;
    });
  }, []);

  useAtajo("mod++", () => moverEscala(1));
  useAtajo("mod+-", () => moverEscala(-1));
  // pywebview no tiene recarga nativa (no hay barra de navegador): Ctrl+R
  // vuelve a levantar la app con el código fresco del disco.
  useAtajo("mod+r", () => location.reload());

  if (!contexto) return <Cargando />;

  const valor = {
    contexto,
    escala: {
      valor: PASOS[iEscala],
      puedeAchicar: iEscala > 0,
      puedeAgrandar: iEscala < PASOS.length - 1,
      mover: moverEscala,
    },
  };
  return (
    <AppContext.Provider value={valor}>
      {children}
      {enMock() && <div className="marca-mock">modo diseño · datos de prueba</div>}
    </AppContext.Provider>
  );
}

export function useApp() {
  const valor = useContext(AppContext);
  if (!valor) throw new Error("useApp() fuera de <AppProvider>");
  return valor;
}
