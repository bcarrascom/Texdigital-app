/* Pone un elemento con popover="manual" en la capa superior del navegador,
   la misma de los <dialog> abiertos con showModal, y al frente de todo lo
   que ya está ahí. Sin esto, un diálogo abierto tapa con su fondo la
   animación de correo enviado y los avisos (z-index no le gana a esa capa).

   La capa superior se apila por orden de llegada: el último que entra queda
   arriba. Por eso se llama cada vez que aparece algo nuevo (sacarlo y volver
   a ponerlo lo deja primero), aunque ya estuviera ahí.

   Un navegador sin popover (WKWebView de un macOS viejo) no hace nada: el
   atributo se ignora y el elemento se ve como antes, con su z-index. */
export function alFrente(el) {
  if (!el?.showPopover) return;
  try {
    if (el.matches(":popover-open")) el.hidePopover();
    el.showPopover();
  } catch { /* fuera del documento o ya cerrándose */ }
}
