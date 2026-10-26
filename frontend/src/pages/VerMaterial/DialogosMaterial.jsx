import { useState } from "react";
import { api } from "@/services/api";
import Segmento from "@/components/Segmento/Segmento";
import Campo, { enterGuarda } from "@/components/Campo/Campo";
import { unidadDe } from "@/pages/Inventario/TablaMateriales";
import IconoUnidad from "@/assets/svg/box.svg?react";
import IconoMetro from "@/assets/svg/ruler.svg?react";
import IconoChevron from "@/assets/svg/chevron-down.svg?react";
import IconoBuscar from "@/assets/svg/search.svg?react";
import IconoMas from "@/assets/svg/plus.svg?react";
import * as fmt from "@/utils/formato";

/* Los diálogos de la pantalla de un material: Ajustar (cantidad o precio),
   Editar, Restock (nace del botón, ver components/DialogoMorph) y Eliminar. */

const redondear = (n) => Math.round(n * 100) / 100;
const numeroONull = (texto) => { const n = parseFloat(texto); return Number.isNaN(n) ? null : n; };

function hoyIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ── Ajustar ─────────────────────────────────────────────────────────────────

/* Cantidad: DOS formas de escribir el MISMO ajuste — "Sumar o restar" o
   "Cantidad final"; se completa cualquiera y el otro se calcula solo. Se
   guarda siempre la cantidad FINAL (ver ajustar_cantidad): el delta es una
   comodidad del formulario. `editado` recuerda cuál tocó el usuario, para no
   pisarle lo que está tipeando con el valor derivado del otro.

   Precio: el precio de VENTA, el único de los dos que se pone a mano (el
   costo sale de los restocks). Vacío = sin precio, que no es lo mismo que $0:
   sin precio, sus estructuras vuelven a cobrar por catálogo. */
