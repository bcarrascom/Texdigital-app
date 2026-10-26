import { createContext, useContext, useEffect } from "react";

/* Los cambios sin guardar de la página de Configuración abierta (pedido de
   Bruno, 2026-10-26): antes de salir —Volver, Escape, la X de la ventana u
   otra categoría— Configuración pregunta si guardarlos, listándolos todos
   (ver DialogoSalir en Configuracion.jsx).

   Cada página que se edita entera y se guarda con la barra de abajo avisa
   lo suyo en cada render:

       useCambiosPendientes({
         cambios: ["IVA: 19 % → 21 %", ...],   ← vacío: no hay nada pendiente
         error: null | "por qué no se puede guardar",
         guardar: async () => true | false,    ← true si guardó
       });
*/
export const CambiosPendientes = createContext(() => {});

export function useCambiosPendientes({ cambios, error, guardar }) {
  const registrar = useContext(CambiosPendientes);
  const clave = JSON.stringify([cambios, error]);
  useEffect(() => {
    registrar(cambios.length ? { cambios, error, guardar } : null);
  }, [clave, guardar]);
  // Al salir de la página, ya no hay nada pendiente suyo.
  useEffect(() => () => registrar(null), []);
}

/* "$11.000" / "sin valor": un monto para la lista de cambios. */
export const montoOVacio = (texto) => (texto ? texto : "sin valor");
