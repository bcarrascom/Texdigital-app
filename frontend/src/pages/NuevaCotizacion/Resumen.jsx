import { forwardRef } from "react";
import * as fmt from "@/utils/formato";
import { completo } from "./producto";

/* El último panel del carril: la tabla de todos los productos (clic en una
   fila vuelve a ese producto), los totales y Guardar / Guardar y abrir. */

const Cifra = ({ et, val, total }) => (
  <div className={`cifra${total ? " cifra--total" : ""}`}>
    <span className="cifra__et">{et}</span><span className="cifra__val">{val}</span>
  </div>
);

const medida = (v) => (v ? fmt.medida(String(v).replace(",", ".")) : "—");

const Resumen = forwardRef(function Resumen(
  { productos, despacho, instalacion, faltanMateriales, onIr, onQuitar, onAgregar, onGuardar }, ref,
) {
  let cant = 0, ml = 0, m2 = 0, total = 0;
  productos.forEach((p) => {
    const c = p.calc || {};
    cant += parseInt(p.cantidad, 10) || 0;
    ml += c.ml || 0;
    m2 += c.m2 || 0;
    total += c.total || 0;
  });
  const general = total + (despacho || 0) + (instalacion || 0);
  const superficie = [ml ? `${fmt.cantidad(ml)} ML` : "", m2 ? `${fmt.cantidad(m2)} M²` : ""].filter(Boolean).join(" · ");

  return (
    <div className="tablero" ref={ref}>
      <section className="resumen">
        <header className="resumen__cab">
          <div>
            <h1 className="hoja__titulo">Resumen</h1>
            <p className="hoja__bajada">Clic en una fila para volver a ese producto.</p>
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
                <td /><td className="num">{total ? fmt.pesos(total) : "—"}</td><td />
              </tr>
            </tbody>
          </table>
        </div>

        <div className="resumen__pie">
          <div className="resumen__cierre">
            <div className="cifras">
              <Cifra et="Productos" val={total ? fmt.pesos(total) : "—"} />
              {!!despacho && <Cifra et="Despacho" val={fmt.pesos(despacho)} />}
              {!!instalacion && <Cifra et="Instalación" val={fmt.pesos(instalacion)} />}
              <Cifra et="Total" val={general ? fmt.pesos(general) : "—"} total />
            </div>
          </div>
          <span className="barra__sep" />
          <div className="resumen__acciones">
            <button className="btn btn--secundario btn--chico" type="button" onClick={() => onGuardar(false)}>Guardar</button>
            <button className="btn btn--primario btn--chico" type="button" onClick={() => onGuardar(true)}>
              Guardar y abrir <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
});

export default Resumen;
