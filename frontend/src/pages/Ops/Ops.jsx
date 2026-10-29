import { useNavigate } from "react-router";
import { api } from "@/services/api";
import { rutas } from "@/router/rutas";
import { Accion, Acciones, Buscador, RejillaTarjetas, SeccionModulo, coincide, escalon, useBusqueda } from "@/components/CuerpoModulo/CuerpoModulo";
import { TarjetaOp } from "@/components/Tarjeta/Tarjeta";
import "./Ops.css";

/* Contenido del módulo Órdenes de Producción (antes, su panel en menu.html):
   el panel de producción (su propia ventana, ver ui/panel_produccion.py), el
   historial y las OPs activas con su cuenta regresiva de entrega. El
   buscador (número, cliente o nombre del trabajo) filtra las activas y deja
   seguir la búsqueda en el historial, que cruza todas. La página y el paso
   entre módulos los pone pages/Modulos. */
export default function Ops({ datos }) {
  const navigate = useNavigate();
  const [busqueda, setBusqueda] = useBusqueda();
  const ops = datos?.ops || [];
  const texto = busqueda.trim();
  const visibles = ops.filter((o) => coincide(texto, [o.numero, o.empresa, o.nombre]));

  return (
    <>
      <Acciones>
        <Accion className="accion--panel-produccion" titulo="Panel de producción"
                desc="Listado y calendario de las OPs activas" onClick={() => api.ir("panel_produccion")} />
        <Accion titulo="Historial de OPs" desc="Todas las OPs" indice={1}
                onClick={() => navigate(rutas.historialOps(), { state: { desde: rutas.ops() } })} />
      </Acciones>

      <SeccionModulo titulo={texto ? `OPs activas · ${visibles.length} de ${ops.length}` : "OPs activas"}
                     accesorio={<Buscador valor={busqueda} onCambiar={setBusqueda} placeholder="Buscar por número, cliente o trabajo" />}>
        {/* Un 33 % más anchas que las demás tarjetas: el espacio de más es
            para la cuenta regresiva de entrega. */}
        <RejillaTarjetas vacio={texto ? `Ninguna OP activa calza con “${texto}”.` : "No hay OPs activas."}
                         anchoTarjeta="calc(9.5rem * 1.33)">
          {visibles.map((o, i) => <TarjetaOp key={o.numero} o={o} conEntrega style={escalon(i)} />)}
        </RejillaTarjetas>
        {/* Las entregadas y canceladas no están acá: la misma búsqueda,
            sobre todas las OPs. */}
        {texto && (
          <button type="button" className="modulo-buscar-mas"
                  onClick={() => navigate(`${rutas.historialOps()}?q=${encodeURIComponent(texto)}`, { state: { desde: rutas.ops() } })}>
            Buscar “{texto}” en todas las OPs (historial) →
          </button>
        )}
      </SeccionModulo>
    </>
  );
}
