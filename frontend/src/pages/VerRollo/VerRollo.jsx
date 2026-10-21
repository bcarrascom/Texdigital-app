import { useCallback, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import { rutas } from "@/router/rutas";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import Dialogo from "@/components/Dialogo/Dialogo";
import Etiqueta from "@/components/Etiqueta/Etiqueta";
import { Dato, Datos } from "@/components/Detalle/Detalle";
import Historial, { EnlaceOp } from "@/pages/Inventario/Historial";
import Campo, { enterGuarda } from "@/components/Campo/Campo";
import * as fmt from "@/utils/formato";
import "@/pages/Inventario/Ficha.css";

/* La pantalla de un rollo de tela (antes recursos/pantallas/ver-rollo.html):
   sus datos, y su vida entera como timeline — los ajustes a mano, los
   consumos de cada OP y los cambios de Activo/Inactivo con su motivo. Acá
   viven Editar, Ajustar cantidad, Activar/Desactivar y Decomisionar: la
   tabla del módulo solo lista y navega.

   El consumo real es AUTOMÁTICO al aprobar una cotización (ver
   core/repositorio_inventario.py::consumir_para_op); "Ajustar cantidad" es
   la herramienta de corrección manual, con una descripción para poder
   revisarla después. */

const ETIQUETA_TIPO = { ajuste: "Ajuste", consumo: "Consumo", activacion: "Activación" };
const esActivo = (r) => (r.estado || "activo") === "activo";
const redondear = (n) => Math.round(n * 100) / 100;
const SIN_ENTRADAS = [];   // estable entre renders: un [] nuevo rompería el memo del historial

async function cargarRollo(id) {
  const [rollo, textiles, proveedores] = await Promise.all([
    api.obtener_rollo(id), api.cargar_textiles_inventario(), api.cargar_proveedores(),
  ]);
  return { rollo: rollo || null, textiles: textiles || [], proveedores: proveedores || [] };
}

export default function VerRollo() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(() => cargarRollo(id), [id]);
  const [dialogo, setDialogo] = useState(null);   // "editar" | "ajustar" | "activacion" | "decomisionar" | null
  const r = datos?.rollo;
  const cerrar = () => setDialogo(null);

  async function cambiarEstado(descripcion) {
    const activoNuevo = !esActivo(r);
    cerrar();
    await api.ajustar_estado_rollo(r.id, activoNuevo, descripcion);
    await recargar();
    aviso(activoNuevo ? "Rollo activado." : "Rollo desactivado.", "info");
  }

  /* Decomisionar no es destructivo (el rollo sale de los activos pero su
     historial queda archivado, ver decomisionar_rollo): un solo botón de
     confirmación alcanza. Después se vuelve a la tabla de rollos. */
  async function decomisionar() {
    cerrar();
    await api.decomisionar_rollo(r.id);
    aviso("Rollo decomisionado.", "info");
    if (location.state?.desde?.startsWith(rutas.inventario())) navigate(-1);
    else navigate(rutas.inventario(), { replace: true });
  }

  const deshacer = useCallback(async (u) => {
    await api.eliminar_ajuste_rollo(id, u.id);
    await recargar();
  }, [id, recargar]);
  const vista = useCallback((u) => vistaUso(u, (numero) => navigate(rutas.verOp(numero), { state: { desde: location.pathname } })),
                            [navigate, location.pathname]);
  const titulo = r ? `Rollo #${r.id} · ${r.nombre_textil || ""}` : "Rollo";

  return (
    <Pagina tema="inventario" titulo={titulo} className="pag-ficha-inventario">
      <Cabecera titulo={titulo}>
        {r && (
          <>
            <button className="cab-btn" onClick={() => setDialogo("decomisionar")}>Decomisionar</button>
            <button className="cab-btn" onClick={() => setDialogo("editar")}>Editar</button>
            <button className="cab-btn" onClick={() => setDialogo("activacion")}>{esActivo(r) ? "Desactivar" : "Activar"}</button>
            <button className="btn btn--primario btn--chico" onClick={() => setDialogo("ajustar")}>Ajustar cantidad</button>
          </>
        )}
      </Cabecera>

      <main className="contenido">
        {cargando ? <Cargando /> : !r ? (
          <p className="seccion-titulo">No se pudo cargar el rollo.</p>
        ) : (
          <div className="ficha">
            <Hoja r={r} />
            <Historial entradas={r.usos || SIN_ENTRADAS} vista={vista} onDeshacer={deshacer}
                       vacio="Todavía no hay ningún ajuste o consumo registrado para este rollo." />
          </div>
        )}
      </main>

      {r && (
        <>
          <datalist id="lista-proveedores">
            {datos.proveedores.map((p) => <option key={p} value={p} />)}
          </datalist>

          <Dialogo abierto={dialogo === "editar"} onCerrar={cerrar} className="dlg-ficha">
            <EditarRollo r={r} textiles={datos.textiles} onCerrar={cerrar}
                         onGuardado={async () => { cerrar(); await recargar(); aviso("Rollo actualizado.", "info"); }} />
          </Dialogo>

          <Dialogo abierto={dialogo === "ajustar"} onCerrar={cerrar} className="dlg-ficha">
            <AjustarRollo r={r} onCerrar={cerrar}
                          onGuardado={async () => { await recargar(); aviso("Cantidad ajustada.", "info"); }} />
          </Dialogo>

          <Dialogo abierto={dialogo === "activacion"} onCerrar={cerrar} className="dlg--desenfoque">
            <Activacion activo={esActivo(r)} onCerrar={cerrar} onConfirmar={cambiarEstado} />
          </Dialogo>

          <Dialogo abierto={dialogo === "decomisionar"} onCerrar={cerrar} onConfirmar={decomisionar} className="dlg--desenfoque">
            <h2 className="dlg__titulo">¿Decomisionar rollo?</h2>
            <p className="dlg__texto">
              Rollo {r.id} · {r.nombre_textil || "sin nombre"}: este rollo no se seleccionará para su uso en trabajos de su textil.
            </p>
            <div className="dlg__acciones">
              <button className="btn btn--fantasma btn--chico" type="button" onClick={cerrar}>Cancelar</button>
              <button className="btn btn--peligro btn--chico" type="button" onClick={decomisionar}>Confirmar</button>
            </div>
          </Dialogo>
        </>
      )}
    </Pagina>
  );
}

