import { useEffect, useState } from "react";
import { api } from "@/services/api";
import * as fmt from "@/utils/formato";
import "./ListaDestinatarios.css";

/* A quiénes va un correo automático, a la vista antes de que salga (regla de
   Bruno, 2026-11-12: ningún correo automático sale sin que el usuario sepa a
   quién). Compacta, para no agrandar el diálogo o el panel donde va:

     · los inscritos en Configuración › Correos, en chips, cada uno con − a la
       derecha para sacarlo solo esta vez;
     · el último elemento de la lista, "+ Agregar", suma otro de los correos
       guardados en la app (o uno escrito), también solo esta vez. La lista
       de Configuración no cambia.

   La usan el Resumen del cotizador (cotización nueva), el diálogo Aprobar
   (la OP nueva), el de Recotizar y "Enviar por correo" de Ver OP:

       const aviso = useDestinatarios("ops");          // "cotizaciones" | "ops"
       <ListaDestinatarios titulo="Se le enviará un correo a" {...aviso} />
       api.aprobar_cotizacion(…, aviso.para);

   Con los correos automáticos de esa parte apagados no se muestra y `para`
   queda vacío; `manual` (Reenviar, que se hace a mano) la muestra igual. */

const igual = (a, b) => a.toLowerCase() === b.toLowerCase();

/* A quiénes va, sin repetir. */
export function destinatarios(opciones, valor) {
  const lista = (opciones?.inscritos || []).map((f) => f.correo)
    .filter((c) => !valor.quitados.some((q) => igual(q, c)));
  for (const c of valor.agregados) if (!lista.some((x) => igual(x, c))) lista.push(c);
  return lista;
}

/* Carga la lista de esa parte y guarda lo que se saca o suma. Con
   `cargar` en false (p. ej. al editar una cotización) no pide nada. */
export function useDestinatarios(parte, { cargar = true, manual = false } = {}) {
  const [opciones, setOpciones] = useState(null);
  const [valor, setValor] = useState({ quitados: [], agregados: [] });
  useEffect(() => {
    if (!cargar) return undefined;
    let vigente = true;
    api.opciones_aviso(parte).then((r) => vigente && setOpciones(r || null));
    return () => { vigente = false; };
  }, [parte, cargar]);
  const visible = !!opciones && (manual || opciones.activo);
  return {
    opciones, valor, visible,
    onCambiar: (cambio) => setValor((v) => ({ ...v, ...cambio })),
    para: visible ? destinatarios(opciones, valor) : [],
  };
}

export default function ListaDestinatarios({ titulo, opciones, valor, onCambiar, visible, alinear = "inicio",
                                             vacio = "Nadie lo recibe. Se inscriben en Configuración › Correos." }) {
  const [agregando, setAgregando] = useState(false);
  const [nuevo, setNuevo] = useState("");
  const [malo, setMalo] = useState(false);
  if (!visible) return null;
  const para = destinatarios(opciones, valor);
  const inscritos = opciones.inscritos.map((f) => f.correo);
  const todos = [...opciones.inscritos, ...opciones.guardados];
  const nombres = Object.fromEntries(todos.map((f) => [f.correo.toLowerCase(), f.nombre]));
  const paraElegir = todos.filter((f) => !para.some((c) => igual(c, f.correo)));
  const idLista = `destinatarios-${titulo.replace(/\W+/g, "-")}`;

  function sacar(c) {
    if (inscritos.some((s) => igual(s, c))) onCambiar({ quitados: [...valor.quitados, c] });
    else onCambiar({ agregados: valor.agregados.filter((a) => !igual(a, c)) });
  }

  /* Enter o salir del campo: lo suma si es un correo; vacío, se cierra. */
  function confirmar() {
    const c = nuevo.trim();
    if (!c) { setAgregando(false); setMalo(false); return; }
    if (!fmt.correoValido(c)) { setMalo(true); return; }
    if (inscritos.some((s) => igual(s, c))) onCambiar({ quitados: valor.quitados.filter((q) => !igual(q, c)) });
    else if (!valor.agregados.some((a) => igual(a, c))) onCambiar({ agregados: [...valor.agregados, c] });
    setNuevo(""); setMalo(false); setAgregando(false);
  }

  function teclas(e) {
    if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); confirmar(); }
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); setNuevo(""); setMalo(false); setAgregando(false); }
  }

  const nota = !para.length ? { tipo: "suave", texto: vacio }
    : !opciones.contrasena_guardada ? { tipo: "aviso", texto: "Falta la contraseña del correo en este computador (Configuración › Correos)." }
    : opciones.prueba?.activo ? { tipo: "suave", texto: `Modo de prueba: va a ${opciones.prueba.direccion}.` }
    : null;

  return (
    <div className="destinatarios" data-alinear={alinear}>
      <span className="destinatarios__titulo">{titulo}</span>
      <ul className="destinatarios__lista">
        {para.map((c) => (
          <li key={c} className="destinatarios__chip" title={nombres[c.toLowerCase()] || undefined}>
            <span>{c}</span>
            <button type="button" aria-label={`No enviar a ${c}`} title="No enviar a este correo esta vez"
                    onClick={() => sacar(c)}>−</button>
          </li>
        ))}
        <li>
          {agregando ? (
            <input className="destinatarios__nuevo" type="email" autoFocus autoComplete="off"
                   list={idLista} placeholder="correo@texdigital.cl" aria-label="Sumar un correo"
                   data-invalido={malo || undefined} title={malo ? "No es un correo válido." : undefined}
                   value={nuevo} onChange={(e) => { setNuevo(e.target.value); setMalo(false); }}
                   onKeyDown={teclas} onBlur={confirmar} />
          ) : (
            <button type="button" className="destinatarios__agregar" title="Sumar un correo solo esta vez"
                    onClick={() => setAgregando(true)}>
              + Agregar
            </button>
          )}
        </li>
      </ul>
      <datalist id={idLista}>
        {paraElegir.map((f) => <option key={f.correo} value={f.correo}>{f.nombre}</option>)}
      </datalist>
      {nota && <p className={`destinatarios__nota destinatarios__nota--${nota.tipo}`}>{nota.texto}</p>}
    </div>
  );
}
