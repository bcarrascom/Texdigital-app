import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { useAvisos } from "@/context/AvisosContext";
import Campo, { enterGuarda } from "@/components/Campo/Campo";
import DialogoMorph from "@/components/DialogoMorph/DialogoMorph";
import CampoTextil, { textilDe } from "./CampoTextil";
import * as fmt from "@/utils/formato";

/* Los diálogos del módulo Inventario: "Rollo nuevo" e "Ingresar material",
   que nacen del botón "+" de su tabla (ver components/DialogoMorph). La
   lista de proveedores vive en Configuración. */

/* Un proveedor nuevo se agrega a la lista al guardar el rollo/material que lo
   usa (la lista crece sola, no es un catálogo cerrado). */
const recordarProveedor = (proveedor) => api.guardar_proveedor(proveedor);

// ── Rollo nuevo ─────────────────────────────────────────────────────────────

/* `textilCreado`: {nombre, ancho} del textil que se acaba de agregar con
   "Textil nuevo" (el diálogo vive en la página, ver Inventario.jsx): el
   rollo lo toma. */
export function DialogoRollo({ abierto, origen, textiles, textilInicial, textilCreado, onTextilNuevo, onCerrar, onGuardado }) {
  return (
    <DialogoMorph abierto={abierto} origen={origen} onCerrar={onCerrar}>
      <FormularioRollo textiles={textiles} textilInicial={textilInicial} textilCreado={textilCreado} onTextilNuevo={onTextilNuevo}
                       onCerrar={onCerrar} onGuardado={onGuardado} />
    </DialogoMorph>
  );
}

/* Lo que dice el campo Textil cuando lo escrito no es un textil de Configuración. */
export const TEXTIL_DESCONOCIDO = "No está en Configuración › Textiles: elígelo de la lista o agrégalo con «Textil nuevo».";

/* El textil recién agregado pasa al formulario. */
export function useTextilCreado(textilCreado, setF) {
  useEffect(() => {
    if (!textilCreado) return;
    setF((x) => ({ ...x, textil: textilCreado.nombre }));
  }, [textilCreado]);
}

/* Sin ancho: el de un rollo es el de su textil en Configuración (pedido de
   Bruno, 2026-11-04, ver core.repositorio_inventario.ancho_rollo). */
