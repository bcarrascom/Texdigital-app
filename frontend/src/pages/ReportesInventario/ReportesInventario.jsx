import { useState } from "react";
import { useSearchParams } from "react-router";
import { AnimatePresence, motion } from "motion/react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import Etiqueta from "@/components/Etiqueta/Etiqueta";
import Segmento from "@/components/Segmento/Segmento";
import * as fmt from "@/utils/formato";
import "./ReportesInventario.css";

/* Reportes mensuales de Inventario (ver core/reportes_inventario.py): cuánto
   se usó y cuánto quedó de cada textil y material, y lo que vale cada cosa.

   Abrir la página es lo que recalcula el reporte del mes en curso (y cierra
   los meses que terminaron): por eso la lista de meses sale de
   abrir_reportes_inventario, no de una lectura cualquiera. A la izquierda los
   meses, agrupados por año; a la derecha el elegido. El mes elegido vive en
   la URL (?anio=&mes=), así "Volver" desde otra pantalla lo deja donde
   estaba; sin nada en la URL, el más nuevo. */

const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
               "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
const FUNDIDO = { duration: 0.18 };   // --m-rapida, como el resto de los repintados de contenido
const nombreMes = (m) => `${MESES[m.mes - 1]} ${m.anio}`;
/* Las cantidades de cada fila, en el orden en que pasan las cosas en el mes:
   [clave, encabezado, "—" si es 0]. Un 0 ingresado o usado es "no hubo
   movimiento" y se lee mejor como guion; un 0 inicial o restante es un dato
   (no había nada) y se muestra. */
const CANTIDADES = [
  ["inicial", "Inicial", false],
  ["ingresado", "Ingresado", true],
  ["usado", "Usado", true],
  ["restante", "Restante", false],
];
/* Qué filas mostrar: todas, o solo las que se movieron en el mes (algo
   ingresado o usado) — con muchos rollos y materiales quietos, lo que
   cambió se pierde entre los que no. */
const FILTROS = [
  { valor: "todos", etiqueta: "Todos" },
  { valor: "movimientos", etiqueta: "Con movimientos" },
];
const seMovio = (f) => Boolean(f.ingresado || f.usado);

/* Cómo contar lo vendido (pedido de Bruno, 2026-10-26): al aprobar, cada
   consumo guarda lo que cobró la cotización con y sin IVA y con y sin
   descuento (ver core/reportes_inventario.py, "valores_vendidos"); estos dos
   switches eligen cuál ver. Por defecto, sin IVA y con descuento: lo que de
   verdad entró, neto. Un reporte guardado antes de esto solo trae
   "valor_vendido": se muestra ese, sea cual sea la elección. */
const IVA = [{ valor: "sin_iva", etiqueta: "Sin IVA" }, { valor: "con_iva", etiqueta: "Con IVA" }];
const DESCUENTO = [{ valor: "con_descuento", etiqueta: "Con descuento" }, { valor: "sin_descuento", etiqueta: "Sin descuento" }];
const claveVendido = ({ iva, descuento }) => (descuento === "con_descuento" ? `${iva}_con_descuento` : iva);
const vendido = (x, forma) => x.valores_vendidos?.[claveVendido(forma)] ?? x.valor_vendido;

export default function ReportesInventario() {
  const [params, setParams] = useSearchParams();
  const { datos: meses, cargando } = useDatos(() => api.abrir_reportes_inventario(), []);
  const lista = meses || [];

  const pedido = { anio: Number(params.get("anio")), mes: Number(params.get("mes")) };
  const elegido = lista.find((m) => m.anio === pedido.anio && m.mes === pedido.mes) || lista[0] || null;
  const elegir = (m) => setParams({ anio: m.anio, mes: m.mes }, { replace: true });
  // Acá y no en Reporte: se mantiene al pasar de un mes a otro.
  const [filtro, setFiltro] = useState("todos");
  const [forma, setForma] = useState({ iva: "sin_iva", descuento: "con_descuento" });

  return (
    <Pagina tema="inventario" titulo="Reportes de inventario" className="pag-reportes-inventario">
      <Cabecera titulo="Reportes de inventario" />

      <main className="contenido">
        {cargando ? <Cargando /> : !elegido ? (
          <p className="reportes__vacio">Todavía no hay movimientos en Inventario para armar un reporte.</p>
        ) : (
          <div className="reportes">
            <ListaMeses meses={lista} elegido={elegido} onElegir={elegir} />
            <AnimatePresence mode="wait" initial={false}>
              <motion.div key={`${elegido.anio}-${elegido.mes}`} className="reportes__cuerpo"
                          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={FUNDIDO}>
                <Reporte mes={elegido} filtro={filtro} onFiltrar={setFiltro} forma={forma} onForma={setForma} />
              </motion.div>
            </AnimatePresence>
          </div>
        )}
      </main>
    </Pagina>
  );
}

