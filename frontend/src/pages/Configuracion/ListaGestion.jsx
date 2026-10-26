import { useState } from "react";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import Dialogo from "@/components/Dialogo/Dialogo";
import IconoBuscar from "@/assets/svg/search.svg?react";
import IconoEditar from "@/assets/svg/pencil.svg?react";
import IconoEliminar from "@/assets/svg/trash-2.svg?react";
import IconoMas from "@/assets/svg/plus.svg?react";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import * as fmt from "@/utils/formato";
import { Fila, Grupo } from "./Ajustes";

/* Una lista de Configuración que se gestiona de a un elemento (Clientes,
   Contactos, Productos): buscador, "Agregar" arriba y editar/eliminar en cada
   fila (aparecen al pasar el mouse, como en Proveedores). Cada cosa se hace en
   un diálogo que se aplica al confirmar.

       <ListaGestion cargar={() => api.obtener_productos()} clave="nombre"
                     singular="producto" plural="productos"
                     texto={(x) => x.nombre}          ← lo que encuentra el buscador
                     sub={(x) => "…"}                 ← la línea chica de cada fila
                     Formulario={...} Eliminar={...}  ← los diálogos: {item, onCerrar, onHecho}
                     mensajes={{ editado: (r) => "…", eliminado: (r) => "…" }} />

   `onHecho(r)` recibe lo que devolvió Python, para armar el mensaje. */

/* Sin tildes ni mayúsculas, como el buscador de la barra lateral. */
export const normalizar = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const capital = (s) => s[0].toUpperCase() + s.slice(1);

export default function ListaGestion({ cargar, clave, singular, plural, texto, sub, Formulario, Eliminar, mensajes = {} }) {
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(cargar, []);
  const [buscar, setBuscar] = useState("");
  const [dialogo, setDialogo] = useState(null);   // { tipo: "nuevo" | "editar" | "eliminar", item }
  if (cargando) return <Cargando />;

  const items = datos || [];
  const filtro = normalizar(buscar.trim());
  const visibles = filtro ? items.filter((x) => normalizar(texto(x)).includes(filtro)) : items;
  const cerrar = () => setDialogo(null);
  const hecho = async (mensaje) => { cerrar(); await recargar(); aviso(mensaje, "info"); };
  const editado = mensajes.editado || (() => `${capital(singular)} actualizado.`);
  const eliminado = mensajes.eliminado || (() => `${capital(singular)} eliminado.`);

  return (
    <>
      <label className="ajustes-buscar ajustes-buscar--lista">
        <IconoBuscar aria-hidden="true" />
        <input type="search" placeholder={`Buscar ${singular}`} aria-label={`Buscar ${singular}`} value={buscar}
               onChange={(e) => setBuscar(e.target.value)}
               onKeyDown={(e) => { if (e.key === "Escape" && buscar) { e.preventDefault(); e.stopPropagation(); setBuscar(""); } }} />
      </label>

      <Grupo titulo={filtro ? `${visibles.length} de ${items.length}` : fmt.plural(items.length, singular, plural)}>
        <Fila etiqueta={`Agregar ${singular}`} icono={IconoMas} color="#2E9D5B" onClick={() => setDialogo({ tipo: "nuevo" })} />
        {visibles.map((x) => (
          <div key={x[clave]} className="fila-ajuste fila-ajuste--acciones fila-gestion">
            <span className="fila-textil__info">
              <span className="fila-textil__nombre">{x[clave]}</span>
              <span className="fila-textil__sub">{sub(x) || "—"}</span>
            </span>
            <span className="fila-ajuste__control">
              <button className="btn-fila-ajuste" type="button" title="Editar" aria-label={`Editar ${x[clave]}`}
                      onClick={() => setDialogo({ tipo: "editar", item: x })}><IconoEditar /></button>
              <button className="btn-fila-ajuste btn-fila-ajuste--peligro" type="button" title="Eliminar" aria-label={`Eliminar ${x[clave]}`}
                      onClick={() => setDialogo({ tipo: "eliminar", item: x })}><IconoEliminar /></button>
            </span>
          </div>
        ))}
        {!visibles.length && (
          <p className="ajustes-vacio">{filtro ? `Ningún ${singular} coincide con “${buscar.trim()}”.` : `Todavía no hay ${plural}.`}</p>
        )}
      </Grupo>

      <Dialogo abierto={dialogo?.tipo === "nuevo" || dialogo?.tipo === "editar"} onCerrar={cerrar} className="dlg--desenfoque dlg-catalogo">
        <Formulario item={dialogo?.item} onCerrar={cerrar}
                    onHecho={(r) => hecho(dialogo?.item ? editado(r) : `${capital(singular)} agregado.`)} />
      </Dialogo>
      <Dialogo abierto={dialogo?.tipo === "eliminar"} onCerrar={cerrar} className="dlg--desenfoque dlg-catalogo">
        <Eliminar item={dialogo?.item} onCerrar={cerrar} onHecho={(r) => hecho(eliminado(r))} />
      </Dialogo>
    </>
  );
}

export function Nota({ children }) {
  return <p className="ajustes-nota ajustes-nota--aviso dlg-catalogo__nota" role="status"><IconoAviso aria-hidden="true" /><span>{children}</span></p>;
}

export function Acciones({ onCerrar, enviando, texto, peligro = false }) {
  return (
    <div className="dlg__acciones">
      <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
      <button className={`btn ${peligro ? "btn--peligro" : "btn--primario"} btn--chico`} type="submit" disabled={enviando}>{texto}</button>
    </div>
  );
}
