import { useState } from "react";
import { api } from "@/services/api";
import Campo, { enterGuarda } from "@/components/Campo/Campo";
import Segmento from "@/components/Segmento/Segmento";
import * as fmt from "@/utils/formato";
import { ErrorGeneral, useEnvio } from "./DialogosCatalogo";
import ListaGestion, { Acciones, Nota } from "./ListaGestion";

/* Clientes y contactos: las dos listas que sugiere el cotizador (ver
   core/repositorio.py, clientes.json y contactos.json en Dropbox/SGTD/Conf).
   Agregar, editar y eliminar, cada cosa en un diálogo que se aplica al
   confirmar. Las cotizaciones y OPs ya hechas guardan una copia de estos
   datos: cambiarlos acá no las toca.

   Un cliente se liga a sus direcciones de despacho por el RUT: si cambia el
   RUT o el nombre, sus direcciones lo siguen, y si se elimina, se borran. */

const LISTAS = [{ valor: "clientes", etiqueta: "Clientes" }, { valor: "contactos", etiqueta: "Contactos" }];

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

/* Las direcciones siguen al cliente (ver core.repositorio.editar_cliente). */
const conDirecciones = (n) => (n === 1 ? "su dirección" : `sus ${n} direcciones`);
const MENSAJES_CLIENTE = {
  editado: (r) => `Cliente actualizado${r?.direcciones ? `, con ${conDirecciones(r.direcciones)}` : ""}.`,
  eliminado: (r) => `Cliente eliminado${r?.direcciones ? `, con ${conDirecciones(r.direcciones)}` : ""}.`,
};

// ── Clientes ───────────────────────────────────────────────────────────────

function Clientes() {
  return (
    <ListaGestion cargar={() => api.obtener_clientes()} clave="empresa" singular="cliente" plural="clientes"
                  texto={(c) => `${c.empresa} ${c.rut} ${c.razon_social}`}
                  sub={(c) => [c.rut, c.razon_social, c.direcciones && fmt.plural(c.direcciones, "dirección", "direcciones")].filter(Boolean).join(" · ")}
                  Formulario={FormularioCliente} Eliminar={EliminarCliente} mensajes={MENSAJES_CLIENTE} />
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
