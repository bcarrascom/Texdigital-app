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
     pieFicha   (producto) → pie de cada ficha (opcional: la OP no lleva)
     aparecer   las fichas aparecen en escalón (solo la primera que se abre;
                las que llegan de costado con ←/→ entran ya armadas)

   Cada vista tiene su propio carrusel del visor: mirar una ficha (mouse o
   foco) lo congela en ese producto. */
export function VistaDetalle({ productos, hoja, lateral, pieFicha, aparecer = true }) {
  const carrusel = useCarrusel(productos.length);
  return (
    <div className="vista" data-sin-aparecer={aparecer ? undefined : ""}>
      <div className="vista__izq">
        {hoja}
        <section>
          <h2 className="seccion-titulo">Productos · {productos.length}</h2>
          <div className="productos">
            {productos.map((p, i) => (
              <FichaProducto key={i} p={p} i={i} mirando={i === carrusel.indice} pie={pieFicha?.(p)}
                             onMirar={() => carrusel.mirar(i)} onSoltar={carrusel.soltar} />
            ))}
          </div>
        </section>
      </div>

      <aside className="vista__der">
        <div className="lateral">
          <VisorProducto producto={productos[carrusel.indice]} indice={carrusel.indice} total={productos.length} />
          {lateral}
        </div>
      </aside>
    </div>
  );
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
  const etiquetas = [
    p.tema && "Tema: " + p.tema,
    ...(bl
      ? [p.caja && p.caja !== "Sin caja" ? p.caja : "Sin caja"]
      : [p.textil || p.tela, p.impresion, ...(p.estructuras || []), ...(p.terminaciones || [])]),
    p.obs && "Obs: " + p.obs,
  ].filter(Boolean);

  return (
    <article className="ficha-prod" style={{ "--i": i }} data-mirando={mirando || undefined}
             onMouseEnter={onMirar} onMouseLeave={onSoltar} onFocus={onMirar} onBlur={onSoltar}>
      <div className="ficha-prod__cab">
        <span className="ficha-prod__n">{i + 1}.</span>
        <span className="ficha-prod__nombre">{bl ? p.tela || "Backlight" : p.producto || "—"}</span>
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
