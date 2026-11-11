import { useState } from "react";
import { api } from "@/services/api";
import * as fmt from "@/utils/formato";

/* Aviso de cotización nueva, en el pie del Resumen (Bruno, 2026-11-11): al
   crear una cotización, la gente de Texdigital inscrita en Configuración ›
   Correos › Cotizaciones recibe el PDF. Es OTRO correo que el del cliente
   (ese sale con "Enviar correo" de Ver cotización), con su propio asunto y
   mensaje. Al editar una cotización no aparece: es solo al crearla.

   Compacto: los inscritos en chips, cada uno con × para sacarlo solo esta
   vez, y "+ Agregar" para sumar otro de los correos guardados en la app (o
   uno escrito). El estado vive en NuevaCotizacion: { quitados, agregados }. */

const igual = (a, b) => a.toLowerCase() === b.toLowerCase();

/* A quiénes va, sin repetir. */
export function destinatariosAviso(opciones, aviso) {
  const lista = (opciones?.inscritos || []).map((f) => f.correo)
    .filter((c) => !aviso.quitados.some((q) => igual(q, c)));
  for (const c of aviso.agregados) if (!lista.some((x) => igual(x, c))) lista.push(c);
  return lista;
}

export default function AvisoAlCrear({ opciones, aviso, onCambiar }) {
  const [agregando, setAgregando] = useState(false);
  const [nuevo, setNuevo] = useState("");
  const [malo, setMalo] = useState(false);
  if (!opciones) return null;
  const para = destinatariosAviso(opciones, aviso);
  const inscritos = opciones.inscritos.map((f) => f.correo);
  const todos = [...opciones.inscritos, ...opciones.guardados];
  const nombres = Object.fromEntries(todos.map((f) => [f.correo.toLowerCase(), f.nombre]));
  const paraElegir = todos.filter((f) => !para.some((c) => igual(c, f.correo)));

  function sacar(c) {
    if (inscritos.some((s) => igual(s, c))) onCambiar({ quitados: [...aviso.quitados, c] });
    else onCambiar({ agregados: aviso.agregados.filter((a) => !igual(a, c)) });
  }

  /* Enter o salir del campo: lo suma si es un correo; vacío, se cierra. */
  function confirmar() {
    const c = nuevo.trim();
    if (!c) { setAgregando(false); setMalo(false); return; }
    if (!fmt.correoValido(c)) { setMalo(true); return; }
    if (inscritos.some((s) => igual(s, c))) onCambiar({ quitados: aviso.quitados.filter((q) => !igual(q, c)) });
    else if (!aviso.agregados.some((a) => igual(a, c))) onCambiar({ agregados: [...aviso.agregados, c] });
    setNuevo(""); setMalo(false); setAgregando(false);
  }

  function teclas(e) {
    if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); confirmar(); }
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); setNuevo(""); setMalo(false); setAgregando(false); }
  }

  const nota = !para.length ? { tipo: "suave", texto: "Nadie recibe el aviso. Se inscriben en Configuración › Correos." }
    : !opciones.contrasena_guardada ? { tipo: "aviso", texto: "Falta la contraseña del correo en este computador (Configuración › Correos)." }
    : opciones.prueba?.activo ? { tipo: "suave", texto: `Modo de prueba: va a ${opciones.prueba.direccion}.` }
    : null;

  return (
    <div className="aviso-crear">
      <span className="aviso-crear__titulo" title="Al guardarla, les llega el PDF de la cotización nueva. No es el correo al cliente.">
        Aviso de cotización nueva a
      </span>
      <ul className="aviso-crear__lista">
        {para.map((c) => (
          <li key={c} className="aviso-crear__chip" title={nombres[c.toLowerCase()] || undefined}>
            <span>{c}</span>
            <button type="button" aria-label={`No avisar a ${c}`} title="No avisar a este correo esta vez"
                    onClick={() => sacar(c)}>×</button>
          </li>
        ))}
        <li>
          {agregando ? (
            <input className="aviso-crear__nuevo" type="email" autoFocus autoComplete="off"
                   list="aviso-crear-guardados" placeholder="correo@texdigital.cl" aria-label="Sumar un correo"
                   data-invalido={malo || undefined} title={malo ? "No es un correo válido." : undefined}
                   value={nuevo} onChange={(e) => { setNuevo(e.target.value); setMalo(false); }}
                   onKeyDown={teclas} onBlur={confirmar} />
          ) : (
            <button type="button" className="aviso-crear__agregar" title="Sumar un correo solo para esta cotización"
                    onClick={() => setAgregando(true)}>
              + Agregar
            </button>
          )}
        </li>
      </ul>
      <datalist id="aviso-crear-guardados">
        {paraElegir.map((f) => <option key={f.correo} value={f.correo}>{f.nombre}</option>)}
      </datalist>
      {nota && <p className={`aviso-crear__nota aviso-crear__nota--${nota.tipo}`}>{nota.texto}</p>}
    </div>
  );
}

/* Después de guardar: manda el aviso y cuenta cómo le fue (la pantalla ya
   pudo haber vuelto al listado; los avisos son de toda la app). Si falla, la
   cotización ya quedó guardada. */
export async function enviarAvisoCreacion(numero, para, avisar) {
  const n = fmt.numero(numero);
  const r = (await api.enviar_aviso_cotizacion_nueva(numero, para)) || {};
  if (r.ok) avisar(`Aviso de la cotización ${n} enviado a ${r.a.join(", ")}${r.prueba ? " (prueba)" : ""}.`, "info", 6000);
  else avisar(`No se pudo enviar el aviso de la cotización ${n}: ${r.error || "error desconocido"} La cotización quedó guardada.`, "error", 10000);
}
