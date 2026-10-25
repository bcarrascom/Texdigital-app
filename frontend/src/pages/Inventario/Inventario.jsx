import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router";
import { AnimatePresence, motion } from "motion/react";
import { api } from "@/services/api";
import { rutas } from "@/router/rutas";
import SwitchIconos from "@/components/SwitchIconos/SwitchIconos";
import IconoTextiles from "@/assets/svg/spiral.svg?react";
import IconoMateriales from "@/assets/svg/boxes.svg?react";
import TablaRollos from "./TablaRollos";
import TablaMateriales from "./TablaMateriales";
import { DialogoMaterial, DialogoRollo } from "./DialogosInventario";
import "./Inventario.css";

/* Contenido del módulo Inventario (antes, su panel en menu.html): dos tablas
   —rollos de tela y materiales no textiles— con un switch al lado del título
   para pasar de una a otra, y la lista de proveedores. Cada fila lleva a la
   pantalla de ese rollo/material, donde están sus ajustes; acá solo se da de
   alta (el "+" de cada tabla) y se activa/desactiva un rollo de un toque.
   "Proveedores" es un atajo a esa categoría de Configuración, donde vive la
   lista.

   La URL manda (para que "Volver" desde un rollo/material reaparezca en la
   misma tabla):
     ?vista=materiales      la tabla de materiales en vez de la de rollos
     ?buscar=<textil>       la búsqueda de rollos ya escrita (aviso de stock)
     ?nuevo_textil=<textil> abre "Rollo nuevo" con ese textil ya elegido (los
                            atajos "+ Nuevo rollo" de los avisos de materiales) */

const VISTAS = [
  { valor: "textiles", Icono: IconoTextiles, titulo: "Rollos de tela" },
  { valor: "materiales", Icono: IconoMateriales, titulo: "Materiales" },
];
const FUNDIDO = { duration: 0.18 };   // --m-rapida, como el resto de los repintados de contenido
// Sin datos todavía: listas vacías estables (un [] nuevo por render rompería el memo de las tablas).
const VACIO = { rollos: [], materiales: [], textiles: [], proveedores: [], nombres: [] };

/* Todo lo que necesitan las dos tablas y sus formularios, de una vez. */
export async function cargarInventario() {
  const [rollos, materiales, textiles, proveedores, nombres] = await Promise.all([
    api.listar_rollos(), api.listar_materiales(), api.cargar_textiles_inventario(),
    api.cargar_proveedores(), api.cargar_nombres_materiales(),
  ]);
  return { rollos: rollos || [], materiales: materiales || [], textiles: textiles || [],
           proveedores: proveedores || [], nombres: nombres || [] };
}

export default function Inventario({ datos, recargar }) {
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const [params, setParams] = useSearchParams();
  const vista = params.get("vista") === "materiales" ? "materiales" : "textiles";
  const d = datos || VACIO;

  const masRollo = useRef(null);
  const masMaterial = useRef(null);
  const [dialogo, setDialogo] = useState(null);   // "rollo" | "material" | null
  const [textilInicial, setTextilInicial] = useState("");

  /* Llegando con ?nuevo_textil: se abre "Rollo nuevo" con el textil elegido y
     el parámetro se saca (si no, volver a esta pantalla lo reabriría). */
  const nuevoTextil = params.get("nuevo_textil");
  useEffect(() => {
    if (!nuevoTextil) return;
    setTextilInicial(nuevoTextil);
    setParams((p) => { const n = new URLSearchParams(p); n.delete("nuevo_textil"); return n; }, { replace: true });
    // Después del primer cuadro: el botón "+" de donde nace el diálogo tiene que estar en su lugar.
    requestAnimationFrame(() => setDialogo("rollo"));
  }, [nuevoTextil]);

  const cambiarVista = (v) => setParams((p) => {
    const n = new URLSearchParams(p);
    if (v === "materiales") n.set("vista", v); else n.delete("vista");
    return n;
  }, { replace: true });

  const desde = pathname + search;
  const cerrar = () => setDialogo(null);
  const alGuardar = async () => { cerrar(); await recargar(); };

  /* Las tablas están memorizadas (memo): abrir o cerrar un diálogo cambia el
     estado de esta página, y sin esto se volvía a dibujar cada fila — con
     cientos de rollos, la animación del diálogo se congelaba. Por eso todo lo
     que se les pasa tiene que ser estable entre renders: `recargar` cambia
     en cada render del módulo, así que se lee desde un ref. */
  const recargarRef = useRef(recargar);
  useEffect(() => { recargarRef.current = recargar; });
  const abrirRollo = useCallback((id) => navigate(rutas.verRollo(id), { state: { desde } }), [navigate, desde]);
  const abrirMaterial = useCallback((id) => navigate(rutas.verMaterial(id), { state: { desde } }), [navigate, desde]);
  const nuevoRollo = useCallback(() => { setTextilInicial(""); setDialogo("rollo"); }, []);
  const nuevoMaterial = useCallback(() => setDialogo("material"), []);
  const cambiarEstado = useCallback(async (id, activo) => {
    await api.cambiar_estado_rollo(id, activo);
    await recargarRef.current();
  }, []);

  return (
    <>
      <div>
        <div className="modulo-cuerpo__titulo-fila">
          <h1 className="modulo-cuerpo__titulo">Inventario</h1>
          <SwitchIconos opciones={VISTAS} valor={vista} onCambiar={cambiarVista} etiqueta="Vista de inventario" />
          <span className="cabecera__sep" />
          <button className="cab-btn" type="button" title="Cuánto se usó y cuánto queda, mes a mes"
                  onClick={() => navigate(rutas.reportesInventario(), { state: { desde } })}>Reportes</button>
          <button className="cab-btn" type="button" title="Abrir la lista de proveedores, en Configuración"
                  onClick={() => navigate(rutas.configuracion("proveedores"), { state: { desde } })}>Proveedores</button>
        </div>
        <p className="modulo-cuerpo__bajada">
          {vista === "materiales" ? "Materiales — stock disponible." : "Rollos de tela — stock disponible."}
        </p>
      </div>

      <section className="modulo-seccion">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={vista} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={FUNDIDO}>
            {vista === "textiles" ? (
              <TablaRollos
                rollos={d.rollos} buscarInicial={params.get("buscar") || ""}
                botonNuevo={masRollo} onNuevo={nuevoRollo} onAbrir={abrirRollo} onCambiarEstado={cambiarEstado}
              />
            ) : (
              <TablaMateriales
                materiales={d.materiales} botonNuevo={masMaterial} onNuevo={nuevoMaterial} onAbrir={abrirMaterial}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </section>

      <datalist id="lista-proveedores">
        {d.proveedores.map((p) => <option key={p} value={p} />)}
      </datalist>
      <DialogoRollo abierto={dialogo === "rollo"} origen={masRollo} textiles={d.textiles} textilInicial={textilInicial}
                    onCerrar={cerrar} onGuardado={alGuardar} />
      <DialogoMaterial abierto={dialogo === "material"} origen={masMaterial} materiales={d.materiales} nombres={d.nombres}
                       onCerrar={cerrar} onGuardado={alGuardar} />
    </>
  );
}
