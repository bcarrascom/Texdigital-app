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

/* "1,5" / "1.5" / 1.5 → 1.5; lo que no se pueda leer, 0. */
export function aNumero(v) {
  const x = parseFloat(String(v ?? "").replace(",", "."));
  return isNaN(x) ? 0 : x;
}

export const soloDigitos = (v) => String(v ?? "").replace(/\D/g, "");

/* Formato chileno del RUT mientras se escribe ("12.345.678-9"). La versión
   canónica es core.repositorio.formatear_rut — esta es la misma regla del
   lado del navegador para no cruzar el puente en cada tecla: si allá
   cambia, hay que cambiarla acá también. */
export function rut(raw) {
  const s = String(raw ?? "").replace(/[^\dkK]/g, "").toUpperCase();
  if (!s) return "";
  const cuerpo = s.slice(0, -1), dv = s.slice(-1);
  if (!cuerpo) return dv;
  return cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + "-" + dv;
}

/* plural(3, "rollo", "rollos") → "3 rollos" */
export const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;

/* "20/10/2026" (o con guiones) → timestamp, 0 si no se puede leer. */
export function fechaDMAaTime(fechaDMA) {
  const [d, m, a] = String(fechaDMA || "").split(/[/-]/).map(Number);
  if (!d || !m || !a) return 0;
  return new Date(a, m - 1, d).getTime();
}
