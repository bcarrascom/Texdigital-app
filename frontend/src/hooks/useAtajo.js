import { useEffect, useRef } from "react";

/* Atajo de teclado mientras el componente está montado.

       useAtajo("escape", volver);
       useAtajo("mod+s", guardar);         // mod = Ctrl en Windows, ⌘ en Mac

   Reglas heredadas de app.js:
     · con un <dialog> modal abierto no corre ninguno (el diálogo se maneja
       solo: Escape lo cierra, Enter confirma lo suyo);
     · Enter dentro de un <textarea> es salto de línea, no "confirmar";
     · si dos componentes registran el mismo atajo, corren los dos. */

export function comboDe(e) {
  const partes = [];
  if (e.ctrlKey || e.metaKey) partes.push("mod");
  if (e.shiftKey) partes.push("shift");
  if (e.altKey) partes.push("alt");
  partes.push(e.key.toLowerCase());
  return partes.join("+");
}

export function useAtajo(combo, fn, activo = true) {
  // La función más reciente sin volver a registrar el listener en cada render.
  const ref = useRef(fn);
  useEffect(() => { ref.current = fn; });

  useEffect(() => {
    if (!activo) return;
    const objetivo = combo.toLowerCase();
    const alPresionar = (e) => {
      if (document.querySelector("dialog[open]")) return;
      const c = comboDe(e);
      if (c !== objetivo) return;
      if (c === "enter" && e.target.tagName === "TEXTAREA") return;
      e.preventDefault();
      ref.current(e);
    };
    document.addEventListener("keydown", alPresionar);
    return () => document.removeEventListener("keydown", alPresionar);
  }, [combo, activo]);
}