/* Los meses agrupados por año, el más nuevo arriba. */
function ListaMeses({ meses, elegido, onElegir }) {
  const anios = [...new Set(meses.map((m) => m.anio))];
  return (
    <nav className="reportes__meses" aria-label="Meses">
      {anios.map((anio) => (
        <div key={anio} className="reportes__anio">
          <h2 className="seccion-titulo">{anio}</h2>
          {meses.filter((m) => m.anio === anio).map((m) => {
            const actual = m.anio === elegido.anio && m.mes === elegido.mes;
            return (
              <button key={m.mes} type="button" className="reportes__mes" aria-current={actual || undefined}
                      onClick={() => onElegir(m)}>
                <span>{MESES[m.mes - 1]}</span>
                {!m.cerrado && <Etiqueta tipo="tema">En curso</Etiqueta>}
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

function Reporte({ mes, filtro, onFiltrar, forma, onForma }) {
  const { datos: r, cargando } = useDatos(() => api.obtener_reporte_inventario(mes.anio, mes.mes), [mes.anio, mes.mes]);
  if (cargando) return <Cargando />;
  if (!r) return <p className="reportes__vacio">No se pudo leer el reporte de {nombreMes(mes)}.</p>;

  const t = r.totales;
  const soloMovimientos = filtro === "movimientos";
  return (
    <>
      <div className="reporte__cab">
        <div>
          <h1 className="reporte__titulo">{nombreMes(r)}</h1>
          <p className="reporte__bajada">
            {r.cerrado
              ? `Mes cerrado · calculado el ${r.generado}`
              : `Mes en curso · al ${r.generado}, se actualiza cada vez que se abre esta página`}
          </p>
        </div>
        <div className="reporte__opciones">
          <Segmento etiqueta="Valor vendido con o sin IVA" opciones={IVA} valor={forma.iva}
                    onCambiar={(iva) => onForma({ ...forma, iva })} />
          <Segmento etiqueta="Valor vendido con o sin descuento" opciones={DESCUENTO} valor={forma.descuento}
                    onCambiar={(descuento) => onForma({ ...forma, descuento })} />
          <Segmento etiqueta="Qué filas mostrar" opciones={FILTROS} valor={filtro} onCambiar={onFiltrar} />
        </div>
      </div>

      <div className="reporte__cifras">
        <Cifra etiqueta={`Valor vendido · ${forma.iva === "con_iva" ? "con IVA" : "sin IVA"}, ${forma.descuento === "con_descuento" ? "con descuento" : "sin descuento"}`}
               valor={fmt.pesos(vendido(t, forma))}
               detalle={`Textiles ${fmt.pesos(vendido(t.textiles, forma))} · Materiales ${fmt.pesos(vendido(t.materiales, forma))}`} />
        <Cifra etiqueta="Valor restante" valor={fmt.pesos(t.valor_restante)}
               detalle={`Textiles ${fmt.pesos(t.textiles.valor_restante)} · Materiales ${fmt.pesos(t.materiales.valor_restante)}`} />
        <Cifra etiqueta="Tela usada" valor={`${fmt.cantidad(t.textiles.usado)} m`} detalle="En OPs, ajustes y rollos decomisionados" />
        <Cifra etiqueta="Tela restante" valor={`${fmt.cantidad(t.textiles.restante)} m`}
               detalle={r.cerrado ? "Al cierre del mes" : "Hoy"} />
      </div>

      <Tabla titulo="Textiles" columna="Textil" filas={r.textiles} total={t.textiles} conCantidades forma={forma}
             soloMovimientos={soloMovimientos}
             detalle={(f) => fmt.plural(f.rollos, "rollo", "rollos")}
             sinValor={(f) => (f.sin_valor === f.rollos ? "Sin valor de venta" : `${fmt.plural(f.sin_valor, "rollo", "rollos")} sin valor de venta`)} />
      <Tabla titulo="Materiales" columna="Material" filas={r.materiales} total={t.materiales} forma={forma}
             soloMovimientos={soloMovimientos}
             sinValor={() => "Sin valor de venta"} />
    </>
  );
}

function Cifra({ etiqueta, valor, detalle }) {
  return (
    <div className="cifra">
      <span className="cifra__etiqueta">{etiqueta}</span>
      <span className="cifra__valor">{valor}</span>
      <span className="cifra__detalle">{detalle}</span>
    </div>
  );
}

/* Una tabla por tipo de stock: inicial + ingresado − usado da el restante.
   "Usado" es todo lo que salió (OPs, ajustes que restan, rollos
   decomisionados); "Valor vendido" solo lo de las OPs, al valor de cada
   venta — por eso no es usado × valor. Las cantidades se suman en el total
   solo en textiles (todo es metros); en materiales se mezclan unidades y
   metros, así que su total es solo de plata. Una fila con algo sin valor de
   venta lo dice debajo del nombre: su plata no está completa.

   Con `soloMovimientos` se esconden las filas que no ingresaron ni usaron
   nada; el total sigue siendo el de todas (lo de las escondidas también está
   en bodega), y por eso lo dice. */
function Tabla({ titulo, columna, filas: todas, total, conCantidades = false, soloMovimientos = false, detalle, sinValor, forma }) {
  const filas = soloMovimientos ? todas.filter(seMovio) : todas;
  const filtrando = filas.length !== todas.length;
  return (
    <section className="reporte__seccion">
      <h2 className="seccion-titulo">
        {titulo}
        {filtrando && <span className="reporte__conteo"> · {filas.length} de {todas.length}</span>}
      </h2>
      <div className="tabla-caja">
        {!filas.length && todas.length ? (
          <p className="reportes__vacio">Ningún {titulo === "Textiles" ? "textil" : "material"} tuvo movimientos este mes.</p>
        ) : filas.length ? (
          <table className="tabla reporte__tabla">
            <thead>
              <tr>
                <th>{columna}</th>
                {CANTIDADES.map(([clave, texto]) => <th key={clave} className="num">{texto}</th>)}
                <th className="num">Valor vendido</th>
                <th className="num">Valor restante</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => {
                const aviso = f.sin_valor > 0 ? sinValor(f) : null;
                return (
                  <tr key={f.nombre}>
                    <td>
                      <div className="reporte__nombre">
                        <span>{f.nombre}</span>
                        {(detalle || aviso) && (
                          <small>
                            {detalle?.(f)}{detalle && aviso && " · "}{aviso && <span className="reporte__aviso">{aviso}</span>}
                          </small>
                        )}
                      </div>
                    </td>
                    {CANTIDADES.map(([clave, , guionSiCero]) => (
                      <td key={clave} className="num">
                        {!f[clave] && guionSiCero ? <span className="sin-dato">—</span> : `${fmt.cantidad(f[clave])} ${f.unidad}`}
                      </td>
                    ))}
                    <td className="num"><Plata valor={vendido(f, forma)} sinValor={aviso && !vendido(f, forma)} /></td>
                    <td className="num"><Plata valor={f.valor_restante} sinValor={aviso && !f.valor_restante} /></td>
                  </tr>
                );
              })}
              <tr data-total="">
                <td>{filtrando ? "Total, con los sin movimientos" : "Total"}</td>
                {CANTIDADES.map(([clave]) => (
                  <td key={clave} className="num">{conCantidades ? `${fmt.cantidad(total[clave])} m` : ""}</td>
                ))}
                <td className="num">{fmt.pesos(vendido(total, forma))}</td>
                <td className="num">{fmt.pesos(total.valor_restante)}</td>
              </tr>
            </tbody>
          </table>
        ) : <p className="reportes__vacio">Sin {titulo.toLowerCase()} usados ni en stock este mes.</p>}
      </div>
    </section>
  );
}

/* "—" cuando no hay valor de venta con que calcularlo: $0 diría que no vale nada. */
function Plata({ valor, sinValor }) {
  return sinValor ? <span className="sin-dato">—</span> : fmt.pesos(valor);
}
