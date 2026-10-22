import { completo } from "./producto";

/* El índice del trabajo: un botón por producto (relleno suave si está
   completo, pleno el actual), "+" para agregar, y "Resumen". NO se mueve al
   cambiar de panel. */
export default function Mapa({ productos, actual, onIr, onAgregar }) {
  const hechos = productos.filter(completo).length;
  return (
    <nav className="mapa" aria-label="Productos de la cotización">
      {productos.map((p, i) => {
        const ok = completo(p);
        return (
          <button key={i} type="button" className="mapa__num" data-estado={ok ? "completo" : "vacio"}
                  aria-current={actual === i ? "true" : undefined}
                  title={`Producto ${i + 1} · ${ok ? "completo" : "incompleto"}`}
                  onClick={() => onIr(i)}>
            {i + 1}
          </button>
        );
      })}
      <button type="button" className="mapa__num mapa__num--mas" title="Agregar un producto" onClick={onAgregar}>+</button>
      <span className="mapa__sep" />
      <button type="button" className="mapa__num mapa__resumen"
              aria-current={actual === "resumen" ? "true" : undefined} onClick={() => onIr("resumen")}>
        Resumen
      </button>
      <span className="mapa__cuenta">{hechos} de {productos.length} completos</span>
    </nav>
  );
}
