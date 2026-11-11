import { forwardRef } from "react";
import { textoRazon } from "@/components/Descuentos/Descuentos";
import * as fmt from "@/utils/formato";
import { completo } from "./producto";
import AvisoAlCrear from "./AvisoAlCrear";

/* El último panel del carril: la tabla de todos los productos (clic en una
   fila vuelve a ese producto), los descuentos, los totales y Guardar /
   Guardar y abrir.

   Los descuentos (pedido de Bruno, 2026-11-06) vienen de
   api.calcular_descuentos (`desglose`, core.precios.explicar_descuento): el
   automático de cada línea, o el puesto a mano. Clic en el descuento de una
   fila lo cambia (onEditarDescuento("p0"…, "despacho", "instalacion")); el
   del pedido y Restablecer van abajo. Junto a Guardar, al crear una
   cotización, el aviso a la gente de Texdigital (AvisoAlCrear). */

const Cifra = ({ et, val, total, clase = "" }) => (
  <div className={`cifra${total ? " cifra--total" : ""} ${clase}`}>
    <span className="cifra__et">{et}</span><span className="cifra__val">{val}</span>
  </div>
);

const medida = (v) => (v ? fmt.medida(String(v).replace(",", ".")) : "—");

/* La celda del descuento de una línea: el monto y debajo la razón. Se aprieta
   para cambiarlo (sin seguir el clic de la fila, que vuelve al producto). */
function CeldaDescuento({ linea, onEditar }) {
  if (!linea) return <td className="num">—</td>;
  const con = linea.monto > 0 || linea.manual;
  return (
    <td className="num">
      <button type="button" className="celda-descuento" title="Cambiar el descuento"
              onClick={(e) => { e.stopPropagation(); onEditar(); }}>
        {con ? (
          <>
            <b>− {fmt.pesos(linea.monto)}</b>
            <span>{textoRazon(linea.pct, linea.razon)}</span>
          </>
        ) : <span className="celda-descuento__agregar">+ Descuento</span>}
      </button>
    </td>
  );
}

