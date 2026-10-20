/* ═══════════════════════════════════════════════════════════════════════════
   api.js — el puente entre React y Python. Reemplaza a
   recursos/pantallas/api.js con la misma idea: ninguna página sabe dónde
   corre, todas llaman igual.

       import { api } from "@/services/api";
       const op = await api.obtener_despacho(numero);   // siempre una promesa

     · Dentro de la app (pywebview) → window.pywebview.api.<método>
     · En el navegador con `npm run dev` → services/mocks/*.js
     · (a futuro, versión web) → fetch a una API HTTP: se cambia acá y
       ninguna página se entera.

   En el build de producción NUNCA se cae a los mocks: si pywebview tarda,
   se espera — mostrar datos inventados en la app real sería peor que
   esperar un poco más.
   ═══════════════════════════════════════════════════════════════════════════ */

/* pywebview avisa con 'pywebviewready'. Si en este tiempo no llegó y
   estamos en desarrollo, asumimos navegador. */
const TIMEOUT_MOCK = 1200;

let modo = null;      // "app" | "mock", se resuelve una sola vez
let listo = null;     // promesa de esa resolución
let mocks = null;     // métodos de mocks/*.js, cargados solo en modo mock

function resolverModo() {
  if (listo) return listo;
  listo = new Promise((resolve) => {
    const enApp = () => {
      modo = "app";
      resolve(modo);
    };
    if (window.pywebview?.api) return enApp();
    window.addEventListener("pywebviewready", enApp, { once: true });
    if (import.meta.env.DEV) {
      setTimeout(() => {
        if (modo) return;
        modo = "mock";
        document.documentElement.dataset.modo = "mock";
        resolve(modo);
      }, TIMEOUT_MOCK);
    }
  });
  return listo;
}

/* Todos los mocks juntos en un solo objeto: en una SPA no hay "pantalla
   actual" que elegir, y dos páginas que llaman al mismo método de Python
   tienen que recibir lo mismo. */
async function cargarMocks() {
  if (mocks) return mocks;
  // Detrás de DEV para que los mocks ni siquiera entren al build.
  const modulos = import.meta.env.DEV ? import.meta.glob("./mocks/*.js") : {};
  const cargados = await Promise.all(Object.values(modulos).map((importar) => importar()));
  mocks = Object.assign({}, ...cargados.map((m) => m.default));
  return mocks;
}

async function llamar(metodo, args) {
  if ((await resolverModo()) === "app") {
    const fn = window.pywebview.api[metodo];
    if (typeof fn !== "function") {
      throw new Error(`La API de Python no expone '${metodo}' (ver ui/api_app.py).`);
    }
    return fn.apply(window.pywebview.api, args);
  }

  const mock = (await cargarMocks())[metodo];
  if (mock === undefined) {
    console.warn(`[api] Falta el mock de '${metodo}' — agregalo en src/services/mocks/.`);
    return undefined;
  }
  return typeof mock === "function" ? mock(...args) : mock;
}

/* Proxy: cualquier nombre de método se traduce a una llamada, sin tener que
   declararlos acá. */
export const api = new Proxy(Object.create(null), {
  get(_, metodo) {
    if (metodo === "then") return undefined; // que `await api` no lo confunda con una promesa
    return (...args) => llamar(metodo, args);
  },
});

export const esperarApi = resolverModo;
export const enApp = () => modo === "app";
export const enMock = () => modo === "mock";
