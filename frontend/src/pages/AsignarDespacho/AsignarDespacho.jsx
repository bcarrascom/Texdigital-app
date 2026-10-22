import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import DialogoMorph from "@/components/DialogoMorph/DialogoMorph";
import FormularioDireccion from "@/pages/Despachos/FormularioDireccion";
import { claveRut, direccionTexto } from "@/pages/Despachos/direcciones";
import IconoAceptar from "@/assets/svg/arrow-down.svg?react";
import IconoMas from "@/assets/svg/plus.svg?react";
import IconoQuitar from "@/assets/svg/x.svg?react";
import IconoPin from "@/assets/svg/map-pin-house.svg?react";
import IconoCheck from "@/assets/svg/check.svg?react";
import * as fmt from "@/utils/formato";
import "./AsignarDespacho.css";

/* Asignar dirección a una OP recién llegada a Despachos (antes
   recursos/pantallas/asignar-despacho.html). La dirección es POR PRODUCTO
   (una OP puede repartirse a varios lugares): se elige una dirección (o se
   crea con el "+"), se seleccionan las tarjetas de producto que van ahí y se
   acepta — esos productos pasan del pin a un check verde.

   No hay botón "Completar": apenas el último producto queda con dirección,
   la OP pasa sola a Asignadas/ (ver core.repositorio_despachos.
   _sincronizar_carpeta). El indicador de arriba de las tarjetas es pasivo. */

async function cargar(numero) {
  const [op, direcciones, clientes, regiones] = await Promise.all([
    api.obtener_asignacion_despacho(numero), api.cargar_todas_direcciones(),
    api.cargar_clientes_direccion(), api.cargar_regiones(),
  ]);
  if (!op) return null;
  return { op: { ...op, productos: op.productos || [] }, direcciones: direcciones || [], clientes: clientes || [], regiones: regiones || [] };
}

export default function AsignarDespacho() {
  const numero = Number(useParams().numero);
  const aviso = useAvisos();
  const { datos, cargando } = useDatos(() => cargar(numero), [numero]);
  const titulo = `Asignar dirección · OP ${fmt.numero(numero)}`;

  return (
    <Pagina tema="despachos" titulo={titulo} className="pag-asignar-despacho">
      <Cabecera titulo={titulo} />
      <main className="contenido">
        {cargando ? <Cargando /> : !datos ? (
          <p className="seccion-titulo">No se pudo cargar la OP {fmt.numero(numero)}.</p>
        ) : <Asignacion inicial={datos} aviso={aviso} />}
      </main>
    </Pagina>
  );
}

/* La pantalla ya cargada. Los productos se actualizan en el lugar al asignar
   o quitar (sin volver a pedir la OP): así cada tarjeta es el MISMO elemento
   antes y después, y el pin se transforma en check con su transición. */
