/* Mocks de Configuración: precios y reglas (ver ui/api_configuracion.py).
   Los rollos son los mismos de mocks/inventario.js, así el resumen y "valor
   de todos los rollos" se ven también en Inventario. */
import { rollos } from "./inventario";

let ajustes = {
  modo: "por_textil",
  textiles: [
    { nombre: "Bistretch", ancho: 1.48, cobro: "fijo", valor: 11000, anteriores: ["Bi-stretch"] },
    { nombre: "Blackout", ancho: 1.48, cobro: "fijo", valor: 12000 },
    { nombre: "Felpa gruesa", ancho: 1.38, cobro: "rollo", valor: 12000 },
    { nombre: "Gasa", ancho: 1.46, cobro: "fijo", valor: 12000 },
    { nombre: "Lona mate", ancho: 3.2, cobro: "rollo", valor: null },
    { nombre: "Poliéster satinado", ancho: 1.5, cobro: "rollo", valor: null },
    { nombre: "Tela backlit", ancho: 3, cobro: "fijo", valor: 14000, backlight: true },
    { nombre: "Tela sin rollos", ancho: 1.5, cobro: "rollo", valor: null },
  ],
};

function resumen(nombre) {
  const suyos = rollos.filter((r) => r.nombre_textil === nombre);
  if (!suyos.length) return null;
  const valores = suyos.map((r) => r.valor).filter((v) => v != null);
  return {
    rollos: suyos.length, sin_valor: suyos.length - valores.length,
    minimo: valores.length ? Math.min(...valores) : null, maximo: valores.length ? Math.max(...valores) : null,
  };
}

const componentes = {
  estructuras: [
    { nombre: "Asta fibra de vidrio vela 2 mts", valor: 17000, unidad: "un.", por_materiales: null },
    { nombre: "Base auto", valor: 11000, unidad: "un.", por_materiales: "asociados" },
    { nombre: "Estaca", valor: 10000, unidad: "un.", por_materiales: null },
    { nombre: "Perfil 10 cm", valor: 9000, unidad: "un.", por_materiales: "mismo_nombre" },
  ],
  terminaciones: [
    { nombre: "Basta", valor: 3500, unidad: "un.", por_materiales: null },
    { nombre: "Bolsillos", valor: 3500, unidad: "un.", por_materiales: null },
    { nombre: "Ojetillos", valor: 14500, unidad: "un.", por_materiales: null },
  ],
};

let cajas = {
  luces: { "Basic 5": 14507, M3: 7756, "Malla 150": 40128 },
  traseras: { "Trovicel 122": 5000, "Alucobond 122x244": 14040 },
  armado: { minimo: 10000, simple: 7000, medio: 6000, complejo: 5000, jumbo: 4500 },
  fp: { 35: 13992, 100: 18794, 350: 40374 },
  perfiles: { "PERFIL 60 MM": 6974, "PERFIL 100 MM DOBLE": 11485 },
  pintura_por_ml: 4000,
};

const REGLAS_DEFECTO = { iva: 19, ml_minimo: 2, m2_minimo: 2, tramos_descuento: [[50, 20], [20, 10], [10, 5]] };
let reglas = structuredClone(REGLAS_DEFECTO);

const sinValor = (v) => !(v > 0);

const cobroDe = (modo, t) => (modo === "por_textil" ? t.cobro : modo);

