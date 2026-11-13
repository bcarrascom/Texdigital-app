import { useEffect, useRef, useState } from "react";
import { animate, cubicBezier, motion, useMotionValue, useReducedMotion, useTransform } from "motion/react";
import "./CorreoEnviado.css";

/* "Correo enviado" (idea de Bruno, 2026-11-12): un rectángulo chico aparece
   abajo a la derecha, con su borde derecho más allá del borde de la ventana.
   Adentro, el sobre abierto se cierra (un Lottie del ícono mail de Feather
   que se abre, "mail.json", pasado al revés), y ya cerrado se va hacia la
   derecha con ease-in hasta salir de la pantalla: el correo se empaquetó y
   salió. Después el rectángulo se retira.

   Está atada al envío: Python la pide cada vez que sale un correo
   (core.correos.enviar → ApiApp._correo_enviado → window.TD.correoEnviado),
   venga de donde venga. Ninguna pantalla la llama por su cuenta: la que
   envió, si quiere mostrar su aviso de texto después, espera a que termine:

       const r = await api.enviar_…();
       if (r.ok) { await trasCorreoEnviado(); aviso("Correo enviado a …"); }

   La capa (<CapaCorreoEnviado />) se monta una vez, en App. Si se piden
   varias seguidas, van una detrás de otra. Con "reducir movimiento" del
   sistema, no se muestra y resuelve al tiro.

   Para verla y ajustarla: la página de desarrollo (botón "dev" del pie del
   menú) la reproduce con otros tiempos y más lento, y muestra el sobre
   cuadro a cuadro. Los tiempos que se usan de verdad son TIEMPOS, abajo.

   El sobre se dibuja con las mismas formas y cuadros clave del Lottie
   (32×32, 20 cuadros a 30 fps): `cuadro` va de 20 (abierto) a 0 (cerrado) y
   de él sale cada trazo. */

let reproducir = null;   // lo pone la capa montada

/* `opciones` (solo para la página de desarrollo): { tiempos: {…TIEMPOS},
   velocidad: 0.25 = cuatro veces más lento }. */
export function animarCorreoEnviado(opciones = {}) {
  return reproducir ? reproducir(opciones) : Promise.resolve();
}

/* Resuelve cuando no queda ninguna animación por mostrar. Espera un poco
   antes de mirar: el pedido de Python puede llegar justo después de la
   respuesta del envío. */
let enCurso = Promise.resolve();
export async function trasCorreoEnviado() {
  await new Promise((r) => setTimeout(r, 120));
  await enCurso;
}

// ── El sobre, cuadro a cuadro ──────────────────────────────────────────────

const CUADROS = 20;
const FPS = 30;
const suave = cubicBezier(0.3, 0, 0.3, 1);   // el ease de las posiciones del Lottie

const lerp = (a, b, t) => a + (b - a) * t;
const tramo = (f, desde, hasta) => Math.min(1, Math.max(0, (f - desde) / (hasta - desde)));

/* Valor en el cuadro f de una lista de [cuadro, valor] (lineal entre claves). */
function claves(f, lista) {
  if (f <= lista[0][0]) return lista[0][1];
  for (let i = 1; i < lista.length; i++) {
    const [f1, v1] = lista[i];
    if (f <= f1) {
      const [f0, v0] = lista[i - 1];
      return lerp(v0, v1, (f - f0) / (f1 - f0));
    }
  }
  return lista[lista.length - 1][1];
}

// Cuánto baja todo el sobre al abrirse (cuadros 0 → 15).
const bajada = (f) => lerp(0, 2.5, suave(tramo(f, 0, 15)));

/* El cuerpo: rectángulo redondeado de 20×16 centrado en (16, 16), que empieza
   arriba al medio y va en el sentido del reloj (como en el Lottie, así el
   recorte abre justo el borde de arriba). */
const cuerpo = (f) => {
  const y = bajada(f);
  return `M16 ${8 + y} H24 A2 2 0 0 1 26 ${10 + y} V${22 + y} A2 2 0 0 1 24 ${24 + y} H8 `
    + `A2 2 0 0 1 6 ${22 + y} V${10 + y} A2 2 0 0 1 8 ${8 + y} Z`;
};
const CUERPO_INICIO = [[5, 0], [6, 4], [7, 10], [8, 12], [10, 13], [13, 14]];
const CUERPO_FIN = [[5, 100], [6, 96], [7, 90], [8, 88], [10, 87], [13, 86]];

/* La solapa: una V que se da vuelta hacia arriba (cuadros 0 → 15). */
const solapa = (f) => {
  const t = suave(tramo(f, 0, 15));
  const x = lerp(10, 9.188, t), ya = lerp(-3.5, -5.125, t), yb = lerp(3.5, -12.25, t);
  const cy = 13.5 + bajada(f);
  return `M${16 + x} ${cy + ya} L16 ${cy + yb} L${16 - x} ${cy + ya}`;
};
/* El pliegue de adentro: la misma V, fija, que aparece al abrirse. */
const pliegue = (f) => {
  const cy = 13.5 + bajada(f);
  return `M26 ${cy - 3.5} L16 ${cy + 3.5} L6 ${cy - 3.5}`;
};

/* La hoja que asoma: sube (cuadros 10 → 20) y se ve la mitad de arriba de su
   contorno (recorte 25 % → 75 %). */
