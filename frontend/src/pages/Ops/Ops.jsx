import { useNavigate } from "react-router";
import { api } from "@/services/api";
import { rutas } from "@/router/rutas";
import { Accion, Acciones, RejillaTarjetas, SeccionModulo, escalon } from "@/components/CuerpoModulo/CuerpoModulo";
import { TarjetaOp } from "@/components/Tarjeta/Tarjeta";
import "./Ops.css";

/* Contenido del módulo Órdenes de Producción (antes, su panel en menu.html):
   el panel de producción (su propia ventana, ver ui/panel_produccion.py), el
   historial y las OPs activas con su cuenta regresiva de entrega. La página
   y el paso entre módulos los pone pages/Modulos. */
export default function Ops({ datos }) {
  const navigate = useNavigate();
  const ops = datos?.ops || [];

  return (
    <>
      <Acciones>
        <Accion className="accion--panel-produccion" titulo="Panel de producción"
                desc="Listado y calendario de las OPs activas" onClick={() => api.ir("panel_produccion")} />
        <Accion titulo="Historial de OPs" desc="Todas las OPs" indice={1}
                onClick={() => navigate(rutas.historialOps(), { state: { desde: rutas.ops() } })} />
      </Acciones>

      <SeccionModulo titulo="OPs activas">
        {/* Un 33 % más anchas que las demás tarjetas: el espacio de más es
            para la cuenta regresiva de entrega. */}
        <RejillaTarjetas vacio="No hay OPs activas." anchoTarjeta="calc(9.5rem * 1.33)">
          {ops.map((o, i) => <TarjetaOp key={o.numero} o={o} conEntrega style={escalon(i)} />)}
        </RejillaTarjetas>
      </SeccionModulo>
    </>
  );
}
