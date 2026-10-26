import { useMemo, useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import IconoEliminar from "@/assets/svg/trash-2.svg?react";
import IconoMas from "@/assets/svg/plus.svg?react";
import { BarraGuardar, Fila, Grupo, NotaSoloLectura } from "./Ajustes";
import { useCambiosPendientes } from "./cambiosPendientes";

/* Reglas de cobro: el IVA, el mínimo que se cobra por textil y los tramos
   del descuento por volumen (ver core/reglas_cobro.py). Ajuste GLOBAL; cada
   cotización guarda las reglas con que se calculó, así que cambiarlas no
   cambia las ya hechas. */

const MAX_TRAMOS = 10;

/* "19" / "2,5" → número; vacío o ilegible → null. */
function leer(texto) {
  const t = String(texto ?? "").trim().replace(",", ".");
  if (!t || !/^\d*\.?\d*$/.test(t)) return null;
  const n = parseFloat(t);
  return isNaN(n) ? null : n;
}
const mostrar = (n) => String(n).replace(".", ",");
const soloNumero = (t) => t.replace(/[^\d,.]/g, "");

const aBorrador = (r) => ({
  iva: mostrar(r.iva), ml_minimo: mostrar(r.ml_minimo), m2_minimo: mostrar(r.m2_minimo),
  // De menor a mayor, como se leen: "desde 10 m², 5 %".
  tramos: [...r.tramos_descuento].sort((a, b) => a[0] - b[0]).map(([m2, pct]) => ({ m2: mostrar(m2), pct: mostrar(pct) })),
});

/* Los cambios del borrador, uno por línea, para el diálogo de salir. */
const textoTramos = (tramos) => tramos.map((t) => `desde ${t.m2 || "?"} m² ${t.pct || "?"} %`).join(" · ") || "sin tramos";
function describirCambios(original, actual) {
  const cambios = [];
  if (original.iva !== actual.iva) cambios.push(`IVA: ${original.iva} % → ${actual.iva || "?"} %`);
  if (original.ml_minimo !== actual.ml_minimo) cambios.push(`Mínimo de textiles: ${original.ml_minimo} ML → ${actual.ml_minimo || "?"} ML`);
  if (original.m2_minimo !== actual.m2_minimo) cambios.push(`Mínimo de Backlight: ${original.m2_minimo} m² → ${actual.m2_minimo || "?"} m²`);
  if (JSON.stringify(original.tramos) !== JSON.stringify(actual.tramos)) {
    cambios.push(`Descuento por volumen: ${textoTramos(original.tramos)} → ${textoTramos(actual.tramos)}`);
  }
  return cambios;
}

/* Misma regla que core.reglas_cobro.validar: {campo: mensaje}. */
function validar(b) {
  const e = {};
  const iva = leer(b.iva);
  if (iva == null || iva >= 100) e.iva = "Un % entre 0 y 100.";
  if (leer(b.ml_minimo) == null) e.ml_minimo = "0 o más.";
  if (leer(b.m2_minimo) == null) e.m2_minimo = "0 o más.";
  const vistos = new Set();
  b.tramos.forEach((t, i) => {
    const m2 = leer(t.m2), pct = leer(t.pct);
    if (!(m2 > 0)) e[`tramo:${i}`] = "Los m² tienen que ser más que 0.";
    else if (vistos.has(m2)) e[`tramo:${i}`] = "Ya hay un tramo desde esos m².";
    else if (!(pct > 0 && pct < 100)) e[`tramo:${i}`] = "El descuento, un % entre 0 y 100.";
    if (m2 != null) vistos.add(m2);
  });
  return e;
}

export default function Reglas() {
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(() => api.obtener_reglas_cobro(), []);
  const [borrador, setBorrador] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const original = useMemo(() => (datos ? aBorrador(datos.reglas) : null), [datos]);
  const actual = borrador || original;
  const errores = useMemo(() => (actual ? validar(actual) : {}), [actual]);
  useCambiosPendientes({
    cambios: borrador && original ? describirCambios(original, borrador) : [],
    error: Object.keys(errores).length
      ? (Object.keys(errores).length === 1 ? "hay 1 valor que no es válido." : `hay ${Object.keys(errores).length} valores que no son válidos.`) : null,
    guardar,
  });
  if (cargando || !actual) return <Cargando />;

  const soloLectura = datos.solo_lectura;
  const hayCambios = JSON.stringify(actual) !== JSON.stringify(original);
  const porDefecto = aBorrador(datos.por_defecto);
  const enDefecto = JSON.stringify(actual) === JSON.stringify(porDefecto);
  const cantidadErrores = Object.keys(errores).length;

  const cambiar = (cambio) => setBorrador({ ...actual, ...cambio });
  const cambiarTramo = (i, cambio) => cambiar({ tramos: actual.tramos.map((t, k) => (k === i ? { ...t, ...cambio } : t)) });

  async function guardar() {
    if (cantidadErrores || guardando) return false;
    setGuardando(true);
    try {
      const r = await api.guardar_reglas_cobro({
        iva: leer(actual.iva), ml_minimo: leer(actual.ml_minimo), m2_minimo: leer(actual.m2_minimo),
        tramos_descuento: actual.tramos.map((t) => [leer(t.m2), leer(t.pct)]),
      });
      if (!r?.ok) { aviso(r?.errores?.[0]?.mensaje || "No se pudo guardar.", "error"); return false; }
      await recargar();
      setBorrador(null);
      aviso("Reglas de cobro guardadas.", "info");
      return true;
    } finally {
      setGuardando(false);
    }
  }

  const campo = (clave, sufijo, etiqueta) => (
    <span className="regla-campo">
      <input className="entrada entrada--num regla-campo__entrada" type="text" inputMode="decimal" autoComplete="off"
             aria-label={etiqueta} aria-invalid={errores[clave] ? true : undefined} disabled={soloLectura}
             value={actual[clave]} onChange={(e) => cambiar({ [clave]: soloNumero(e.target.value) })} />
      <span className="regla-campo__sufijo">{sufijo}</span>
    </span>
  );

  return (
    <>
      <NotaSoloLectura visible={soloLectura} que="Estas reglas" />

      <Grupo titulo="Impuesto">
        <FilaRegla etiqueta="IVA" error={errores.iva}>{campo("iva", "%", "IVA en %")}</FilaRegla>
      </Grupo>

      <Grupo titulo="Mínimo que se cobra"
             pie="Si todos los productos de un mismo textil suman menos que esto, se cobra el mínimo. En Backlight se suman todos juntos.">
        <FilaRegla etiqueta="Textiles" error={errores.ml_minimo}>{campo("ml_minimo", "ML", "Mínimo de textiles en metros lineales")}</FilaRegla>
        <FilaRegla etiqueta="Backlight" error={errores.m2_minimo}>{campo("m2_minimo", "m²", "Mínimo de Backlight en metros cuadrados")}</FilaRegla>
      </Grupo>

      <Grupo titulo="Descuento por volumen"
             pie="Se descuenta del costo de impresión cuando los m² impresos de un textil llegan a un tramo (en Backlight, de todos juntos). Si el descuento del cliente sale mayor, se usa ese: nunca los dos.">
        {actual.tramos.length ? actual.tramos.map((t, i) => (
          <FilaRegla key={i} etiqueta={`Tramo ${i + 1}`} error={errores[`tramo:${i}`]}>
            <span className="regla-texto">desde</span>
            <span className="regla-campo">
              <input className="entrada entrada--num regla-campo__entrada" type="text" inputMode="decimal" autoComplete="off"
                     aria-label={`Tramo ${i + 1}: desde cuántos m²`} disabled={soloLectura} value={t.m2}
                     onChange={(e) => cambiarTramo(i, { m2: soloNumero(e.target.value) })} />
              <span className="regla-campo__sufijo">m²</span>
            </span>
            <span className="regla-campo">
              <input className="entrada entrada--num regla-campo__entrada" type="text" inputMode="decimal" autoComplete="off"
                     aria-label={`Tramo ${i + 1}: % de descuento`} disabled={soloLectura} value={t.pct}
                     onChange={(e) => cambiarTramo(i, { pct: soloNumero(e.target.value) })} />
              <span className="regla-campo__sufijo">%</span>
            </span>
            <button className="btn-fila-ajuste btn-fila-ajuste--peligro" type="button" title="Quitar tramo" disabled={soloLectura}
                    onClick={() => cambiar({ tramos: actual.tramos.filter((_, k) => k !== i) })}>
              <IconoEliminar />
            </button>
          </FilaRegla>
        )) : <p className="ajustes-vacio">Sin tramos: no hay descuento por volumen.</p>}
        {actual.tramos.length < MAX_TRAMOS && !soloLectura && (
          <Fila etiqueta="Agregar tramo" icono={IconoMas} color="#2E9D5B"
                onClick={() => cambiar({ tramos: [...actual.tramos, { m2: "", pct: "" }] })} />
        )}
      </Grupo>

      {!enDefecto && !soloLectura && (
        <Grupo>
          <Fila etiqueta="Volver a las reglas que traía la app" onClick={() => setBorrador(porDefecto)} />
        </Grupo>
      )}

      <BarraGuardar visible={hayCambios} guardando={guardando} onDescartar={() => setBorrador(null)} onGuardar={guardar}
                    error={cantidadErrores ? (cantidadErrores === 1 ? "hay 1 valor que no es válido." : `hay ${cantidadErrores} valores que no son válidos.`) : null} />
    </>
  );
}

function FilaRegla({ etiqueta, error, children }) {
  return (
    <div className="fila-ajuste fila-regla" data-invalido={error ? "" : undefined}>
      <span className="fila-textil__info">
        <span className="fila-textil__nombre">{etiqueta}</span>
        {error && <span className="fila-textil__error">{error}</span>}
      </span>
      <span className="fila-ajuste__control">{children}</span>
    </div>
  );
}
