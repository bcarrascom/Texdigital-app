import { useCallback, useState } from "react";
import { createPortal } from "react-dom";
import IconoAbierta from "@/assets/svg/package-open.svg?react";
import IconoCerrada from "@/assets/svg/package.svg?react";
import "./CajaEnvio.css";

/* La animación de "Entregado": una caja fija en el borde derecho de la
   ventana aparece abierta, se cierra y se desliza fuera de la ventana. Va en
   un portal a <body>: dentro de la página, cualquier ancestro con transform
   (la transición entre páginas, el slide entre módulos) haría que
   position:fixed se mida contra él y no contra la ventana.

       const [caja, animarEnvio] = useCajaEnvio();
       await animarEnvio();      // resuelve cuando la caja ya salió
       ...
       return <>{...}{caja}</>;

   Tiempos (de la pantalla vieja): a los 550 ms arranca el cierre (dura
   --m-media, 280 ms), 300 ms de pausa, y la salida dura --m-lenta (560 ms). */
const CIERRE = 550, SALIDA = 1130, FIN = 1690;

export function useCajaEnvio() {
  const [fase, setFase] = useState(null);   // null | "montada" | "abierta" | "cerrada" | "salir"

  const animar = useCallback(() => new Promise((resolve) => {
    setFase("montada");
    // Dos cuadros: el primero la monta invisible, el segundo dispara el fade-in.
    requestAnimationFrame(() => requestAnimationFrame(() => setFase("abierta")));
    setTimeout(() => setFase("cerrada"), CIERRE);
    setTimeout(() => setFase("salir"), SALIDA);
    setTimeout(() => { setFase(null); resolve(); }, FIN);
  }), []);

  const caja = fase && createPortal(
    <div className="caja-envio" aria-hidden="true"
         data-mostrar={fase !== "montada" || undefined}
         data-cerrada={fase === "cerrada" || fase === "salir" || undefined}
         data-salir={fase === "salir" || undefined}>
      <div className="caja-envio__icono">
        <IconoAbierta className="icono-caja icono-caja--abierta" />
        <IconoCerrada className="icono-caja icono-caja--cerrada" />
      </div>
    </div>,
    document.body,
  );

  return [caja, animar];
}
