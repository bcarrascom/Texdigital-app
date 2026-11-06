import { useLayoutEffect, useRef } from "react";
import { useCarrusel } from "@/hooks/useCarrusel";
import Etiqueta from "@/components/Etiqueta/Etiqueta";
import VisorProducto from "@/components/VisorProducto/VisorProducto";
import * as fmt from "@/utils/formato";
import "./Detalle.css";

/* Piezas de las pantallas de detalle — ver-cotización y ver-OP, que son la
   MISMA cotización mirada del lado comercial o del de producción. La página
   pone la clase "pag-detalle" (más la suya) y arma:

       <VistaDetalle productos={cot.productos} aparecer
                     hoja={<section className="hoja">...</section>}
                     lateral={<Plata t={...} />}
                     pieFicha={(p) => <span>Total</span>} />

     hoja       la hoja de datos de arriba a la izquierda
     lateral    lo que va en el panel derecho debajo del visor (la plata en
                la cotización, la logística en la OP)
     pieFicha   (producto, índice) → pie de cada ficha (opcional: la OP no lleva)
     aparecer   las fichas aparecen en escalón (solo la primera que se abre;
                las que llegan de costado con ←/→ entran ya armadas)

   Cada vista tiene su propio carrusel del visor: mirar una ficha (mouse o
   foco) lo congela en ese producto. */
export function VistaDetalle({ productos, hoja, lateral, pieFicha, aparecer = true }) {
  const carrusel = useCarrusel(productos.length);
  const refLateral = useRef(null);
  useLateralSinScroll(refLateral);
  return (
    <div className="vista" data-sin-aparecer={aparecer ? undefined : ""}>
      <div className="vista__izq">
        {hoja}
        <section>
          <h2 className="seccion-titulo">Productos · {productos.length}</h2>
          <div className="productos">
            {productos.map((p, i) => (
              <FichaProducto key={i} p={p} i={i} mirando={i === carrusel.indice} pie={pieFicha?.(p, i)}
                             onMirar={() => carrusel.mirar(i)} onSoltar={carrusel.soltar} />
            ))}
          </div>
        </section>
      </div>

      <aside className="vista__der">
        <div className="lateral" ref={refLateral}>
          <VisorProducto producto={productos[carrusel.indice]} indice={carrusel.indice} total={productos.length} />
          {lateral}
        </div>
      </aside>
    </div>
  );
}

/* La tarjeta lateral nunca scrollea por dentro (pedido de Bruno, 2026-11-06).
   Si cabe en la ventana, se pega arriba (top 0). Si es más alta —con los
   desgloses de la plata abiertos—, se pega con un top negativo de lo que
   sobra: baja con la página hasta que se ve su final, y ahí se queda. Así,
   scrolleando la página se llega a los dos extremos. Se vuelve a medir cada
   vez que la tarjeta o la ventana cambian de alto. */
function useLateralSinScroll(ref) {
  useLayoutEffect(() => {
    const el = ref.current;
    const scroller = el?.closest(".contenido");
    if (!el || !scroller) return undefined;
    const medir = () => {
      // La vista va con `zoom`: lo medido sale escalado, el `top` se escribe sin escalar.
      const zoom = parseFloat(getComputedStyle(el.closest(".vista") || el).zoom) || 1;
      const cs = getComputedStyle(scroller);
      const visible = scroller.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      const sobra = el.getBoundingClientRect().height - visible;
      el.style.setProperty("--lateral-top", sobra > 0 ? `${-sobra / zoom}px` : "0px");
    };
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    ro.observe(scroller);
    medir();
    return () => ro.disconnect();
  }, [ref]);
}

/* La grilla de datos de la hoja (etiqueta chica arriba, valor abajo). Los
   vacíos no aparecen: un "—" ahí es ruido, no información.

       <Datos lista={[["Empresa", cot.empresa], ["RUT", cot.rut, { mono: true }],
                      ["Descripción", cot.descripcion, { ancho: true }]]} />
   `children` se agrega al final (p. ej. un dato editable). */
export function Datos({ lista, children }) {
  return (
    <div className="datos">
      {lista.filter(([, val]) => val || val === 0).map(([et, val, { mono, ancho } = {}]) => (
        <Dato key={et} etiqueta={et} mono={mono} ancho={ancho}>{val}</Dato>
      ))}
      {children}
    </div>
  );
}

export function Dato({ etiqueta, mono, ancho, children }) {
  return (
    <div className={`dato${ancho ? " dato--ancho" : ""}`}>
      <span className="dato__et">{etiqueta}</span>
      <span className={`dato__val${mono ? " dato__val--mono" : ""}`}>{children}</span>
    </div>
  );
}

/* ── Ficha de producto ────────────────────────────────────────────────────
   El JSON guardado NO trae lo mismo en los dos tipos: backlight trae Tela +
   Caja, el estándar trae producto + Estructuras + Terminaciones + Impresión
   (ver _producto_a_json_pantalla en ui/api_ver_cotizacion.py y api_ver_op.py). */
function FichaProducto({ p, i, mirando, pie, onMirar, onSoltar }) {
  const bl = p.tipo === "backlight";
  /* El textil y el tema van como texto bajo el nombre, no como píldoras
     (pedido de Bruno, 2026-11-06): son lo que identifica al producto. En
     backlight el nombre ya es la tela. */
  const textil = bl ? "" : p.textil || p.tela;
  const etiquetas = [
    ...(bl
      ? [p.caja && p.caja !== "Sin caja" ? p.caja : "Sin caja"]
      : [p.impresion, ...(p.estructuras || []), ...(p.terminaciones || [])]),
    p.obs && "Obs: " + p.obs,
  ].filter(Boolean);

  return (
    <article className="ficha-prod" style={{ "--i": i }} data-mirando={mirando || undefined}
             onMouseEnter={onMirar} onMouseLeave={onSoltar} onFocus={onMirar} onBlur={onSoltar}>
      <div className="ficha-prod__cab">
        <span className="ficha-prod__n">{i + 1}.</span>
        <div className="ficha-prod__titulos">
          <span className="ficha-prod__nombre">{bl ? p.tela || "Backlight" : p.producto || "—"}</span>
          {textil && <span className="ficha-prod__textil">{textil}</span>}
          {p.tema && <span className="ficha-prod__tema">Tema: {p.tema}</span>}
        </div>
      </div>
      <span className="ficha-prod__tipo">
        <Etiqueta tipo={bl ? "neutra" : "tema"}>{bl ? "Backlight" : "Estándar"}</Etiqueta>
      </span>
      <div className="ficha-prod__linea">
        <span>Medidas</span><b>{fmt.medida(fmt.aNumero(p.ancho))} × {fmt.medida(fmt.aNumero(p.alto))} m</b>
      </div>
      <div className="ficha-prod__linea"><span>Cantidad</span><b>{parseInt(p.cantidad, 10) || 0}</b></div>
      <div className="ficha-prod__linea">
        <span>Superficie</span>
        <b>{p.ml != null ? `${fmt.cantidad(p.ml)} ML` : p.m2 != null ? `${fmt.cantidad(p.m2)} M²` : "—"}</b>
      </div>
      <div className="ficha-prod__etiquetas">
        {etiquetas.map((e, k) => <Etiqueta key={k}>{e}</Etiqueta>)}
      </div>
      {pie && <div className="ficha-prod__pie">{pie}</div>}
    </article>
  );
}
