import { useEffect, useState } from "react";
import { api } from "@/services/api";
import Dialogo from "@/components/Dialogo/Dialogo";
import Cargando from "@/components/Cargando/Cargando";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import IconoAdjunto from "@/assets/svg/paperclip.svg?react";
import * as fmt from "@/utils/formato";
import "./EnviarCorreo.css";

/* "Enviar correo" de una cotización (pedido de Bruno, 2026-11-09; ver
   ui/api_correos.py): le manda al cliente el PDF con un asunto y un mensaje,
   y el cliente responde a ese correo para aprobarla o pedir cambios.

   Dos pasos:
     1. ¿A quién? Los datos del cliente y sus correos guardados (el del
        contacto de la cotización y el del cliente en Configuración), para
        confirmar que es el correcto. Si la cotización no cambió desde el
        último envío, lo advierte acá, antes de seguir.
     2. El correo: con copia, asunto, mensaje (ya rellenados con la plantilla
        de Configuración › Correos) y el PDF adjunto, que se puede abrir.

   Sale por el correo de la app (ver core/correos.py), con la contraseña
   guardada en este computador; sin ella, el panel lo dice y no deja enviar. */

const ORIGEN = { contacto: "Contacto de la cotización", cliente: "Cliente en Configuración" };

/* "a@b.cl, c@d.cl" → ["a@b.cl", "c@d.cl"] */
const separar = (texto) => String(texto || "").split(/[,;]/).map((c) => c.trim()).filter(Boolean);

export default function DialogoEnviarCorreo({ abierto, numero, onCerrar, onEnviado }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} className="dlg--desenfoque dlg-correo">
      <PanelCorreo numero={numero} onCerrar={onCerrar} onEnviado={onEnviado} />
    </Dialogo>
  );
}