export function AjustarMaterial({ m, onCerrar, onGuardado }) {
  const unidad = unidadDe(m);
  const [tipo, setTipo] = useState("Cantidad");
  const [delta, setDelta] = useState("");
  const [final, setFinal] = useState("");
  const [editado, setEditado] = useState(null);   // "delta" | "final" | null
  const [precio, setPrecio] = useState(m.valor != null ? fmt.clp(m.valor) : "");
  const [descripcion, setDescripcion] = useState("");
  const [invalido, setInvalido] = useState(false);

  const cantidadFinal = editado === "delta"
    ? (numeroONull(delta) == null ? null : redondear(m.cantidad + numeroONull(delta)))
    : (numeroONull(final) == null ? null : redondear(numeroONull(final)));
  const negativo = cantidadFinal != null && cantidadFinal < 0;
  const diferencia = cantidadFinal == null ? 0 : redondear(cantidadFinal - m.cantidad);
  const preview = cantidadFinal == null ? ""
    : negativo ? "No puede quedar negativo."
    : `${fmt.cantidad(m.cantidad)} → ${fmt.cantidad(cantidadFinal)} ${unidad}`
      + (diferencia ? ` (${diferencia > 0 ? "+" : "-"}${fmt.cantidad(Math.abs(diferencia))})` : " (sin cambio)");

  function cambiarDelta(v) {
    setEditado("delta"); setDelta(v); setInvalido(false);
    setFinal(numeroONull(v) == null ? "" : String(redondear(m.cantidad + numeroONull(v))));
  }
  function cambiarFinal(v) {
    setEditado("final"); setFinal(v); setInvalido(false);
    setDelta(numeroONull(v) == null ? "" : String(redondear(numeroONull(v) - m.cantidad)));
  }

  async function guardar(e) {
    e.preventDefault();
    if (tipo === "Precio") {
      await api.ajustar_valor_material(m.id, fmt.leerClp(precio), descripcion.trim());
      onGuardado("Precio de venta actualizado.");
      return;
    }
    if (cantidadFinal == null || negativo) { setInvalido(true); return; }
    // Un ajuste que no mueve nada no es un ajuste: no se guarda un "104 → 104".
    if (cantidadFinal === m.cantidad) { onCerrar(); return; }
    await api.ajustar_cantidad_material(m.id, cantidadFinal, descripcion.trim());
    onGuardado("Cantidad actualizada.");
  }

  return (
    <form onSubmit={guardar} onKeyDown={enterGuarda}>
      <h2 className="dlg__titulo">Ajustar · {m.nombre}</h2>
      <div className="ajustar__stock">
        <span>Cantidad actual</span>
        <strong>{fmt.cantidad(m.cantidad)} {unidad}</strong>
      </div>
      <div className="ajustar__form ajustar__form--con-tipo">
        <div className="ajustar__tipo">
          <Segmento opciones={[{ valor: "Cantidad" }, { valor: "Precio" }]} valor={tipo} onCambiar={setTipo} etiqueta="Qué se ajusta" />
        </div>
        {tipo === "Cantidad" ? (
          <div className="campo ajustar__campo-delta" data-invalido={invalido || negativo || undefined}>
            <div className="ajustar__par">
              <div>
                <label className="campo__etiqueta" htmlFor="dma-delta">Sumar o restar</label>
                <input className="entrada" id="dma-delta" type="number" step="0.01" placeholder="ej. -3" data-autofoco
                       value={delta} onChange={(e) => cambiarDelta(e.target.value)} />
              </div>
              <div>
                <label className="campo__etiqueta" htmlFor="dma-final">Cantidad final</label>
                <input className="entrada" id="dma-final" type="number" step="0.01"
                       value={final} onChange={(e) => cambiarFinal(e.target.value)} />
              </div>
            </div>
            <span className="campo__ayuda">{preview}</span>
          </div>
        ) : (
          <Campo id="dma-precio" etiqueta="Precio de venta nuevo" className="ajustar__campo-delta"
                 ayuda={m.valor != null ? `Actual: ${fmt.pesos(m.valor)}/${unidad}` : "Todavía sin precio de venta."}>
            <input className="entrada" id="dma-precio" type="text" inputMode="numeric" placeholder="$" autoFocus
                   value={precio} onChange={(e) => setPrecio(fmt.clp(e.target.value))} />
          </Campo>
        )}
        <Campo id="dma-descripcion" etiqueta="Descripción" className="ajustar__campo-descripcion">
          <textarea className="entrada" id="dma-descripcion" rows={3} placeholder="Qué pasó (opcional)…"
                    value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        </Campo>
        <button className="btn btn--primario btn--chico ajustar__guardar" type="submit">Guardar</button>
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cerrar</button>
      </div>
    </form>
  );
}

// ── Editar ──────────────────────────────────────────────────────────────────

/* Consumo automático (core.repositorio_materiales.TIPOS_CONSUMO_VALIDOS): qué
   parámetros pide cada fórmula, y los productos/estructuras que la disparan
   (sin fórmula no hay nada que asociar). */
const CONSUMOS = [
  { valor: "", texto: "Sin fórmula automática", ayuda: "Se descuenta solo a mano, desde “Ajustar cantidad”." },
  { valor: "fijo_por_producto", texto: "Cantidad fija por producto", ayuda: "Cada producto asociado gasta la misma cantidad, sin importar su tamaño." },
  { valor: "metro_lineal_salto", texto: "Por tramos de metro lineal", ayuda: "Se gasta en bloques enteros: cada tramo de metros lineales suma la cantidad fija." },
  { valor: "metro_lineal_directo", texto: "Metro lineal directo", ayuda: "Gasta exactamente los metros lineales del producto (sin el margen de la impresora)." },
  { valor: "perimetro", texto: "Por el contorno de la pieza", ayuda: "Gasta el contorno de cada pieza: 2 × (ancho + alto). Para lo que se aplica por los 4 bordes, como la silicona de un backlight." },
  { valor: "manual", texto: "Monto manual al aprobar", ayuda: "Al aprobar la cotización se pide el monto gastado — una vez por cotización, no por producto." },
];

const COBRO = [
  { valor: "unidad", etiqueta: <IconoUnidad aria-hidden="true" />, titulo: "Por unidad" },
  { valor: "metro", etiqueta: <IconoMetro aria-hidden="true" />, titulo: "Por metro" },
];

