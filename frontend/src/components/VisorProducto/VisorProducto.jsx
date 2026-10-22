import { useEffect, useRef, useState } from "react";
import * as fmt from "@/utils/formato";
import "./VisorProducto.css";

/* La figura del producto que se está mirando (ver-cotización, ver-OP): su
   proporción, las cotas, las unidades y unos puntitos con cuál de todos es.
   La figura es una PROPORCIÓN, no una escala en metros: el lado largo
   siempre ocupa el alto disponible, igual que al crear el producto.

   Al pasar de un producto a otro el rectángulo se reacomoda con transición
   CSS (x/y/width/height) y su borde brilla mientras dura el cambio. */

const ALTO = 70;
// --m-visor (VisorProducto.css): 3 × --m-media
const DURACION_BRILLO_MS = 840;

export default function VisorProducto({ producto: p, indice, total }) {
  const [brillo, setBrillo] = useState(false);
  const primera = useRef(true);

  useEffect(() => {
    if (primera.current) { primera.current = false; return; }  // sin brillo al cargar
    setBrillo(true);
    const t = setTimeout(() => setBrillo(false), DURACION_BRILLO_MS);
    return () => clearTimeout(t);
  }, [indice]);

  if (!p) return null;
  const cant = parseInt(p.cantidad, 10) || 0;
  const ancho = fmt.aNumero(p.ancho), alto = fmt.aNumero(p.alto);
  const conMedidas = ancho > 0 && alto > 0;
  const largo = Math.max(ancho, alto), corto = Math.min(ancho, alto);
  const w = conMedidas ? ALTO * (corto / largo) : 60;

  return (
    <div className="visor">
      <div className="visor__cab">
        <span className="visor__n">{indice + 1}.</span>
        <span className="visor__tema">{p.tema || p.producto || p.tela || "Sin tema"}</span>
      </div>
      <div className="visor__marco">
        <svg viewBox="0 0 100 100" role="img" aria-label="Proporción del producto">
          <rect className={`visor__rect${brillo ? " visor__rect--brillo" : ""}`}
                x={50 - w / 2} y="15" width={w} height={ALTO} rx="2" />
          {/* Cotas en posición fija (no siguen al rectángulo): así el número
              nunca queda detrás del borde mientras dura la animación. */}
          <text className="visor__cota" x="50" y="10" textAnchor="middle">
            {conMedidas && `${fmt.medida(corto)} m`}
          </text>
          <text className="visor__cota" x="9" y="50" textAnchor="middle" transform="rotate(-90 9 50)">
            {conMedidas && `${fmt.medida(largo)} m`}
          </text>
        </svg>
      </div>
      <div className="visor__pie">
        <span className="visor__unidades">{cant} {cant === 1 ? "unidad" : "unidades"}</span>
        <span className="visor__puntos">
          {Array.from({ length: total }, (_, k) => (
            <span key={k} className="visor__punto" data-activo={k === indice || undefined} />
          ))}
        </span>
      </div>
    </div>
  );
}
