import Dialogo from "@/components/Dialogo/Dialogo";
import "./DialogoActualizacion.css";

/* Buscar e instalar una versión nueva (ver hooks/useActualizacion). Lo abre
   el botón "Actualizar a vX" del pie del menú y Configuración › General.

       const act = useActualizacion();
       <DialogoActualizacion abierto={abierto} {...act} onCerrar={() => setAbierto(false)} />

   Mientras descarga no se puede cerrar: la app se va a cerrar sola. */
export default function DialogoActualizacion({ abierto, estado, buscar, instalar, onCerrar }) {
  const fase = estado?.fase;
  const ocupado = fase === "descargando" || fase === "listo";
  return (
    <Dialogo abierto={abierto} onCerrar={ocupado ? () => {} : onCerrar}
             onConfirmar={fase === "disponible" ? instalar : undefined} className="dlg-actualizacion">
      <Contenido estado={estado || { fase: "buscando" }} buscar={buscar} instalar={instalar} onCerrar={onCerrar} />
    </Dialogo>
  );
}

function Contenido({ estado, buscar, instalar, onCerrar }) {
  const { fase, version, nueva, progreso, error } = estado;
  const cerrar = <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cerrar</button>;

  if (fase === "disponible") return (
    <>
      <h2 className="dlg__titulo">Hay una versión nueva: {nueva}</h2>
      <p className="dlg__texto">
        Tienes la v{version}. Al actualizar, la app se cierra y se vuelve a abrir sola en un momento:
        guarda antes lo que estés haciendo. Las cotizaciones, OPs y ajustes no se tocan, están en Dropbox.
      </p>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Más tarde</button>
        <button className="btn btn--primario btn--chico" type="button" onClick={instalar} data-autofoco>Actualizar ahora</button>
      </div>
    </>
  );

  if (fase === "descargando") return (
    <>
      <h2 className="dlg__titulo">Descargando {nueva}…</h2>
      <p className="dlg__texto">No cierres la app: se cierra y se vuelve a abrir sola cuando termine.</p>
      <div className="act-barra" role="progressbar" aria-valuemin={0} aria-valuemax={100}
           aria-valuenow={progreso ?? undefined} data-indeterminada={progreso == null || undefined}>
        <span style={{ width: `${progreso ?? 30}%` }} />
      </div>
      <p className="act-pct">{progreso != null ? `${progreso} %` : ""}</p>
    </>
  );

  if (fase === "listo") return (
    <>
      <h2 className="dlg__titulo">Listo</h2>
      <p className="dlg__texto">La app se va a cerrar y a volver a abrir con la {nueva}.</p>
    </>
  );

  if (fase === "error") return (
    <>
      <h2 className="dlg__titulo">No se pudo actualizar</h2>
      <p className="dlg__texto">{error}</p>
      <div className="dlg__acciones">
        {cerrar}
        <button className="btn btn--primario btn--chico" type="button" onClick={buscar}>Reintentar</button>
      </div>
    </>
  );

  if (fase === "al_dia") return (
    <>
      <h2 className="dlg__titulo">Tienes la última versión</h2>
      <p className="dlg__texto">Esta es la v{version}.</p>
      <div className="dlg__acciones">{cerrar}</div>
    </>
  );

  if (fase === "no_disponible") return (
    <>
      <h2 className="dlg__titulo">Actualizaciones</h2>
      <p className="dlg__texto">Solo funcionan en la app instalada, no corriendo desde el código fuente.</p>
      <div className="dlg__acciones">{cerrar}</div>
    </>
  );

  return (
    <>
      <h2 className="dlg__titulo">Buscando una versión nueva…</h2>
      <div className="act-barra" data-indeterminada><span /></div>
      <div className="dlg__acciones">{cerrar}</div>
    </>
  );
}
