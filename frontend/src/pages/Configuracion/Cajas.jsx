import { useMemo, useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import * as fmt from "@/utils/formato";
import { BarraGuardar, Grupo, NotaSoloLectura } from "./Ajustes";
import { FilaPrecio } from "./ListaPrecios";

/* Cajas de Backlight: lo que vale cada pieza de una caja (ver
   core/valor_cajas.py para cómo se suman). Las piezas son las del catálogo
   de la app; acá se cambia solo cuánto vale cada una. */

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

export default function Cajas() {
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(() => api.obtener_precios_cajas(), []);
  const [borrador, setBorrador] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const original = useMemo(() => (datos ? aBorrador(datos.cajas) : null), [datos]);
  const actual = borrador || original;
  const errores = useMemo(() => {
    if (!actual) return {};
    const malos = {};
    for (const { clave } of SECCIONES) {
      for (const [k, v] of Object.entries(actual[clave])) if (!(fmt.leerClp(v) > 0)) malos[`${clave}:${k}`] = v === "" ? "Falta el valor." : "Tiene que ser mayor que 0.";
    }
    if (!(fmt.leerClp(actual.pintura_por_ml) > 0)) malos.pintura = actual.pintura_por_ml === "" ? "Falta el valor." : "Tiene que ser mayor que 0.";
    return malos;
  }, [actual]);
  if (cargando || !actual) return <Cargando />;

  const soloLectura = datos.solo_lectura;
  const hayCambios = JSON.stringify(actual) !== JSON.stringify(original);
  const cantidadErrores = Object.keys(errores).length;

  const cambiar = (seccion, k, valor) => setBorrador({ ...actual, [seccion]: { ...actual[seccion], [k]: valor } });

  async function guardar() {
    if (cantidadErrores || guardando) return;
    setGuardando(true);
    try {
      const enviar = Object.fromEntries(SECCIONES.map(({ clave }) =>
        [clave, Object.fromEntries(Object.entries(actual[clave]).map(([k, v]) => [k, fmt.leerClp(v)]))]));
      enviar.pintura_por_ml = fmt.leerClp(actual.pintura_por_ml);
      const r = await api.guardar_precios_cajas(enviar);
      if (!r?.ok) { aviso(r?.errores?.[0]?.mensaje || "No se pudo guardar.", "error"); return; }
      await recargar();
      setBorrador(null);
      aviso("Precios de cajas guardados.", "info");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <NotaSoloLectura visible={soloLectura} />
      {SECCIONES.map((s) => (
        <Grupo key={s.clave} titulo={s.titulo} pie={s.pie}>
          {Object.entries(actual[s.clave]).map(([k, v]) => (
            <FilaPrecio key={k} id={`caja-${s.clave}-${k}`} nombre={s.nombre ? s.nombre(k) : k} valor={v}
                        error={errores[`${s.clave}:${k}`]} deshabilitado={soloLectura} onCambiar={(x) => cambiar(s.clave, k, x)} />
          ))}
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