export function EditarMaterial({ m, onCerrar, onGuardado }) {
  const p = m.consumo_parametros || {};
  const [f, setF] = useState({
    nombre: m.nombre || "", tipo: m.tipo === "metro" ? "metro" : "unidad",
    proveedor: m.proveedor || "", valor: m.valor != null ? fmt.clp(m.valor) : "",
    consumo: m.tipo_consumo || "", n: p.n ?? "", paso: p.paso ?? "",
  });
  const [productos, setProductos] = useState(m.productos_asociados || []);
  const [estructuras, setEstructuras] = useState(m.estructuras_asociadas || []);
  const [errorNombre, setErrorNombre] = useState(false);
  const set = (clave, valor) => setF((x) => ({ ...x, [clave]: valor }));
  const consumo = CONSUMOS.find((c) => c.valor === f.consumo) || CONSUMOS[0];

  function parametros() {
    const n = parseFloat(f.n);
    if (f.consumo === "fijo_por_producto") return { n: n || 0 };
    if (f.consumo === "metro_lineal_salto") return { paso: parseFloat(f.paso) || 0, n: n || 0 };
    // Vacío = 1 pasada, el caso normal; se manda explícito para que el
    // material guarde lo que de verdad va a usar y no dependa del default.
    if (f.consumo === "perimetro") return { n: n || 1 };
    return {};
  }

  async function guardar(e) {
    e.preventDefault();
    const nombre = f.nombre.trim();
    setErrorNombre(!nombre);
    if (!nombre) return;
    await api.editar_material(m.id, nombre, f.tipo, fmt.leerClp(f.valor), f.proveedor.trim(),
                              f.consumo || null, parametros(), productos, estructuras);
    onGuardado();
  }

  return (
    <form onSubmit={guardar} onKeyDown={enterGuarda}>
      <h2 className="dlg__titulo">Editar material · {m.nombre}</h2>
      <div className="dlg-ficha__campos">
        <Campo id="dme-nombre" etiqueta="Material" requerido invalido={errorNombre}>
          <div className="material-row">
            <input className="entrada" id="dme-nombre" type="text" autoComplete="off" data-autofoco
                   value={f.nombre} onChange={(e) => set("nombre", e.target.value)} />
            <Segmento opciones={COBRO} valor={f.tipo} onCambiar={(v) => set("tipo", v)}
                      etiqueta="Cómo se cobra este material" className="segmento--iconos" />
          </div>
        </Campo>
        <div className="fila fila--proveedor">
          <Campo id="dme-proveedor" etiqueta="Proveedor">
            <input className="entrada" id="dme-proveedor" type="text" list="lista-proveedores" autoComplete="off" placeholder="Opcional"
                   value={f.proveedor} onChange={(e) => set("proveedor", e.target.value)} />
          </Campo>
          <Campo id="dme-valor" etiqueta={f.tipo === "metro" ? "Precio de venta por metro" : "Precio de venta por unidad"}>
            <input className="entrada" id="dme-valor" type="text" inputMode="numeric" placeholder="Opcional"
                   value={f.valor} onChange={(e) => set("valor", fmt.clp(e.target.value))} />
          </Campo>
        </div>
        <p className="campo__ayuda">
          El precio de venta es lo que cobran las cotizaciones nuevas por este material — las ya guardadas no
          cambian de precio. Cambiarlo queda registrado en el historial. El costo no se edita acá: se cuenta solo
          con cada restock.
        </p>

        <div className="fila fila--consumo">
          <Campo id="dme-consumo" etiqueta="Consumo automático">
            <div className="campo-select">
              <select className="entrada" id="dme-consumo" value={f.consumo} onChange={(e) => set("consumo", e.target.value)}>
                {CONSUMOS.map((c) => <option key={c.valor} value={c.valor}>{c.texto}</option>)}
              </select>
              <IconoChevron className="campo-select__chevron" aria-hidden="true" />
            </div>
          </Campo>
          {f.consumo === "fijo_por_producto" && (
            <Campo id="dme-n" etiqueta="Cantidad" className="campo--estrecho">
              <input className="entrada" id="dme-n" type="number" step="0.01" min="0" placeholder="0"
                     value={f.n} onChange={(e) => set("n", e.target.value)} />
            </Campo>
          )}
        </div>
        <p className="campo__ayuda">{consumo.ayuda}</p>

        {/* El perímetro no necesita medidas (salen de la pieza): solo las pasadas, 1 por defecto. */}
        {f.consumo === "perimetro" && (
          <div className="fila">
            <Campo id="dme-n-perimetro" etiqueta="Pasadas por el contorno" className="campo--estrecho">
              <input className="entrada" id="dme-n-perimetro" type="number" step="0.01" min="0" placeholder="1"
                     value={f.n} onChange={(e) => set("n", e.target.value)} />
            </Campo>
          </div>
        )}
        {f.consumo === "metro_lineal_salto" && (
          <div className="fila">
            <Campo id="dme-paso" etiqueta="Cada cuántos metros">
              <input className="entrada" id="dme-paso" type="number" step="0.01" min="0" placeholder="0"
                     value={f.paso} onChange={(e) => set("paso", e.target.value)} />
            </Campo>
            <Campo id="dme-n-salto" etiqueta="Cantidad por tramo">
              <input className="entrada" id="dme-n-salto" type="number" step="0.01" min="0" placeholder="0"
                     value={f.n} onChange={(e) => set("n", e.target.value)} />
            </Campo>
          </div>
        )}

        {f.consumo && (
          <>
            <ListaAsociada id="dme-productos" etiqueta="Productos que lo gastan" lista="lista-productos-catalogo"
                           placeholder="Buscar producto…" items={productos} onCambiar={setProductos}
                           ayuda="«Backlight»: todos los backlight. «Backlight + Caja»: solo los que llevan caja (con un perfil elegido)." />
            <ListaAsociada id="dme-estructuras" etiqueta="Estructuras o perfiles que lo gastan" lista="lista-estructuras-catalogo"
                           placeholder="Buscar estructura o perfil…" items={estructuras} onCambiar={setEstructuras}
                           ayuda="Un perfil de caja (PERFIL …) lo gasta cada backlight con caja de ese perfil, y se cobra además del precio del perfil. En una estructura, en cambio, reemplaza su valor." />
          </>
        )}
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit">Guardar</button>
      </div>
    </form>
  );
}

