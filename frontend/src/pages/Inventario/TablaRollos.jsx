import { memo, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import SwitchIconos from "@/components/SwitchIconos/SwitchIconos";
import IconoNombre from "@/assets/svg/a-large-small.svg?react";
import IconoId from "@/assets/svg/arrow-down-0-1.svg?react";
import IconoRestante from "@/assets/svg/ruler-dimension-line.svg?react";
import IconoMostrar from "@/assets/svg/eye.svg?react";
import IconoNoPriorizar from "@/assets/svg/eye-dashed.svg?react";
import IconoOcultar from "@/assets/svg/eye-off.svg?react";
import CeldasPlata from "./Plata";
import * as fmt from "@/utils/formato";

/* La tabla de rollos de tela. Cada celda combina varios datos (un
   "principal" + detalle chico abajo), así entra en el ancho del módulo sin
   scroll horizontal. Un click en la fila abre el rollo (ver-rollo); el punto
   de color antes del textil es un atajo para activarlo/desactivarlo ahí
   mismo. El orden, el modo de los inactivos y la búsqueda son del cliente:
   la lista completa ya está acá. */

/* Cada orden con una sola dirección fija: Nombre A-Z, ID de menor a mayor y
   cantidad restante de menor a mayor — así los rollos más flacos quedan
   arriba, empujando a terminarlos primero (mismo criterio de negocio que
   consumir_para_op en core/repositorio_inventario.py). */
const ORDENES = [
  { valor: "nombre", Icono: IconoNombre, titulo: "Ordenar por nombre de textil (A-Z)" },
  { valor: "id", Icono: IconoId, titulo: "Ordenar por ID" },
  { valor: "metros_restantes", Icono: IconoRestante, titulo: "Ordenar por cantidad restante" },
];

/* Cuánto se esconden los inactivos — un solo botón que cicla los tres. */
const MODOS_INACTIVOS = [
  { valor: "mostrar", Icono: IconoMostrar, titulo: "Rollos inactivos: mostrar (mezclados con los activos)" },
  { valor: "no-priorizar", Icono: IconoNoPriorizar, titulo: "Rollos inactivos: no priorizar (siempre debajo de los activos)" },
  { valor: "ocultar", Icono: IconoOcultar, titulo: "Rollos inactivos: ocultar" },
];

const activo = (r) => (r.estado || "activo") === "activo";

function ordenar(lista, campo) {
  const valor = campo === "nombre" ? (r) => (r.nombre_textil || "").toLowerCase() : (r) => r[campo] ?? 0;
  return lista.slice().sort((a, b) => (valor(a) < valor(b) ? -1 : valor(a) > valor(b) ? 1 : 0));
}

/* "mostrar": mezclados. "no-priorizar": activos arriba y los inactivos
   abajo, cada grupo en el orden que ya traía (filter() no reordena).
   "ocultar": fuera. */
function aplicarModo(lista, modo) {
  if (modo === "ocultar") return lista.filter(activo);
  if (modo === "no-priorizar") return [...lista.filter(activo), ...lista.filter((r) => !activo(r))];
  return lista;
}

/* memo: no se vuelve a dibujar cuando cambia algo de la página que no le
   toca (p. ej. abrir un diálogo) — ver Inventario.jsx. */
export default memo(function TablaRollos({ rollos, buscarInicial = "", onAbrir, onCambiarEstado, botonNuevo, onNuevo }) {
  const [buscar, setBuscar] = useState(buscarInicial);
  // Una búsqueda que llega por la URL (el aviso de stock) pisa la escrita.
  useEffect(() => { if (buscarInicial) setBuscar(buscarInicial); }, [buscarInicial]);
  const [orden, setOrden] = useState("id");
  const [modo, setModo] = useState("mostrar");

  const filtro = buscar.trim().toLowerCase();
  const filas = aplicarModo(
    ordenar(filtro ? rollos.filter((r) => [r.id, r.nombre_textil].some((v) => String(v || "").toLowerCase().includes(filtro))) : rollos, orden),
    modo,
  );
  // El separador "Inactivos" va justo antes del primero, y solo si hay
  // algún activo arriba (si son todos de un tipo, no hay nada que separar).
  const primerInactivo = modo === "no-priorizar" ? filas.findIndex((r) => !activo(r)) : -1;

  return (
    <>
      <div className="barra-inventario">
        <input className="entrada" type="search" placeholder="Buscar por ID o textil…"
               value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        <SwitchIconos opciones={ORDENES} valor={orden} onCambiar={setOrden} etiqueta="Ordenar rollos por" />
        <ToggleInactivos modo={modo} onCambiar={setModo} />
        <button ref={botonNuevo} className="btn-nuevo" type="button" title="Nuevo rollo" onClick={onNuevo}>+</button>
      </div>
      <div className="tabla-caja">
        <table className="tabla tabla-rollos">
          <thead>
            <tr>
              <th>Rollo</th>
              <th>Origen</th>
              <th>Stock</th>
              <th className="num">Gastos</th>
              <th className="num">Valor</th>
              <th className="num">Ganancias</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((r, i) => [
              i === primerInactivo && i > 0 && (
                <tr key="separador" className="fila-separador-inactivos"><td colSpan={6}>Inactivos</td></tr>
              ),
              <FilaRollo key={r.id} r={r} onAbrir={() => onAbrir(r.id)} onCambiarEstado={() => onCambiarEstado(r.id, !activo(r))} />,
            ])}
          </tbody>
        </table>
        {!filas.length && <p className="estado-vacio">No hay rollos de tela guardados todavía.</p>}
      </div>
    </>
  );
});