/* ── La hoja de datos ───────────────────────────────────────────────────── */

function Hoja({ r }) {
  const activo = esActivo(r);
  const pct = r.metros_iniciales ? Math.round((r.metros_restantes / r.metros_iniciales) * 100) : 0;
  const plata = (v) => (v != null ? fmt.pesos(v) : "—");
  return (
    <section className="hoja">
      <div className="hoja__cab">
        <div className="hoja__cab-izq">
          <span className="hoja__num">#{r.id}</span>
          <span className="hoja__nombre">{r.nombre_textil || "—"}</span>
        </div>
        <Etiqueta tipo={activo ? "ok" : "neutra"}>{activo ? "Activo" : "Inactivo"}</Etiqueta>
      </div>
      <Datos lista={[
        ["Ancho", `${fmt.cantidad(r.ancho)} m`],
        ["Proveedor", r.proveedor || "—"],
        ["Fecha de ingreso", r.fecha, { mono: true }],
        ["Compra", r.precio_compra ? fmt.pesos(r.precio_compra) : "—", { mono: true }],
        ["Valor por m", plata(r.valor), { mono: true }],
        ["Valor total", plata(r.valor != null ? r.valor * r.metros_iniciales : null), { mono: true }],
        ["Valor restante", plata(r.valor != null ? r.valor * r.metros_restantes : null), { mono: true }],
      ]}>
        <Dato etiqueta="Stock">
          <span className="stock">
            <span className="stock__texto">{fmt.cantidad(r.metros_restantes)} / {fmt.cantidad(r.metros_iniciales)} m</span>
            <span className="stock__barra"><i style={{ width: `${pct}%` }} /></span>
          </span>
        </Dato>
      </Datos>
    </section>
  );
}