function Asignacion({ inicial, aviso }) {
  const [productos, setProductos] = useState(inicial.op.productos);
  const [direcciones, setDirecciones] = useState(inicial.direcciones);
  const [elegida, setElegida] = useState("");            // índice en `direcciones`, como texto ("" = ninguna)
  const [seleccion, setSeleccion] = useState(() => new Set());
  const [panel, setPanel] = useState(false);
  const mas = useRef(null);
  const op = inicial.op;

  const asignadosN = productos.filter((p) => p.direccion).length;
  const completo = productos.length > 0 && asignadosN === productos.length;
  const todos = productos.length > 0 && seleccion.size === productos.length;
  const algunoConDireccion = [...seleccion].some((i) => productos[i]?.direccion);

  /* Aviso la primera vez que queda completa (y de nuevo si se quita una y se
     vuelve a completar), no en cada render. */
  const avisado = useRef(completo);
  useEffect(() => {
    if (completo && !avisado.current) aviso("Todos los productos tienen dirección — ya podés volver.", "info");
    avisado.current = completo;
  }, [completo]);

  const tocar = (i) => setSeleccion((s) => { const n = new Set(s); n.has(i) ? n.delete(i) : n.add(i); return n; });

  async function aceptar() {
    const direccion = direcciones[Number(elegida)];
    if (!direccion || !seleccion.size) return;
    const indices = [...seleccion];
    await api.asignar_direccion_productos(op.numero, indices, direccion);
    setProductos((ps) => ps.map((p, i) => (indices.includes(i) ? { ...p, direccion } : p)));
    setSeleccion(new Set());
    aviso(indices.length === 1 ? "Dirección asignada a 1 producto." : `Dirección asignada a ${indices.length} productos.`, "info");
  }

  async function quitar() {
    const indices = [...seleccion].filter((i) => productos[i].direccion);
    if (!indices.length) return;
    await api.quitar_direccion_productos(op.numero, indices);
    setProductos((ps) => ps.map((p, i) => (indices.includes(i) ? { ...p, direccion: null } : p)));
    setSeleccion(new Set());
    aviso("Dirección quitada.", "info");
  }

  /* Guardada la dirección nueva, la lista se vuelve a pedir y queda elegida. */
  async function guardarNueva(direccion) {
    await api.guardar_direccion_nueva(direccion);
    setPanel(false);
    const lista = (await api.cargar_todas_direcciones()) || [];
    setDirecciones(lista);
    const i = lista.findIndex((d) => (d.calle || "").toLowerCase() === direccion.calle.toLowerCase()
                                    && (d.numero || "").toLowerCase() === direccion.numero.toLowerCase());
    if (i >= 0) setElegida(String(i));
    aviso("Dirección guardada.", "info");
  }

  return (
    <div className="vista-asignar">
      <section className="hoja">
        <div className="hoja__cab">
          <span className="hoja__num">{fmt.numero(op.numero)}</span>
          <span className="hoja__nombre">{op.nombre}</span>
          <span className="hoja__meta">{[op.empresa, op.contacto].filter(Boolean).join(" · ")}</span>
        </div>
        <div className="selector-direccion">
          <SelectorDireccion direcciones={direcciones} op={op} valor={elegida} onCambiar={setElegida} />
          <button className="btn-icono" type="button" title="Asignar la dirección elegida a los productos seleccionados"
                  disabled={elegida === "" || !seleccion.size} onClick={aceptar}>
            <IconoAceptar aria-hidden="true" />
          </button>
          <button ref={mas} className="btn-icono" type="button" title="Agregar dirección nueva" onClick={() => setPanel(true)}>
            <IconoMas aria-hidden="true" />
          </button>
          {algunoConDireccion && (
            <button className="btn-icono btn-icono--peligro" type="button" title="Quitar dirección de los productos seleccionados" onClick={quitar}>
              <IconoQuitar aria-hidden="true" />
            </button>
          )}
        </div>
      </section>

      <section className="hoja">
        <div className="productos-cab">
          <h2 className="seccion-titulo">Productos</h2>
          <span className="estado-asignacion" data-completo={completo || undefined}>
            {completo ? "✓ Todos los productos tienen dirección" : `${asignadosN}/${productos.length} productos con dirección`}
          </span>
          <button className="btn btn--secundario btn--chico" type="button"
                  onClick={() => setSeleccion(todos ? new Set() : new Set(productos.map((_, i) => i)))}>
            {todos ? "Deseleccionar todos" : "Seleccionar todos"}
          </button>
        </div>
        <div className="tarjetas-productos">
          {productos.map((p, i) => (
            <TarjetaProducto key={i} p={p} seleccionada={seleccion.has(i)} onClick={() => tocar(i)} />
          ))}
        </div>
      </section>

      <DialogoMorph abierto={panel} origen={mas} onCerrar={() => setPanel(false)} anchoRem={28}>
        <FormularioDireccion titulo="Dirección nueva" clienteDefecto={{ empresa: op.empresa, rut: op.rut }}
                             clientes={inicial.clientes} regiones={inicial.regiones} onGuardar={guardarNueva} />
      </DialogoMorph>
    </div>
  );
}

/* TODAS las direcciones guardadas, en dos grupos: primero las del cliente de
   esta OP, después el resto. El valor de cada opción es su índice en la
   lista plana, así no importa en qué grupo cayó. */
function SelectorDireccion({ direcciones, op, valor, onCambiar }) {
  const propias = [], otras = [];
  direcciones.forEach((d, i) => (claveRut(d.rut) === claveRut(op.rut) ? propias : otras).push(i));
  const opcion = (i) => {
    const d = direcciones[i];
    return <option key={i} value={i}>{d.alias || direccionTexto(d)} · {d.comuna || "—"}</option>;
  };
  return (
    <select className="entrada" aria-label="Dirección" value={valor} onChange={(e) => onCambiar(e.target.value)}>
      <option value="">— Elegí una dirección —</option>
      {propias.length > 0 && <optgroup label={`Direcciones de ${op.empresa || "este cliente"}`}>{propias.map(opcion)}</optgroup>}
      {otras.length > 0 && <optgroup label="Otras direcciones">{otras.map(opcion)}</optgroup>}
    </select>
  );
}

function TarjetaProducto({ p, seleccionada, onClick }) {
  return (
    <button type="button" className="tarjeta-producto" data-seleccionado={seleccionada || undefined}
            aria-pressed={seleccionada} onClick={onClick}>
      {/* Pin y check superpuestos: al asignar, uno se va girando y el otro entra. */}
      <span className="tarjeta-producto__badge" data-asignado={p.direccion ? "" : undefined}>
        <IconoPin className="badge__pin" aria-hidden="true" />
        <IconoCheck className="badge__check" aria-hidden="true" />
      </span>
      <span className="tarjeta-producto__nombre">{p.nombre || "—"}</span>
      <span className="tarjeta-producto__linea"><span>Tema</span><b>{p.tema || "—"}</b></span>
      <span className="tarjeta-producto__linea"><span>Cantidad</span><b>{p.cantidad ?? "—"}</b></span>
      <span className="tarjeta-producto__direccion" data-vacia={p.direccion ? undefined : ""}>
        {p.direccion ? direccionTexto(p.direccion) : "Sin dirección asignada"}
      </span>
    </button>
  );
}
