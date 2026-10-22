/* Mocks de Configuración › Textiles (ver ui/api_configuracion.py). Los
   rollos son los mismos de mocks/inventario.js, así el resumen y "valor de
   todos los rollos" se ven también en Inventario. */
import { rollos } from "./inventario";

let ajustes = {
  modo: "por_textil",
  textiles: [
    { nombre: "Bistretch", ancho: 1.48, cobro: "fijo", valor: 11000 },
    { nombre: "Blackout", ancho: 1.48, cobro: "fijo", valor: 12000 },
    { nombre: "Felpa gruesa", ancho: 1.38, cobro: "rollo", valor: 12000 },
    { nombre: "Gasa", ancho: 1.46, cobro: "fijo", valor: 12000 },
    { nombre: "Lona mate", ancho: 3.2, cobro: "rollo", valor: null },
    { nombre: "Poliéster satinado", ancho: 1.5, cobro: "rollo", valor: null },
    { nombre: "Tela backlit", ancho: 3, cobro: "fijo", valor: 14000 },
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
