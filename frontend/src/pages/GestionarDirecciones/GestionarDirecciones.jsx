import { useState } from "react";
import { api } from "@/services/api";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import Dialogo from "@/components/Dialogo/Dialogo";
import FormularioDireccion from "@/pages/Despachos/FormularioDireccion";
import { REGION_DEFECTO } from "@/pages/Despachos/direcciones";
import IconoEditar from "@/assets/svg/pencil.svg?react";
import IconoEliminar from "@/assets/svg/trash-2.svg?react";
import "./GestionarDirecciones.css";

/* Gestionar direcciones, submódulo de Despachos (antes recursos/pantallas/
   gestionar-direcciones.html): agregar, editar y eliminar las direcciones
   guardadas (direcciones.json) y ver de qué cliente es cada una. A la
   derecha, el mapa de la dirección elegida, que acompaña el scroll.

   Editar o eliminar acá NO afecta a las OPs que ya tengan alguna puesta: esa
   asignación es una copia hecha en el momento, no una referencia viva. */

async function cargar() {
  const [direcciones, clientes, regiones] = await Promise.all([
    api.listar_direcciones_gestion(), api.cargar_clientes_gestion(), api.cargar_regiones(),
  ]);
  return { direcciones: direcciones || [], clientes: clientes || [], regiones: regiones || [] };
}

/* Con alias, el alias manda: "Bodega · Av. Matta 500". */
function lineaDireccion(d) {
  const linea1 = [d.calle, d.numero].filter(Boolean).join(" ");
  return d.alias ? `${d.alias} · ${linea1}` : (linea1 || "—");
}
const paraMapa = (d) => [[d.calle, d.numero].filter(Boolean).join(" "), d.comuna, d.region].filter(Boolean).join(", ");

