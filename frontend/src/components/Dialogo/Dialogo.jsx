import { useEffect, useRef } from "react";
import "./Dialogo.css";

/* Diálogo modal sobre <dialog> nativo (showModal): el navegador ya se
   encarga del fondo, del foco y de Escape.

       <Dialogo abierto={abierto} onCerrar={() => setAbierto(false)}
                onConfirmar={eliminar}>
         <h2 className="dlg__titulo">¿Eliminar?</h2>
         ...
       </Dialogo>

   Enter confirma (fuera de un <textarea>), pero solo si `puedeConfirmar` —
   misma regla que tenían los diálogos de las pantallas viejas. Con un
   diálogo abierto, los atajos de la página no corren (ver useAtajo).
   Un hijo con el atributo data-autofoco recibe el foco al abrirse. */
export default function Dialogo({ abierto, onCerrar, onConfirmar, puedeConfirmar = true, className, children }) {
  const ref = useRef(null);

  useEffect(() => {
    const dlg = ref.current;
    if (abierto && !dlg.open) {
      dlg.showModal();
      // El campo marcado con data-autofoco se lleva el foco al abrir.
      dlg.querySelector("[data-autofoco]")?.focus();
    } else if (!abierto && dlg.open) dlg.close();
  }, [abierto]);

  return (
    <dialog
      ref={ref}
      className={className}
      // Escape: el navegador lo cerraría por su cuenta y el estado de React
      // quedaría diciendo "abierto". Se cancela y se cierra por el estado.
      onCancel={(e) => { e.preventDefault(); onCerrar(); }}
      onKeyDown={(e) => {
        if (e.key !== "Enter" || e.target.tagName === "TEXTAREA") return;
        if (onConfirmar && puedeConfirmar) {
          e.preventDefault();
          onConfirmar();
        }
      }}
    >
      {abierto && children}
    </dialog>
  );
}