function FilaRollo({ r, onAbrir, onCambiarEstado }) {
  const esActivo = activo(r);
  // El precio de compra se omite del todo si no se cargó, en vez de "· —".
  const origen = [r.fecha, r.precio_compra ? fmt.pesos(r.precio_compra) : null].filter(Boolean).join(" · ");
  const pct = r.metros_iniciales ? Math.round((r.metros_restantes / r.metros_iniciales) * 100) : 0;

  return (
    <tr tabIndex={0} onClick={onAbrir}
        onKeyDown={(e) => {
          // Solo la fila: el Enter del punto de estado no tiene que abrir además el rollo.
          if (e.target !== e.currentTarget || (e.key !== "Enter" && e.key !== " ")) return;
          e.preventDefault();
          onAbrir();
        }}>
      <td>
        <div className="celda-combo">
          <span className="celda-combo__principal">
            <button type="button" className={`estado-punto estado-punto--${esActivo ? "activo" : "inactivo"}`}
                    title={esActivo ? "Marcar como inactivo (no se selecciona para stock)" : "Reactivar"}
                    onClick={(e) => { e.stopPropagation(); onCambiarEstado(); }} />
            {r.nombre_textil || "—"}
          </span>
          <span className="celda-combo__detalle"><span className="celda-combo__id">#{r.id}</span> · {fmt.cantidad(r.ancho)} m</span>
        </div>
      </td>
      <td>
        <div className="celda-combo">
          <span className="celda-combo__principal">{r.proveedor || "—"}</span>
          <span className="celda-combo__detalle">{origen}</span>
        </div>
      </td>
      <td>
        <div className="stock">
          <span className="stock__texto">{fmt.cantidad(r.metros_restantes)} / {fmt.cantidad(r.metros_iniciales)} m</span>
          <span className="stock__barra"><i style={{ width: `${pct}%` }} /></span>
        </div>
      </td>
      <CeldasPlata obj={r} sufijo="/m" />
    </tr>
  );
}

/* Un solo botón-"ventana" que cicla los tres modos: con cada click el ícono
   actual se desliza hacia abajo y sale por el marco (que lo recorta) mientras
   el siguiente entra desde arriba — siempre en ese sentido, como un carrete.
   La sombra solo aparece mientras se mueve. */
function ToggleInactivos({ modo, onCambiar }) {
  const i = MODOS_INACTIVOS.findIndex((m) => m.valor === modo);
  const { Icono, titulo } = MODOS_INACTIVOS[i];
  const siguiente = MODOS_INACTIVOS[(i + 1) % MODOS_INACTIVOS.length].valor;
  const sombra = "drop-shadow(0 5px 4px rgba(22, 22, 26, .4))";
  const quieto = "drop-shadow(0 0 0 rgba(22, 22, 26, 0))";

  return (
    <button type="button" className="toggle-inactivos" title={titulo} onClick={() => onCambiar(siguiente)}>
      <AnimatePresence initial={false}>
        <motion.span key={modo} className="toggle-inactivos__icono"
                     initial={{ y: "-100%", filter: sombra }}
                     animate={{ y: 0, filter: quieto }}
                     exit={{ y: "100%", filter: sombra }}
                     transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}>
          <Icono aria-hidden="true" />
        </motion.span>
      </AnimatePresence>
    </button>
  );
}
