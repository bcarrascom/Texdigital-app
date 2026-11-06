import { useState } from "react";
import { pct, textoRazon } from "@/components/Descuentos/Descuentos";
import * as fmt from "@/utils/formato";

/* Lo que baja y lo que sube el precio de cada producto (pedido de Bruno,
   2026-11-06): el descuento, "−20 % (volumen)", en rojo, y lo que suma
   cobrar el mínimo de un textil, "+19 % (cobro mínimo)", en verde. Corto a
   propósito: el usuario lo entiende una vez, y después un texto largo
   estorba. Todo viene armado de core.precios.explicar_descuento —ver
   ui/api_ver_cotizacion.py—, con las mismas reglas que calcularon el total:
   acá solo se muestra, no se calcula nada.

   Los descuentos se cambian desde acá mismo, sin entrar a Editar: clic en el
   de una ficha o en una línea del panel abre su diálogo
   (components/Descuentos).

     PieProducto   el pie de cada ficha
     PlataAjustes  la plata del panel derecho: solo las líneas que tienen
                   descuento o cobro mínimo */

/* Una línea de explicar_descuento en el formato que pide el diálogo. */
export const lineaParaDialogo = (linea, titulo) => ({
  titulo, precio: linea.precio, monto: linea.monto, manual: linea.manual, automatico: linea.automatico,
});

const textoDescuento = (d) => textoRazon(d.pct, d.razon);
const textoMinimo = (m) => `+${pct(m.pct)} (cobro mínimo)`;

export function PieProducto({ p, onEditar }) {
  const d = p.descuento || {};
  const conDescuento = d.monto > 0 || !!d.manual;
  const ajustado = conDescuento || d.minimo;
  return (
    <>
      {ajustado && <div className="pie-linea"><span>Precio</span><b>{fmt.pesos(d.precio - (d.minimo?.monto || 0))}</b></div>}
      {conDescuento ? (
        <button type="button" className="pie-linea pie-editable ajuste--descuento" onClick={onEditar}
                title="Cambiar el descuento">
          <span>{textoDescuento(d)}</span><b>− {fmt.pesos(d.monto)}</b>
        </button>
      ) : (
        <button type="button" className="pie-agregar" onClick={onEditar}>+ Descuento</button>
      )}
      {d.minimo && (
        <div className="pie-linea ajuste--minimo">
          <span>{textoMinimo(d.minimo)}</span><b>+ {fmt.pesos(d.minimo.monto)}</b>
        </div>
      )}
      <div className="pie-linea pie-linea--total">
        <span>Total</span><b>{fmt.pesos(ajustado ? d.total : p.total)}</b>
      </div>
    </>
  );
}

const Linea = ({ et, val, clase = "" }) => (
  <div className={`plata__linea ${clase}`}><span>{et}</span><b>{val}</b></div>
);

/* Cerrado, solo el total restado o sumado; apretando el título se abre con
   una línea por producto: el nombre y el monto, y debajo el % y la razón.
   Las de Descuentos se pueden apretar para cambiarlas. */
function Grupo({ titulo, tipo, total, items }) {
  const [abierto, setAbierto] = useState(false);
  if (!items.length) return null;
  const signo = tipo === "descuento" ? "−" : "+";
  /* El listado está siempre en el DOM y se abre animando su alto (ver
     .plata__desplegable); cerrado queda `inert`, sin foco ni clics. */
  return (
    <div className={`plata__grupo ajuste--${tipo}`}>
      <button type="button" className="plata__linea plata__abrir" aria-expanded={abierto}
              onClick={() => setAbierto((a) => !a)}>
        <span>{titulo} <span className="plata__flecha" aria-hidden="true">▼</span></span>
        <b>{signo} {fmt.pesos(total)}</b>
      </button>
      <div className="plata__desplegable" data-abierto={abierto || undefined} inert={!abierto}>
        <div className="plata__desplegable-in">
          {items.map((it, k) => {
            const contenido = (
              <>
                <span className="plata__item-nombre" title={it.nombre}>{it.nombre}</span>
                <b>{signo} {fmt.pesos(it.monto)}</b>
                <span className="plata__item-razon">{it.razon}</span>
              </>
            );
            return it.onEditar
              ? <button key={k} type="button" className="plata__item plata__item--editable" onClick={it.onEditar}
                        title="Cambiar el descuento">{contenido}</button>
              : <div key={k} className="plata__item">{contenido}</div>;
          })}
        </div>
      </div>
    </div>
  );
}

/* `onEditar(clave)`: "p0", "p1"… para un producto, "despacho", "instalacion"
   o "pedido". `onRestablecer`: el botón, solo si hay algo puesto a mano. */
export function PlataAjustes({ t, d, productos, onEditar, onRestablecer }) {
  // Solo las que tienen descuento, para no gastar espacio: a una sin
  // descuento se le agrega desde su ficha ("+ Descuento").
  const lineasDescuento = [
    ...productos.map((p, i) => ({ clave: `p${i}`, nombre: `${i + 1}. ${p.descuento?.nombre || ""}`, l: p.descuento })),
    ...["despacho", "instalacion"].filter((k) => d?.[k]).map((k) => ({ clave: k, nombre: d[k].nombre, l: d[k] })),
  ].filter((x) => x.l?.monto > 0);
  const descuentos = lineasDescuento.map(({ clave, nombre, l }) => ({
    nombre, monto: l.monto, razon: textoDescuento(l), onEditar: () => onEditar(clave),
  }));
  const pedido = d?.pedido;
  if (pedido?.monto > 0) {
    descuentos.push({ nombre: "Adicional del pedido", monto: pedido.monto,
                      razon: textoRazon(pedido.pct, "pedido"), onEditar: () => onEditar("pedido") });
  }
  const minimos = productos.filter((p) => p.descuento?.minimo).map((p) => ({
    nombre: `${productos.indexOf(p) + 1}. ${p.descuento.nombre}`, monto: p.descuento.minimo.monto,
    razon: textoMinimo(p.descuento.minimo),
  }));

  const totalDescuento = t.descuento_monto || 0;
  const sumaMinimos = minimos.reduce((s, it) => s + it.monto, 0);
  const hayAjustes = totalDescuento > 0 || minimos.length > 0;

  return (
    <div className="plata">
      <Linea et={hayAjustes ? "Subtotal" : "Neto"} val={fmt.pesos((t.neto || 0) - sumaMinimos)} />
      <Grupo titulo="Descuentos" tipo="descuento" total={totalDescuento} items={descuentos} />
      <Grupo titulo="Cobros mínimos" tipo="minimo" total={sumaMinimos} items={minimos} />
      {hayAjustes && <Linea et="Neto total" val={fmt.pesos(t.neto_total || 0)} clase="plata__linea--neto" />}
      <Linea et={`IVA (${fmt.cantidad(t.iva_pct ?? 19)}%)`} val={fmt.pesos(t.iva || 0)} />
      <Linea et="Total" val={fmt.pesos(t.total || 0)} clase="plata__linea--total" />
      <div className="plata__acciones">
        <button type="button" className="btn btn--fantasma btn--chico" onClick={() => onEditar("pedido")}>
          Descuento del pedido
        </button>
        {d?.hay_manuales && (
          <button type="button" className="btn btn--fantasma btn--chico" onClick={onRestablecer}>
            Restablecer descuentos
          </button>
        )}
      </div>
    </div>
  );
}
