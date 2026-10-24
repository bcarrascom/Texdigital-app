import { useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import Dialogo from "@/components/Dialogo/Dialogo";
import Campo, { enterGuarda } from "@/components/Campo/Campo";
import Segmento from "@/components/Segmento/Segmento";
import IconoBuscar from "@/assets/svg/search.svg?react";
import IconoEditar from "@/assets/svg/pencil.svg?react";
import IconoEliminar from "@/assets/svg/trash-2.svg?react";
import IconoMas from "@/assets/svg/plus.svg?react";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import * as fmt from "@/utils/formato";
import { Fila, Grupo } from "./Ajustes";
import { ErrorGeneral, useEnvio } from "./DialogosCatalogo";

/* Clientes y contactos: las dos listas que sugiere el cotizador (ver
   core/repositorio.py, clientes.json y contactos.json en Dropbox/SGTD/Conf).
   Agregar, editar y eliminar, cada cosa en un diálogo que se aplica al
   confirmar. Las cotizaciones y OPs ya hechas guardan una copia de estos
   datos: cambiarlos acá no las toca.

   Un cliente se liga a sus direcciones de despacho por el RUT: si cambia el
   RUT o el nombre, sus direcciones lo siguen, y si se elimina, se borran. */

const LISTAS = [{ valor: "clientes", etiqueta: "Clientes" }, { valor: "contactos", etiqueta: "Contactos" }];

/* Sin tildes ni mayúsculas, como el buscador de la barra lateral. */
const normalizar = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const NO_CAMBIAN = "Las cotizaciones y OPs ya hechas conservan los datos con que se hicieron.";

export default function ClientesContactos() {
  const [lista, setLista] = useState("clientes");
  return (
    <>
      <div className="ajustes-pestanas">
        <Segmento etiqueta="Qué lista ver" opciones={LISTAS} valor={lista} onCambiar={setLista} bloque />
      </div>
      {lista === "clientes" ? <Clientes /> : <Contactos />}
    </>
  );
}

/* La lista con su buscador, "Agregar" arriba y editar/eliminar en cada fila
   (aparecen al pasar el mouse, como en Proveedores). */
function ListaGestion({ cargar, clave, singular, plural, texto, sub, Formulario, Eliminar }) {
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
                    onHecho={(r) => hecho(dialogo?.item ? mensajeEditado(singular, r) : `${capital(singular)} agregado.`)} />
      </Dialogo>
      <Dialogo abierto={dialogo?.tipo === "eliminar"} onCerrar={cerrar} className="dlg--desenfoque dlg-catalogo">
        <Eliminar item={dialogo?.item} onCerrar={cerrar} onHecho={(r) => hecho(mensajeEliminado(singular, r))} />
      </Dialogo>
    </>
  );
}

const capital = (s) => s[0].toUpperCase() + s.slice(1);
const conDirecciones = (n) => (n === 1 ? "su dirección" : `sus ${n} direcciones`);
const mensajeEditado = (singular, r) =>
  `${capital(singular)} actualizado${r?.direcciones ? `, con ${conDirecciones(r.direcciones)}` : ""}.`;
const mensajeEliminado = (singular, r) =>
  `${capital(singular)} eliminado${r?.direcciones ? `, con ${conDirecciones(r.direcciones)}` : ""}.`;

function Nota({ children }) {
  return <p className="ajustes-nota ajustes-nota--aviso dlg-catalogo__nota" role="status"><IconoAviso aria-hidden="true" /><span>{children}</span></p>;
}

function Acciones({ onCerrar, enviando, texto, peligro = false }) {
  return (
    <div className="dlg__acciones">
      <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
      <button className={`btn ${peligro ? "btn--peligro" : "btn--primario"} btn--chico`} type="submit" disabled={enviando}>{texto}</button>
    </div>
  );
}

// ── Clientes ───────────────────────────────────────────────────────────────

function Clientes() {
  return (
    <ListaGestion cargar={() => api.obtener_clientes()} clave="empresa" singular="cliente" plural="clientes"
                  texto={(c) => `${c.empresa} ${c.rut} ${c.razon_social}`}
                  sub={(c) => [c.rut, c.razon_social, c.direcciones && fmt.plural(c.direcciones, "dirección", "direcciones")].filter(Boolean).join(" · ")}
                  Formulario={FormularioCliente} Eliminar={EliminarCliente} />
  );
}

function FormularioCliente({ item, onCerrar, onHecho }) {
  const [f, setF] = useState({ empresa: item?.empresa ?? "", rut: item?.rut ?? "", razon_social: item?.razon_social ?? "" });
  const set = (clave, valor) => setF((x) => ({ ...x, [clave]: valor }));
  const { errores, enviando, confirmar } = useEnvio(
    () => (item ? api.editar_cliente(item.empresa, f) : api.crear_cliente(f)), onHecho);
  const cambiaLigado = item?.direcciones > 0 && (f.rut !== item.rut || f.empresa.trim() !== item.empresa);

  return (
    <form onSubmit={confirmar} onKeyDown={enterGuarda} noValidate>
      <h2 className="dlg__titulo">{item ? "Editar cliente" : "Agregar cliente"}</h2>
      <div className="dlg-catalogo__campos">
        <Campo id="cli-empresa" etiqueta="Empresa" requerido invalido={!!errores.empresa} error={errores.empresa}
               ayuda="El nombre con que se busca en el cotizador.">
          <input className="entrada" id="cli-empresa" type="text" autoComplete="off" data-autofoco
                 value={f.empresa} onChange={(e) => set("empresa", e.target.value)} />
        </Campo>
        <Campo id="cli-rut" etiqueta="RUT" invalido={!!errores.rut}>
          <input className="entrada" id="cli-rut" type="text" autoComplete="off" placeholder="12.345.678-5"
                 value={f.rut} onChange={(e) => set("rut", fmt.rut(e.target.value))} />
        </Campo>
        <Campo id="cli-razon" etiqueta="Razón social">
          <input className="entrada" id="cli-razon" type="text" autoComplete="off"
                 value={f.razon_social} onChange={(e) => set("razon_social", e.target.value)} />
        </Campo>
      </div>
      {cambiaLigado && <Nota>Sus {fmt.plural(item.direcciones, "dirección guardada pasa", "direcciones guardadas pasan")} a los datos nuevos. {NO_CAMBIAN}</Nota>}
      {item && !cambiaLigado && <p className="campo__ayuda dlg-catalogo__nota">{NO_CAMBIAN}</p>}
      <ErrorGeneral texto={errores.general || errores.rut} />
      <Acciones onCerrar={onCerrar} enviando={enviando} texto={item ? "Guardar" : "Agregar"} />
    </form>
  );
}