function FormularioRollo({ textiles, textilInicial = "", textilCreado, onTextilNuevo, onCerrar, onGuardado }) {
  const aviso = useAvisos();
  const [f, setF] = useState({ id: "", textil: textilInicial, restantes: "", proveedor: "", compra: "", valor: "" });
  const [errores, setErrores] = useState({});
  const set = (clave, valor) => setF((x) => ({ ...x, [clave]: valor }));
  useTextilCreado(textilCreado, setF);
  const textil = textilDe(textiles, f.textil);

  /* El número: el siguiente, ya escrito; se puede cambiar por otro (p. ej. el
     de la etiqueta del rollo, pedido de Bruno, 2026-11-04) que no tenga ni
     haya tenido otro rollo. Python lo revisa mientras se escribe. */
  const [sugerido, setSugerido] = useState("");
  const [errorId, setErrorId] = useState(null);
  useEffect(() => {
    api.siguiente_id_rollo().then((id) => {
      setSugerido(id);
      setF((x) => (x.id ? x : { ...x, id }));
    });
  }, []);
  const idElegido = f.id.trim() && f.id.trim() !== sugerido ? f.id.trim() : null;
  useEffect(() => {
    setErrorId(null);
    if (!idElegido) return;
    let vigente = true;
    const espera = setTimeout(() => api.validar_id_rollo(idElegido).then((r) => vigente && setErrorId(r?.error || null)), 250);
    return () => { vigente = false; clearTimeout(espera); };
  }, [idElegido]);

  /* Al elegir un textil se sugiere el valor (el del rollo más reciente de ese
     textil o, si no hay, el del catálogo — ver valor_sugerido_textil). Solo si
     el campo está vacío: no pisa uno que el usuario ya escribió. */
  useEffect(() => {
    if (!textil || f.valor) return;
    let vigente = true;
    api.valor_sugerido_textil(textil).then((v) => {
      if (vigente && v != null) setF((x) => (x.valor ? x : { ...x, valor: fmt.clp(v) }));
    });
    return () => { vigente = false; };
  }, [textil]);

  async function guardar(e) {
    e.preventDefault();
    const restantes = parseFloat(f.restantes);
    const valor = fmt.leerClp(f.valor), proveedor = f.proveedor.trim();
    // Proveedor y valor obligatorios: sin valor no hay precio de venta con el
    // que calcular las ganancias del rollo, y su fila queda a medias en "—".
    const faltan = {
      id: !f.id.trim() || !!errorId, textil: !textil, restantes: !(restantes > 0),
      proveedor: !proveedor, valor: !(valor > 0),
    };
    setErrores(faltan);
    if (Object.values(faltan).some(Boolean)) return;
    await recordarProveedor(proveedor);
    // Sin cambiar el número, se pide "el siguiente": si otra instalación tomó
    // el sugerido mientras tanto, este rollo se lleva el que sigue.
    const r = await api.crear_rollo(textil, restantes, fmt.leerClp(f.compra) || 0, valor, proveedor, idElegido);
    if (r?.error) {
      setErrorId(r.error);
      setErrores((x) => ({ ...x, id: true }));
      return;
    }
    aviso(r?.id ? `Rollo #${r.id} guardado.` : "Rollo guardado.", "info");
    onGuardado();
  }

  return (
    <form onSubmit={guardar} onKeyDown={enterGuarda}>
      <h2 className="dlg__titulo">Rollo nuevo</h2>
      <div className="dlg-inventario__campos">
        <CampoTextil id="dr-textil" textiles={textiles} valor={f.textil} onCambiar={(v) => set("textil", v)} onNuevo={onTextilNuevo}
                     invalido={errores.textil} error={f.textil.trim() ? TEXTIL_DESCONOCIDO : undefined} autofoco />
        <div className="fila">
          <Campo id="dr-id" etiqueta="Número" requerido invalido={errores.id || !!errorId} error={errorId || undefined}>
            <input className="entrada" id="dr-id" type="text" inputMode="numeric" autoComplete="off" placeholder={sugerido}
                   value={f.id} onChange={(e) => set("id", e.target.value.replace(/[^\d]/g, "").slice(0, 4))} />
          </Campo>
          <Campo id="dr-restantes" etiqueta="Metros disponibles" requerido invalido={errores.restantes}>
            <input className="entrada" id="dr-restantes" type="number" step="0.01" min="0" value={f.restantes} onChange={(e) => set("restantes", e.target.value)} />
          </Campo>
        </div>
        {/* El proveedor, al doble de ancho que el precio de compra: los nombres
            suelen ser largos. */}
        <div className="fila fila--proveedor">
          <Campo id="dr-proveedor" etiqueta="Proveedor" requerido invalido={errores.proveedor}>
            <input className="entrada" id="dr-proveedor" type="text" list="lista-proveedores" autoComplete="off"
                   value={f.proveedor} onChange={(e) => set("proveedor", e.target.value)} />
          </Campo>
          <Campo id="dr-compra" etiqueta="Precio de compra">
            <input className="entrada" id="dr-compra" type="text" inputMode="numeric" placeholder="Opcional"
                   value={f.compra} onChange={(e) => set("compra", fmt.clp(e.target.value))} />
          </Campo>
        </div>
        <Campo id="dr-valor" etiqueta="Valor por ML/M²" requerido invalido={errores.valor} className="campo--mitad">
          <input className="entrada" id="dr-valor" type="text" inputMode="numeric"
                 value={f.valor} onChange={(e) => set("valor", fmt.clp(e.target.value))} />
        </Campo>
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit">Guardar</button>
      </div>
    </form>
  );
}

// ── Ingresar material ───────────────────────────────────────────────────────

/* Una sola acción para dar de alta un material nuevo O sumarle stock a uno
   que ya existe (ver core.repositorio_materiales.ingresar_material: busca por
   nombre). Por eso el nombre es texto libre con autocompletado: el usuario no
   elige entre "nuevo" y "existente", escribe el nombre y listo. */
export function DialogoMaterial({ abierto, origen, materiales, nombres, onCerrar, onGuardado }) {
  return (
    <DialogoMorph abierto={abierto} origen={origen} onCerrar={onCerrar}>
      <FormularioMaterial materiales={materiales} nombres={nombres} onCerrar={onCerrar} onGuardado={onGuardado} />
    </DialogoMorph>
  );
}

