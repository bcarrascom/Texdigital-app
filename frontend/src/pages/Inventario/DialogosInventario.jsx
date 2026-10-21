import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { useAvisos } from "@/context/AvisosContext";
import Dialogo from "@/components/Dialogo/Dialogo";
import Campo, { enterGuarda } from "@/components/Campo/Campo";
import DialogoMorph from "@/components/DialogoMorph/DialogoMorph";
import IconoEditar from "@/assets/svg/pencil.svg?react";
import IconoEliminar from "@/assets/svg/trash-2.svg?react";
import IconoGuardar from "@/assets/svg/check.svg?react";
import IconoCancelar from "@/assets/svg/x.svg?react";
import * as fmt from "@/utils/formato";

/* Los diálogos del módulo Inventario: "Rollo nuevo" e "Ingresar material"
   (que nacen del botón "+" de su tabla, ver components/DialogoMorph) y la
   lista de proveedores. */

/* Un proveedor nuevo se agrega a la lista al guardar el rollo/material que lo
   usa (la lista crece sola, no es un catálogo cerrado). */
const recordarProveedor = (proveedor) => api.guardar_proveedor(proveedor);

// ── Rollo nuevo ─────────────────────────────────────────────────────────────

export function DialogoRollo({ abierto, origen, textiles, textilInicial, onCerrar, onGuardado }) {
  return (
    <DialogoMorph abierto={abierto} origen={origen} onCerrar={onCerrar}>
      <FormularioRollo textiles={textiles} textilInicial={textilInicial} onCerrar={onCerrar} onGuardado={onGuardado} />
    </DialogoMorph>
  );
}