const Resumen = forwardRef(function Resumen(
  { productos, despacho, instalacion, desglose, faltanMateriales, onIr, onQuitar, onAgregar, onGuardar,
    onEditarDescuento, onRestablecer, avisoCrear, opcionesAviso, onAvisoCrear }, ref,
) {
  let cant = 0, ml = 0, m2 = 0, total = 0;
  productos.forEach((p) => {
    const c = p.calc || {};
    cant += parseInt(p.cantidad, 10) || 0;
    ml += c.ml || 0;
    m2 += c.m2 || 0;
    total += c.total || 0;
  });
  const superficie = [ml ? `${fmt.cantidad(ml)} ML` : "", m2 ? `${fmt.cantidad(m2)} M²` : ""].filter(Boolean).join(" · ");
  const t = desglose?.totales;
  const pedido = desglose?.pedido?.monto || 0;
  const descuentoProductos = (desglose?.productos || []).reduce((s, l) => s + (l?.monto || 0), 0);
  const extras = [["despacho", "Despacho", despacho], ["instalacion", "Instalación", instalacion]].filter(([, , v]) => v);

  return (
    <div className="tablero" ref={ref}>
      <section className="resumen">
        <header className="resumen__cab">
          <div>
            <h1 className="hoja__titulo">Resumen</h1>
            <p className="hoja__bajada">Clic en una fila para volver a ese producto; en su descuento, para cambiarlo.</p>
          </div>
          <span className="barra__sep" />
          <button className="btn btn--secundario btn--chico" type="button" onClick={onAgregar}>+ Agregar producto</button>
        </header>

        {faltanMateriales && (
          <p className="aviso-materiales">
            <span className="aviso-materiales__icono" aria-hidden="true">!</span>
            Materiales insuficientes
          </p>
        )}

        <div className="tabla-caja">
          <table className="tabla">
            <thead>
              <tr>
                <th style={{ width: "3rem" }}>#</th>
                <th style={{ width: "6rem" }}>Tipo</th>
                <th>Producto / tela</th>
                <th>Tema</th>
                <th className="num" style={{ width: "5rem" }}>Cant.</th>
                <th className="num" style={{ width: "6rem" }}>Ancho</th>
                <th className="num" style={{ width: "6rem" }}>Alto</th>
                <th className="num" style={{ width: "8rem" }}>Superficie</th>
                <th className="num" style={{ width: "8rem" }}>Valor unit.</th>
                <th className="num" style={{ width: "8rem" }}>Total</th>
                <th className="num" style={{ width: "9rem" }}>Descuento</th>
                <th style={{ width: "2.5rem" }} />
              </tr>
            </thead>
            <tbody>
              {productos.map((p, i) => {
                const c = p.calc || {};
                const bl = p.tipo === "backlight";
                return (
                  <tr key={i} onClick={() => onIr(i)} style={completo(p) ? undefined : { opacity: 0.6 }}>
                    <td className="num">{i + 1}</td>
                    <td><span className={`tipo-chip${bl ? " tipo-chip--bl" : ""}`}>{bl ? "Backlight" : "Estándar"}</span></td>
                    <td>{(bl ? p.tela : p.producto) || "—"}</td>
                    <td>{p.tema || "—"}</td>
                    <td className="num">{p.cantidad || "—"}</td>
                    <td className="num">{medida(p.ancho)}</td>
                    <td className="num">{medida(p.alto)}</td>
                    <td className="num">
                      {c.ml != null ? `${fmt.cantidad(c.ml)} ML` : c.m2 != null ? `${fmt.cantidad(c.m2)} M²` : "—"}
                    </td>
                    <td className="num">{c.valor_unitario != null ? fmt.pesos(c.valor_unitario) : "—"}</td>
                    <td className="num">{c.total != null ? fmt.pesos(c.total) : "—"}</td>
                    <CeldaDescuento linea={desglose?.productos?.[i]} onEditar={() => onEditarDescuento(`p${i}`)} />
                    <td>
                      <span className="quitar-fila" title="Quitar"
                            onClick={(e) => { e.stopPropagation(); onQuitar(i); }}>✕</span>
                    </td>
                  </tr>
                );
              })}
              <tr data-total="">
                <td /><td /><td>TOTAL</td><td />
                <td className="num">{cant}</td><td /><td />
                <td className="num">{superficie || "—"}</td>
                <td /><td className="num">{total ? fmt.pesos(total) : "—"}</td>
                <td className="num">{descuentoProductos ? `− ${fmt.pesos(descuentoProductos)}` : "—"}</td><td />
              </tr>
              {extras.map(([clave, nombre, monto]) => (
                <tr key={clave} data-extra="">
                  <td /><td /><td>{nombre}</td><td colSpan={6} />
                  <td className="num">{fmt.pesos(monto)}</td>
                  <CeldaDescuento linea={desglose?.[clave]} onEditar={() => onEditarDescuento(clave)} />
                  <td />
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="resumen__pie">
          <div className="resumen__cierre">
            <div className="cifras">
              <Cifra et="Subtotal" val={t ? fmt.pesos(t.neto) : "—"} />
              {!!(t?.descuento - pedido) && (
                <Cifra et="Descuentos" val={`− ${fmt.pesos(t.descuento - pedido)}`} clase="cifra--descuento" />
              )}
              {!!pedido && (
                <Cifra et={`Adicional del pedido ${textoRazon(desglose.pedido.pct, "pedido").replace(" (pedido)", "")}`}
                       val={`− ${fmt.pesos(pedido)}`} clase="cifra--descuento" />
              )}
              {!!t?.descuento && <Cifra et="Neto total" val={fmt.pesos(t.neto_total)} />}
              {t && <Cifra et={`IVA (${fmt.cantidad(t.iva_pct)}%)`} val={fmt.pesos(t.iva)} />}
              <Cifra et="Total" val={t ? fmt.pesos(t.total) : "—"} total />
            </div>
            <div className="resumen__descuentos">
              <button className="btn btn--fantasma btn--chico" type="button" onClick={() => onEditarDescuento("pedido")}>
                Descuento del pedido
              </button>
              {desglose?.hay_manuales && (
                <button className="btn btn--fantasma btn--chico" type="button" onClick={onRestablecer}>
                  Restablecer descuentos
                </button>
              )}
            </div>
          </div>
          <span className="barra__sep" />
          <div className="resumen__guardar">
            {avisoCrear && <AvisoAlCrear opciones={opcionesAviso} aviso={avisoCrear} onCambiar={onAvisoCrear} />}
            <div className="resumen__acciones">
              <button className="btn btn--secundario btn--chico" type="button" onClick={() => onGuardar(false)}>Guardar</button>
              <button className="btn btn--primario btn--chico" type="button" onClick={() => onGuardar(true)}>
                Guardar y abrir <span aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
});

export default Resumen;
