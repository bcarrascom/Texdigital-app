import { memo, useState } from "react";
import IconoFlecha from "@/assets/svg/arrow-down.svg?react";
import CeldasPlata from "./Plata";
import * as fmt from "@/utils/formato";

/* La tabla de materiales no textiles (ver core/repositorio_materiales.py):
   sin activo/inactivo, "todos son activos". Mismas columnas de plata que la de
   rollos, para que las dos tablas se lean igual. Un click en la fila abre el
   material (ver-material).

   Orden por columna: click en un encabezado cicla ascendente → descendente →
   vuelve al orden de siempre (alfabético por material). "Material" no tiene
   "apagado" propio — sería lo mismo que el de siempre —, así que alterna
   asc ⇄ desc nomás. Las columnas de plata ordenan por su cifra UNITARIA (la
   de arriba); un dato que falta va siempre al final. */

const COLUMNAS = [
  ["material", "Material", "material"],
  ["origen", "Origen", "proveedor"],
  ["cantidad", "Cantidad", "cantidad"],
  ["gasto_unitario", "Gastos", "gasto unitario"],
  ["valor_unitario", "Valor", "valor unitario"],
  ["ganancia_unitaria", "Ganancias", "ganancia por unidad"],
];
const POR_DEFECTO = { columna: "material", direccion: "asc" };

export const unidadDe = (m) => (m?.tipo === "metro" ? "m" : "un.");

/* El proveedor del último restock es el relevante para reponer (un material
   puede haber tenido varios a lo largo de su historial). */
export const ultimoRestock = (m) => (m.historial || []).slice().reverse().find((h) => h.tipo === "restock") || null;
const proveedorDe = (m) => ultimoRestock(m)?.proveedor || m.proveedor || "";

function siguienteOrden(actual, columna) {
  if (actual.columna !== columna) return { columna, direccion: "asc" };
  if (columna === "material") return { columna, direccion: actual.direccion === "asc" ? "desc" : "asc" };
  return actual.direccion === "asc" ? { columna, direccion: "desc" } : POR_DEFECTO;
}

function valorDe(m, columna) {
  if (columna === "cantidad") return m.cantidad || 0;
  if (columna === "origen") return proveedorDe(m).trim().toLowerCase() || null;
  if (columna === "material") return (m.nombre || "").trim().toLowerCase();
  return m[columna];
}

function ordenar(lista, { columna, direccion }) {
  const signo = direccion === "desc" ? -1 : 1;
  return lista.slice().sort((a, b) => {
    const va = valorDe(a, columna), vb = valorDe(b, columna);
    // "—" no es ni el más chico ni el más grande: es la ausencia del dato.
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    return (typeof va === "string" ? va.localeCompare(vb, "es") : va - vb) * signo;
  });
}

/* memo: no se vuelve a dibujar cuando cambia algo de la página que no le
   toca (p. ej. abrir un diálogo) — ver Inventario.jsx. */
export default memo(function TablaMateriales({ materiales, onAbrir, botonNuevo, onNuevo }) {
  const [buscar, setBuscar] = useState("");
  const [orden, setOrden] = useState(POR_DEFECTO);
  const filtro = buscar.trim().toLowerCase();
  const filas = ordenar(filtro ? materiales.filter((m) => (m.nombre || "").toLowerCase().includes(filtro)) : materiales, orden);
  const enDefecto = orden.columna === POR_DEFECTO.columna && orden.direccion === POR_DEFECTO.direccion;

  return (
    <>
      <div className="barra-inventario">
        <input className="entrada" type="search" placeholder="Buscar material…"
               value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        <button ref={botonNuevo} className="btn-nuevo" type="button" title="Ingresar material" onClick={onNuevo}>+</button>
      </div>
      <div className="tabla-caja">
        <table className="tabla tabla-materiales">
          <thead>
            <tr>
              {COLUMNAS.map(([col, texto, aria]) => {
                const cambiar = () => setOrden((o) => siguienteOrden(o, col));
                return (
                  <th key={col} tabIndex={0} role="button" aria-label={`Ordenar por ${aria}`}
                      data-orden-activa={!enDefecto && orden.columna === col ? "" : undefined}
                      data-orden-dir={orden.direccion} onClick={cambiar}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); cambiar(); } }}>
                    {texto}<IconoFlecha className="th-orden__flecha" aria-hidden="true" />
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {filas.map((m) => <FilaMaterial key={m.id} m={m} onAbrir={() => onAbrir(m.id)} />)}
          </tbody>
        </table>
        {!filas.length && <p className="estado-vacio">No hay materiales guardados todavía.</p>}
      </div>
    </>
  );
});

function FilaMaterial({ m, onAbrir }) {
  const ultimo = ultimoRestock(m);
  const detalle = ultimo
    ? [ultimo.fecha, ultimo.costo_unitario != null ? `${fmt.pesos(ultimo.costo_unitario)}/${unidadDe(m)}` : null].filter(Boolean).join(" · ")
    : "";
  return (
    <tr tabIndex={0} onClick={onAbrir}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onAbrir(); } }}>
      <td>{m.nombre}</td>
      <td>
        <div className="celda-combo">
          <span className="celda-combo__principal">{proveedorDe(m) || "—"}</span>
          <span className="celda-combo__detalle">{detalle}</span>
        </div>
      </td>
      <td className="num">{fmt.cantidad(m.cantidad)} {unidadDe(m)}</td>
      <CeldasPlata obj={m} sufijo={`/${unidadDe(m)}`} />
    </tr>
  );
}
