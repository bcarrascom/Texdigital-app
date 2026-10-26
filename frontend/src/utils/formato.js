/* Formato chileno (miles con punto, coma decimal). Mismas reglas que
   core/presentar_op.py (_fmt_medida / _fmt_cantidad), para que la pantalla y
   los documentos generados no muestren números distintos. */

export const medida = (v) => Number(v).toFixed(3).replace(".", ",");

export function cantidad(v) {
  const n = Math.round(Number(v) * 100) / 100;
  return n.toLocaleString("es-CL", { maximumFractionDigits: 2 });
}

export const pesos = (v) => "$" + Math.round(Number(v)).toLocaleString("es-CL");

/* Como pesos(), pero con el signo ANTES del $ ("-$5.000", no "$-5.000"): para
   donde una cifra negativa de verdad pasa (una ganancia en rojo). pesos() no
   se cambia a propósito: tiene que dar lo mismo que los documentos generados. */
export const pesosConSigno = (v) => (v < 0 ? "-" + pesos(-v) : pesos(v));

/* Montos en pesos mientras se escriben (siempre enteros): se guarda solo el
   número, el "$" y los puntos de miles son de despliegue.
       leerClp("$12.500") → 12500     clp("12500") → "$12.500" */
export function leerClp(texto) {
  const limpio = String(texto ?? "").replace(/[^\d]/g, "");
  return limpio ? parseInt(limpio, 10) : null;
}
export function clp(texto) {
  const n = leerClp(texto);
  return n == null ? "" : "$" + n.toLocaleString("es-CL");
}

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

/* Si el dígito verificador del RUT calza (módulo 11). La versión canónica es
   core.repositorio.rut_valido: si allá cambia, acá también. */
export function rutValido(raw) {
  const s = String(raw ?? "").replace(/[^\dkK]/g, "").toUpperCase();
  if (s.length < 2 || !/^\d+$/.test(s.slice(0, -1))) return false;
  const cuerpo = s.slice(0, -1), dv = s.slice(-1);
  let suma = 0;
  [...cuerpo].reverse().forEach((d, i) => { suma += Number(d) * (2 + (i % 6)); });
  const resto = 11 - (suma % 11);
  return dv === (resto === 11 ? "0" : resto === 10 ? "K" : String(resto));
}

/* plural(3, "rollo", "rollos") → "3 rollos" */
export const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;

/* Días de calendario desde hoy hasta una fecha "dd/mm/aaaa" (o con guiones),
   sin horas: "hoy" no puede depender de a qué hora se mire. null si no se
   puede leer. */
export function diasHasta(fechaDMA) {
  const t = fechaDMAaTime(fechaDMA);
  if (!t) return null;
  const hoy = new Date();
  return Math.round((t - new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate())) / 86400000);
}

/* "Entrega en 3 días" · "Entrega hoy" · "Entrega atrasada hace 2 días" */
export function textoEntrega(fechaDMA) {
  const n = diasHasta(fechaDMA);
  if (n == null) return "";
  if (n > 0) return `Entrega en ${n} ${n === 1 ? "día" : "días"}`;
  if (n === 0) return "Entrega hoy";
  return `Entrega atrasada hace ${-n} ${-n === 1 ? "día" : "días"}`;
}

/* "20/10/2026" (o con guiones) → timestamp, 0 si no se puede leer. */
export function fechaDMAaTime(fechaDMA) {
  const [d, m, a] = String(fechaDMA || "").split(/[/-]/).map(Number);
  if (!d || !m || !a) return 0;
  return new Date(a, m - 1, d).getTime();
}
