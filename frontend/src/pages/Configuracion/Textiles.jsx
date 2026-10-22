import { useMemo, useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import Segmento from "@/components/Segmento/Segmento";
import Dialogo from "@/components/Dialogo/Dialogo";
import IconoRollos from "@/assets/svg/spiral.svg?react";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import * as fmt from "@/utils/formato";
import { BarraGuardar, Fila, Grupo, NotaSoloLectura } from "./Ajustes";

/* Textiles: cuánto se cobra por metro de cada uno (ver
   core/precios_textiles.py). Cada textil se cobra por un valor fijo, escrito
   acá, o por el valor de venta del rollo del que sale la tela; el switch de
   arriba decide si vale lo mismo para todos o lo que diga cada uno.

   Es un ajuste GLOBAL (Dropbox): vale para todos los que cotizan. Se edita
   todo junto y se guarda con un botón; mientras haya algo que no se puede
   cobrar (un textil fijo sin valor), no se deja guardar. */

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

const cobroDe = (modo, t) => (modo === "por_textil" ? t.cobro : modo);

/* Misma regla que core.precios_textiles.validar: {nombre: mensaje}. */
function validar(modo, textiles) {
  const errores = {};
  for (const t of textiles) {
    const valor = fmt.leerClp(t.valor);
    if (valor == null) {
      if (cobroDe(modo, t) === "fijo") errores[t.nombre] = "Falta el valor por metro.";
    } else if (!(valor > 0)) errores[t.nombre] = "El valor tiene que ser mayor que 0.";
  }
  return errores;
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

  // Lo guardado, como borrador: comparar contra esto dice si hay cambios.
  const original = useMemo(() => (datos ? aBorrador(datos) : null), [datos]);
  const actual = borrador || original;
  const errores = useMemo(() => (actual ? validar(actual.modo, actual.textiles) : {}), [actual]);
  if (cargando || !actual) return <Cargando />;

  const soloLectura = datos.solo_lectura;
  const hayCambios = JSON.stringify(actual) !== JSON.stringify(original);
  const cantidadErrores = Object.keys(errores).length;
  const resumen = Object.fromEntries(datos.textiles.map((t) => [t.nombre, t]));

  const cambiar = (cambio) => setBorrador({ ...actual, ...cambio });
  const cambiarTextil = (nombre, cambio) =>
    cambiar({ textiles: actual.textiles.map((t) => (t.nombre === nombre ? { ...t, ...cambio } : t)) });

  async function guardar() {
    if (cantidadErrores || guardando) return;
    setGuardando(true);
    try {
      const r = await api.guardar_precios_textiles({
        modo: actual.modo,
        textiles: actual.textiles.map((t) => ({ nombre: t.nombre, cobro: t.cobro, valor: fmt.leerClp(t.valor) })),
      });
      if (!r?.ok) {
        aviso(r?.errores?.[0]?.mensaje || "No se pudo guardar.", "error");
        return;
      }
      await recargar();
      setBorrador(null);
      aviso("Precios de textiles guardados.", "info");
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
               : "Por metro lineal (en Backlight, por metro cuadrado). En los que se cobran por rollo el valor es opcional: se usa solo si el textil no tiene ningún rollo con valor."}>
        {actual.textiles.map((t) => (
          <FilaTextil key={t.nombre} textil={t} resumen={resumen[t.nombre]} modo={actual.modo}
                      error={errores[t.nombre]} soloLectura={soloLectura} inventario={datos.inventario}
                      onCambiar={(cambio) => cambiarTextil(t.nombre, cambio)}
                      onRollos={() => setRollosDe(resumen[t.nombre])} />
        ))}
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

function FilaTextil({ textil: t, resumen, modo, error, soloLectura, inventario, onCambiar, onRollos }) {
  const cobro = cobroDe(modo, t);
  const r = resumen?.rollos;
  // Por rollo, sin ningún rollo con valor, el textil cae al valor fijo (o sale sin precio).
  const sinPrecio = cobro === "rollo" && !(r?.minimo != null) && !fmt.leerClp(t.valor);
  const id = `valor-${t.nombre}`;
  return (
    <div className="fila-ajuste fila-textil" data-invalido={error ? "" : undefined}>
      <span className="fila-textil__info">
        <label className="fila-textil__nombre" htmlFor={id}>{t.nombre}</label>
        <span className="fila-textil__sub">
          {resumen?.ancho ? `${fmt.cantidad(resumen.ancho)} m de ancho · ` : ""}
          {inventario ? textoRollos(r) : ""}
        </span>
        {error && <span className="fila-textil__error">{error}</span>}
        {!error && sinPrecio && <span className="fila-textil__aviso">Sin rollos con valor ni valor fijo: se cotizaría sin precio.</span>}
      </span>
      {modo === "por_textil" && (
        <Segmento etiqueta={`Cómo se cobra ${t.nombre}`} opciones={COBROS} valor={t.cobro}
                  deshabilitado={soloLectura} onCambiar={(c) => onCambiar({ cobro: c })} />
      )}
      <input className="entrada entrada--num fila-textil__valor" id={id} type="text" inputMode="numeric" autoComplete="off"
             placeholder={cobro === "rollo" ? "Opcional" : "$0"} aria-invalid={error ? true : undefined}
             disabled={soloLectura} value={t.valor}
             onChange={(e) => onCambiar({ valor: fmt.clp(e.target.value) })} />
      {inventario && (
        <button className="btn-fila-ajuste" type="button" title="Cambiar el valor de todos sus rollos"
                aria-label={`Cambiar el valor de todos los rollos de ${t.nombre}`}
                disabled={soloLectura || !r} onClick={onRollos}>
          <IconoRollos />
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