function EliminarCliente({ item, onCerrar, onHecho }) {
  const { errores, enviando, confirmar } = useEnvio(() => api.eliminar_cliente(item.empresa), onHecho);
  return (
    <form onSubmit={confirmar} noValidate>
      <h2 className="dlg__titulo">¿Eliminar a {item.empresa}?</h2>
      <p className="dlg__texto">Deja de aparecer en el cotizador. {NO_CAMBIAN}</p>
      {item.direcciones > 0 && <Nota>También se {item.direcciones === 1 ? "borra su dirección guardada" : `borran sus ${item.direcciones} direcciones guardadas`}.</Nota>}
      <ErrorGeneral texto={errores.general} />
      <Acciones onCerrar={onCerrar} enviando={enviando} texto="Eliminar" peligro />
    </form>
  );
}

// ── Contactos ──────────────────────────────────────────────────────────────

const descuentoTexto = (d) => (d && Number(d) ? `${String(d).replace(".", ",")} % de descuento` : null);

function Contactos() {
  return (
    <ListaGestion cargar={() => api.obtener_contactos()} clave="contacto" singular="contacto" plural="contactos"
                  texto={(c) => `${c.contacto} ${c.email} ${c.condicion}`}
                  sub={(c) => [c.email, descuentoTexto(c.descuento), c.condicion].filter(Boolean).join(" · ")}
                  Formulario={FormularioContacto} Eliminar={EliminarContacto} />
  );
}

function FormularioContacto({ item, onCerrar, onHecho }) {
  const [f, setF] = useState({
    contacto: item?.contacto ?? "", email: item?.email ?? "",
    descuento: item?.descuento && item.descuento !== "0" ? String(item.descuento).replace(".", ",") : "",
    condicion: item?.condicion ?? "",
  });
  const set = (clave, valor) => setF((x) => ({ ...x, [clave]: valor }));
  const { errores, enviando, confirmar } = useEnvio(
    () => (item ? api.editar_contacto(item.contacto, f) : api.crear_contacto(f)), onHecho);

  return (
    <form onSubmit={confirmar} onKeyDown={enterGuarda} noValidate>
      <h2 className="dlg__titulo">{item ? "Editar contacto" : "Agregar contacto"}</h2>
      <div className="dlg-catalogo__campos">
        <Campo id="con-nombre" etiqueta="Nombre" requerido invalido={!!errores.contacto} error={errores.contacto}>
          <input className="entrada" id="con-nombre" type="text" autoComplete="off" data-autofoco
                 value={f.contacto} onChange={(e) => set("contacto", e.target.value)} />
        </Campo>
        <Campo id="con-email" etiqueta="Correo" invalido={!!errores.email}>
          <input className="entrada" id="con-email" type="email" autoComplete="off"
                 value={f.email} onChange={(e) => set("email", e.target.value)} />
        </Campo>
        <Campo id="con-descuento" etiqueta="Descuento (%)" invalido={!!errores.descuento}
               ayuda="El que el cotizador propone al elegir este contacto. Vacío, sin descuento.">
          <input className="entrada entrada--num" id="con-descuento" type="text" inputMode="decimal" autoComplete="off" placeholder="0"
                 value={f.descuento} onChange={(e) => set("descuento", e.target.value.replace(/[^\d,.]/g, ""))} />
        </Campo>
        <Campo id="con-condicion" etiqueta="Condición de pago">
          <input className="entrada" id="con-condicion" type="text" autoComplete="off" placeholder="Ej.: 30 días"
                 value={f.condicion} onChange={(e) => set("condicion", e.target.value)} />
        </Campo>
      </div>
      {item && <p className="campo__ayuda dlg-catalogo__nota">{NO_CAMBIAN}</p>}
      <ErrorGeneral texto={errores.general || errores.email || errores.descuento} />
      <Acciones onCerrar={onCerrar} enviando={enviando} texto={item ? "Guardar" : "Agregar"} />
    </form>
  );
}

function EliminarContacto({ item, onCerrar, onHecho }) {
  const { errores, enviando, confirmar } = useEnvio(() => api.eliminar_contacto(item.contacto), onHecho);
  return (
    <form onSubmit={confirmar} noValidate>
      <h2 className="dlg__titulo">¿Eliminar a {item.contacto}?</h2>
      <p className="dlg__texto">Deja de aparecer en el cotizador. {NO_CAMBIAN}</p>
      <ErrorGeneral texto={errores.general} />
      <Acciones onCerrar={onCerrar} enviando={enviando} texto="Eliminar" peligro />
    </form>
  );
}
