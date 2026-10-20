import { useNavigate } from "react-router";
import { api } from "@/services/api";
import { useAtajo } from "@/hooks/useAtajo";
import { useDatos } from "@/hooks/useDatos";
import { rutas } from "@/router/rutas";
import PaginaModulo, { Accion, Acciones, SeccionModulo } from "@/components/PaginaModulo/PaginaModulo";
import Cargando from "@/components/Cargando/Cargando";
import { TarjetaCotizacion, TarjetaPendiente } from "@/components/Tarjeta/Tarjeta";
import "./Cotizaciones.css";

/* Módulo Cotizaciones (antes, su panel en menu.html): "Nueva cotización",
   las incompletas sueltas al lado, y abajo todas las cotizaciones guardadas.
   Los datos son los mismos del menú (ApiMenu.obtener_resumen). */

/* El escalón de aparición se corta acá: con muchas cotizaciones, la última
   no puede tardar segundos en aparecer. */
const MAX_ESCALON = 12;
const escalon = (i) => ({ "--i": Math.min(i, MAX_ESCALON) });

export default function Cotizaciones() {
  const navigate = useNavigate();
  const { datos, cargando, recargar } = useDatos(() => api.obtener_resumen(), []);
  useAtajo("f5", recargar);

  const pendientes = datos?.pendientes || [];
  const cotizaciones = datos?.cotizaciones || [];

  return (
    <PaginaModulo tema="cotizaciones" titulo="Cotizaciones">
      <Acciones>
        <Accion titulo="Nueva cotización" desc="Empezar un trabajo nuevo, de cualquier tipo de producto."
                onClick={() => navigate(rutas.nuevaCotizacion())} />
        {/* Las incompletas, sueltas junto a "Nueva cotización": acá no son
            un listado, son el aviso de "esto quedó a medio hacer". Sin
            ninguna, no dejan rastro. */}
        {pendientes.length > 0 && (
          <div className="incompletas-sueltas" style={{ "--i": 1 }}>
            {pendientes.map((p) => <TarjetaPendiente key={p.id} p={p} />)}
          </div>
        )}
      </Acciones>

      <SeccionModulo titulo="cotizaciones">
        {cargando ? <Cargando /> : cotizaciones.length ? (
          <div className="rejilla-tarjetas aparecer">
            {cotizaciones.map((c, i) => <TarjetaCotizacion key={c.numero} c={c} style={escalon(i)} />)}
          </div>
        ) : (
          <p className="rejilla-tarjetas__vacio">Todavía no hay cotizaciones.</p>
        )}
      </SeccionModulo>
    </PaginaModulo>
  );
}
