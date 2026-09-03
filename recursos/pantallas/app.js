/* ═══════════════════════════════════════════════════════════════════════════
   app.js — utilidades compartidas por todas las pantallas.
   Se carga DESPUÉS de api.js y ANTES del script propio de la pantalla.

   Incluye:
     · TD.iniciar()        arranque común: cabecera, escala de texto, atajos
     · TD.escala           palanca A− / A+ (el arreglo de resoluciones, del
                           lado del usuario)
     · TD.aviso()          avisos flotantes
     · TD.fmt              formato chileno (miles con punto, coma decimal)
     · TD.atajo()          atajos de teclado declarativos
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  const TD = (window.TD = window.TD || {});

  /* ── Escala de texto ─────────────────────────────────────────────────────
     El problema original: la pantalla chica de alta resolución achica todo.
     WebView2 ya respeta el escalado de Windows, pero además le damos al
     usuario una palanca explícita que vale para TODA la app. Se persiste con
     la API de Python (método `guardar_preferencia`), no en localStorage: así
     el valor sobrevive a reinstalaciones y lo comparten todas las ventanas. */

  const PASOS = [0.85, 0.925, 1, 1.1, 1.25, 1.4, 1.6];
  let _iEscala = 2;   // 1.0

  const escala = {
    aplicar(valor) {
      const i = PASOS.indexOf(valor);
      _iEscala = i >= 0 ? i : 2;
      document.documentElement.style.setProperty("--ui-escala", PASOS[_iEscala]);
      const et = document.querySelector("[data-escala-valor]");
      if (et) et.textContent = Math.round(PASOS[_iEscala] * 100) + "%";
      const menos = document.querySelector("[data-escala='-']");
      const mas = document.querySelector("[data-escala='+']");
      if (menos) menos.disabled = _iEscala === 0;
      if (mas) mas.disabled = _iEscala === PASOS.length - 1;
    },
    mover(delta) {
      const i = Math.min(PASOS.length - 1, Math.max(0, _iEscala + delta));
      if (i === _iEscala) return;
      escala.aplicar(PASOS[i]);
      TD.api.guardar_preferencia("escala_ui", PASOS[i]);
    },
    valor() { return PASOS[_iEscala]; },
  };
  TD.escala = escala;

  /* ── Avisos flotantes ──────────────────────────────────────────────────── */

  TD.aviso = function (texto, tipo, ms) {
    let pila = document.querySelector(".pila-avisos");
    if (!pila) {
      pila = document.createElement("div");
      pila.className = "pila-avisos";
      document.body.appendChild(pila);
    }
    const el = document.createElement("div");
    el.className = "aviso aviso--" + (tipo || "info");
    el.setAttribute("role", tipo === "error" ? "alert" : "status");
    el.textContent = texto;
    pila.appendChild(el);
    setTimeout(function () { el.remove(); }, ms || 3500);
  };

  /* ── Formato chileno ─────────────────────────────────────────────────────
     Mismas reglas que core/presentar_op.py (_fmt_medida / _fmt_cantidad) para
     que el HTML y los documentos generados no muestren números distintos. */

  TD.fmt = {
    medida(v) { return Number(v).toFixed(3).replace(".", ","); },
    cantidad(v) {
      const n = Math.round(Number(v) * 100) / 100;
      return n.toLocaleString("es-CL", { maximumFractionDigits: 2 });
    },
    pesos(v) {
      return "$" + Math.round(Number(v)).toLocaleString("es-CL");
    },
    fecha(iso) {
      if (!iso) return "";
      const [a, m, d] = String(iso).replace(/\//g, "-").split("-");
      return d && m && a ? d + "-" + m + "-" + a : iso;
    },
  };

  /* ── Atajos de teclado ───────────────────────────────────────────────────
     Reemplaza los bind("<Return>") / bind("<Escape>") de Tkinter. */

  const _atajos = [];
  TD.atajo = function (combo, fn) {
    _atajos.push({ combo: combo.toLowerCase(), fn: fn });
  };

  function comboDe(e) {
    const partes = [];
    if (e.ctrlKey || e.metaKey) partes.push("mod");
    if (e.shiftKey) partes.push("shift");
    if (e.altKey) partes.push("alt");
    partes.push(e.key.toLowerCase());
    return partes.join("+");
  }

  document.addEventListener("keydown", function (e) {
    // Con un <dialog> modal abierto, los atajos de la pantalla no corren: el
    // diálogo se maneja solo (Escape lo cierra, Enter confirma lo suyo). Sin
    // esto el Escape global "Volver" se comía el cierre del modal y encima
    // cerraba la pantalla entera por detrás.
    if (document.querySelector("dialog[open]")) return;
    const c = comboDe(e);
    // Enter dentro de un <textarea> es salto de línea, no "confirmar".
    if (c === "enter" && e.target.tagName === "TEXTAREA") return;
    const coinciden = _atajos.filter(function (a) { return a.combo === c; });
    if (!coinciden.length) return;
    e.preventDefault();
    // Se ejecutan TODAS las que coinciden, no solo la primera: app.js registra
    // atajos genéricos (Escape → Volver) y la pantalla registra los suyos; que
    // el orden de registro decidiera cuál corre es una trampa silenciosa.
    coinciden.forEach(function (a) { a.fn(e); });
  });

  /* ── Cabecera común ──────────────────────────────────────────────────────
     Cablea los botones que llevan data-* en el HTML, para que ninguna
     pantalla tenga que repetir esta lógica. */

  function cablearCabecera() {
    document.querySelectorAll("[data-escala]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        escala.mover(btn.dataset.escala === "+" ? 1 : -1);
      });
    });
    const ayuda = document.querySelector("[data-accion='manual']");
    if (ayuda) ayuda.addEventListener("click", function () { TD.api.abrir_manual(); });

    const volver = document.querySelector("[data-accion='volver']");
    if (volver) volver.addEventListener("click", function () { TD.api.volver(); });
    TD.atajo("escape", function () { if (volver) volver.click(); });

    TD.atajo("mod++", function () { escala.mover(1); });
    TD.atajo("mod+-", function () { escala.mover(-1); });

    /* Ctrl+R / Cmd+R recarga la pantalla actual desde el archivo .html en
       disco — pywebview no expone un reload nativo (no hay barra de
       navegador de por medio), así que sin esto Ctrl+R no hacía nada. Un
       reload de verdad (no solo re-pedir datos, como el F5 de menu.html)
       vuelve a levantar HTML/CSS/JS tal como estén guardados: útil para
       ver cambios sin reiniciar toda la app. TD.api.obtener_contexto()
       responde con el mismo estado de navegación de siempre (Python no se
       entera de este reload), así que la pantalla vuelve a quedar
       mostrando lo mismo que tenía, con el código fresco. */
    TD.atajo("mod+r", function () { location.reload(); });
  }

  /* ── Arranque ────────────────────────────────────────────────────────────
     Toda pantalla termina su script con:  TD.iniciar(async () => { ... });   */

  /* Las tres puntitos de [data-cargando] son opcionales: solo las pantallas
     que los tengan en su HTML los usan. Mientras `main` no resuelve (el
     tiempo real de espera a Python, más el TIMEOUT de detección de modo en
     api.js) el contenido real —marcado [data-tras-carga]— queda escondido
     detrás; ni una ni otra cosa hace falta declarar en cada pantalla, con
     poner el HTML alcanza. */
  TD.iniciar = function (main) {
    document.addEventListener("DOMContentLoaded", async function () {
      cablearCabecera();
      await TD.listo();
      try {
        const ctx = (await TD.api.obtener_contexto()) || {};
        if (ctx.escala_ui) escala.aplicar(ctx.escala_ui); else escala.aplicar(1);
        const v = document.querySelector("[data-version]");
        if (v && ctx.version) v.textContent = "v" + ctx.version;
        TD.contexto = ctx;
        if (main) await main(ctx);
      } catch (err) {
        console.error(err);
        TD.aviso("Error al iniciar la pantalla: " + err.message, "error", 8000);
      } finally {
        const cargando = document.querySelector("[data-cargando]");
        if (cargando) cargando.hidden = true;
        document.querySelectorAll("[data-tras-carga]").forEach(function (el) {
          el.hidden = false;
        });
      }
    });
  };
})();
