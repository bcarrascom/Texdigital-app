import Dialogo from "@/components/Dialogo/Dialogo";
import * as fmt from "@/utils/formato";

/* Confirmación antes de quitar un producto. */
export function DialogoQuitar({ indice, onCerrar, onConfirmar }) {
  return (
    <Dialogo abierto={indice != null} onCerrar={onCerrar} onConfirmar={onConfirmar}>
      <h2 className="dlg__titulo">¿Quitar el producto {indice + 1}?</h2>
      <p className="dlg__texto">Se pierde lo que hayas cargado en él. No se puede deshacer.</p>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--peligro" onClick={onConfirmar}>Eliminar</button>
      </div>
    </Dialogo>
  );
}

/* Aviso antes de Guardar / Guardar y abrir con stock insuficiente. NO
   bloquea: cualquiera de los botones decide qué pasa (el único bloqueo real
   es al aprobar, ver VerCotizacion). "+ Nuevo rollo" guarda el progreso y
   lleva a Inventario con ese textil ya elegido; "Volver" desde ahí reabre
   este mismo borrador. */
export function DialogoMateriales({ faltantes, onDecidir, onNuevoRollo }) {
  return (
    <Dialogo abierto={!!faltantes} onCerrar={() => onDecidir("cancelar")} className="dlg-materiales">
      <h2 className="dlg__titulo">
        <span className="aviso-materiales__icono" aria-hidden="true" style={{ marginRight: ".4em" }}>!</span>
        Materiales insuficientes
      </h2>
      <p className="dlg__texto">No hay stock suficiente de estos textiles para cubrir la cotización:</p>
      <div className="materiales-faltantes">
        {(faltantes || []).map((f) => (
          <div key={f.textil} className="material-falta">
            <div className="material-falta__info">
              <strong>{f.textil}</strong>
              <span>
                Faltan {fmt.cantidad(f.faltante)} m — necesita {fmt.cantidad(f.necesario)} m, hay {fmt.cantidad(f.disponible)} m
              </span>
            </div>
            <button className="btn btn--secundario btn--chico material-falta__btn" type="button"
                    onClick={() => onNuevoRollo(f.textil)}>+ Nuevo rollo</button>
          </div>
        ))}
      </div>
      <div className="dlg__acciones dlg__acciones--materiales">
        <button className="btn btn--fantasma" type="button" onClick={() => onDecidir("cancelar")}>Cancelar</button>
        <button className="btn btn--secundario" type="button" onClick={() => onDecidir("progreso")}>Guardar progreso</button>
        <button className="btn btn--secundario" type="button" onClick={() => onDecidir("guardar")}>Guardar</button>
        <button className="btn btn--primario" type="button" onClick={() => onDecidir("guardar-abrir")}>Guardar y abrir →</button>
      </div>
    </Dialogo>
  );
}
