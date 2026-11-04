import Campo from "@/components/Campo/Campo";
import "./CampoTextil.css";

/* El textil de un rollo ("Rollo nuevo" y "Editar rollo"). Pedido de Bruno
   (2026-11-04): se escribe, con autocompletado de los textiles de
   Configuración, en vez de buscarlo en una lista de cien. Si lo escrito no es
   ninguno, se destaca "Textil nuevo": un atajo al diálogo de agregar textil
   de Configuración, con ese nombre ya puesto (ver Inventario.jsx). */

/* Sin tildes ni mayúsculas, para reconocer "lona rustica" como "Lona rústica". */
const clave = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toLowerCase();

/* El textil del catálogo que es `texto`, o null. Primero el idéntico: "Gasa
   rustica" y una "Gasa rústica" podrían ser dos textiles distintos. */
export function textilDe(textiles, texto) {
  const t = (texto || "").trim();
  if (!t) return null;
  return textiles.find((x) => x === t) || textiles.find((x) => x.toLowerCase() === t.toLowerCase())
    || textiles.find((x) => clave(x) === clave(t)) || null;
}

/* `error`: el texto de abajo cuando `invalido` (por defecto, "Obligatorio"). */
export default function CampoTextil({ id, textiles, valor, onCambiar, onNuevo, invalido, error, autofoco }) {
  const existente = textilDe(textiles, valor);
  const nuevo = !!valor.trim() && !existente;
  return (
    <Campo id={id} etiqueta="Textil" requerido invalido={invalido} error={error}>
      <div className="campo-textil">
        <input className="entrada" id={id} type="text" list={`${id}-lista`} autoComplete="off" data-autofoco={autofoco || undefined}
               placeholder="Escribe para buscar…" value={valor} onChange={(e) => onCambiar(e.target.value)}
               // "lona rustica" queda escrito como en Configuración.
               onBlur={() => existente && existente !== valor && onCambiar(existente)} />
        <button className={`btn btn--chico campo-textil__nuevo ${nuevo ? "btn--primario" : "btn--secundario"}`} type="button"
                title={nuevo ? `Agregar «${valor.trim()}» a Configuración › Textiles` : "Agregar un textil a Configuración › Textiles"}
                onClick={() => onNuevo(nuevo ? valor.trim() : "")}>
          Textil nuevo
        </button>
      </div>
      <datalist id={`${id}-lista`}>
        {textiles.map((t) => <option key={t} value={t} />)}
      </datalist>
    </Campo>
  );
}
