import { useState } from "react";
import { api } from "@/services/api";
import { useApp } from "@/context/AppContext";
import Dialogo from "@/components/Dialogo/Dialogo";
import * as fmt from "@/utils/formato";

/* Los diálogos de VerCotizacion: eliminar, el bloqueo por falta de stock y
   el de aprobar (fechas + materiales a cargar a mano). */

export function DialogoEliminar({ abierto, cot, onCerrar, onConfirmar }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} onConfirmar={onConfirmar}>
      <h2 className="dlg__titulo">¿Eliminar la cotización?</h2>
      <p className="dlg__texto">
        La cotización {fmt.numero(cot.numero)} de {cot.empresa || "—"} se borra del listado. No se puede deshacer.
      </p>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--peligro btn--chico" onClick={onConfirmar}>Eliminar</button>
      </div>
    </Dialogo>
  );
}

/* Bloqueo de verdad, sin forma de "aprobar igual" — a diferencia del aviso
   de nueva cotización (que deja guardar de todos modos), acá hay que
   resolver el faltante antes. "+ Nuevo rollo" lleva a Inventario con el
   textil ya elegido, y "Volver" desde ahí reaparece en esta cotización. */
export function DialogoMaterialesBloqueado({ abierto, faltantes, onCerrar, onNuevoRollo }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} className="dlg-materiales-bloqueado">
      <h2 className="dlg__titulo">
        <span className="aviso-materiales__icono" aria-hidden="true" style={{ marginRight: ".4em" }}>!</span>
        No se puede aprobar
      </h2>
      <p className="dlg__texto">Falta stock de estos textiles para cubrir la cotización:</p>
      <div className="materiales-faltantes">
        {faltantes.map((f) => (
          <div key={f.textil} className="material-falta">
            <div className="material-falta__info">
              <strong>{f.textil}</strong>
              <span>Faltan {f.faltante} m — necesita {f.necesario} m, hay {f.disponible} m</span>
            </div>
            <button className="btn btn--secundario btn--chico material-falta__btn" type="button"
                    onClick={() => onNuevoRollo(f.textil)}>+ Nuevo rollo</button>
          </div>
        ))}
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--primario btn--chico" type="button" onClick={onCerrar}>Entendido</button>
      </div>
    </Dialogo>
  );
}

/* Las dos fechas que pedía ui/dialogo_aprobar.py, con su misma regla:
   ingreso arranca en HOY (no en la fecha de la cotización) y se puede
   cambiar; entrega arranca vacía, se lleva el foco, y mientras no haya
   fecha el botón Aprobar queda apagado.

   Materiales "manual" (core.repositorio_materiales, tipo_consumo=="manual")
   asociados a los productos: se piden acá, porque recién ahora se sabe que
   la cotización se va a convertir en OP. Dejar un monto vacío es válido:
   ese material simplemente no se descuenta. */
export function DialogoAprobar({ abierto, cot, manuales, onCerrar, onEditar, onAprobada }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar}>
      {/* Montado solo mientras está abierto: cada apertura arranca de cero. */}
      <FormularioAprobar cot={cot} manuales={manuales} onCerrar={onCerrar} onEditar={onEditar} onAprobada={onAprobada} />
    </Dialogo>
  );
}

function FormularioAprobar({ cot, manuales, onCerrar, onEditar, onAprobada }) {
  const { contexto } = useApp();
  // La fecha de hoy la pone Python (hoy_iso): la del sistema puede estar
  // corrida y tiene que ser la misma que usa el resto de la app.
  const [ingreso, setIngreso] = useState(contexto.hoy_iso || new Date().toISOString().slice(0, 10));
  const [entrega, setEntrega] = useState("");
  const [entregaInvalida, setEntregaInvalida] = useState(false);
  const [consumos, setConsumos] = useState({});
  const [faltantes, setFaltantes] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const listo = !!(ingreso && entrega) && !enviando;

  async function aprobar() {
    if (!entrega) { setEntregaInvalida(true); return; }
    const consumosManuales = Object.fromEntries(
      Object.entries(consumos).map(([id, v]) => [id, fmt.aNumero(v)]).filter(([, v]) => v > 0),
    );
    setEnviando(true);
    const r = (await api.aprobar_cotizacion(cot.numero, ingreso, entrega, consumosManuales)) || {};
    setEnviando(false);
    if (r.ok) { onCerrar(); onAprobada(); return; }
    // Stock insuficiente (red de seguridad: el stock cambió mientras el
    // diálogo estaba abierto) o la cotización ya no existe: NO se cierra, se
    // muestra qué falta, sin perder las fechas cargadas.
    setFaltantes(r.faltantes || []);
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); if (listo) aprobar(); }}>
      <h2 className="dlg__titulo">¿Aprobar la cotización {fmt.numero(cot.numero)}?</h2>
      <p className="dlg__texto">Aprobar una cotización la vuelve una OP: sale del listado y pasa al historial.</p>
      <div className="dlg__campos">
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="fecha-ingreso" data-requerido>Fecha de ingreso</label>
          <input className="entrada" id="fecha-ingreso" type="date" value={ingreso}
                 onChange={(e) => setIngreso(e.target.value)} />
          <span className="campo__ayuda">Hoy, salvo que la cambies.</span>
        </div>
        <div className="campo" data-invalido={entregaInvalida || undefined}>
          <label className="campo__etiqueta" htmlFor="fecha-entrega" data-requerido>Fecha de entrega</label>
          <input className="entrada" id="fecha-entrega" type="date" value={entrega} data-autofoco
                 onChange={(e) => { setEntrega(e.target.value); setEntregaInvalida(false); }} />
          <span className="campo__error">Poné una fecha de entrega.</span>
        </div>
      </div>

      {faltantes && (
        <div className="dlg-faltantes">
          <div className="dlg-faltantes__titulo">No se puede aprobar: faltan materiales</div>
          {faltantes.map((f) => (
            <p key={f.textil} className="dlg-faltantes__item">
              {f.textil} — faltan {f.faltante} m (necesita {f.necesario} m, hay {f.disponible} m)
            </p>
          ))}
        </div>
      )}

      {manuales.length > 0 && (
        <div className="dlg-materiales-manuales">
          <div className="dlg-materiales-manuales__titulo">Materiales a cargar a mano</div>
          {manuales.map((m) => (
            <div key={m.id} className="campo">
              <label className="campo__etiqueta" htmlFor={`material-manual-${m.id}`}>{m.nombre}</label>
              <input className="entrada" type="number" min="0" step="any" placeholder="0"
                     id={`material-manual-${m.id}`} value={consumos[m.id] ?? ""}
                     onChange={(e) => setConsumos((c) => ({ ...c, [m.id]: e.target.value }))} />
            </div>
          ))}
        </div>
      )}

      <div className="dlg__acciones">
        <button type="button" className="btn btn--fantasma btn--chico" onClick={onCerrar}>Cancelar</button>
        <button type="button" className="btn btn--secundario btn--chico" onClick={() => { onCerrar(); onEditar(); }}>Editar</button>
        <button type="submit" className="btn btn--primario btn--chico" disabled={!listo}>Aprobar</button>
      </div>
    </form>
  );
}
