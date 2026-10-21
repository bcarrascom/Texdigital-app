import { useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import { rutas } from "@/router/rutas";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import Dialogo from "@/components/Dialogo/Dialogo";
import DialogoMorph from "@/components/DialogoMorph/DialogoMorph";
import Etiqueta from "@/components/Etiqueta/Etiqueta";
import { Datos } from "@/components/Detalle/Detalle";
import Historial, { EnlaceOp } from "@/pages/Inventario/Historial";
import { unidadDe } from "@/pages/Inventario/TablaMateriales";
import { AjustarMaterial, EditarMaterial, EliminarMaterial, Restock } from "./DialogosMaterial";
import * as fmt from "@/utils/formato";
import "@/pages/Inventario/Ficha.css";
import "./VerMaterial.css";

/* La pantalla de un material no textil (antes recursos/pantallas/
   ver-material.html). Calco de la del rollo, con sus diferencias:
     · sin ID visible (es solo para la lógica): el nombre es el título;
     · en vez de Activo/Inactivo, la etiqueta dice cómo se cobra;
     · el historial tiene cuatro tipos: restock (proveedor y costo), ajuste
       (en + o en -), consumo (automático al aprobar una OP, con el link) y
       precio (cambio del precio de venta, el único que no mueve stock).
   Acá viven Ajustar (cantidad o precio), Editar, Restock y Eliminar. */

const ETIQUETA_TIPO = { restock: "Restock", ajuste: "Ajuste", consumo: "Consumo", precio: "Precio" };
const plata = (v, sufijo = "") => (v == null ? "—" : fmt.pesos(v) + sufijo);

async function cargarMaterial(id) {
  const [material, proveedores, productos, estructuras] = await Promise.all([
    api.obtener_material(id), api.cargar_proveedores(),
    api.cargar_productos_catalogo(), api.cargar_estructuras_catalogo(),
  ]);
  return { material: material || null, proveedores: proveedores || [], productos: productos || [], estructuras: estructuras || [] };
}

/* Un material ya no tiene "un" proveedor: cada restock puede traer uno
   distinto, así que m.proveedor solo es la sugerencia para el próximo. La
   lista real sale de los restocks del historial, más reciente primero. */
function proveedoresDeHistorial(m) {
  const vistos = new Set();
  (m.historial || []).slice().reverse().forEach((h) => { if (h.tipo === "restock" && h.proveedor) vistos.add(h.proveedor); });
  return [...vistos];
}

export default function VerMaterial() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(() => cargarMaterial(id), [id]);
  const [dialogo, setDialogo] = useState(null);   // "ajustar" | "editar" | "restock" | "eliminar" | null
  const botonRestock = useRef(null);
  const m = datos?.material;
  const cerrar = () => setDialogo(null);
  const alGuardar = async (texto) => { cerrar(); await recargar(); aviso(texto, "info"); };

  /* Un material no tiene "decomisionado": se borra para siempre. Después se
     vuelve a la tabla de materiales. */
  async function eliminar() {
    cerrar();
    await api.eliminar_material(m.id);
    aviso("Material eliminado.", "info");
    if (location.state?.desde?.startsWith(rutas.inventario())) navigate(-1);
    else navigate(rutas.inventario({ vista: "materiales" }), { replace: true });
  }

  async function deshacer(u) {
    await api.eliminar_ultimo_historial_material(m.id, u.id);
    await recargar();
  }

  const abrirOp = (numero) => navigate(rutas.verOp(numero), { state: { desde: location.pathname } });
  const titulo = m ? `Material · ${m.nombre || ""}` : "Material";

  return (
    <Pagina tema="inventario" titulo={titulo} className="pag-ficha-inventario pag-ver-material">
      <Cabecera titulo={titulo}>
        {m && (
          <>
            <button className="cab-btn" onClick={() => setDialogo("eliminar")}>Eliminar</button>
            <button className="cab-btn" onClick={() => setDialogo("editar")}>Editar</button>
            <button className="btn btn--primario btn--chico" onClick={() => setDialogo("ajustar")}>Ajustar</button>
            <button ref={botonRestock} className="btn btn--primario btn--chico" onClick={() => setDialogo("restock")}>Restock</button>
          </>
        )}
      </Cabecera>

      <main className="contenido">
        {cargando ? <Cargando /> : !m ? (
          <p className="seccion-titulo">No se pudo cargar el material.</p>
        ) : (
          <div className="ficha">
            <Hoja m={m} />
            <Historial entradas={m.historial || []} vista={(u) => vistaEntrada(u, m, abrirOp)} onDeshacer={deshacer}
                       vacio="Todavía no hay ningún restock, ajuste, consumo ni cambio de precio registrado para este material." />
          </div>
        )}
      </main>

      {m && (
        <>
          <datalist id="lista-proveedores">{datos.proveedores.map((p) => <option key={p} value={p} />)}</datalist>
          <datalist id="lista-productos-catalogo">{datos.productos.map((p) => <option key={p} value={p} />)}</datalist>
          <datalist id="lista-estructuras-catalogo">{datos.estructuras.map((e) => <option key={e} value={e} />)}</datalist>

          <Dialogo abierto={dialogo === "ajustar"} onCerrar={cerrar} className="dlg-ajustar-material">
            <AjustarMaterial m={m} onCerrar={cerrar} onGuardado={alGuardar} />
          </Dialogo>
          <Dialogo abierto={dialogo === "editar"} onCerrar={cerrar} className="dlg-editar-material">
            <EditarMaterial m={m} onCerrar={cerrar} onGuardado={() => alGuardar("Material actualizado.")} />
          </Dialogo>
          <DialogoMorph abierto={dialogo === "restock"} origen={botonRestock} onCerrar={cerrar} anchoRem={26}>
            <Restock m={m} onGuardado={() => alGuardar("Material restockeado.")} />
          </DialogoMorph>
          <Dialogo abierto={dialogo === "eliminar"} onCerrar={cerrar} className="dlg--desenfoque">
            <EliminarMaterial m={m} onCerrar={cerrar} onEliminar={eliminar} />
          </Dialogo>
        </>
      )}
    </Pagina>
  );
}

