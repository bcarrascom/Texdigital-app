import { useState } from "react";
import Dialogo from "@/components/Dialogo/Dialogo";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import * as fmt from "@/utils/formato";

/* Cuando los precios cambiaron desde que se hizo la cotización (ver
   core/lista_precios.py, "cambios_precios" de obtener_cotizacion): la
   cotización se sigue mostrando con SUS precios, y un aviso chico arriba de
   la hoja ofrece revisar qué cambió. El usuario decide: actualizarla a los
   precios de hoy o mantener los suyos (y no se vuelve a preguntar mientras
   los precios no cambien otra vez). */

export function AvisoPrecios({ onRevisar }) {
  return (
    <div className="aviso-precios" role="status">
      <IconoAviso className="aviso-precios__icono" aria-hidden="true" />
      <p className="aviso-precios__texto">Algunos componentes de esta cotización cambiaron de precio desde que se hizo.</p>
      <button className="btn btn--secundario btn--chico" type="button" onClick={onRevisar}>Revisar</button>
    </div>
  );
}

const valor = (c, v) => (v == null ? "sin precio" : c.formato === "metros" ? `${fmt.cantidad(v)}${c.unidad}` : `${fmt.pesos(v)}${c.unidad}`);

/* "+$4.500" / "−$1.200": cuánto sube o baja. */
const diferencia = (antes, ahora) => {
  const d = Math.round(ahora - antes);
  return d === 0 ? "" : `${d > 0 ? "+" : "−"}${fmt.pesos(Math.abs(d))}`;
};

export function DialogoPrecios({ abierto, cambios, onCerrar, onDecidir }) {
  const [enviando, setEnviando] = useState(false);
  async function decidir(actualizar) {
    setEnviando(true);
    try { await onDecidir(actualizar); } finally { setEnviando(false); }
  }

  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} className="dlg--desenfoque dlg-precios">
      {cambios && (
        <>
          <h2 className="dlg__titulo">Cambiaron precios</h2>
          <p className="dlg__texto">
            La cotización se sigue mostrando con los precios de cuando se hizo. Esto es lo que cambió desde entonces:
          </p>

          {cambios.componentes.length > 0 && (
            <table className="precios-tabla">
              <thead><tr><th>Componente</th><th className="num">Antes</th><th className="num">Hoy</th></tr></thead>
              <tbody>
                {cambios.componentes.map((c) => (
                  <tr key={`${c.tipo}-${c.nombre}`}>
                    <td><span className="precios-tabla__tipo">{c.tipo}</span>{c.nombre}</td>
                    <td className="num precios-tabla__antes">{valor(c, c.antes)}</td>
                    <td className="num">{valor(c, c.ahora)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3 className="precios-subtitulo">Con los precios de hoy</h3>
          <div className="precios-impacto">
            {cambios.productos.map((p) => (
              <div key={p.indice} className="precios-impacto__fila">
                <span>{p.nombre}</span>
                <span className="precios-impacto__montos">
                  {fmt.pesos(p.antes)} → <b>{fmt.pesos(p.ahora)}</b>
                  <em>{diferencia(p.antes, p.ahora)}</em>
                </span>
              </div>
            ))}
            <div className="precios-impacto__fila precios-impacto__fila--total">
              <span>Total con IVA</span>
              <span className="precios-impacto__montos">
                {fmt.pesos(cambios.total.antes)} → <b>{fmt.pesos(cambios.total.ahora)}</b>
                <em>{diferencia(cambios.total.antes, cambios.total.ahora)}</em>
              </span>
            </div>
          </div>

          <p className="dlg__texto precios-nota">
            Si la mantienes, no se vuelve a preguntar hasta que estos precios cambien otra vez.
          </p>
          <div className="dlg__acciones">
            <button className="btn btn--fantasma btn--chico" type="button" disabled={enviando} onClick={() => decidir(false)}>
              Mantener los de la cotización
            </button>
            <button className="btn btn--primario btn--chico" type="button" disabled={enviando} onClick={() => decidir(true)}>
              Actualizar a los precios de hoy
            </button>
          </div>
        </>
      )}
    </Dialogo>
  );
}