export default {
  obtener_precios_textiles: () => ({
    modo: ajustes.modo, inventario: true, solo_lectura: false,
    textiles: ajustes.textiles.map((t) => ({ ...t, rollos: resumen(t.nombre) })),
  }),

  guardar_precios_textiles(datos) {
    const errores = datos.textiles
      .filter((t) => (t.valor == null ? cobroDe(datos.modo, t) === "fijo" : !(t.valor > 0)))
      .map((t) => ({ textil: t.nombre, mensaje: t.valor == null ? "Falta el valor por metro." : "El valor tiene que ser un monto mayor que 0." }));
    if (errores.length) return { ok: false, errores };
    ajustes = { modo: datos.modo, textiles: ajustes.textiles.map((t) => ({ ...t, ...datos.textiles.find((x) => x.nombre === t.nombre) })) };
    return { ok: true };
  },

  obtener_precios_componentes: (tipo) => ({ filas: structuredClone(componentes[tipo]), solo_lectura: false }),
  guardar_precios_componentes(tipo, filas) {
    const errores = filas.filter((f) => sinValor(f.valor)).map((f) => ({ nombre: f.nombre, mensaje: "Falta el valor." }));
    if (errores.length) return { ok: false, errores };
    componentes[tipo] = componentes[tipo].map((f) => ({ ...f, valor: filas.find((x) => x.nombre === f.nombre)?.valor ?? f.valor }));
    return { ok: true };
  },

  obtener_precios_cajas: () => ({ cajas: structuredClone(cajas), solo_lectura: false }),
  guardar_precios_cajas(nuevas) {
    const malos = Object.values(nuevas).flatMap((v) => (typeof v === "object" ? Object.values(v) : [v])).filter(sinValor);
    if (malos.length) return { ok: false, errores: [{ mensaje: "Falta un valor." }] };
    cajas = structuredClone(nuevas);
    return { ok: true };
  },

  obtener_reglas_cobro: () => ({ reglas: structuredClone(reglas), por_defecto: structuredClone(REGLAS_DEFECTO), solo_lectura: false }),
  guardar_reglas_cobro(nuevas) {
    if (!(nuevas.iva >= 0 && nuevas.iva < 100)) return { ok: false, errores: [{ campo: "iva", mensaje: "El IVA tiene que ser un % entre 0 y 100." }] };
    reglas = { ...nuevas, tramos_descuento: [...nuevas.tramos_descuento].sort((a, b) => b[0] - a[0]) };
    return { ok: true };
  },

  agregar_textil({ nombre, ancho, backlight, valor }) {
    nombre = (nombre || "").trim();
    const errores = {};
    if (!nombre) errores.nombre = "Falta el nombre.";
    else if (ajustes.textiles.some((t) => t.nombre.toLowerCase() === nombre.toLowerCase())) errores.nombre = "Ya existe uno con ese nombre.";
    const n = parseFloat(String(ancho).replace(",", "."));
    if (!(n > 0 && n <= 10)) errores.ancho = "El ancho tiene que ser más que 0 y hasta 10 m.";
    if (valor == null && ajustes.modo !== "rollo") errores.valor = "Falta el valor por metro.";
    if (Object.keys(errores).length) return { ok: false, errores };
    ajustes.textiles.push({ nombre, ancho: n, cobro: "fijo", valor: valor ?? null, backlight, agregado: true, anteriores: [] });
    return { ok: true };
  },
  editar_textil(actual, { nombre, ancho, backlight }) {
    nombre = (nombre || "").trim();
    const t = ajustes.textiles.find((x) => x.nombre === actual);
    if (!nombre) return { ok: false, errores: { nombre: "Falta el nombre." } };
    if (nombre !== actual && ajustes.textiles.some((x) => x !== t && x.nombre.toLowerCase() === nombre.toLowerCase())) {
      return { ok: false, errores: { nombre: "Ya existe uno con ese nombre." } };
    }
    let renombrados = 0;
    if (nombre !== actual) {
      for (const r of rollos) if (r.nombre_textil === actual) { r.nombre_textil = nombre; renombrados++; }
      t.anteriores = [...(t.anteriores || []), actual];
    }
    Object.assign(t, { nombre, ancho: parseFloat(String(ancho).replace(",", ".")), backlight });
    return { ok: true, rollos: renombrados };
  },
  agregar_componente(tipo, { nombre, unidad, valor }) {
    nombre = (nombre || "").trim();
    if (!nombre) return { ok: false, errores: { nombre: "Falta el nombre." } };
    if (componentes[tipo].some((c) => c.nombre.toLowerCase() === nombre.toLowerCase())) return { ok: false, errores: { nombre: "Ya existe uno con ese nombre." } };
    if (!(valor > 0)) return { ok: false, errores: { valor: "Falta el valor." } };
    componentes[tipo].push({ nombre, valor, unidad, por_materiales: null, agregado: true });
    return { ok: true };
  },

  fijar_valor_rollos(nombre, valor) {
    if (!(valor > 0)) return { ok: false, error: "El valor tiene que ser un monto mayor que 0." };
    let cambiados = 0;
    for (const r of rollos) {
      if (r.nombre_textil !== nombre || r.valor === valor) continue;
      r.valor = valor;
      cambiados++;
    }
    return { ok: true, cambiados };
  },
};
