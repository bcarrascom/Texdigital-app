import { useMemo, useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import * as fmt from "@/utils/formato";
import { BarraGuardar, Grupo, NotaSoloLectura } from "./Ajustes";
import { FilaPrecio } from "./ListaPrecios";
import { nombresMateriales } from "./Productos";

/* Backlight: los márgenes de costura del corte de la tela (ver
   core/corte_backlight.py) y lo que vale cada pieza de una caja (ver
   core/valor_cajas.py para cómo se suman). Las piezas son las del catálogo
   de la app; acá se cambia solo cuánto vale cada una. Un perfil con
   materiales de Inventario asociados cobra sus materiales ADEMÁS de su precio
   (para cobrar solo los materiales, el perfil va en $0). Todo se guarda
   junto, con la barra de abajo. */

const FALTA = { valor: "el valor de venta", consumo: "un consumo automático que se calcule al cotizar" };

/* Lo que dice la fila de un perfil con materiales asociados. */
function textoPerfil(materiales) {
  if (!materiales?.length) return {};
  const incompleto = materiales.find((m) => m.falta);
  return {
    sub: `Más sus materiales de Inventario: ${nombresMateriales(materiales)}`,
    nota: incompleto ? `Sus materiales no se cobran: a «${incompleto.nombre}» le falta ${FALTA[incompleto.falta]}.` : null,
    ayuda: incompleto ? null : "Se suman a este precio. Para cobrar solo los materiales, pon el perfil en $0.",
  };
}

const MARGENES = [
  { clave: "caja_terminada", nombre: "Caja terminada", sub: "Cuando se midió la caja terminada, o la caja es nuestra." },
  { clave: "area_visual", nombre: "Área visual", sub: "Cuando se midió el área visual: hay que envolver más perfil." },
];

/* "1,5" → 1.5; vacío o ilegible → null. */
function leerCm(texto) {
  const t = String(texto ?? "").trim().replace(",", ".");
  if (!t || !/^\d*\.?\d*$/.test(t)) return null;
  const n = parseFloat(t);
  return isNaN(n) ? null : n;
}

const ARMADO = {
  minimo: "Menos de 1 ML", simple: "De 1 a 4 ML", medio: "De 4 a 6 ML", complejo: "De 6 a 8 ML", jumbo: "8 ML o más",
};

const SECCIONES = [
  { clave: "luces", titulo: "Luces · por unidad" },
  { clave: "fp", titulo: "Fuentes de poder · por unidad", nombre: (k) => `${k} W` },
  { clave: "perfiles", titulo: "Perfiles · por metro lineal de caja" },
  { clave: "traseras", titulo: "Traseras · por m² de caja" },
  { clave: "armado", titulo: "Armado · por metro lineal de caja", nombre: (k) => ARMADO[k] || k,
    pie: "La tarifa se elige por los metros lineales que tiene la caja, y se cobra por cada uno." },
];

const aBorrador = (cajas) => ({
  ...Object.fromEntries(SECCIONES.map(({ clave }) =>
    [clave, Object.fromEntries(Object.entries(cajas[clave]).map(([k, v]) => [k, fmt.clp(v)]))])),
  pintura_por_ml: fmt.clp(cajas.pintura_por_ml),
});
const aBorradorMargenes = (m) => Object.fromEntries(MARGENES.map(({ clave }) => [clave, String(m[clave]).replace(".", ",")]));

export default function Cajas() {
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(() => api.obtener_precios_cajas(), []);
  const [borrador, setBorrador] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const original = useMemo(() => (datos ? { ...aBorrador(datos.cajas), margenes: aBorradorMargenes(datos.margenes_cm) } : null), [datos]);
  const actual = borrador || original;
  const errores = useMemo(() => {
    if (!actual) return {};
    const malos = {};
    for (const { clave } of SECCIONES) {
      // Un perfil puede ir en $0 (ver core.precios_componentes); lo demás, no.
      const minimo = clave === "perfiles" ? 0 : 1;
      for (const [k, v] of Object.entries(actual[clave])) {
        const n = fmt.leerClp(v);
        if (n == null || n < minimo) malos[`${clave}:${k}`] = v === "" ? "Falta el valor." : "Tiene que ser mayor que 0.";
      }
    }
    if (!(fmt.leerClp(actual.pintura_por_ml) > 0)) malos.pintura = actual.pintura_por_ml === "" ? "Falta el valor." : "Tiene que ser mayor que 0.";
    for (const { clave } of MARGENES) {
      const n = leerCm(actual.margenes[clave]);
      if (n == null || n > 20) malos[`margen:${clave}`] = "Un margen entre 0 y 20 cm.";
    }
    return malos;
  }, [actual]);
  if (cargando || !actual) return <Cargando />;

  const soloLectura = datos.solo_lectura;
  const margenesSoloLectura = datos.margenes_solo_lectura;
  const hayCambios = JSON.stringify(actual) !== JSON.stringify(original);
  const cantidadErrores = Object.keys(errores).length;

  const cambiar = (seccion, k, valor) => setBorrador({ ...actual, [seccion]: { ...actual[seccion], [k]: valor } });

  async function guardar() {
    if (cantidadErrores || guardando) return;
    setGuardando(true);
    try {
      // Los precios y los márgenes son dos archivos: se guarda solo lo que cambió.
      const { margenes, ...precios } = actual;
      const { margenes: margenesAntes, ...preciosAntes } = original;
      if (JSON.stringify(precios) !== JSON.stringify(preciosAntes)) {
        const enviar = Object.fromEntries(SECCIONES.map(({ clave }) =>
          [clave, Object.fromEntries(Object.entries(precios[clave]).map(([k, v]) => [k, fmt.leerClp(v)]))]));
        enviar.pintura_por_ml = fmt.leerClp(precios.pintura_por_ml);
        const r = await api.guardar_precios_cajas(enviar);
        if (!r?.ok) { aviso(r?.errores?.[0]?.mensaje || "No se pudo guardar.", "error"); return; }
      }
      if (JSON.stringify(margenes) !== JSON.stringify(margenesAntes)) {
        const r = await api.guardar_margenes_corte(Object.fromEntries(MARGENES.map(({ clave }) => [clave, leerCm(margenes[clave])])));
        if (!r?.ok) { aviso(Object.values(r?.errores || {})[0] || "No se pudo guardar.", "error"); return; }
      }
      await recargar();
      setBorrador(null);
      aviso("Ajustes de Backlight guardados.", "info");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <NotaSoloLectura visible={soloLectura} />

      <Grupo titulo="Corte de la tela"
             pie="Se le suma a cada medida del backlight para cortar la tela. Lo usan la OP impresa y el panel de producción, y no cambia el precio.">
        {MARGENES.map((m) => (
          <div key={m.clave} className="fila-ajuste fila-regla" data-invalido={errores[`margen:${m.clave}`] ? "" : undefined}>
            <span className="fila-textil__info">
              <label className="fila-textil__nombre" htmlFor={`margen-${m.clave}`}>{m.nombre}</label>
              <span className="fila-textil__sub">{m.sub}</span>
              {errores[`margen:${m.clave}`] && <span className="fila-textil__error">{errores[`margen:${m.clave}`]}</span>}
            </span>
            <span className="regla-campo">
              <span className="regla-texto">+</span>
              <input className="entrada entrada--num regla-campo__entrada" id={`margen-${m.clave}`} type="text" inputMode="decimal"
                     autoComplete="off" disabled={margenesSoloLectura} value={actual.margenes[m.clave]}
                     onChange={(e) => setBorrador({ ...actual, margenes: { ...actual.margenes, [m.clave]: e.target.value.replace(/[^\d,.]/g, "") } })} />
              <span className="regla-campo__sufijo">cm</span>
            </span>
          </div>
        ))}
      </Grupo>

      {SECCIONES.map((s) => (
        <Grupo key={s.clave} titulo={s.titulo}
               pie={s.clave === "perfiles"
                 ? "Por metro lineal de caja. Para cobrar además lo que gasta de un material de Inventario, asócialo al perfil en la ficha del material; para cobrar solo los materiales, deja el perfil en $0."
                 : s.pie}>
          {Object.entries(actual[s.clave]).map(([k, v]) => {
            const m = s.clave === "perfiles" ? textoPerfil(datos.materiales_perfiles?.[k]) : {};
            return (
              <FilaPrecio key={k} id={`caja-${s.clave}-${k}`} nombre={s.nombre ? s.nombre(k) : k} valor={v}
                          sub={m.sub} ayuda={m.ayuda} nota={m.nota}
                          error={errores[`${s.clave}:${k}`]} deshabilitado={soloLectura} onCambiar={(x) => cambiar(s.clave, k, x)} />
            );
          })}
        </Grupo>
      ))}
      <Grupo titulo="Pintura · por metro lineal de caja">
        <FilaPrecio id="caja-pintura" nombre="Pintura" valor={actual.pintura_por_ml}
                    error={errores.pintura} deshabilitado={soloLectura}
                    onCambiar={(x) => setBorrador({ ...actual, pintura_por_ml: x })} />
      </Grupo>
      <BarraGuardar visible={hayCambios} guardando={guardando} onDescartar={() => setBorrador(null)} onGuardar={guardar}
                    error={cantidadErrores ? (cantidadErrores === 1 ? "1 valor falta o no es válido." : `${cantidadErrores} valores faltan o no son válidos.`) : null} />
    </>
  );
}