/* Cómo se ve cada entrada del historial. Un consumo trae el rastro completo
   hacia la OP que lo generó (cliente/tema/obs), grabado tal cual al momento
   del consumo — no depende de que esa OP siga existiendo. Una activación no
   mueve metros: en vez de "40 → 40 m" dice a qué estado pasó. */
function vistaUso(u, abrirOp) {
  const consumo = u.tipo === "consumo";
  const activacion = u.tipo === "activacion";
  const activado = u.estado_nuevo === "activo";
  return {
    chip: ETIQUETA_TIPO[u.tipo] || u.tipo,
    variante: consumo ? "consumo" : activacion ? (activado ? "activo" : "inactivo") : undefined,
    cambio: activacion
      ? (activado ? "Activado" : "Desactivado")
      : `${fmt.cantidad(u.metros_restantes_anterior)} → ${fmt.cantidad(u.metros_restantes_nuevo)} m`,
    fecha: u.fecha,
    descripcion: consumo ? null : u.descripcion,
    datos: consumo ? [
      ["OP", u.numero_op && <EnlaceOp numero={u.numero_op} onAbrir={() => abrirOp(u.numero_op)} />],
      ["Cliente", u.cliente], ["Tema", u.tema], ["Obs", u.obs],
    ] : [],
  };
}

/* ── Diálogos ───────────────────────────────────────────────────────────── */