export default function GestionarDirecciones() {
  const aviso = useAvisos();
  const { datos, cargando, recargar } = useDatos(cargar, []);
  const [buscar, setBuscar] = useState("");
  const [idElegida, setIdElegida] = useState(null);
  const [editando, setEditando] = useState(undefined);    // undefined = cerrado · null = nueva · dirección = editar
  const [aEliminar, setAEliminar] = useState(null);

  const direcciones = datos?.direcciones || [];
  const filtro = buscar.trim().toLowerCase();
  const filas = (filtro ? direcciones.filter((d) => [d.empresa, d.rut, d.alias, d.calle, d.numero, d.comuna, d.region, d.referencia]
    .some((v) => String(v || "").toLowerCase().includes(filtro))) : direcciones.slice())
    .sort((a, b) => (a.empresa || "").localeCompare(b.empresa || "", "es"));
  // Si la elegida quedó fuera del filtro (o se eliminó), el mapa pasa a la primera visible.
  const elegida = filas.find((d) => d.id === idElegida) || filas[0] || null;

  async function guardar(direccion) {
    const eraEdicion = !!editando;
    await api.guardar_direccion_gestion(direccion);
    setEditando(undefined);
    await recargar();
    aviso(eraEdicion ? "Dirección actualizada." : "Dirección guardada.", "info");
  }

  async function eliminar() {
    const d = aEliminar;
    setAEliminar(null);
    await api.eliminar_direccion_gestion(d.id);
    await recargar();
    aviso("Dirección eliminada.", "info");
  }

  return (
    <Pagina tema="despachos" titulo="Gestionar direcciones" className="pag-direcciones">
      <Cabecera titulo="Gestionar direcciones" />
      <main className="contenido">
        {cargando ? <Cargando /> : (
          <div className="vista-direcciones">
            <section className="hoja">
              <div className="barra-direcciones">
                <h1 className="seccion-titulo">Direcciones guardadas</h1>
                <input className="entrada" type="search" placeholder="Buscar por cliente, calle o comuna…"
                       value={buscar} onChange={(e) => setBuscar(e.target.value)} />
                <button className="btn btn--secundario btn--chico" type="button" disabled={!elegida} onClick={() => setEditando(elegida)}>
                  <IconoEditar aria-hidden="true" /> Editar
                </button>
                <button className="btn btn--primario btn--chico" type="button" onClick={() => setEditando(null)}>+ Nueva dirección</button>
              </div>
              <div className="tabla-caja">
                <table className="tabla">
                  <thead><tr><th>Cliente</th><th>Dirección</th><th>Depto / Edificio / Otro</th><th /></tr></thead>
                  <tbody>
                    {filas.map((d) => (
                      <tr key={d.id} data-seleccionada={d.id === elegida?.id || undefined}
                          onClick={() => setIdElegida(d.id)} onDoubleClick={() => setEditando(d)}>
                        <td>{d.empresa ? (
                          <div className="celda-lineas">
                            <span>{d.empresa}</span>
                            {d.rut && <span className="celda-lineas__sub">{d.rut}</span>}
                          </div>
                        ) : <span className="celda-vacia">—</span>}</td>
                        <td>
                          <div className="celda-lineas">
                            <span>{lineaDireccion(d)}</span>
                            <span className="celda-lineas__sub">{d.comuna || "—"}</span>
                            {d.region && d.region !== REGION_DEFECTO && <span className="celda-lineas__sub">{d.region}</span>}
                          </div>
                        </td>
                        <td>{d.referencia || <span className="celda-vacia">—</span>}</td>
                        <td className="acciones">
                          <button className="btn-fila-icono btn-fila-icono--peligro" type="button" title="Eliminar"
                                  onClick={(e) => { e.stopPropagation(); setAEliminar(d); }}>
                            <IconoEliminar aria-hidden="true" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!filas.length && (
                  <p className="estado-vacio">{direcciones.length ? "Ninguna dirección coincide con la búsqueda." : "No hay direcciones guardadas todavía."}</p>
                )}
              </div>
            </section>

            <aside className="lateral-mapa">
              <div className="lateral">
                <div className="mapa-cab">
                  <span className="mapa-cab__titulo">{elegida ? lineaDireccion(elegida) : "Sin direcciones guardadas"}</span>
                  {elegida && <span className="mapa-cab__sub">{[elegida.comuna, elegida.region].filter(Boolean).join(" · ")}</span>}
                </div>
                <div className="mapa-marco">
                  {elegida && (
                    <iframe title="Ubicación en el mapa" loading="lazy" referrerPolicy="no-referrer-when-downgrade"
                            src={`https://www.google.com/maps?q=${encodeURIComponent(paraMapa(elegida))}&output=embed`} />
                  )}
                </div>
              </div>
            </aside>
          </div>
        )}
      </main>

      {datos && (
        <Dialogo abierto={editando !== undefined} onCerrar={() => setEditando(undefined)} className="dlg-direccion">
          <FormularioDireccion titulo={editando ? "Editar dirección" : "Dirección nueva"} inicial={editando || null} conAlias
                               clientes={datos.clientes} regiones={datos.regiones}
                               onCancelar={() => setEditando(undefined)} onGuardar={guardar} />
        </Dialogo>
      )}

      <Dialogo abierto={!!aEliminar} onCerrar={() => setAEliminar(null)} onConfirmar={eliminar} className="dlg--desenfoque">
        <h2 className="dlg__titulo">¿Eliminar esta dirección?</h2>
        {aEliminar && (
          <p className="dlg__texto">
            {lineaDireccion(aEliminar)}{aEliminar.comuna ? `, ${aEliminar.comuna}` : ""} — {aEliminar.empresa || "sin cliente"}.
          </p>
        )}
        <div className="dlg__acciones">
          <button className="btn btn--fantasma btn--chico" type="button" onClick={() => setAEliminar(null)}>Cancelar</button>
          <button className="btn btn--peligro btn--chico" type="button" onClick={eliminar}>Eliminar</button>
        </div>
      </Dialogo>
    </Pagina>
  );
}