function FormularioMaterial({ materiales, nombres, onCerrar, onGuardado }) {
  const aviso = useAvisos();
  // precargado: el precio de venta vino de un material existente (ver cambiar()).
  const [f, setF] = useState({ nombre: "", cantidad: "", proveedor: "", total: "", unitario: "", valor: "", precargado: false });
  const [errores, setErrores] = useState({});

  const existente = materiales.find((m) => (m.nombre || "").trim().toLowerCase() === f.nombre.trim().toLowerCase() && f.nombre.trim()) || null;

  /* Costo total y unitario se completan uno al otro según la cantidad. */
  function completarCostos(x, desde) {
    const cantidad = parseFloat(x.cantidad);
    if (!(cantidad > 0)) return x;
    if (desde === "total" && fmt.leerClp(x.total) != null) return { ...x, unitario: fmt.clp(Math.round(fmt.leerClp(x.total) / cantidad)) };
    if (desde === "unitario" && fmt.leerClp(x.unitario) != null) return { ...x, total: fmt.clp(Math.round(fmt.leerClp(x.unitario) * cantidad)) };
    return x;
  }

  function cambiar(clave, valor) {
    setF((x) => {
      let nuevo = { ...x, [clave]: valor };
      if (clave === "total" || clave === "unitario") nuevo = completarCostos(nuevo, clave);
      if (clave === "cantidad") nuevo = completarCostos(nuevo, fmt.leerClp(x.total) != null ? "total" : "unitario");
      /* Un material que ya existe ya tiene su precio de venta: se muestra de
         solo lectura (cambiarlo es un ajuste, y queda registrado como tal en
         su historial), y si el proveedor está vacío se trae el suyo. */
      if (clave === "nombre") {
        const ya = materiales.find((m) => (m.nombre || "").trim().toLowerCase() === valor.trim().toLowerCase() && valor.trim());
        if (ya) {
          nuevo = { ...nuevo, valor: ya.valor != null ? fmt.clp(ya.valor) : "", proveedor: nuevo.proveedor || ya.proveedor || "", precargado: true };
        } else if (x.precargado) {
          // Dejó de ser uno existente: su precio no es del material nuevo.
          nuevo = { ...nuevo, valor: "", precargado: false };
        }
      }
      return nuevo;
    });
  }

  async function guardar(e) {
    e.preventDefault();
    const cantidad = parseFloat(f.cantidad), proveedor = f.proveedor.trim(), valor = fmt.leerClp(f.valor);
    // El precio de venta solo se exige en un material NUEVO.
    const faltan = { nombre: !f.nombre.trim(), cantidad: !(cantidad > 0), proveedor: !proveedor, valor: !existente && !(valor > 0) };
    setErrores(faltan);
    if (Object.values(faltan).some(Boolean)) return;
    await recordarProveedor(proveedor);
    await api.ingresar_material(f.nombre.trim(), cantidad, "unidad", proveedor, fmt.leerClp(f.total), fmt.leerClp(f.unitario),
                                null, null, null, null, null, existente ? null : valor);
    aviso("Material ingresado.", "info");
    onGuardado();
  }

  const campo = (clave, formato) => ({ value: f[clave], onChange: (e) => cambiar(clave, formato ? formato(e.target.value) : e.target.value) });

  return (
    <form onSubmit={guardar} onKeyDown={enterGuarda}>
      <h2 className="dlg__titulo">Ingresar material</h2>
      <div className="dlg-inventario__campos">
        <Campo id="dm-nombre" etiqueta="Material" requerido invalido={errores.nombre}>
          <input className="entrada" id="dm-nombre" type="text" list="lista-materiales" autoComplete="off" data-autofoco {...campo("nombre")} />
        </Campo>
        <div className="fila">
          <Campo id="dm-cantidad" etiqueta="Cantidad" requerido invalido={errores.cantidad}>
            <input className="entrada" id="dm-cantidad" type="number" step="0.01" min="0" {...campo("cantidad")} />
          </Campo>
          <Campo id="dm-proveedor" etiqueta="Proveedor" requerido invalido={errores.proveedor}>
            <input className="entrada" id="dm-proveedor" type="text" list="lista-proveedores" autoComplete="off" {...campo("proveedor")} />
          </Campo>
        </div>
        <div className="fila">
          <Campo id="dm-total" etiqueta="Costo total">
            <input className="entrada" id="dm-total" type="text" inputMode="numeric" placeholder="Opcional" {...campo("total", fmt.clp)} />
          </Campo>
          <Campo id="dm-unitario" etiqueta="Costo unitario">
            <input className="entrada" id="dm-unitario" type="text" inputMode="numeric" placeholder="Opcional" {...campo("unitario", fmt.clp)} />
          </Campo>
        </div>
        {/* Obligatorio al dar de alta: sin él, el material no aporta ganancias
            y el faltante se nota recién al cotizar. */}
        <Campo id="dm-valor" etiqueta="Precio de venta" requerido={!existente} invalido={errores.valor}
               ayuda={existente ? "Ya cargado. Para cambiarlo, usá “Ajustar · Precio” en el material." : ""}>
          <input className="entrada" id="dm-valor" type="text" inputMode="numeric" readOnly={!!existente} {...campo("valor", fmt.clp)} />
        </Campo>
      </div>
      <datalist id="lista-materiales">
        {nombres.map((n) => <option key={n} value={n} />)}
      </datalist>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit">Guardar</button>
      </div>
    </form>
  );
}