/* Lista aditiva con lupa y "+" redondo: 0..N nombres de un catálogo, sin
   repetidos. Enter agrega (no guarda el formulario). */
function ListaAsociada({ id, etiqueta, lista, placeholder, items, onCambiar, ayuda }) {
  const [texto, setTexto] = useState("");
  function agregar() {
    const t = texto.trim();
    if (t && !items.includes(t)) onCambiar([...items, t]);
    setTexto("");
  }
  return (
    <Campo id={id} etiqueta={etiqueta} ayuda={ayuda}>
      <div className="aditiva">
        <div className="aditiva__alta">
          <div className="entrada-icono">
            <IconoBuscar className="entrada-icono__svg" aria-hidden="true" />
            <input className="entrada" id={id} type="text" list={lista} autoComplete="off" placeholder={placeholder}
                   value={texto} onChange={(e) => setTexto(e.target.value)}
                   onKeyDown={(e) => {
                     if (e.key !== "Enter") return;
                     e.preventDefault(); e.stopPropagation();
                     agregar();
                   }} />
          </div>
          <button className="btn-agregar-redondo" type="button" aria-label={`Agregar a ${etiqueta.toLowerCase()}`} onClick={agregar}>
            <IconoMas aria-hidden="true" />
          </button>
        </div>
        <div className="aditiva__items">
          {items.map((nombre, k) => (
            <div key={nombre} className="pastilla" style={{ "--i": k }}>
              <span className="pastilla__nombre">{nombre}</span>
              <button className="pastilla__quitar" type="button" aria-label="Quitar"
                      onClick={() => onCambiar(items.filter((_, j) => j !== k))}>✕</button>
            </div>
          ))}
        </div>
      </div>
    </Campo>
  );
}

