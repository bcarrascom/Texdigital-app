/* Formato chileno (miles con punto, coma decimal). Mismas reglas que
   core/presentar_op.py (_fmt_medida / _fmt_cantidad), para que la pantalla y
   los documentos generados no muestren números distintos. */

export const medida = (v) => Number(v).toFixed(3).replace(".", ",");

export function cantidad(v) {
  const n = Math.round(Number(v) * 100) / 100;
  return n.toLocaleString("es-CL", { maximumFractionDigits: 2 });
}

export const pesos = (v) => "$" + Math.round(Number(v)).toLocaleString("es-CL");

/* "2026-10-20" o "2026/10/20" → "20-10-2026" */
export function fecha(iso) {
  if (!iso) return "";
  const [a, m, d] = String(iso).replace(/\//g, "-").split("-");
  return d && m && a ? `${d}-${m}-${a}` : iso;
}

/* Número de cotización/OP con ceros a la izquierda: 42 → "0042" */
export const numero = (n) => String(n).padStart(4, "0");