function PanelCorreo({ numero, onCerrar, onEnviado }) {
  const [info, setInfo] = useState(undefined);   // undefined: cargando · null: no se pudo
  const [paso, setPaso] = useState("destinatario");
  const [elegidos, setElegidos] = useState([]);  // correos sugeridos marcados
  const [otros, setOtros] = useState("");
  const [copia, setCopia] = useState("");
  const [asunto, setAsunto] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [errores, setErrores] = useState({});
  const [enviando, setEnviando] = useState(false);
  const [abriendoPdf, setAbriendoPdf] = useState(false);
  const [errorPdf, setErrorPdf] = useState(null);

  useEffect(() => {
    let vivo = true;
    api.preparar_correo_cotizacion(numero).then((r) => {
      if (!vivo) return;
      setInfo(r || null);
      if (!r) return;
      setElegidos(r.sugeridos.length ? [r.sugeridos[0].correo] : []);
      setCopia(r.copia.join(", "));
      setAsunto(r.asunto);
      setMensaje(r.mensaje);
    });
    return () => { vivo = false; };
  }, [numero]);

  if (info === undefined) return <div className="dlg-correo__cargando"><Cargando /></div>;
  if (info === null) {
    return (
      <>
        <h2 className="dlg__titulo">No se pudo preparar el correo</h2>
        <p className="dlg__texto">La cotización {fmt.numero(numero)} ya no existe.</p>
        <div className="dlg__acciones">
          <button className="btn btn--primario btn--chico" type="button" onClick={onCerrar}>Entendido</button>
        </div>
      </>
    );
  }

  const para = [...elegidos, ...separar(otros)];
  const malos = separar(otros).filter((c) => !fmt.correoValido(c));

  function seguir(e) {
    e.preventDefault();
    if (!para.length) { setErrores({ para: "Elige o escribe al menos un correo." }); return; }
    if (malos.length) { setErrores({ para: `«${malos[0]}» no es un correo válido.` }); return; }
    setErrores({});
    setPaso("mensaje");
  }

  async function enviar(e) {
    e.preventDefault();
    if (enviando) return;
    setEnviando(true);
    try {
      const r = await api.enviar_correo_cotizacion(numero, { para, copia: separar(copia), asunto, mensaje });
      if (r?.ok) { onEnviado(r); return; }
      if (r?.errores?.para) setPaso("destinatario");
      setErrores(r?.errores || { general: r?.error || "No se pudo enviar." });
    } finally {
      setEnviando(false);
    }
  }

  async function verPdf() {
    setAbriendoPdf(true);
    setErrorPdf(null);
    try {
      const r = await api.ver_pdf_cotizacion(numero);
      if (!r?.ok) setErrorPdf(r?.error || "No se pudo armar el PDF.");
    } finally {
      setAbriendoPdf(false);
    }
  }

  const alternar = (correo) =>
    setElegidos((xs) => (xs.includes(correo) ? xs.filter((x) => x !== correo) : [...xs, correo]));

  const avisoSinCambios = info.sin_cambios && info.ultimo && (
    <p className="ajustes-nota ajustes-nota--aviso dlg-correo__nota" role="alert">
      <IconoAviso aria-hidden="true" />
      <span>
        <strong>No hay cambios desde el último envío.</strong> El {info.ultimo.fecha} ya se le mandó esta misma
        cotización a {info.ultimo.para.join(", ")}. ¿Seguro que quieres volver a enviarla?
      </span>
    </p>
  );

  const modo = info.prueba?.activo && (
    <p className="dlg-correo__modo">
      Modo de prueba: el correo va a <strong>{info.prueba.direccion}</strong>, no al cliente.
    </p>
  );
  const sinClave = !info.contrasena_guardada && (
    <p className="ajustes-nota ajustes-nota--aviso dlg-correo__nota" role="alert">
      <IconoAviso aria-hidden="true" />
      <span>Falta la contraseña del correo de la app en este computador: escríbela en Configuración › Correos para poder enviar.</span>
    </p>
  );

  // ── Paso 1: a quién ────────────────────────────────────────────────────
  if (paso === "destinatario") {
    return (
      <form onSubmit={seguir} noValidate>
        <h2 className="dlg__titulo">Enviar la cotización {fmt.numero(info.numero)}</h2>
        <p className="dlg__texto">Revisa que el correo sea de este cliente antes de seguir.</p>

        {avisoSinCambios}

        <dl className="dlg-correo__cliente">
          <div className="dlg-correo__dato dlg-correo__dato--ancho"><dt>Empresa</dt><dd>{info.empresa || "—"}</dd></div>
          {info.rut && <div className="dlg-correo__dato"><dt>RUT</dt><dd className="mono">{info.rut}</dd></div>}
          {info.razon_social && <div className="dlg-correo__dato"><dt>Razón social</dt><dd>{info.razon_social}</dd></div>}
          <div className="dlg-correo__dato"><dt>Contacto</dt><dd>{info.contacto || "—"}</dd></div>
          {info.trabajo && <div className="dlg-correo__dato"><dt>Trabajo</dt><dd>{info.trabajo}</dd></div>}
        </dl>

        <div className="campo dlg-correo__para" data-invalido={errores.para ? "" : undefined}>
          <span className="campo__etiqueta" data-requerido>Enviar a</span>
          {info.sugeridos.map((s) => (
            <label key={s.correo} className="chip-casilla dlg-correo__opcion">
              <input type="checkbox" checked={elegidos.includes(s.correo)} onChange={() => alternar(s.correo)} />
              <span className="dlg-correo__opcion-texto">
                <span className="dlg-correo__correo">{s.correo}</span>
                <span className="dlg-correo__origen">{ORIGEN[s.origen]} · {s.nombre}</span>
              </span>
            </label>
          ))}
          {!info.sugeridos.length && (
            <p className="ajustes-nota ajustes-nota--aviso" role="status">
              <IconoAviso aria-hidden="true" />
              <span>Ni el contacto ni el cliente tienen un correo guardado. Escríbelo abajo, y guárdalo en Configuración › Clientes y contactos para la próxima.</span>
            </p>
          )}
          <input className="entrada" type="text" autoComplete="off" aria-label="Otro correo"
                 placeholder={info.sugeridos.length ? "Otro correo (opcional)" : "correo@cliente.cl"}
                 data-autofoco={info.sugeridos.length ? undefined : ""}
                 value={otros} onChange={(e) => { setOtros(e.target.value); setErrores({}); }} />
          <span className="campo__ayuda">Varios correos, separados por coma.</span>
          {errores.para && <span className="campo__error">{errores.para}</span>}
        </div>

        <p className="dlg-correo__pregunta">
          {para.length
            ? <>¿Es correcto enviarla a <strong>{para.join(", ")}</strong>?</>
            : "Elige a quién enviarla."}
        </p>

        <div className="dlg__acciones">
          <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
          <button className="btn btn--primario btn--chico" type="submit" disabled={!para.length} data-autofoco={info.sugeridos.length ? "" : undefined}>
            Sí, es el correo correcto →
          </button>
        </div>
      </form>
    );
  }

  // ── Paso 2: el correo ──────────────────────────────────────────────────
  /* Enter en un campo NO envía: un correo al cliente sale solo con el botón. */
  const sinEnter = (e) => { if (e.key === "Enter" && e.target.tagName === "INPUT") e.preventDefault(); };

  return (
    <form onSubmit={enviar} onKeyDown={sinEnter} noValidate>
      <h2 className="dlg__titulo">El correo para {info.empresa || "el cliente"}</h2>

      <div className="dlg-correo__campos">
        <div className="dlg-correo__fila">
          <span className="dlg-correo__et">De</span>
          <span className="dlg-correo__val">{info.remitente}</span>
        </div>
        <div className="dlg-correo__fila">
          <span className="dlg-correo__et">Para</span>
          <span className="dlg-correo__val">
            <strong>{para.join(", ")}</strong>{" "}
            <button className="dlg-correo__cambiar" type="button" onClick={() => setPaso("destinatario")}>Cambiar</button>
          </span>
        </div>
        <div className="campo" data-invalido={errores.copia ? "" : undefined}>
          <label className="campo__etiqueta" htmlFor="correo-copia">Con copia a</label>
          <input className="entrada" id="correo-copia" type="text" autoComplete="off" placeholder="Opcional"
                 value={copia} onChange={(e) => { setCopia(e.target.value); setErrores({}); }} />
          {errores.copia && <span className="campo__error">{errores.copia}</span>}
        </div>
        <div className="campo" data-invalido={errores.asunto ? "" : undefined}>
          <label className="campo__etiqueta" htmlFor="correo-asunto-envio" data-requerido>Asunto</label>
          <input className="entrada" id="correo-asunto-envio" type="text" autoComplete="off"
                 value={asunto} onChange={(e) => { setAsunto(e.target.value); setErrores({}); }} />
          <span className="campo__error">{errores.asunto}</span>
        </div>
        <div className="campo" data-invalido={errores.mensaje ? "" : undefined}>
          <label className="campo__etiqueta" htmlFor="correo-mensaje-envio" data-requerido>Mensaje</label>
          <textarea className="entrada dlg-correo__mensaje" id="correo-mensaje-envio" rows={8}
                    value={mensaje} onChange={(e) => { setMensaje(e.target.value); setErrores({}); }} />
          <span className="campo__error">{errores.mensaje}</span>
        </div>
        <div className="dlg-correo__adjunto">
          <IconoAdjunto aria-hidden="true" />
          <span className="dlg-correo__adjunto-nombre">{info.adjunto}</span>
          <button className="btn btn--secundario btn--chico" type="button" disabled={abriendoPdf} onClick={verPdf}>
            {abriendoPdf ? "Armando…" : "Ver PDF"}
          </button>
        </div>
        {errorPdf && <p className="dlg-correo__error" role="alert">{errorPdf}</p>}
      </div>

      {info.sin_cambios && (
        <p className="dlg-correo__recordatorio">
          <IconoAviso aria-hidden="true" /> Es la misma cotización que se envió el {info.ultimo.fecha}.
        </p>
      )}
      {modo}
      {sinClave}
      {errores.general && <p className="dlg-correo__error" role="alert">{errores.general}</p>}

      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={() => setPaso("destinatario")}>← Volver</button>
        <button className="btn btn--primario btn--chico" type="submit" disabled={enviando || !info.contrasena_guardada}>
          {enviando ? "Enviando…" : info.sin_cambios ? "Enviar de nuevo" : "Enviar"}
        </button>
      </div>
    </form>
  );
}
