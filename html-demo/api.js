/* ═══════════════════════════════════════════════════════════════════════════
   api.js — el puente entre las pantallas HTML y Python.

   Esta es LA pieza clave del flujo de trabajo: la misma pantalla HTML corre
   en dos entornos sin cambiar una línea.

     · Dentro de la app  → las llamadas van a window.pywebview.api
                           (ui/panel_produccion.py ya usa este mecanismo).
     · En el navegador   → las llamadas las responde el mock de la pantalla
                           (mocks/<pantalla>.js). Así se puede diseñar,
                           revisar y ajustar sin abrir Python.

   Uso desde una pantalla:

       await TD.api.obtener_ops();          // devuelve una promesa, siempre
       TD.api.cerrar();                     // sin await si no importa el valor

   ── OJO con los módulos ES ────────────────────────────────────────────────
   pywebview carga las pantallas por file:// y Chromium bloquea `import` y
   `fetch()` sobre file:// (CORS). Por eso: scripts clásicos, sin type=module,
   y los mocks son .js que se registran solos — nunca .json cargados con fetch.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  const TD = (window.TD = window.TD || {});

  const _mocks = Object.create(null);
  let _pantalla = document.documentElement.dataset.pantalla || "desconocida";
  let _modo = null;          // "app" | "mock", se resuelve una sola vez
  let _listo = null;         // promesa de resolución

  /* Registra el mock de una pantalla. Lo llama mocks/<pantalla>.js:
         TD.mock("inicio", { obtener_contexto: () => ({...}) });
     Cada clave es un método de la API de Python. El valor puede ser un valor
     fijo o una función (sincrónica o async) que recibe los mismos argumentos. */
  TD.mock = function (pantalla, metodos) {
    _mocks[pantalla] = Object.assign(_mocks[pantalla] || {}, metodos);
  };

  /* pywebview inyecta window.pywebview.api de forma asíncrona y avisa con el
     evento 'pywebviewready'. Si no llega en TIMEOUT ms, asumimos navegador. */
  const TIMEOUT = 1200;

  function resolverModo() {
    if (_listo) return _listo;
    _listo = new Promise(function (resolve) {
      function listo() {
        _modo = "app";
        document.documentElement.dataset.modo = "app";
        resolve("app");
      }
      if (window.pywebview && window.pywebview.api) return listo();
      window.addEventListener("pywebviewready", listo, { once: true });
      setTimeout(function () {
        if (_modo) return;
        _modo = "mock";
        document.documentElement.dataset.modo = "mock";
        mostrarMarcaMock();
        resolve("mock");
      }, TIMEOUT);
    });
    return _listo;
  }

  function mostrarMarcaMock() {
    if (document.querySelector(".marca-mock")) return;
    const marca = document.createElement("div");
    marca.className = "marca-mock";
    marca.textContent = "modo diseño · datos de prueba";
    document.body.appendChild(marca);
  }

  async function llamar(metodo, args) {
    const modo = await resolverModo();

    if (modo === "app") {
      const fn = window.pywebview.api[metodo];
      if (typeof fn !== "function") {
        throw new Error(
          "La API de Python no expone '" + metodo + "'. " +
          "Revisá contratos/" + _pantalla + ".md — el contrato y la clase " +
          "Api de Python quedaron desincronizados."
        );
      }
      return fn.apply(window.pywebview.api, args);
    }

    const mock = _mocks[_pantalla];
    if (!mock || !(metodo in mock)) {
      console.warn(
        "[TD] Falta el mock de '" + metodo + "' para la pantalla '" + _pantalla +
        "'. Agregalo en mocks/" + _pantalla + ".js."
      );
      return undefined;
    }
    const valor = mock[metodo];
    return typeof valor === "function" ? valor.apply(mock, args) : valor;
  }

  /* Proxy: cualquier nombre de método se traduce a una llamada. No hay que
     declarar los métodos acá — el contrato vive en contratos/<pantalla>.md. */
  TD.api = new Proxy(Object.create(null), {
    get: function (_, metodo) {
      if (metodo === "then") return undefined;   // no confundir a await
      return function () {
        return llamar(metodo, Array.prototype.slice.call(arguments));
      };
    },
  });

  TD.enApp = function () { return _modo === "app"; };
  TD.listo = resolverModo;
  TD.pantalla = function () { return _pantalla; };
})();
