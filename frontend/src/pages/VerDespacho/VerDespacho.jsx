import { useState } from "react";
import { useParams } from "react-router";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import Etiqueta from "@/components/Etiqueta/Etiqueta";
import * as fmt from "@/utils/formato";
import "./VerDespacho.css";

/* Detalle de una OP ya asignada (Despachos/OPs/Asignadas) — obtener_despacho
   (numero). La dirección de cada producto ya se puso en la pantalla de
   asignación (asignar-despacho) — acá solo se genera la guía de despacho,
   posiblemente parcial (ver core/repositorio_despachos.py). Como la dirección
   es por producto, una guía solo puede incluir productos que compartan la
   MISMA dirección — se valida acá antes de llamar al backend (que también lo
   valida, por las dudas). Las guías ya emitidas quedan listadas abajo, cada
   una reimprimible. */

const ESTADOS = {
  pendiente:  { texto: "Pendiente",  tipo: "tema" },
  parcial:    { texto: "Parcial",    tipo: "aviso" },
  despachado: { texto: "Despachado", tipo: "ok" },
};

/* Clave estable para comparar si dos productos van a la MISMA dirección (no
   alcanza con comparar objetos — vienen de JSON distinto en cada recarga). */
function claveDireccion(d) {
  if (!d) return "";
  return [d.calle, d.numero, d.comuna, d.region].map((x) => (x || "").trim().toLowerCase()).join("|");
}

function direccionTexto(d) {
  if (!d) return "—";
  const linea1 = [d.calle, d.numero].filter(Boolean).join(" ");
  return [linea1, d.comuna].filter(Boolean).join(", ") || "—";
}

async function cargarDespacho(numero) {
  const op = await api.obtener_despacho(numero);
  if (!op) return null;
  return { ...op, productos: op.productos || [], guias: op.guias || [] };
}

export default function VerDespacho() {
  const numero = Number(useParams().numero);
  const { datos: op, cargando, recargar } = useDatos(() => cargarDespacho(numero), [numero]);
  const titulo = `Despacho OP ${fmt.numero(numero)}`;

  return (
    <Pagina tema="despachos" titulo={titulo} className="pag-ver-despacho">
      <Cabecera titulo={titulo} />
      <main className="contenido">
        {cargando ? <Cargando /> : op ? (
          <div className="vista-despacho">
            <Hoja op={op} />
            <Productos op={op} alGenerar={recargar} />
            <Guias guias={op.guias} />
          </div>
        ) : (
          <p className="vacio">No se pudo cargar el despacho de la OP {fmt.numero(numero)}.</p>
        )}
      </main>
    </Pagina>
  );
}

/* ── Cabecera / datos ─────────────────────────────────────────────────── */

