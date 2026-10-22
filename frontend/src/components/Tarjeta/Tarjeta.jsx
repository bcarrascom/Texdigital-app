import { useLocation, useNavigate } from "react-router";
import { rutas } from "@/router/rutas";
import * as fmt from "@/utils/formato";

/* Tarjetas de registro (.reg en base.css): el mazo del menú y, más
   adelante, los listados de cada módulo. Cada tipo sabe adónde lleva al
   hacer click; `style` deja pasar las variables del mazo (--i, --fila). */

/* `className` y el resto de las props (onDoubleClick, data-*...) pasan al botón. */
export default function Tarjeta({ num, sub, pie, progreso, incompleta, title, onClick, style, className = "", children, ...resto }) {
  return (
    <button type="button" className={`reg${incompleta ? " reg--incompleta" : ""}${className ? ` ${className}` : ""}`}
            title={title} onClick={onClick} style={style} {...resto}>
      <span className="reg__num">{num}</span>
      <span className="reg__sub">{sub}</span>
      {pie && <span className="reg__pie">{pie}</span>}
      {children}
      {/* La barra vive en el CANTO de la tarjeta: escondida detrás del
          módulo, esa línea de color es lo único que asoma (ver base.css). */}
      {progreso !== undefined && (
        <span className="reg__barra"><i style={{ width: `${progreso}%` }} /></span>
      )}
    </button>
  );
}

/* Navega a la ficha recordando desde qué página se la abrió (state.desde):
   así la ficha sabe, por ejemplo, si después de eliminar puede simplemente
   volver al listado o tiene que ir a buscarlo (ver VerCotizacion). */
function useAbrir() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  return (ruta) => navigate(ruta, { state: { desde: pathname } });
}

const porcentaje = (parte, total) => (total ? Math.round((parte / total) * 100) : 0);

export function TarjetaCotizacion({ c, style }) {
  const abrir = useAbrir();
  return <Tarjeta num={c.numero} sub={c.empresa || "—"} style={style}
                  onClick={() => abrir(rutas.verCotizacion(c.numero))} />;
}

/* Las incompletas no tienen número: muestran "3/7". */
export function TarjetaPendiente({ p, style }) {
  const abrir = useAbrir();
  return (
    <Tarjeta incompleta num={`${p.completos}/${p.total}`} sub={p.nombre_trabajo || "Sin nombre"}
             progreso={porcentaje(p.completos, p.total)} style={style}
             title={`Incompleta · ${p.completos} de ${p.total} productos · ${p.nombre_trabajo || ""}`}
             onClick={() => abrir(rutas.retomarPendiente(p.id))} />
  );
}

/* `conEntrega` solo en el listado del módulo: en el mazo del menú la tarjeta
   es de alto fijo y no hay lugar para la fecha y la cuenta regresiva. */
export function TarjetaOp({ o, style, conEntrega }) {
  const abrir = useAbrir();
  return (
    <Tarjeta num={o.numero} sub={o.empresa || "—"} style={style}
             pie={conEntrega ? o.fecha_entrega || "" : undefined}
             title={`OP ${o.numero} · ${o.empresa || ""} · entrega ${o.fecha_entrega || "—"}`}
             onClick={() => abrir(rutas.verOp(o.numero))}>
      {conEntrega && <span className="reg__entrega">{fmt.textoEntrega(o.fecha_entrega)}</span>}
    </Tarjeta>
  );
}

/* OP de Despachos/OPs/NoAsignadas: "asignados/total" con la misma barra que
   una cotización incompleta — la dirección es POR PRODUCTO (ver
   core/repositorio_despachos.py), así que se muestra cuánto falta. */
export function TarjetaDespacho({ d, style }) {
  const abrir = useAbrir();
  return (
    <Tarjeta incompleta num={`${d.asignados}/${d.total}`} sub={d.nombre || `OP ${d.numero}`}
             progreso={porcentaje(d.asignados, d.total)} style={style}
             title={`OP ${d.numero} · ${d.asignados} de ${d.total} productos con dirección · ${d.nombre || ""}`}
             onClick={() => abrir(rutas.asignarDespacho(d.numero))} />
  );
}

/* Acá la barra es "cuánta tela queda": metros_restantes sobre metros_iniciales. */
export function TarjetaRollo({ r, style }) {
  const abrir = useAbrir();
  return (
    <Tarjeta incompleta num={r.id} sub={r.nombre_textil || "Sin nombre"}
             progreso={porcentaje(r.metros_restantes, r.metros_iniciales)} style={style}
             title={`Rollo ${r.id} · ${r.nombre_textil || ""} · ${fmt.cantidad(r.metros_restantes)} de ${fmt.cantidad(r.metros_iniciales)} m`}
             onClick={() => abrir(rutas.verRollo(r.id))} />
  );
}
