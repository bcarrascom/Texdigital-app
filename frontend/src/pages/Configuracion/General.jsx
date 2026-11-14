import { useState } from "react";
import Dialogo from "@/components/Dialogo/Dialogo";
import Campo from "@/components/Campo/Campo";
import { api } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { useActualizacion } from "@/hooks/useActualizacion";
import { ControlTexto } from "@/components/Cabecera/Cabecera";
import DialogoActualizacion from "@/components/Actualizacion/DialogoActualizacion";
import IconoInfo from "@/assets/svg/info.svg?react";
import IconoActualizar from "@/assets/svg/refresh-cw.svg?react";
import IconoTexto from "@/assets/svg/a-large-small.svg?react";
import IconoManual from "@/assets/svg/book-open.svg?react";
import IconoPrueba from "@/assets/svg/flask-conical.svg?react";
import { Fila, Grupo } from "./Ajustes";
import { MANUAL_VISIBLE } from "@/utils/manual";

/* Lo que dice la fila de actualizaciones según cómo va la búsqueda. */
const DETALLE = {
  buscando: "Buscando…",
  al_dia: "Al día",
  disponible: (e) => `Hay una nueva: ${e.nueva}`,
  descargando: "Descargando…",
  listo: "Reiniciando…",
  error: "No se pudo buscar",
};

/* General: la versión, buscar actualizaciones, el tamaño del texto y el
   manual. Lo mismo que el pie del menú, reunido en un solo lugar.

   "Versiones de prueba" busca también las betas (tags con guion, p. ej.
   v2.2.0-rc1), que la app nunca ofrece sola: pide una contraseña, que
   revisa Python (ver ui/api_actualizacion.py). Pedido de Bruno, 2026-11-05. */
export default function General() {
  const { contexto } = useApp();
  const actualizacion = useActualizacion();
  const [dialogo, setDialogo] = useState(false);
  const [pidiendo, setPidiendo] = useState(false);   // el diálogo de la contraseña
  const { estado } = actualizacion;
  const detalle = DETALLE[estado?.fase];

  function buscar() {
    // Con una versión ya encontrada, no hace falta volver a buscar.
    if (!["disponible", "descargando", "listo"].includes(estado?.fase)) actualizacion.buscar();
    setDialogo(true);
  }

  return (
    <>
      <Grupo>
        <Fila icono={IconoInfo} etiqueta="Versión" detalle={contexto.version ? `v${contexto.version}` : "—"} />
        <Fila icono={IconoActualizar} color="#3478F6" etiqueta="Buscar actualizaciones"
              detalle={typeof detalle === "function" ? detalle(estado) : detalle} onClick={buscar} />
        <Fila icono={IconoPrueba} color="#8E8E93" etiqueta="Versiones de prueba" onClick={() => setPidiendo(true)} />
      </Grupo>
      <Grupo>
        <Fila icono={IconoTexto} color="#5E6AD2" etiqueta="Tamaño del texto"><ControlTexto /></Fila>
      </Grupo>
      {MANUAL_VISIBLE && (
        <Grupo>
          <Fila icono={IconoManual} color="#E8772E" etiqueta="Manual de uso" onClick={() => api.abrir_manual()} />
        </Grupo>
      )}
      <DialogoActualizacion abierto={dialogo} {...actualizacion} onCerrar={() => setDialogo(false)} />
      <Dialogo abierto={pidiendo} onCerrar={() => setPidiendo(false)} className="dlg--desenfoque dlg-catalogo">
        <FormularioContrasena buscarBetas={actualizacion.buscarBetas} onCerrar={() => setPidiendo(false)}
                              onHecho={() => { setPidiendo(false); setDialogo(true); }} />
      </Dialogo>
    </>
  );
}

function FormularioContrasena({ buscarBetas, onCerrar, onHecho }) {
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function confirmar(e) {
    e.preventDefault();
    if (enviando) return;
    setEnviando(true);
    try {
      const r = await buscarBetas(contrasena);
      if (r.ok) onHecho();
      else setError(r.error);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={confirmar} noValidate>
      <h2 className="dlg__titulo">Versiones de prueba</h2>
      <p className="dlg__texto">
        Busca también las versiones que todavía se están probando. No son para el trabajo del día a día, son solo para desarrolladores.
      </p>
      <div className="dlg-catalogo__campos">
        <Campo id="contrasena-betas" etiqueta="Contraseña" requerido invalido={!!error} error={error || ""}>
          <input className="entrada" id="contrasena-betas" type="password" autoComplete="off" data-autofoco
                 value={contrasena} onChange={(e) => { setContrasena(e.target.value); setError(null); }} />
        </Campo>
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit" disabled={enviando || !contrasena}>Buscar</button>
      </div>
    </form>
  );
}
