import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router";

/* "← Volver": un paso atrás en el historial de React Router — reemplaza a
   la pila de navegación que tenía ApiApp en Python. Si la página se abrió
   sin historial previo (p. ej. después de un Ctrl+R), va al inicio. */
export function useVolver() {
  const navigate = useNavigate();
  const location = useLocation();
  return useCallback(() => {
    if (location.key === "default") navigate("/", { replace: true });
    else navigate(-1);
  }, [navigate, location.key]);
}