/* ── La hoja de datos ─────────────────────────────────────────────────────
   Las mismas 9 cifras que la tabla de materiales, en el mismo orden (gastos,
   valor, ganancias). "—" cuando el dato todavía no existe, nunca "$0", que
   significaría otra cosa. */
function Hoja({ m }) {
  const por = `/${unidadDe(m)}`;
  const proveedores = proveedoresDeHistorial(m);
  const mono = { mono: true };
  return (
    <section className="hoja">
      <div className="hoja__cab">
        <div className="hoja__cab-izq">
          <span className="hoja__nombre--principal">{m.nombre || "—"}</span>
        </div>
        <Etiqueta>{m.tipo === "metro" ? "Por metro" : "Por unidad"}</Etiqueta>
      </div>
      <Datos lista={[
        ["Cantidad", `${fmt.cantidad(m.cantidad)} ${unidadDe(m)}`, mono],
        ["Gasto unitario", plata(m.gasto_unitario, por), mono],
        ["Gasto este mes", plata(m.gasto_mes), mono],
        ["Gasto total", plata(m.gasto_total), mono],
        ["Valor unitario", plata(m.valor_unitario, por), mono],
        ["Valor restante", plata(m.valor_restante), mono],
        ["Valor vendido", plata(m.valor_vendido), mono],
        ["Ganancia unitaria", plata(m.ganancia_unitaria, por), mono],
        ["Ganancias este mes", plata(m.ganancia_mes), mono],
        ["Ganancias totales", plata(m.ganancia_total), mono],
        ["Proveedores", proveedores.length ? proveedores.join(", ") : "—", { ancho: true }],
      ]} />
    </section>
  );
}

/* El NETO de un movimiento, con signo: "+25", "-18". La entrada guarda la
   cantidad de antes y la de después (no un delta), así que se deriva acá; el
   signo sale del número, no del tipo — un ajuste puede ir para los dos lados. */
function netoDe(u) {
  const delta = Math.round(((u.cantidad_nueva || 0) - (u.cantidad_anterior || 0)) * 100) / 100;
  if (!delta) return "";
  return (delta > 0 ? "+" : "-") + fmt.cantidad(Math.abs(delta));
}

/* Cómo se ve cada entrada del historial. Un cambio de precio no mueve stock:
   en vez de "10 → 10 un." muestra el cambio de precio, y no tiene neto. */
function vistaEntrada(u, m, abrirOp) {
  const unidad = unidadDe(m);
  const restock = u.tipo === "restock", consumo = u.tipo === "consumo", precio = u.tipo === "precio";
  const neto = precio ? "" : netoDe(u);
  return {
    chip: ETIQUETA_TIPO[u.tipo] || u.tipo,
    variante: restock ? "restock" : consumo ? "consumo" : precio ? "precio" : undefined,
    neto: neto && `${neto} ${unidad}`,
    cambio: precio
      ? `${plata(u.valor_anterior)} → ${plata(u.valor_nuevo)}/${unidad}`
      : `${fmt.cantidad(u.cantidad_anterior)} → ${fmt.cantidad(u.cantidad_nueva)} ${unidad}`,
    fecha: u.fecha,
    descripcion: restock || consumo ? null : u.descripcion,
    datos: restock ? [
      ["Proveedor", u.proveedor],
      ["Costo total", u.costo_total != null ? fmt.pesos(u.costo_total) : null],
      ["Costo unitario", u.costo_unitario != null ? fmt.pesos(u.costo_unitario) : null],
    ] : consumo ? [
      ["OP", u.numero_op && <EnlaceOp numero={u.numero_op} onAbrir={() => abrirOp(u.numero_op)} />],
      ["Cliente", u.cliente],
    ] : [],
  };
}
