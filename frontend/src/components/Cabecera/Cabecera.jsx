import { api } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { useAtajo } from "@/hooks/useAtajo";
import { useVolver } from "@/hooks/useVolver";

/* Cabecera de las pantallas internas (el menú principal no la usa):
   ← Volver · título · [lo que la página agregue] · A− 100% A+ · ?

       <Cabecera titulo="Despacho OP 0042" />
       <Cabecera titulo="..." onVolver={confirmarYSalir}>
         <button className="cab-btn">Extra</button>
       </Cabecera>

   Escape hace lo mismo que el botón Volver. */
export default function Cabecera({ titulo, onVolver, children }) {
  const volverAtras = useVolver();
  const volver = onVolver || volverAtras;
  useAtajo("escape", volver);

  return (
    <header className="cabecera">
      <button className="cab-btn cab-btn--fantasma" onClick={volver}>← Volver</button>
      <span className="cabecera__titulo">{titulo}</span>
      <span className="cabecera__sep" />
      {children}
      <ControlTexto />
      <button className="cab-btn cab-btn--icono" title="Manual de uso" onClick={() => api.abrir_manual()}>
        ?
      </button>
    </header>
  );
}

export function ControlTexto() {
  const { escala } = useApp();
  return (
    <div className="ctrl-texto" title="Tamaño del texto (Ctrl + / Ctrl −)">
      <button className="cab-btn" aria-label="Achicar texto"
              disabled={!escala.puedeAchicar} onClick={() => escala.mover(-1)}>A−</button>
      <span className="ctrl-texto__valor">{Math.round(escala.valor * 100)}%</span>
      <button className="cab-btn" aria-label="Agrandar texto"
              disabled={!escala.puedeAgrandar} onClick={() => escala.mover(1)}>A+</button>
    </div>
  );
}
