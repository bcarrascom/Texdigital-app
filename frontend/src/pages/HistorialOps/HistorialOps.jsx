import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { api } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { rutas } from "@/router/rutas";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Dialogo from "@/components/Dialogo/Dialogo";
import Etiqueta from "@/components/Etiqueta/Etiqueta";
import * as fmt from "@/utils/formato";
import "./HistorialOps.css";

/* Historial de OPs — obtener_historial(anio, mes) / buscar_historial(filtros).

   En la app cada OP es un JSON en carpetas <año>/<mes>: con miles de
   archivos, no se puede cargar todo el historial de una sentada. La pantalla
   calca esa organización en vez de esconderla — el mes y el año de ARRIBA
   son "qué carpeta estoy mirando". El buscador y los filtros son la
   excepción: cliente, material o rango de fechas no tienen sentido acotados
   a un mes, así que cruzan todo el historial.

   Las filas son una tabla, no tarjetas: acá se hojea y se compara. Pasar el
   mouse (o el foco) por una fila despliega un resumen; abrirla lleva a la OP.

   Mes, año, búsqueda y filtros viven en la URL (?anio=&mes=&q=...): al volver
   de una OP, el historial está exactamente donde se lo dejó. */

const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
               "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
const ESTADOS = {
  activa:             { texto: "Activa",             tipo: "tema" },
  entregada:          { texto: "Entregada",          tipo: "ok" },
  entregada_atrasada: { texto: "Entregada atrasada", tipo: "aviso" },
  cancelada:          { texto: "Cancelada",          tipo: "neutra" },
};
const FILTROS = ["cliente", "desde", "hasta", "material"];
const MAX_PRODUCTOS = 3;
const ANIOS_HACIA_ATRAS = 3;

