import { useId, useState } from "react";
import Campo, { enterGuarda } from "@/components/Campo/Campo";
import { REGION_DEFECTO, etiquetaCliente } from "./direcciones";
import "./FormularioDireccion.css";

/* El formulario de una dirección: dirección nueva al asignar un despacho (en
   el panel que nace del "+") y alta/edición en Gestionar direcciones.

     inicial         la dirección a editar, o null para una nueva
     clienteDefecto  {empresa, rut} precargado (el cliente de la OP: el caso
                     común); vale aunque no esté en `clientes` con ese formato
     clientes        [{empresa, rut}] para elegir de la lista
     conAlias        pide el alias ("Bodega", "Casa matriz"...)
     onCancelar      sin él no hay botón Cancelar (en el panel, afuera o
                     Escape cancelan) y la referencia va junto a Guardar

   El cliente hay que ELEGIRLO de la lista (no vale cualquier texto). */
export default function FormularioDireccion({ titulo, inicial = null, clienteDefecto = null, clientes, regiones,
                                              conAlias = false, onCancelar, onGuardar }) {
  const lista = useId();
  const [f, setF] = useState({
    cliente: inicial ? etiquetaCliente(inicial) : etiquetaCliente(clienteDefecto),
    alias: inicial?.alias || "", calle: inicial?.calle || "", numero: inicial?.numero || "",
    comuna: inicial?.comuna || "", region: inicial?.region || REGION_DEFECTO, referencia: inicial?.referencia || "",
  });
  const [errores, setErrores] = useState({});
  const set = (clave) => (e) => setF((x) => ({ ...x, [clave]: e.target.value }));

  function resolverCliente(texto) {
    const fijo = inicial || clienteDefecto;
    if (fijo && texto === etiquetaCliente(fijo)) return { empresa: fijo.empresa, rut: fijo.rut };
    return clientes.find((c) => etiquetaCliente(c) === texto) || null;
  }

  async function guardar(e) {
    e.preventDefault();
    const cliente = resolverCliente(f.cliente.trim());
    const faltan = {
      cliente: !cliente, calle: !f.calle.trim(), numero: !f.numero.trim(),
      comuna: !f.comuna.trim(), region: !f.region,
    };
    setErrores(faltan);
    if (Object.values(faltan).some(Boolean)) return;
    await onGuardar({
      ...(inicial?.id ? { id: inicial.id } : {}),
      rut: cliente.rut, empresa: cliente.empresa,
      ...(conAlias ? { alias: f.alias.trim() } : {}),
      calle: f.calle.trim(), numero: f.numero.trim(), comuna: f.comuna.trim(),
      region: f.region, referencia: f.referencia.trim(),
    });
  }

  const referencia = (
    <Campo id="fd-referencia" etiqueta="Depto / Edificio / Otro" className="campo--referencia">
      <input className="entrada" id="fd-referencia" type="text" placeholder="N° depto, edificio, letra de casa…"
             value={f.referencia} onChange={set("referencia")} />
    </Campo>
  );

  return (
    <form className="form-direccion" onSubmit={guardar} onKeyDown={enterGuarda}>
      <h2 className="dlg__titulo">{titulo}</h2>
      <div className="form-direccion__campos">
        <Campo id="fd-cliente" etiqueta="Cliente" requerido invalido={errores.cliente} error="Elegí un cliente de la lista">
          <input className="entrada" id="fd-cliente" type="text" list={lista} autoComplete="off" data-autofoco
                 placeholder="Nombre de empresa o RUT…" value={f.cliente} onChange={set("cliente")} />
          <datalist id={lista}>{clientes.map((c) => <option key={etiquetaCliente(c)} value={etiquetaCliente(c)} />)}</datalist>
        </Campo>
        {conAlias && (
          <Campo id="fd-alias" etiqueta="Alias">
            <input className="entrada" id="fd-alias" type="text" placeholder="Bodega, casa matriz, obra… (opcional)"
                   value={f.alias} onChange={set("alias")} />
          </Campo>
        )}
        <Campo id="fd-calle" etiqueta="Nombre de calle" requerido invalido={errores.calle}>
          <input className="entrada" id="fd-calle" type="text" value={f.calle} onChange={set("calle")} />
        </Campo>
        <div className="fila">
          <Campo id="fd-numero" etiqueta="Número" requerido invalido={errores.numero}>
            <input className="entrada" id="fd-numero" type="text" value={f.numero} onChange={set("numero")} />
          </Campo>
          <Campo id="fd-comuna" etiqueta="Comuna" requerido invalido={errores.comuna}>
            <input className="entrada" id="fd-comuna" type="text" value={f.comuna} onChange={set("comuna")} />
          </Campo>
        </div>
        <Campo id="fd-region" etiqueta="Región" requerido invalido={errores.region}>
          <select className="entrada" id="fd-region" value={f.region} onChange={set("region")}>
            {(regiones.includes(f.region) ? regiones : [f.region, ...regiones]).map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </Campo>
        {onCancelar && referencia}
      </div>
      {onCancelar ? (
        <div className="dlg__acciones">
          <button className="btn btn--fantasma btn--chico" type="button" onClick={onCancelar}>Cancelar</button>
          <button className="btn btn--primario btn--chico" type="submit">Guardar</button>
        </div>
      ) : (
        /* Sin Cancelar, la referencia sube a la altura de Guardar: el panel
           queda más bajo. */
        <div className="form-direccion__acciones">
          {referencia}
          <button className="btn btn--primario btn--chico" type="submit">Guardar</button>
        </div>
      )}
    </form>
  );
}
