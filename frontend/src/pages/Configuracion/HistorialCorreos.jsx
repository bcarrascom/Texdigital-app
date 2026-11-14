import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { useAvisos } from "@/context/AvisosContext";
import * as fmt from "@/utils/formato";

/* Historial de correos (Bruno, 2026-11-13): los que envió la app, mes a mes.
   Cada uno es una copia .eml en SGTD/Correos/<año>/<mes>/, con el nombre
   "<asunto> - <operación>.eml" (core.correos.guardar_eml). Clic en uno lo
   abre con el programa de correo del computador. */

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
  "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

function cuando(iso) {
  const [f, h = ""] = String(iso).split("T");
  const [, m, d] = f.split("-");
  return `${d}-${m} ${h.slice(0, 5)}`;
}

export default function HistorialCorreos({ onCerrar }) {
  const aviso = useAvisos();
  const [datos, setDatos] = useState(null);

  function cargar(anio, mes) {
    api.historial_correos(anio, mes).then((r) => setDatos(r || { meses: [], correos: [] }));
  }
  useEffect(() => { cargar(); }, []);

  if (!datos) return <h2 className="dlg__titulo">Historial de correos</h2>;

  // Los meses vienen del más nuevo al más viejo.
  const i = datos.meses.findIndex((m) => m.anio === datos.anio && m.mes === datos.mes);
  const anterior = datos.meses[i === -1 ? 0 : i + 1];
  const siguiente = i > 0 ? datos.meses[i - 1] : null;
  const ir = (m) => m && cargar(m.anio, m.mes);

  async function abrir(c) {
    const ok = await api.abrir_correo_historial(c.archivo);
    if (!ok) aviso("Ese correo ya no está en la carpeta.", "error");
  }

  return (
    <>
      <h2 className="dlg__titulo">Historial de correos</h2>
      <div className="historial-correos__mes">
        <button type="button" className="btn btn--fantasma btn--chico" aria-label="Mes anterior"
                disabled={!anterior} onClick={() => ir(anterior)}>‹</button>
        <span>{MESES[datos.mes - 1]} {datos.anio} · {fmt.plural(datos.correos.length, "correo", "correos")}</span>
        <button type="button" className="btn btn--fantasma btn--chico" aria-label="Mes siguiente"
                disabled={!siguiente} onClick={() => ir(siguiente)}>›</button>
      </div>
      {datos.correos.length ? (
        <ul className="historial-correos__lista">
          {datos.correos.map((c) => {
            const todos = [...c.para, ...c.copia];
            return (
              <li key={c.archivo}>
                <button type="button" className="historial-correos__fila" title={todos.join(", ")} onClick={() => abrir(c)}>
                  <span className="historial-correos__asunto">{c.asunto || "(sin asunto)"}</span>
                  <span className="historial-correos__fecha">{cuando(c.fecha)}</span>
                  <span className="historial-correos__detalle">
                    {c.operacion && <span className="historial-correos__operacion">{c.operacion}</span>}
                    <span className="historial-correos__para">
                      {todos[0] || ""}{todos.length > 1 ? ` +${todos.length - 1}` : ""}
                    </span>
                    {c.prueba && <span className="historial-correos__prueba">prueba</span>}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="dlg__texto">Ningún correo enviado este mes.</p>
      )}
      <div className="dlg__acciones historial-correos__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={() => api.abrir_carpeta_correos()}>
          Abrir la carpeta
        </button>
        <button className="btn btn--secundario btn--chico" type="button" data-autofoco onClick={onCerrar}>Cerrar</button>
      </div>
    </>
  );
}