export default function HistorialOps() {
  const { contexto } = useApp();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();

  // La fecha de hoy la pone Python (hoy_iso), igual que en el resto de la app.
  const [anioHoy, mesHoy] = (contexto.hoy_iso || new Date().toISOString()).split("-").map(Number);
  const anio = Number(params.get("anio")) || anioHoy;
  const mes = Number(params.get("mes")) || mesHoy;
  const texto = params.get("q") || "";
  const filtros = Object.fromEntries(FILTROS.map((f) => [f, params.get(f) || ""]));
  const hayFiltros = FILTROS.some((f) => filtros[f]);

  const [filas, setFilas] = useState(null);
  const [dialogoAbierto, setDialogoAbierto] = useState(false);
  /* Lo que se escribe en el buscador vive acá y se copia a la URL, no al
     revés: la URL se actualiza un instante después de cada tecla, y un campo
     que leyera su valor de ahí perdería letras al escribir rápido. */
  const [busqueda, setBusqueda] = useState(texto);
  const pedido = useRef(0);   // se descartan las respuestas de búsquedas viejas

  /* Con búsqueda o algún filtro activo, el mes/año no manda: se cruza todo
     el historial. Sin nada de eso, se mira la "carpeta" elegida. */
  const consulta = params.toString();
  useEffect(() => {
    const n = ++pedido.current;
    const traer = texto.trim() || hayFiltros
      ? api.buscar_historial({ texto: texto.trim(), ...filtros })
      : api.obtener_historial(anio, mes);
    Promise.resolve(traer).then((lista) => { if (n === pedido.current) setFilas(lista || []); });
  }, [consulta]);  // todo lo que importa está en la URL

  const cambiar = (cambios) => setParams((p) => {
    const nuevos = new URLSearchParams(p);
    Object.entries(cambios).forEach(([k, v]) => (v ? nuevos.set(k, v) : nuevos.delete(k)));
    return nuevos;
  }, { replace: true });

  /* Elegir mes o año es una intención clara de "quiero ver esa carpeta":
     pisa cualquier búsqueda o filtro que hubiera quedado activo. */
  function irACarpeta(cambios) {
    setBusqueda("");
    cambiar({ q: "", ...Object.fromEntries(FILTROS.map((f) => [f, ""])), ...cambios });
  }

  const anios = Array.from({ length: ANIOS_HACIA_ATRAS + 1 }, (_, i) => anioHoy - i);

  return (
    <Pagina tema="ops" titulo="Historial de OPs" className="pag-historial-ops">
      <Cabecera titulo="Historial de OPs" />

      <main className="contenido">
        <div className="vista-historial">
          <div className="filtros">
            <div className="filtros__nav">
              <select className="entrada" aria-label="Mes" value={mes} onChange={(e) => irACarpeta({ mes: e.target.value })}>
                {MESES.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
              </select>
              <select className="entrada" aria-label="Año" value={anio} onChange={(e) => irACarpeta({ anio: e.target.value })}>
                {anios.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
            <div className="filtros__busqueda">
              <input className="entrada" type="search" placeholder="Buscar por número o nombre…"
                     value={busqueda} onChange={(e) => { setBusqueda(e.target.value); cambiar({ q: e.target.value }); }} />
              {/* El puntito avisa que hay filtros aplicados: si no, cerrar el
                  diálogo borra el rastro de por qué el listado sale filtrado. */}
              <button className="cab-btn btn-filtros" type="button" data-activo={hayFiltros || undefined}
                      onClick={() => setDialogoAbierto(true)}>Filtros</button>
            </div>
          </div>

          <div className="tabla-caja">
            {filas && filas.length > 0 && (
              <table className="tabla">
                <thead>
                  <tr>
                    <th className="num num--izq">N°</th>
                    <th>Nombre</th>
                    <th>Cliente</th>
                    <th className="num">Entrega</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                {filas.map((o) => (
                  <GrupoFila key={o.numero} o={o}
                             onAbrir={() => navigate(rutas.verOp(o.numero), { state: { desde: rutas.historialOps() } })} />
                ))}
              </table>
            )}
            {filas && !filas.length && <p className="historial-vacio">No hay OPs que calcen con la búsqueda.</p>}
          </div>
        </div>
      </main>

      <DialogoFiltros abierto={dialogoAbierto} filtros={filtros} onCerrar={() => setDialogoAbierto(false)}
                      onAplicar={(f) => { setDialogoAbierto(false); cambiar(f); }} />
    </Pagina>
  );
}

/* Cada OP es su propio <tbody> —fila principal + fila de detalle—: así el
   :hover vale para las dos y sigue activo aunque el mouse baje desde la fila
   hacia el detalle que recién se reveló (ver HistorialOps.css). */
function GrupoFila({ o, onAbrir }) {
  const est = ESTADOS[o.estado] || { texto: o.estado || "—", tipo: "neutra" };
  return (
    <tbody className="fila-grupo">
      <tr className="fila-principal" tabIndex={0} onClick={onAbrir}
          onKeyDown={(e) => { if (e.key === "Enter") onAbrir(); }}>
        <td className="num num--izq">{fmt.numero(o.numero)}</td>
        <td>{o.nombre || "—"}</td>
        <td>{o.empresa || "—"}</td>
        <td className="num">{o.fecha_entrega || "—"}</td>
        <td><Etiqueta tipo={est.tipo}>{est.texto}</Etiqueta></td>
      </tr>
      <tr className="fila-detalle">
        <td colSpan={5}>
          <div className="fila-detalle__marco">
            <div className="fila-detalle__interior">
              <Detalle o={o} />
            </div>
          </div>
        </td>
      </tr>
    </tbody>
  );
}

/* Lo básico para reconocer la OP sin abrirla: a la izquierda qué se produce
   (hasta 3 productos), a la derecha los datos del trabajo — no las cifras ni
   las etiquetas completas, para eso está la pantalla de la OP. */
function Detalle({ o }) {
  const productos = (o.productos || []).map(resumenProducto);
  const restantes = productos.length - MAX_PRODUCTOS;
  return (
    <div className="fila-detalle__cuerpo">
      <div className="fila-detalle__col">
        <ul className="fila-detalle__productos">
          {productos.length ? productos.slice(0, MAX_PRODUCTOS).map((p, i) => (
            <li key={i}><b>{p.nombre}</b><span>{[p.textil, p.extras.join(", ")].filter(Boolean).join(" · ") || "—"}</span></li>
          )) : <li><b>Sin productos.</b></li>}
        </ul>
        {restantes > 0 && <span className="fila-detalle__mas">+{restantes} más</span>}
      </div>
      <div className="fila-detalle__col">
        <div className="fila-detalle__datos">
          <div className="fila-detalle__dato"><span>Ingreso</span><b>{o.fecha_ingreso || "—"}</b></div>
          <div className="fila-detalle__dato"><span>Contacto</span><b>{o.contacto || "—"}</b></div>
          <div className="fila-detalle__dato"><span>Despacho</span><b>{o.despacho ? "Sí" : "No"}</b></div>
          <div className="fila-detalle__dato"><span>Instalación</span><b>{o.instalacion ? "Sí" : "No"}</b></div>
        </div>
      </div>
    </div>
  );
}

/* Backlight no se nombra por su tela (esa va en la línea de detalle): es
   "Backlight", o "Backlight + Caja" si lleva caja de verdad — la única
   variación que importa para reconocerlo de un vistazo. */
function resumenProducto(p) {
  const bl = p.tipo === "backlight";
  return {
    nombre: bl ? (p.caja && p.caja !== "Sin caja" ? "Backlight + Caja" : "Backlight") : p.producto || "—",
    textil: bl ? p.tela : p.textil,
    extras: bl ? [] : [...(p.estructuras || []), ...(p.terminaciones || [])],
  };
}

/* Filtros avanzados: se editan en el diálogo y recién se aplican con
   "Aplicar" (cerrar sin aplicar no cambia nada). */
function DialogoFiltros({ abierto, filtros, onCerrar, onAplicar }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} className="dlg-filtros">
      <FormularioFiltros inicial={filtros} onCerrar={onCerrar} onAplicar={onAplicar} />
    </Dialogo>
  );
}

