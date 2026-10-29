import { useNavigate } from "react-router";
import { rutas } from "@/router/rutas";
import { Accion, Acciones, Buscador, RejillaTarjetas, SeccionModulo, coincide, escalon, useBusqueda } from "@/components/CuerpoModulo/CuerpoModulo";
import { TarjetaCotizacion, TarjetaPendiente } from "@/components/Tarjeta/Tarjeta";
import "./Cotizaciones.css";

/* Contenido del módulo Cotizaciones (antes, su panel en menu.html):
   "Nueva cotización", las incompletas sueltas al lado, y abajo todas las
   cotizaciones guardadas, con un buscador por número, cliente o nombre del
   trabajo. La página y el paso entre módulos los pone pages/Modulos; los
   datos son los del menú (ApiMenu.obtener_resumen). */
export default function Cotizaciones({ datos }) {
  const navigate = useNavigate();
  const [busqueda, setBusqueda] = useBusqueda();
  const pendientes = datos?.pendientes || [];
  const cotizaciones = datos?.cotizaciones || [];
  const texto = busqueda.trim();
  const visibles = cotizaciones.filter((c) => coincide(texto, [c.numero, c.empresa, c.nombre]));

  return (
    <>
      <Acciones>
        <Accion titulo="Nueva cotización" desc="Empezar un trabajo nuevo, de cualquier tipo de producto."
                onClick={() => navigate(rutas.nuevaCotizacion(), { state: { desde: rutas.cotizaciones() } })} />
        {/* Las incompletas, sueltas junto a "Nueva cotización": acá no son
            un listado, son el aviso de "esto quedó a medio hacer". Sin
            ninguna, no dejan rastro. */}
        {pendientes.length > 0 && (
          <div className="incompletas-sueltas" style={{ "--i": 1 }}>
            {pendientes.map((p) => <TarjetaPendiente key={p.id} p={p} />)}
          </div>
        )}
      </Acciones>

      <SeccionModulo titulo={texto ? `cotizaciones · ${visibles.length} de ${cotizaciones.length}` : "cotizaciones"}
                     accesorio={cotizaciones.length > 0 && (
                       <Buscador valor={busqueda} onCambiar={setBusqueda} placeholder="Buscar por número, cliente o trabajo" />
                     )}>
        <RejillaTarjetas vacio={texto ? `Ninguna cotización calza con “${texto}”.` : "Todavía no hay cotizaciones."}>
          {visibles.map((c, i) => <TarjetaCotizacion key={c.numero} c={c} conNombre style={escalon(i)} />)}
        </RejillaTarjetas>
      </SeccionModulo>
    </>
  );
}
