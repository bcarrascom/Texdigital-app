import { useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import IconoEditar from "@/assets/svg/pencil.svg?react";
import IconoEliminar from "@/assets/svg/trash-2.svg?react";
import IconoGuardar from "@/assets/svg/check.svg?react";
import IconoCancelar from "@/assets/svg/x.svg?react";
import IconoMas from "@/assets/svg/plus.svg?react";
import { plural } from "@/utils/formato";
import { Fila, Grupo } from "./Ajustes";

/* Proveedores: la lista simple de proveedores.json (ver core/repositorio.py),
   con alta, renombrar en el lugar y eliminar. Es la que sugieren los
   formularios de rollos y materiales — y también crece sola: un proveedor
   nuevo escrito ahí se agrega acá al guardar. */
export default function Proveedores() {
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(() => api.cargar_proveedores(), []);
  const proveedores = datos || [];
  const [editando, setEditando] = useState(null);   // nombre en edición, o null
  const [nuevo, setNuevo] = useState("");

  async function agregar() {
    const nombre = nuevo.trim();
    if (!nombre) return;
    if (proveedores.some((p) => p.toLowerCase() === nombre.toLowerCase())) {
      aviso("Ese proveedor ya está en la lista.", "aviso");
      return;
    }
    await api.guardar_proveedor(nombre);
    setNuevo("");
    await recargar();
    aviso("Proveedor agregado.", "info");
  }

  async function renombrar(actual, nombre) {
    if (!nombre || nombre === actual) { setEditando(null); return; }
    if (!(await api.editar_proveedor(actual, nombre))) { aviso("Ya existe un proveedor con ese nombre.", "error"); return; }
    setEditando(null);
    await recargar();
    aviso("Proveedor actualizado.", "info");
  }

  async function eliminar(nombre) {
    await api.eliminar_proveedor(nombre);
    await recargar();
    aviso("Proveedor eliminado.", "info");
  }

  if (cargando) return <Cargando />;

  return (
    <>
      <Grupo>
        <div className="fila-ajuste fila-ajuste--alta">
          <input className="entrada" type="text" placeholder="Nuevo proveedor…" autoComplete="off" aria-label="Nuevo proveedor"
                 value={nuevo} onChange={(e) => setNuevo(e.target.value)}
                 onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); agregar(); } }} />
          <button className="btn btn--primario btn--chico" type="button" disabled={!nuevo.trim()} onClick={agregar}>
            <IconoMas aria-hidden="true" /> Agregar
          </button>
        </div>
      </Grupo>

      <Grupo titulo={proveedores.length ? plural(proveedores.length, "proveedor", "proveedores") : null}
             pie="Los rollos y materiales que ya tienen un proveedor no cambian al renombrarlo o eliminarlo acá: guardan una copia del nombre, no un enlace a esta lista.">
        {proveedores.length ? proveedores.map((p) => p === editando
          ? <FilaEditando key={p} nombre={p} onGuardar={(n) => renombrar(p, n)} onCancelar={() => setEditando(null)} />
          : (
            <Fila key={p} etiqueta={p} className="fila-ajuste--acciones">
              <button className="btn-fila-ajuste" type="button" title="Renombrar" onClick={() => setEditando(p)}><IconoEditar /></button>
              <button className="btn-fila-ajuste btn-fila-ajuste--peligro" type="button" title="Eliminar" onClick={() => eliminar(p)}><IconoEliminar /></button>
            </Fila>
          ))
          : <p className="ajustes-vacio">Todavía no hay proveedores guardados.</p>}
      </Grupo>
    </>
  );
}

/* Renombrar es en el lugar (la fila se vuelve un campo con ✓ / ✕): el nombre
   es lo único que se edita. Escape cancela solo la edición. */
function FilaEditando({ nombre, onGuardar, onCancelar }) {
  const [valor, setValor] = useState(nombre);
  return (
    <div className="fila-ajuste fila-ajuste--editando">
      <input className="entrada" type="text" autoComplete="off" autoFocus aria-label={`Renombrar ${nombre}`} value={valor}
             onFocus={(e) => e.target.select()} onChange={(e) => setValor(e.target.value)}
             onKeyDown={(e) => {
               if (e.key === "Enter") { e.preventDefault(); onGuardar(valor.trim()); }
               if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); e.nativeEvent.stopImmediatePropagation(); onCancelar(); }
             }} />
      <button className="btn-fila-ajuste" type="button" title="Guardar" onClick={() => onGuardar(valor.trim())}><IconoGuardar /></button>
      <button className="btn-fila-ajuste" type="button" title="Cancelar" onClick={onCancelar}><IconoCancelar /></button>
    </div>
  );
}