function FormularioFiltros({ inicial, onAplicar }) {
  const [f, setF] = useState(inicial);
  const campo = (clave) => ({ value: f[clave], onChange: (e) => setF((x) => ({ ...x, [clave]: e.target.value })) });
  const vacios = Object.fromEntries(FILTROS.map((k) => [k, ""]));
  return (
    <form onSubmit={(e) => { e.preventDefault(); onAplicar(Object.fromEntries(FILTROS.map((k) => [k, f[k].trim()]))); }}>
      <h2 className="dlg__titulo">Filtros avanzados</h2>
      <div className="dlg__campos">
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="f-cliente">Cliente</label>
          <input className="entrada" id="f-cliente" type="text" placeholder="Nombre de la empresa" data-autofoco {...campo("cliente")} />
        </div>
        <div className="fila">
          <div className="campo">
            <label className="campo__etiqueta" htmlFor="f-desde">Entrega desde</label>
            <input className="entrada" id="f-desde" type="date" {...campo("desde")} />
          </div>
          <div className="campo">
            <label className="campo__etiqueta" htmlFor="f-hasta">Entrega hasta</label>
            <input className="entrada" id="f-hasta" type="date" {...campo("hasta")} />
          </div>
        </div>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="f-material">Material</label>
          <input className="entrada" id="f-material" type="text" placeholder="Textil, material de caja o estructura" {...campo("material")} />
        </div>
      </div>
      <div className="dlg__acciones">
        <button type="button" className="btn btn--fantasma btn--chico" onClick={() => onAplicar(vacios)}>Limpiar</button>
        <button type="submit" className="btn btn--primario btn--chico">Aplicar</button>
      </div>
    </form>
  );
}