function EditarRollo({ r, textiles, onCerrar, onGuardado }) {
  const [f, setF] = useState({
    textil: r.nombre_textil || "", ancho: r.ancho ?? "", proveedor: r.proveedor || "",
    compra: r.precio_compra ? fmt.clp(r.precio_compra) : "", valor: r.valor != null ? fmt.clp(r.valor) : "",
  });
  const [errores, setErrores] = useState({});
  const set = (clave, valor) => setF((x) => ({ ...x, [clave]: valor }));

  async function guardar(e) {
    e.preventDefault();
    const ancho = parseFloat(f.ancho);
    const faltan = { textil: !f.textil, ancho: !(ancho > 0) };
    setErrores(faltan);
    if (Object.values(faltan).some(Boolean)) return;
    const proveedor = f.proveedor.trim();
    if (proveedor) await api.guardar_proveedor(proveedor);
    await api.editar_rollo(r.id, f.textil, ancho, fmt.leerClp(f.compra) || 0, fmt.leerClp(f.valor), proveedor);
    onGuardado();
  }

  return (
    <form onSubmit={guardar} onKeyDown={enterGuarda}>
      <h2 className="dlg__titulo">Editar rollo</h2>
      <div className="dlg-ficha__campos">
        <Campo id="dre-textil" etiqueta="Textil" requerido invalido={errores.textil}>
          <select className="entrada" id="dre-textil" data-autofoco value={f.textil} onChange={(e) => set("textil", e.target.value)}>
            <option value="" disabled>Seleccionar textil…</option>
            {/* El textil actual aunque ya no esté en el catálogo: si no, el select quedaría vacío. */}
            {(textiles.includes(f.textil) || !f.textil ? textiles : [f.textil, ...textiles]).map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </Campo>
        <Campo id="dre-ancho" etiqueta="Ancho de tela (m)" requerido invalido={errores.ancho}>
          <input className="entrada" id="dre-ancho" type="number" step="0.01" min="0" value={f.ancho} onChange={(e) => set("ancho", e.target.value)} />
        </Campo>
        <div className="fila fila--proveedor">
          <Campo id="dre-proveedor" etiqueta="Proveedor">
            <input className="entrada" id="dre-proveedor" type="text" list="lista-proveedores" autoComplete="off" placeholder="Opcional"
                   value={f.proveedor} onChange={(e) => set("proveedor", e.target.value)} />
          </Campo>
          <Campo id="dre-compra" etiqueta="Precio de compra">
            <input className="entrada" id="dre-compra" type="text" inputMode="numeric" placeholder="Opcional"
                   value={f.compra} onChange={(e) => set("compra", fmt.clp(e.target.value))} />
          </Campo>
        </div>
        <Campo id="dre-valor" etiqueta="Valor por ML/M²" className="campo--mitad">
          <input className="entrada" id="dre-valor" type="text" inputMode="numeric" placeholder="Opcional"
                 value={f.valor} onChange={(e) => set("valor", fmt.clp(e.target.value))} />
        </Campo>
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit">Guardar</button>
      </div>
    </form>
  );
}

/* "Ajustar cantidad": un delta en + o en - con vista previa. Guardar NO
   cierra el diálogo (se pueden cargar varias correcciones seguidas, y el
   stock de arriba se actualiza); "Cerrar" sí. */
function AjustarRollo({ r, onCerrar, onGuardado }) {
  const [delta, setDelta] = useState("0");
  const [descripcion, setDescripcion] = useState("");
  const [invalido, setInvalido] = useState(false);
  const d = parseFloat(delta);
  const nuevo = Number.isFinite(d) ? redondear(r.metros_restantes + d) : null;
  const negativo = nuevo != null && nuevo < 0;
  const preview = !Number.isFinite(d) || d === 0 ? ""
    : negativo ? "No puede quedar negativo."
    : `${fmt.cantidad(r.metros_restantes)} → ${fmt.cantidad(nuevo)} m`;

  async function guardar(e) {
    e.preventDefault();
    if (!Number.isFinite(d)) { setInvalido(true); return; }
    if (d === 0) return;   // no es un ajuste: nada que guardar
    if (negativo) return;
    await api.ajustar_restante_rollo(r.id, nuevo, descripcion.trim());
    setDelta("0");
    setDescripcion("");
    onGuardado();
  }

  return (
    <form onSubmit={guardar} onKeyDown={enterGuarda}>
      <h2 className="dlg__titulo">Ajustar cantidad</h2>
      <div className="ajustar__stock">
        <span>Stock actual</span>
        <strong>{fmt.cantidad(r.metros_restantes)} / {fmt.cantidad(r.metros_iniciales)} m</strong>
      </div>
      <div className="ajustar__form">
        <Campo id="da-delta" etiqueta="Ajuste (metros)" ayuda={preview} invalido={invalido || negativo} className="ajustar__campo-delta">
          <input className="entrada" id="da-delta" type="number" step="0.01" data-autofoco value={delta}
                 onFocus={(e) => e.target.select()}
                 onChange={(e) => { setDelta(e.target.value); setInvalido(false); }} />
        </Campo>
        <Campo id="da-descripcion" etiqueta="Descripción" className="ajustar__campo-descripcion">
          <textarea className="entrada" id="da-descripcion" rows={3} value={descripcion} onChange={(e) => setDescripcion(e.target.value)}
                    placeholder="Qué pasó (ej. recorte con error de medida, tela dañada, recuento físico)…" />
        </Campo>
        <button className="btn btn--primario btn--chico ajustar__guardar" type="submit">Guardar</button>
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cerrar</button>
      </div>
    </form>
  );
}

/* Activar/Desactivar con motivo: a diferencia del punto de color de la
   tabla (sin rastro), acá queda en el historial. */
function Activacion({ activo, onCerrar, onConfirmar }) {
  const [descripcion, setDescripcion] = useState("");
  return (
    <>
      <h2 className="dlg__titulo">{activo ? "¿Desactivar rollo?" : "¿Activar rollo?"}</h2>
      <div className="dlg-ficha__campos">
        <Campo id="dac-descripcion" etiqueta="Descripción">
          <textarea className="entrada" id="dac-descripcion" rows={3} placeholder="Motivo (opcional)…" data-autofoco
                    value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        </Campo>
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="button" onClick={() => onConfirmar(descripcion.trim())}>Confirmar</button>
      </div>
    </>
  );
}