const hoja = (f) => {
  const cy = lerp(20.826, 14.201, suave(tramo(f, 10, 20))) + bajada(f);
  const p = (x, y) => `${16 + x} ${cy + y}`;
  return `M${p(-7.046, 3.799)} L${p(-7.046, -1.818)} Q${p(-7.046, -3.818)} ${p(-5.046, -3.818)} `
    + `L${p(5.046, -3.818)} Q${p(7.046, -3.818)} ${p(7.046, -1.818)} L${p(7.046, 3.818)}`;
};
const HOJA_INICIO = [[11, 50], [13, 36.444], [14, 30.667], [15, 26.889], [20, 25]];
const HOJA_FIN = [[11, 50], [13, 63.056], [14, 69.583], [15, 72.111], [20, 75]];

export function Sobre({ cuadro, className = "correo-enviado__sobre" }) {
  const dCuerpo = useTransform(cuadro, cuerpo);
  const largoCuerpo = useTransform(cuadro, (f) => (claves(f, CUERPO_FIN) - claves(f, CUERPO_INICIO)) / 100);
  const desfaseCuerpo = useTransform(cuadro, (f) => claves(f, CUERPO_INICIO) / 100);
  const dSolapa = useTransform(cuadro, solapa);
  const dPliegue = useTransform(cuadro, pliegue);
  const opPliegue = useTransform(cuadro, (f) => tramo(f, 0, 2));
  const dHoja = useTransform(cuadro, hoja);
  const largoHoja = useTransform(cuadro, (f) => (claves(f, HOJA_FIN) - claves(f, HOJA_INICIO)) / 100);
  const desfaseHoja = useTransform(cuadro, (f) => claves(f, HOJA_INICIO) / 100);
  const opHoja = useTransform(largoHoja, (l) => (l > 0.005 ? 1 : 0));   // un trazo de largo 0 igual dejaría un punto

  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth={2}
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <motion.path d={dCuerpo} pathLength={largoCuerpo} pathOffset={desfaseCuerpo} />
      <motion.path d={dPliegue} style={{ opacity: opPliegue }} />
      <motion.path d={dSolapa} />
      <motion.path d={dHoja} pathLength={largoHoja} pathOffset={desfaseHoja} style={{ opacity: opHoja }} />
    </svg>
  );
}

// ── La capa ────────────────────────────────────────────────────────────────

export { CUADROS };

/* Cuánto dura cada parte, en milisegundos (los eligió Bruno en la página de
   desarrollo, 2026-11-12). El cierre va más rápido que el Lottie (667 ms). */
export const TIEMPOS = {
  entra: 220,    // el rectángulo entra
  cierra: 380,   // el sobre se cierra
  pausa: 170,    // cerrado, quieto
  seVa: 370,     // el sobre se va a la derecha
  sale: 210,     // el rectángulo se retira
};
export const ETAPAS = [
  { clave: "entra", nombre: "Entra el rectángulo" },
  { clave: "cierra", nombre: "Se cierra el sobre" },
  { clave: "pausa", nombre: "Pausa, cerrado" },
  { clave: "seVa", nombre: "El sobre se va" },
  { clave: "sale", nombre: "Sale el rectángulo" },
];
const EASE = {
  entra: [0.22, 1, 0.36, 1],    // ease-out
  cierra: "linear",             // el ease de cada trazo ya va en los cuadros clave
  seVa: [0.55, 0, 1, 0.45],     // ease-in
  sale: [0.4, 0, 1, 1],
};

const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

export default function CapaCorreoEnviado() {
  const reducido = useReducedMotion();
  const cola = useRef([]);            // los que esperan su turno: [resolver]
  const ocupada = useRef(false);
  const mostrado = useRef(null);      // el id que ya se animó (React puede correr el efecto dos veces)
  const [turno, setTurno] = useState(null);   // { id, resolver, opciones } del que se está mostrando
  const caja = useRef(null);
  const sobre = useRef(null);
  const cuadro = useMotionValue(CUADROS);

  useEffect(() => {
    reproducir = (opciones) => {
      if (reducido) return Promise.resolve();
      const p = new Promise((resolver) => {
        if (ocupada.current) { cola.current.push({ resolver, opciones }); return; }
        ocupada.current = true;
        setTurno({ id: Date.now(), resolver, opciones });
      });
      enCurso = enCurso.then(() => p);   // trasCorreoEnviado espera también a esta
      return p;
    };
    window.TD = window.TD || {};
    window.TD.correoEnviado = () => { animarCorreoEnviado(); };
    return () => { reproducir = null; delete window.TD.correoEnviado; };
  }, [reducido]);

  useEffect(() => {
    if (!turno || mostrado.current === turno.id) return;
    mostrado.current = turno.id;
    const t = { ...TIEMPOS, ...turno.opciones?.tiempos };
    const lento = 1 / (turno.opciones?.velocidad || 1);
    const en = (clave) => ({ duration: (t[clave] * lento) / 1000, ease: EASE[clave] });
    (async () => {
      try {
        cuadro.set(CUADROS);
        await animate(caja.current, { x: ["110%", "0%"] }, en("entra"));
        await animate(cuadro, 0, en("cierra"));
        await esperar(t.pausa * lento);
        await animate(sobre.current, { x: [0, 200] }, en("seVa"));
        await animate(caja.current, { x: "110%" }, en("sale"));
      } finally {
        turno.resolver();
        const siguiente = cola.current.shift();
        if (siguiente) setTurno({ id: Date.now() + 1, ...siguiente });
        else { ocupada.current = false; setTurno(null); }
      }
    })();
  }, [turno, cuadro]);

  if (!turno) return null;
  return (
    <div key={turno.id} ref={caja} className="correo-enviado" role="status">
      <span className="correo-enviado__texto">Correo enviado</span>
      <div ref={sobre} className="correo-enviado__mover">
        <Sobre cuadro={cuadro} />
      </div>
    </div>
  );
}