// ── Restock ─────────────────────────────────────────────────────────────────

/* Sumar stock a este material: la MISMA ingresar_material del "+" del módulo
   (busca por nombre y suma), solo que acá el nombre ya se conoce. La fecha se
   puede cambiar, para cargar una compra de unos días atrás. Un solo botón:
   afuera o Escape cancela. */
export function Restock({ m, onGuardado }) {
  const [f, setF] = useState({ cantidad: "", fecha: hoyIso(), proveedor: m.proveedor || "", gasto: "" });
  const [errores, setErrores] = useState({});
  const set = (clave, valor) => setF((x) => ({ ...x, [clave]: valor }));

  async function guardar(e) {
    e.preventDefault();
    const cantidad = parseFloat(f.cantidad);
    const faltan = { cantidad: !(cantidad > 0), fecha: !f.fecha };
    setErrores(faltan);
    if (Object.values(faltan).some(Boolean)) return;
    const proveedor = f.proveedor.trim();
    if (proveedor) await api.guardar_proveedor(proveedor);
    await api.ingresar_material(m.nombre, cantidad, m.tipo, proveedor, fmt.leerClp(f.gasto), null,
                                null, null, null, null, f.fecha);
    onGuardado();
  }

  return (
    <form onSubmit={guardar} onKeyDown={enterGuarda}>
      <h2 className="dlg__titulo">Restock</h2>
      <div className="dlg-ficha__campos">
        <div className="fila">
          <Campo id="rs-cantidad" etiqueta="Cantidad" requerido invalido={errores.cantidad}>
            <input className="entrada" id="rs-cantidad" type="number" step="0.01" min="0" data-autofoco
                   value={f.cantidad} onChange={(e) => set("cantidad", e.target.value)} />
          </Campo>
          <Campo id="rs-fecha" etiqueta="Fecha" requerido invalido={errores.fecha}>
            <input className="entrada" id="rs-fecha" type="date" value={f.fecha} onChange={(e) => set("fecha", e.target.value)} />
          </Campo>
        </div>
        <div className="fila fila--proveedor">
          <Campo id="rs-proveedor" etiqueta="Proveedor">
            <input className="entrada" id="rs-proveedor" type="text" list="lista-proveedores" autoComplete="off" placeholder="Opcional"
                   value={f.proveedor} onChange={(e) => set("proveedor", e.target.value)} />
          </Campo>
          <Campo id="rs-gasto" etiqueta="Gasto">
            <input className="entrada" id="rs-gasto" type="text" inputMode="numeric" placeholder="Opcional"
                   value={f.gasto} onChange={(e) => set("gasto", fmt.clp(e.target.value))} />
          </Campo>
        </div>
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--primario btn--chico" type="submit">Guardar</button>
      </div>
    </form>
  );
}

// ── Eliminar ────────────────────────────────────────────────────────────────

/* Borrar para siempre exige tipear el nombre EXACTO (como borrar un
   repositorio en GitHub): un material no tiene "decomisionado" como los
   rollos, así que este es el único freno contra un clic apurado. */
export function EliminarMaterial({ m, onCerrar, onEliminar }) {
  const [texto, setTexto] = useState("");
  const coincide = texto === m.nombre;
  return (
    <>
      <h2 className="dlg__titulo">¿Eliminar este material?</h2>
      <p className="dlg__texto">
        El material “{m.nombre}” se borra para siempre, junto con todo su historial. No se puede deshacer.
      </p>
      <div className="dlg-ficha__campos">
        <Campo id="confirmar-nombre" etiqueta="Escribí el nombre del material para confirmar">
          <input className="entrada" id="confirmar-nombre" type="text" autoComplete="off" data-autofoco
                 value={texto} onChange={(e) => setTexto(e.target.value)}
                 onKeyDown={(e) => { if (e.key === "Enter" && coincide) { e.preventDefault(); onEliminar(); } }} />
        </Campo>
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--peligro btn--chico" type="button" disabled={!coincide} onClick={onEliminar}>Eliminar</button>
      </div>
    </>
  );
}
