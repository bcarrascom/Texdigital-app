/* Un campo de formulario con su etiqueta, su ayuda y su mensaje de
   "Obligatorio" (los estilos .campo están en base.css).

       <Campo id="dr-ancho" etiqueta="Ancho (m)" requerido invalido={errores.ancho}>
         <input className="entrada" id="dr-ancho" ... />
       </Campo>

   `error` cambia el texto de "Obligatorio" (p. ej. "Elegí un cliente de la lista"). */
export default function Campo({ id, etiqueta, requerido, invalido, ayuda, error = "Obligatorio", className = "", children }) {
  return (
    <div className={`campo ${className}`} data-invalido={invalido || undefined}>
      <label className="campo__etiqueta" htmlFor={id} data-requerido={requerido || undefined}>{etiqueta}</label>
      {children}
      {ayuda && <span className="campo__ayuda">{ayuda}</span>}
      {requerido && <span className="campo__error">{error}</span>}
    </div>
  );
}

/* Enter en cualquier campo intenta guardar — también en un <select>, que por
   sí solo no envía el formulario. Si falta algo, guardar() solo marca los
   campos en rojo: un Enter con el formulario a medias no guarda nada. */
export function enterGuarda(e) {
  if (e.key !== "Enter" || e.target.tagName === "TEXTAREA" || e.target.tagName === "BUTTON") return;
  e.preventDefault();
  e.currentTarget.requestSubmit();
}