function FormularioRollo({ textiles, textilInicial = "", onCerrar, onGuardado }) {
  const aviso = useAvisos();
  const [f, setF] = useState({ textil: textilInicial, ancho: "", restantes: "", proveedor: "", compra: "", valor: "" });
  const [errores, setErrores] = useState({});
  const set = (clave, valor) => setF((x) => ({ ...x, [clave]: valor }));

  /* Al elegir un textil se sugiere el valor (el del rollo más reciente de ese
     textil o, si no hay, el del catálogo — ver valor_sugerido_textil). Solo si
     el campo está vacío: no pisa uno que el usuario ya escribió. */
  useEffect(() => {
    if (!f.textil || f.valor) return;
    let vigente = true;
    api.valor_sugerido_textil(f.textil).then((v) => {
      if (vigente && v != null) setF((x) => (x.valor ? x : { ...x, valor: fmt.clp(v) }));
    });
    return () => { vigente = false; };
  }, [f.textil]);

  async function guardar(e) {
    e.preventDefault();
    const ancho = parseFloat(f.ancho), restantes = parseFloat(f.restantes);
    const valor = fmt.leerClp(f.valor), proveedor = f.proveedor.trim();
    // Proveedor y valor obligatorios: sin valor no hay precio de venta con el
    // que calcular las ganancias del rollo, y su fila queda a medias en "—".
    const faltan = {
      textil: !f.textil, ancho: !(ancho > 0), restantes: !(restantes > 0),
      proveedor: !proveedor, valor: !(valor > 0),
    };
    setErrores(faltan);
    if (Object.values(faltan).some(Boolean)) return;
    await recordarProveedor(proveedor);
    await api.crear_rollo(f.textil, ancho, restantes, fmt.leerClp(f.compra) || 0, valor, proveedor);
    aviso("Rollo guardado.", "info");
    onGuardado();
  }

  return (
    <form onSubmit={guardar} onKeyDown={enterGuarda}>
      <h2 className="dlg__titulo">Rollo nuevo</h2>
      <div className="dlg-inventario__campos">
        <Campo id="dr-textil" etiqueta="Textil" requerido invalido={errores.textil}>
          <select className="entrada" id="dr-textil" data-autofoco value={f.textil} onChange={(e) => set("textil", e.target.value)}>
            <option value="" disabled>Seleccionar textil…</option>
            {textiles.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </Campo>
        <div className="fila">
          <Campo id="dr-ancho" etiqueta="Ancho de tela (m)" requerido invalido={errores.ancho}>
            <input className="entrada" id="dr-ancho" type="number" step="0.01" min="0" value={f.ancho} onChange={(e) => set("ancho", e.target.value)} />
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

// ── Proveedores ─────────────────────────────────────────────────────────────

/* Lista simple (proveedores.json, ver core/repositorio.py) con editar en el
   lugar, eliminar y agregar. Los rollos y materiales que ya tienen un
   proveedor cargado no se tocan: ahí es una copia de texto, no una
   referencia viva a esta lista. */
export function DialogoProveedores({ abierto, proveedores, onCerrar, onCambio }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} className="dlg-proveedores">
      <ListaProveedores proveedores={proveedores} onCerrar={onCerrar} onCambio={onCambio} />
    </Dialogo>
  );
}

function ListaProveedores({ proveedores, onCerrar, onCambio }) {
  const aviso = useAvisos();
  const [editando, setEditando] = useState(null);   // nombre en edición, o null
  const [nuevo, setNuevo] = useState("");

  async function agregar() {
    const nombre = nuevo.trim();
    if (!nombre) return;
    await api.guardar_proveedor(nombre);
    setNuevo("");
    await onCambio();
    aviso("Proveedor agregado.", "info");
  }

  async function renombrar(actual, nombre) {
    if (!nombre || nombre === actual) { setEditando(null); return; }
    if (!(await api.editar_proveedor(actual, nombre))) { aviso("Ya existe un proveedor con ese nombre.", "error"); return; }
    setEditando(null);
    await onCambio();
    aviso("Proveedor actualizado.", "info");
  }

  async function eliminar(nombre) {
    await api.eliminar_proveedor(nombre);
    await onCambio();
    aviso("Proveedor eliminado.", "info");
  }

  return (
    <>
      <h2 className="dlg__titulo">Proveedores</h2>
      {proveedores.length ? (
        <div className="proveedores-lista">
          {proveedores.map((p) => p === editando
            ? <FilaEditando key={p} nombre={p} onGuardar={(n) => renombrar(p, n)} onCancelar={() => setEditando(null)} />
            : (
              <div key={p} className="fila-proveedor">
                <span className="fila-proveedor__nombre">{p}</span>
                <div className="fila-proveedor__acciones">
                  <button className="btn-fila-icono" type="button" title="Editar" onClick={() => setEditando(p)}><IconoEditar /></button>
                  <button className="btn-fila-icono btn-fila-icono--peligro" type="button" title="Eliminar" onClick={() => eliminar(p)}><IconoEliminar /></button>
                </div>
              </div>
            ))}
        </div>
      ) : <p className="proveedores-vacio">Todavía no hay proveedores guardados.</p>}
      <div className="proveedores-alta">
        <input className="entrada" type="text" placeholder="Nuevo proveedor…" autoComplete="off" data-autofoco
               value={nuevo} onChange={(e) => setNuevo(e.target.value)}
               onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); agregar(); } }} />
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cerrar</button>
      </div>
    </>
  );
}

/* Editar es en el lugar (la fila se vuelve un campo con ✓ / ✕): el nombre es
   lo único que se edita, no vale un segundo diálogo para un solo campo. */
function FilaEditando({ nombre, onGuardar, onCancelar }) {
  const [valor, setValor] = useState(nombre);
  return (
    <div className="fila-proveedor">
      <div className="fila-proveedor__nombre">
        <input className="entrada" type="text" autoComplete="off" autoFocus value={valor}
               onFocus={(e) => e.target.select()} onChange={(e) => setValor(e.target.value)}
               onKeyDown={(e) => {
                 if (e.key === "Enter") { e.preventDefault(); onGuardar(valor.trim()); }
                 // Escape cancela la edición, no cierra el diálogo entero.
                 if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onCancelar(); }
               }} />
      </div>
      <div className="fila-proveedor__acciones">
        <button className="btn-fila-icono" type="button" title="Guardar" onClick={() => onGuardar(valor.trim())}><IconoGuardar /></button>
        <button className="btn-fila-icono" type="button" title="Cancelar" onClick={onCancelar}><IconoCancelar /></button>
      </div>
    </div>
  );
}
