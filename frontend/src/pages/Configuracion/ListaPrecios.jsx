import { useMemo, useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import IconoMas from "@/assets/svg/plus.svg?react";
import * as fmt from "@/utils/formato";
import { BarraGuardar, Fila, Grupo, NotaSoloLectura } from "./Ajustes";
import { DialogoComponente } from "./DialogosCatalogo";

/* Estructuras y Terminaciones: cuánto se cobra por cada una (ver
   core/precios_componentes.py). Los nombres son los del catálogo de la app;
   acá se cambia el valor. Ajuste GLOBAL (Dropbox), se guarda todo junto y no
   se deja guardar con un valor vacío o en 0. Agregar una nueva es aparte, en
   un diálogo que se aplica al confirmar (ver core/catalogo.py). */

const UNIDAD = { "un.": "por unidad", ML: "por metro lineal" };

const FALTA = { valor: "el valor de venta", consumo: "un consumo automático que se calcule al cotizar" };

/* Una estructura con materiales de Inventario asociados se cobra por lo que
   gasta de ellos (ver core.repositorio_materiales.cobro_materiales_producto).
   Su valor de acá queda de respaldo: vale solo si a uno de esos materiales le
   falta con qué cobrarlo. Lo decimos en la fila, para que nadie cambie un
   valor que no se está usando sin saberlo. */
function textoMateriales(materiales) {
  if (!materiales?.length) return {};
  const nombres = materiales.map((m) => m.nombre).join(", ");
  const incompleto = materiales.find((m) => m.falta);
  if (incompleto) {
    return {
      sub: `Materiales de Inventario asociados: ${nombres}`,
      nota: `Se cobra este valor, no sus materiales: a «${incompleto.nombre}» le falta ${FALTA[incompleto.falta]}.`,
    };
  }
  return {
    sub: `Se cobra por sus materiales de Inventario: ${nombres}`,
    ayuda: "Este valor solo se usa si a uno de sus materiales le falta con qué cobrarlo.",
  };
}

export function Estructuras() {
  return <ListaPrecios tipo="estructuras" singular="estructura" plural="estructuras"
                       pie="Para que una estructura se cobre por lo que gasta de un material de Inventario, asócialo en la ficha del material (Inventario › Materiales › Editar). Que se llamen igual no los conecta." />;
}

export function Terminaciones() {
  return <ListaPrecios tipo="terminaciones" singular="terminación" plural="terminaciones" />;
}

const aBorrador = (filas) => filas.map((f) => ({ nombre: f.nombre, valor: f.valor == null ? "" : fmt.clp(f.valor) }));

function ListaPrecios({ tipo, singular, plural, pie }) {
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(() => api.obtener_precios_componentes(tipo), [tipo]);
  const [borrador, setBorrador] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [agregando, setAgregando] = useState(false);

  const original = useMemo(() => (datos ? aBorrador(datos.filas) : null), [datos]);
  const actual = borrador || original;
  const errores = useMemo(() => Object.fromEntries((actual || [])
    .filter((f) => !(fmt.leerClp(f.valor) > 0))
    .map((f) => [f.nombre, f.valor === "" ? "Falta el valor." : "El valor tiene que ser mayor que 0."])), [actual]);
  if (cargando || !actual) return <Cargando />;

  const hayCambios = JSON.stringify(actual) !== JSON.stringify(original);
  const cantidadErrores = Object.keys(errores).length;
  const info = Object.fromEntries(datos.filas.map((f) => [f.nombre, f]));

  async function guardar() {
    if (cantidadErrores || guardando) return;
    setGuardando(true);
    try {
      const r = await api.guardar_precios_componentes(tipo, actual.map((f) => ({ nombre: f.nombre, valor: fmt.leerClp(f.valor) })));
      if (!r?.ok) { aviso(r?.errores?.[0]?.mensaje || "No se pudo guardar.", "error"); return; }
      await recargar();
      setBorrador(null);
      aviso(`Precios de ${plural} guardados.`, "info");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <NotaSoloLectura visible={datos.solo_lectura} />
      <Grupo titulo={fmt.plural(actual.length, singular, plural)} pie={pie}>
        {actual.map((f) => {
          const i = info[f.nombre];
          const m = textoMateriales(i.materiales);
          return (
            <FilaPrecio key={f.nombre} id={`${tipo}-${f.nombre}`} nombre={f.nombre} valor={f.valor}
                        sub={m.sub || [UNIDAD[i.unidad], i.agregado && "agregada en Configuración"].filter(Boolean).join(" · ")}
                        ayuda={m.ayuda} nota={m.nota}
                        error={errores[f.nombre]} deshabilitado={datos.solo_lectura}
                        onCambiar={(valor) => setBorrador(actual.map((x) => (x.nombre === f.nombre ? { ...x, valor } : x)))} />
          );
        })}
        {!datos.solo_lectura && !datos.catalogo_solo_lectura && (
          <Fila etiqueta={`Agregar ${singular}`} icono={IconoMas} color="#2E9D5B"
                onClick={() => (hayCambios ? aviso("Primero guarda o descarta los cambios de precios.", "aviso") : setAgregando(true))} />
        )}
      </Grupo>
      <DialogoComponente abierto={agregando} tipo={tipo} singular={singular} onCerrar={() => setAgregando(false)}
                         onHecho={async () => {
                           setAgregando(false);
                           await recargar();
                           setBorrador(null);
                           aviso(`${singular[0].toUpperCase()}${singular.slice(1)} agregada.`, "info");
                         }} />
      <BarraGuardar visible={hayCambios} guardando={guardando} onDescartar={() => setBorrador(null)} onGuardar={guardar}
                    error={cantidadErrores ? `${fmt.plural(cantidadErrores, singular, plural)} sin un valor válido.` : null} />
    </>
  );
}

/* Una fila con nombre, una línea chica debajo y el monto a la derecha. La
   usan también Cajas. */
export function FilaPrecio({ id, nombre, sub, ayuda, nota, error, valor, deshabilitado, onCambiar }) {
  return (
    <div className="fila-ajuste fila-textil" data-invalido={error ? "" : undefined}>
      <span className="fila-textil__info">
        <label className="fila-textil__nombre" htmlFor={id}>{nombre}</label>
        {sub && <span className="fila-textil__sub">{sub}</span>}
        {ayuda && <span className="fila-textil__sub">{ayuda}</span>}
        {error && <span className="fila-textil__error">{error}</span>}
        {!error && nota && <span className="fila-textil__aviso">{nota}</span>}
      </span>
      <input className="entrada entrada--num fila-textil__valor" id={id} type="text" inputMode="numeric" autoComplete="off"
             placeholder="$0" aria-invalid={error ? true : undefined} disabled={deshabilitado} value={valor}
             onChange={(e) => onCambiar(fmt.clp(e.target.value))} />
    </div>
  );
}