function Hoja({ op }) {
  const estado = ESTADOS[op.estado_despacho] || { texto: op.estado_despacho || "—", tipo: "neutra" };
  const datos = [
    ["Empresa", op.empresa],
    ["RUT", op.rut],
    ["Contacto", op.contacto],
    ["Email", op.email],
    ["Fecha completada", op.fecha_completada],
  ].filter(([, val]) => val || val === 0);

  return (
    <section className="hoja">
      <div className="hoja__cab">
        <span className="hoja__num">{fmt.numero(op.numero)}</span>
        <span className="hoja__nombre">{op.nombre}</span>
        <div className="hoja__badges">
          <Etiqueta tipo={estado.tipo}>{estado.texto}</Etiqueta>
          {op.instalacion && <Etiqueta>Incluye instalación</Etiqueta>}
        </div>
      </div>
      <div className="datos">
        {datos.map(([et, val]) => (
          <div className="dato" key={et}>
            <span className="dato__et">{et}</span>
            <span className="dato__val">{val}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ── Productos y generación de guía ──────────────────────────────────── */

function Productos({ op, alGenerar }) {
  const aviso = useAvisos();
  // Cantidad "a despachar ahora" de cada producto, por índice.
  const [cantidades, setCantidades] = useState({});
  const [observaciones, setObservaciones] = useState("");
  const [generando, setGenerando] = useState(false);

  const conCantidad = op.productos
    .map((p, i) => ({ p, i, cantidad: parseFloat(cantidades[i]) }))
    .filter((x) => x.cantidad > 0);
  // La "dirección activa" es la del primer producto con algo cargado —
  // mientras no haya nada escrito, no hay grupo que resaltar.
  const claveActiva = conCantidad.length ? claveDireccion(conCantidad[0].p.direccion) : null;
  const completo = op.estado_despacho === "despachado";

  async function generar() {
    if (!conCantidad.length) {
      aviso("Indicá alguna cantidad a despachar.", "aviso");
      return;
    }
    if (new Set(conCantidad.map((x) => claveDireccion(x.p.direccion))).size > 1) {
      aviso("Los productos de una misma guía tienen que compartir la misma dirección.", "aviso");
      return;
    }
    const items = conCantidad.map((x) => ({ indice_producto: x.i, cantidad: x.cantidad }));
    setGenerando(true);
    try {
      const guia = await api.generar_guia_despacho(op.numero, items, observaciones.trim());
      if (!guia) {
        aviso("No se pudo generar la guía de despacho.", "error");
        return;
      }
      aviso(`Guía ${guia.numero_guia} generada.`, "info");
      setCantidades({});
      setObservaciones("");
      await alGenerar();
    } finally {
      setGenerando(false);
    }
  }

  return (
    <section className="hoja">
      <h2 className="seccion-titulo">Productos</h2>
      <p className="direccion-celda">
        Cada producto va a la dirección que se le asignó. Para generar una
        guía, indicá cantidades solo en productos de UNA misma dirección —
        los de otra quedan atenuados en la tabla mientras tanto.
      </p>
      <div className="tabla-caja">
        <table className="tabla tabla-productos">
          <thead>
            <tr>
              <th>Producto</th>
              <th>Tema</th>
              <th>Dirección</th>
              <th className="num">Cantidad</th>
              <th className="num">Despachado</th>
              <th className="num">Pendiente</th>
              <th className="num">A despachar ahora</th>
            </tr>
          </thead>
          <tbody>
            {op.productos.map((p, i) => {
              const fuera = claveActiva !== null && claveDireccion(p.direccion) !== claveActiva;
              return (
                <tr key={i} className={fuera ? "fuera-de-grupo" : undefined}>
                  <td>{p.nombre || "—"}</td>
                  <td>{p.tema || "—"}</td>
                  <td className="direccion-celda">{direccionTexto(p.direccion)}</td>
                  <td className="num">{fmt.cantidad(p.cantidad)}</td>
                  <td className="num">{fmt.cantidad(p.cantidad_despachada)}</td>
                  <td className="num">{fmt.cantidad(p.pendiente)}</td>
                  <td className="num">
                    {p.pendiente > 0 ? (
                      <input type="number" min="0" max={p.pendiente} step="any"
                             value={cantidades[i] ?? "0"}
                             onChange={(e) => setCantidades((c) => ({ ...c, [i]: e.target.value }))} />
                    ) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {completo ? (
        <div className="completo-aviso">✓ Esta OP ya fue despachada por completo.</div>
      ) : (
        <div className="generar">
          <div className="campo">
            <label className="campo__etiqueta" htmlFor="observaciones">Observaciones (opcional)</label>
            <textarea className="entrada" id="observaciones" rows="2"
                      value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
          </div>
          <div className="generar__acciones">
            <button className="btn btn--primario" onClick={generar} disabled={generando}>
              Generar guía de despacho
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

/* ── Guías ya generadas ───────────────────────────────────────────────── */

function Guias({ guias }) {
  return (
    <section className="hoja">
      <h2 className="seccion-titulo">Guías generadas</h2>
      {guias.length ? (
        <ul className="guias">
          {guias.map((g) => {
            const resumen = (g.items || []).map((i) => `${i.producto} ×${fmt.cantidad(i.cantidad)}`).join(" · ");
            return (
              <li className="guia-item" key={g.numero_guia}>
                <span className="guia-item__n">N° {g.numero_guia}</span>
                <span className="guia-item__resumen">{g.fecha} · {resumen || "—"}</span>
                <button className="btn btn--secundario btn--chico" type="button"
                        onClick={() => api.reimprimir_guia(g.numero_guia)}>Reimprimir</button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="guias-vacio">Todavía no se generó ninguna guía para esta OP.</p>
      )}
    </section>
  );
}
