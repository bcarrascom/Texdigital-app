import { useMemo, useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import Segmento from "@/components/Segmento/Segmento";
import Dialogo from "@/components/Dialogo/Dialogo";
import IconoRollos from "@/assets/svg/spiral.svg?react";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import IconoEditar from "@/assets/svg/pencil.svg?react";
import IconoEliminar from "@/assets/svg/trash-2.svg?react";
import IconoMas from "@/assets/svg/plus.svg?react";
import * as fmt from "@/utils/formato";
import { BarraGuardar, Fila, Grupo, NotaSoloLectura } from "./Ajustes";
import { DialogoQuitar, DialogoTextil } from "./DialogosCatalogo";
import { montoOVacio, useCambiosPendientes } from "./cambiosPendientes";

/* Textiles: cuánto se cobra por metro de cada uno (ver
   core/precios_textiles.py). Cada textil se cobra por un valor fijo, escrito
   acá, o por el valor de venta del rollo del que sale la tela; el switch de
   arriba decide si vale lo mismo para todos o lo que diga cada uno.

   Es un ajuste GLOBAL (Dropbox): vale para todos los que cotizan. Se edita
   todo junto y se guarda con un botón; mientras haya algo que no se puede
   cobrar (un textil fijo sin valor), no se deja guardar.

   Agregar un textil y cambiarle el nombre o el ancho (el lápiz) son aparte,
   en un diálogo que se aplica al confirmar (ver core/catalogo.py). Con
   precios sin guardar no se deja: al volver a cargar se perderían. */

const MODOS = [
  { valor: "fijo", etiqueta: "Valor fijo" },
  { valor: "rollo", etiqueta: "Por rollo" },
  { valor: "por_textil", etiqueta: "Según cada textil" },
];
const COBROS = [
  { valor: "fijo", etiqueta: "Fijo", titulo: "Un valor por metro, el de acá al lado" },
  { valor: "rollo", etiqueta: "Rollo", titulo: "El valor de venta del rollo del que sale la tela" },
];

const PIE_MODO = {
  fijo: "Todos los textiles se cobran por el valor por metro que tienen acá.",
  rollo: "Todos los textiles se cobran por el valor de venta del rollo del que sale la tela: el mismo que Inventario usaría al aprobar.",
  por_textil: "Cada textil se cobra como diga su propio switch.",
};


/* Misma regla que core.precios_textiles.validar: {nombre: mensaje}. */
function validar(modo, textiles) {
  const errores = {};
  for (const t of textiles) {
    const valor = fmt.leerClp(t.valor);
    if (valor == null) {
      // Obligatorio también por rollo: es lo que se cobra si ningún rollo alcanza.
      errores[t.nombre] = "Falta el valor por metro.";
    } else if (!(valor > 0)) errores[t.nombre] = "El valor tiene que ser mayor que 0.";
  }
  return errores;
}

/* Los cambios del borrador, uno por línea, para el diálogo de salir. */
const NOMBRE_MODO = Object.fromEntries(MODOS.map((m) => [m.valor, m.etiqueta]));
const NOMBRE_COBRO = { fijo: "valor fijo", rollo: "por rollo" };
function describirCambios(original, actual) {
  const cambios = [];
  if (original.modo !== actual.modo) cambios.push(`Cómo se cobran los textiles: ${NOMBRE_MODO[original.modo]} → ${NOMBRE_MODO[actual.modo]}`);
  actual.textiles.forEach((t, k) => {
    const o = original.textiles[k];
    if (!o) return;
    if (o.cobro !== t.cobro) cambios.push(`${t.nombre}: se cobra ${NOMBRE_COBRO[o.cobro]} → ${NOMBRE_COBRO[t.cobro]}`);
    if (o.valor !== t.valor) cambios.push(`${t.nombre}: ${montoOVacio(o.valor)} → ${montoOVacio(t.valor)} por metro`);
  });
  return cambios;
}

/* El borrador: lo que se edita, con el valor como texto ("$12.000"). */
const aBorrador = (d) => ({
  modo: d.modo,
  textiles: d.textiles.map((t) => ({ nombre: t.nombre, cobro: t.cobro, valor: t.valor == null ? "" : fmt.clp(t.valor) })),
});

export default function Textiles() {
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(() => api.obtener_precios_textiles(), []);
  const [borrador, setBorrador] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [rollosDe, setRollosDe] = useState(null);   // textil del diálogo "valor de todos los rollos"
  const [editando, setEditando] = useState(null);   // null | "nuevo" | el textil a editar
  const [quitando, setQuitando] = useState(null);   // el textil a quitar

  // Lo guardado, como borrador: comparar contra esto dice si hay cambios.
  const original = useMemo(() => (datos ? aBorrador(datos) : null), [datos]);
  const actual = borrador || original;
  const errores = useMemo(() => (actual ? validar(actual.modo, actual.textiles) : {}), [actual]);
  useCambiosPendientes({
    cambios: borrador && original ? describirCambios(original, borrador) : [],
    error: Object.keys(errores).length ? `${fmt.plural(Object.keys(errores).length, "textil necesita", "textiles necesitan")} un valor válido.` : null,
    guardar,
  });
  if (cargando || !actual) return <Cargando />;

  const soloLectura = datos.solo_lectura;
  const hayCambios = JSON.stringify(actual) !== JSON.stringify(original);
  const cantidadErrores = Object.keys(errores).length;
  const resumen = Object.fromEntries(datos.textiles.map((t) => [t.nombre, t]));

  const cambiar = (cambio) => setBorrador({ ...actual, ...cambio });
  const soloLecturaCatalogo = soloLectura || datos.catalogo_solo_lectura;

  function abrirEdicion(cual) {
    if (hayCambios) { aviso("Primero guarda o descarta los cambios de precios.", "aviso"); return; }
    setEditando(cual);
  }
  const cambiarTextil = (nombre, cambio) =>
    cambiar({ textiles: actual.textiles.map((t) => (t.nombre === nombre ? { ...t, ...cambio } : t)) });

  async function guardar() {
    if (cantidadErrores || guardando) return false;
    setGuardando(true);
    try {
      const r = await api.guardar_precios_textiles({
        modo: actual.modo,
        textiles: actual.textiles.map((t) => ({ nombre: t.nombre, cobro: t.cobro, valor: fmt.leerClp(t.valor) })),
      });
      if (!r?.ok) {
        aviso(r?.errores?.[0]?.mensaje || "No se pudo guardar.", "error");
        return false;
      }
      await recargar();
      setBorrador(null);
      aviso("Precios de textiles guardados.", "info");
      return true;
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <NotaSoloLectura visible={soloLectura} />

      <Grupo titulo="Cómo se cobran"
             pie={datos.inventario ? PIE_MODO[actual.modo]
               : "Con el módulo Inventario apagado no hay rollos: los textiles solo se pueden cobrar por valor fijo."}>
        <Fila etiqueta="Cobrar los textiles">
          <Segmento etiqueta="Cómo se cobran los textiles" opciones={MODOS} valor={actual.modo}
                    deshabilitado={soloLectura || !datos.inventario} onCambiar={(modo) => cambiar({ modo })} />
        </Fila>
      </Grupo>

      <Grupo titulo={fmt.plural(actual.textiles.length, "textil", "textiles")}
             pie={actual.modo === "fijo" ? "El valor es por metro lineal; en Backlight, por metro cuadrado."
               : "Por metro lineal (en Backlight, por metro cuadrado). En los que se cobran por rollo, este valor se cobra cuando ningún rollo alcanza para el producto (el cotizador lo avisa)."}>
        {actual.textiles.map((t) => (
          <FilaTextil key={t.nombre} textil={t} resumen={resumen[t.nombre]} modo={actual.modo}
                      error={errores[t.nombre]} soloLectura={soloLectura} inventario={datos.inventario}
                      onCambiar={(cambio) => cambiarTextil(t.nombre, cambio)}
                      onRollos={() => setRollosDe(resumen[t.nombre])}
                      onEditar={soloLecturaCatalogo ? null : () => abrirEdicion(resumen[t.nombre])}
                      onQuitar={soloLecturaCatalogo ? null : () => (hayCambios
                        ? aviso("Primero guarda o descarta los cambios de precios.", "aviso") : setQuitando(resumen[t.nombre]))} />
        ))}
        {!soloLecturaCatalogo && <Fila etiqueta="Agregar textil" icono={IconoMas} color="#2E9D5B" onClick={() => abrirEdicion("nuevo")} />}
      </Grupo>

      <BarraGuardar visible={hayCambios} guardando={guardando} onDescartar={() => setBorrador(null)} onGuardar={guardar}
                    error={cantidadErrores ? `${fmt.plural(cantidadErrores, "textil necesita", "textiles necesitan")} un valor válido.` : null} />

      <DialogoValorRollos textil={rollosDe} onCerrar={() => setRollosDe(null)}
                          onHecho={async (cambiados, textil) => {
                            setRollosDe(null);
                            await recargar();   // el resumen de rollos; el borrador no se toca
                            aviso(cambiados ? `${fmt.plural(cambiados, "rollo", "rollos")} de ${textil} con el valor nuevo.`
                              : `Los rollos de ${textil} ya tenían ese valor.`, "info");
                          }} />

      <DialogoQuitar abierto={!!quitando} nombre={quitando?.nombre} que="textil"
                     avisos={[quitando?.rollos?.rollos && `Sus ${fmt.plural(quitando.rollos.rollos, "rollo", "rollos")} en Inventario quedan como están, pero no se podrá cotizar con ${quitando.rollos.rollos === 1 ? "él" : "ellos"}.`]}
                     quitar={() => api.quitar_textil(quitando.nombre)} onCerrar={() => setQuitando(null)}
                     onHecho={async () => {
                       const nombre = quitando.nombre;
                       setQuitando(null);
                       await recargar();
                       setBorrador(null);
                       aviso(`${nombre} quitado.`, "info");
                     }} />

      <DialogoTextil abierto={!!editando} textil={editando === "nuevo" ? null : editando} modoCobro={actual.modo}
                     onCerrar={() => setEditando(null)}
                     onHecho={async (r) => {
                       const antes = editando === "nuevo" ? null : editando.nombre;
                       setEditando(null);
                       await recargar();
                       setBorrador(null);
                       aviso(!antes ? "Textil agregado."
                         : r.rollos ? `Textil actualizado, con ${fmt.plural(r.rollos, "rollo renombrado", "rollos renombrados")}.`
                         : "Textil actualizado.", "info");
                     }} />
    </>
  );
}

/* "2 rollos · $12.000 – $14.000" */
function textoRollos(r) {
  if (!r?.rollos) return "Sin rollos en Inventario";
  const partes = [fmt.plural(r.rollos, "rollo", "rollos")];
  if (r.minimo != null) partes.push(r.minimo === r.maximo ? fmt.pesos(r.minimo) : `${fmt.pesos(r.minimo)} – ${fmt.pesos(r.maximo)}`);
  if (r.sin_valor) partes.push(`${r.sin_valor} sin valor`);
  return partes.join(" · ");
}

function FilaTextil({ textil: t, resumen, modo, error, soloLectura, inventario, onCambiar, onRollos, onEditar, onQuitar }) {
  const r = resumen?.rollos;
  const id = `valor-${t.nombre}`;
  return (
    <div className="fila-ajuste fila-textil" data-invalido={error ? "" : undefined}>
      <span className="fila-textil__info">
        <label className="fila-textil__nombre" htmlFor={id}>{t.nombre}</label>
        <span className="fila-textil__sub">
          {[resumen?.ancho && `${fmt.cantidad(resumen.ancho)} m de ancho`, resumen?.backlight && "Backlight",
            inventario && textoRollos(r), resumen?.anteriores?.length && `antes: ${resumen.anteriores.join(", ")}`]
            .filter(Boolean).join(" · ")}
        </span>
        {error && <span className="fila-textil__error">{error}</span>}
      </span>
      {modo === "por_textil" && (
        <Segmento etiqueta={`Cómo se cobra ${t.nombre}`} opciones={COBROS} valor={t.cobro}
                  deshabilitado={soloLectura} onCambiar={(c) => onCambiar({ cobro: c })} />
      )}
      <input className="entrada entrada--num fila-textil__valor" id={id} type="text" inputMode="numeric" autoComplete="off"
             placeholder="$0" aria-invalid={error ? true : undefined}
             disabled={soloLectura} value={t.valor}
             onChange={(e) => onCambiar({ valor: fmt.clp(e.target.value) })} />
      {onEditar && (
        <button className="btn-fila-ajuste" type="button" title="Nombre, ancho y Backlight"
                aria-label={`Editar ${t.nombre}`} onClick={onEditar}>
          <IconoEditar />
        </button>
      )}
      {inventario && (
        <button className="btn-fila-ajuste" type="button" title="Cambiar el valor de todos sus rollos"
                aria-label={`Cambiar el valor de todos los rollos de ${t.nombre}`}
                disabled={soloLectura || !r} onClick={onRollos}>
          <IconoRollos />
        </button>
      )}
      {onQuitar && (
        <button className="btn-fila-ajuste btn-fila-ajuste--peligro" type="button" title="Quitar"
                aria-label={`Quitar ${t.nombre}`} onClick={onQuitar}>
          <IconoEliminar />
        </button>
      )}
    </div>
  );
}

/* "Cambiar el valor de todos los rollos de X": se aplica en el momento, a
   los rollos (no es parte de lo que se guarda abajo), así que avisa bien qué
   va a pasar antes de dejar hacerlo. */
function DialogoValorRollos({ textil, onCerrar, onHecho }) {
  return (
    <Dialogo abierto={!!textil} onCerrar={onCerrar} className="dlg--desenfoque dlg-valor-rollos">
      {textil && <FormularioValorRollos textil={textil} onCerrar={onCerrar} onHecho={onHecho} />}
    </Dialogo>
  );
}

function FormularioValorRollos({ textil, onCerrar, onHecho }) {
  const aviso = useAvisos();
  const [valor, setValor] = useState("");
  const [enviando, setEnviando] = useState(false);
  const r = textil.rollos;
  const monto = fmt.leerClp(valor);
  const valido = monto > 0;

  async function aplicar() {
    if (!valido || enviando) return;
    setEnviando(true);
    try {
      const res = await api.fijar_valor_rollos(textil.nombre, monto);
      if (!res?.ok) { aviso(res?.error || "No se pudo cambiar el valor.", "error"); return; }
      await onHecho(res.cambiados, textil.nombre);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <h2 className="dlg__titulo">Valor de todos los rollos</h2>
      <p className="dlg__texto">
        Le pone el mismo valor de venta por metro a {r.rollos === 1 ? "el rollo" : `los ${r.rollos} rollos`} de <b>{textil.nombre}</b> que
        hay en Inventario, activos e inactivos. Hoy: {textoRollos(r)}.
      </p>
      <div className="campo dlg-valor-rollos__campo">
        <label className="campo__etiqueta" htmlFor="valor-rollos">Valor por metro</label>
        <input className="entrada entrada--num" id="valor-rollos" type="text" inputMode="numeric" autoComplete="off" data-autofoco
               placeholder="$0" value={valor} onChange={(e) => setValor(fmt.clp(e.target.value))}
               onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); aplicar(); } }} />
      </div>
      {valido && (
        <p className="ajustes-nota ajustes-nota--aviso dlg-valor-rollos__aviso" role="alert">
          <IconoAviso aria-hidden="true" />
          <span>
            Se aplica ahora y reemplaza el valor que cada rollo tenía. También cambia lo que Inventario muestra como
            vendido y ganado con esos rollos. Las cotizaciones ya guardadas no cambian.
          </span>
        </p>
      )}
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--peligro btn--chico" type="button" disabled={!valido || enviando} onClick={aplicar}>
          {valido ? `Cambiar ${fmt.plural(r.rollos, "rollo", "rollos")} a ${fmt.pesos(monto)}` : "Cambiar"}
        </button>
      </div>
    </>
  );
}
