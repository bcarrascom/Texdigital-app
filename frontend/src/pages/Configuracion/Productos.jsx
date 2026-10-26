import { useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import Campo, { enterGuarda } from "@/components/Campo/Campo";
import * as fmt from "@/utils/formato";
import { Fila, Grupo } from "./Ajustes";
import { ErrorGeneral, useEnvio } from "./DialogosCatalogo";
import ListaGestion, { Acciones, Nota } from "./ListaGestion";

/* Productos: la lista que se elige en el cotizador (ver core/catalogo.py).
   Un producto es solo un nombre; lo que cuelga de él son los materiales de
   Inventario asociados (se ven en cada fila), que lo siguen si se renombra y
   lo sueltan si se quita. Las cotizaciones y OPs ya hechas conservan el
   nombre con que se hicieron (y una vieja con el nombre anterior sigue
   gastando sus materiales al aprobarla).

   Abajo, aparte, los materiales de "Backlight" y "Backlight + Caja": no son
   productos del cotizador, pero se les asocian materiales igual. */

const NO_CAMBIAN = "Las cotizaciones y OPs ya hechas conservan el nombre con que se hicieron.";
const FALTA = { valor: "sin valor de venta", consumo: "sin consumo automático" };

/* "Ojetillo, Cinta (sin valor de venta)" */
export const nombresMateriales = (ms) =>
  ms.map((m) => (m.falta ? `${m.nombre} (${FALTA[m.falta]})` : m.nombre)).join(", ");
const conMateriales = (ms) => (ms?.length ? `Materiales: ${nombresMateriales(ms)}` : null);
const cuantos = (n) => fmt.plural(n, "material asociado", "materiales asociados");

const MENSAJES = {
  editado: (r) => `Producto renombrado${r?.materiales ? `, con ${cuantos(r.materiales)}` : ""}.`,
  eliminado: (r) => `Producto quitado${r?.materiales ? `: ${fmt.plural(r.materiales, "material dejó", "materiales dejaron")} de estar asociado${r.materiales === 1 ? "" : "s"}` : ""}.`,
};

export default function Productos() {
  return (
    <>
      <ListaGestion cargar={() => api.obtener_productos()} clave="nombre" singular="producto" plural="productos"
                    texto={(p) => `${p.nombre} ${(p.anteriores || []).join(" ")} ${(p.materiales || []).map((m) => m.nombre).join(" ")}`}
                    sub={(p) => [conMateriales(p.materiales), p.anteriores?.length && `antes: ${p.anteriores.join(", ")}`,
                                 p.agregado && "agregado en Configuración"].filter(Boolean).join(" · ")}
                    Formulario={FormularioProducto} Eliminar={QuitarProducto} mensajes={MENSAJES} />
      <MaterialesBacklight />
    </>
  );
}

function MaterialesBacklight() {
  const { datos } = useDatos(() => api.obtener_materiales_backlight(), []);
  if (!datos) return null;
  return (
    <Grupo titulo="Backlight"
           pie="No son productos del cotizador: «Backlight» es todo backlight, y «Backlight + Caja», los que llevan caja. Sus materiales se asocian en la ficha de cada material (Inventario › Materiales › Editar).">
      {datos.map((b) => (
        <Fila key={b.nombre} etiqueta={b.nombre} detalle={b.materiales.length ? nombresMateriales(b.materiales) : "Sin materiales asociados"} />
      ))}
    </Grupo>
  );
}

function FormularioProducto({ item, onCerrar, onHecho }) {
  const [nombre, setNombre] = useState(item?.nombre ?? "");
  const { errores, enviando, confirmar } = useEnvio(
    () => (item ? api.renombrar_producto(item.nombre, { nombre }) : api.agregar_producto({ nombre })), onHecho);
  const renombra = item && nombre.trim() && nombre.trim() !== item.nombre;
  const ms = item?.materiales || [];
  return (
    <form onSubmit={confirmar} onKeyDown={enterGuarda} noValidate>
      <h2 className="dlg__titulo">{item ? "Renombrar producto" : "Agregar producto"}</h2>
      <div className="dlg-catalogo__campos">
        <Campo id="prod-nombre" etiqueta="Nombre" requerido invalido={!!errores.nombre} error={errores.nombre}
               ayuda="Así aparece en el cotizador y en la cotización.">
          <input className="entrada" id="prod-nombre" type="text" autoComplete="off" data-autofoco
                 value={nombre} onChange={(e) => setNombre(e.target.value)} />
        </Campo>
      </div>
      {item && (
        <p className="campo__ayuda dlg-catalogo__nota">
          {ms.length ? `Materiales de Inventario que gasta: ${nombresMateriales(ms)}.` : "No gasta materiales de Inventario."}
        </p>
      )}
      {renombra && (
        <Nota>
          {ms.length === 1 ? "Su material asociado pasa al nombre nuevo. "
            : ms.length ? `Sus ${ms.length} materiales asociados pasan al nombre nuevo. ` : ""}
          {NO_CAMBIAN} Una con el nombre anterior sigue gastando sus materiales al aprobarla.
        </Nota>
      )}
      <ErrorGeneral texto={errores.general} />
      <Acciones onCerrar={onCerrar} enviando={enviando} texto={item ? "Renombrar" : "Agregar"} />
    </form>
  );
}

function QuitarProducto({ item, onCerrar, onHecho }) {
  const { errores, enviando, confirmar } = useEnvio(() => api.quitar_producto(item.nombre), onHecho);
  const ms = item.materiales || [];
  return (
    <form onSubmit={confirmar} noValidate>
      <h2 className="dlg__titulo">¿Quitar {item.nombre}?</h2>
      <p className="dlg__texto">
        Deja de aparecer en el cotizador. {NO_CAMBIAN} Si después lo vuelves a agregar con el mismo nombre, vuelve a su lugar en la lista.
      </p>
      {ms.length > 0 && (
        <Nota>
          {ms.length === 1 ? `${ms[0].nombre} deja de estar asociado` : `${nombresMateriales(ms)} dejan de estar asociados`} a
          este producto: una cotización vieja con este producto ya no {ms.length === 1 ? "lo" : "los"} gasta al aprobarla.
        </Nota>
      )}
      <ErrorGeneral texto={errores.general} />
      <Acciones onCerrar={onCerrar} enviando={enviando} texto="Quitar" peligro />
    </form>
  );
}
