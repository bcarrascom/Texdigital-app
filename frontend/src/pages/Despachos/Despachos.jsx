import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { api } from "@/services/api";
import { rutas } from "@/router/rutas";
import { useAvisos } from "@/context/AvisosContext";
import Dialogo from "@/components/Dialogo/Dialogo";
import Tarjeta, { TarjetaDespacho } from "@/components/Tarjeta/Tarjeta";
import { Accion, Acciones, RejillaTarjetas, SeccionModulo, escalon } from "@/components/CuerpoModulo/CuerpoModulo";
import { useCajaEnvio } from "./CajaEnvio";
import * as fmt from "@/utils/formato";
import "./Despachos.css";

/* Contenido del módulo Despachos (antes, su panel en menu.html): las OPs que
   llegaron sin dirección (cada producto puede ir a un lugar distinto) y las
   que ya tienen dirección en todos sus productos.

   Las asignadas NO navegan al click, a diferencia de cualquier otra tarjeta:
   SELECCIONAN (una sola; con Shift se suman) para actuar con los botones de
   su sección. Doble click abre el despacho (donde se generan las guías). */

const ANCHO_TARJETA = "calc(9.5rem * 1.33)";   // la comuna que rota en el pie no entra en el ancho de siempre
const ROTAR_CADA = 2600;
const ESTADOS = { pendiente: "Pendiente", parcial: "Parcial", despachado: "Despachado" };

export default function Despachos({ datos, recargar }) {
  const navigate = useNavigate();
  const aviso = useAvisos();
  const pendientes = datos?.despachos || [];
  const asignados = datos?.despachos_asignados || [];
  const [seleccion, setSeleccion] = useState(() => new Set());
  const [saliendo, setSaliendo] = useState(null);     // la que se está entregando
  const [confirmar, setConfirmar] = useState(false);
  const [caja, animarEnvio] = useCajaEnvio();
  const tick = useTick(asignados.some((o) => (o.ubicaciones || []).length > 1));

  // Al recargar, lo seleccionado que ya no está (entregado, eliminado) se suelta.
  useEffect(() => {
    setSeleccion((s) => new Set([...s].filter((n) => asignados.some((o) => o.numero === n))));
  }, [datos]);

  /* Sin Shift: selección única (tocar la única elegida la suelta). Con Shift:
     suma o saca esa sola. */
  function tocar(numero, conShift) {
    setSeleccion((s) => {
      if (conShift) {
        const n = new Set(s);
        n.has(numero) ? n.delete(numero) : n.add(numero);
        return n;
      }
      return s.size === 1 && s.has(numero) ? new Set() : new Set([numero]);
    });
  }

  const unica = seleccion.size === 1 ? [...seleccion][0] : null;
  const abrir = (numero) => navigate(rutas.verDespacho(numero), { state: { desde: rutas.despachos() } });

  async function entregar() {
    if (unica == null) return;
    setSaliendo(unica);
    const [, ok] = await Promise.all([animarEnvio(), api.marcar_despacho_entregado(unica)]);
    await recargar();
    setSaliendo(null);
    aviso(ok ? "Despacho marcado como entregado." : "No se pudo marcar como entregado.", ok ? "info" : "error");
  }

  async function eliminar() {
    setConfirmar(false);
    const numeros = [...seleccion];
    await api.eliminar_despachos(numeros);
    await recargar();
    aviso(numeros.length === 1 ? "Despacho eliminado." : `${numeros.length} despachos eliminados.`, "info");
  }

  return (
    <>
      <Acciones>
        <Accion titulo="Gestionar direcciones" desc="Las direcciones guardadas de cada cliente"
                onClick={() => navigate(rutas.gestionarDirecciones(), { state: { desde: rutas.despachos() } })} />
      </Acciones>

      <SeccionModulo titulo="Pendientes de asignar dirección">
        <RejillaTarjetas vacio="No hay despachos pendientes." anchoTarjeta={ANCHO_TARJETA}>
          {pendientes.map((d, i) => <TarjetaDespacho key={d.numero} d={d} style={escalon(i)} />)}
        </RejillaTarjetas>
      </SeccionModulo>

      <section className="modulo-seccion">
        <div className="despachos-cab">
          <h2 className="seccion-titulo">Con dirección asignada</h2>
          {seleccion.size > 1 && <span className="despachos-cab__cuenta">{seleccion.size} seleccionados</span>}
          <span className="cabecera__sep" />
          <button className="cab-btn" type="button" disabled={!seleccion.size || saliendo != null} onClick={() => setConfirmar(true)}>Eliminar</button>
          <button className="cab-btn" type="button" disabled={unica == null || saliendo != null} onClick={() => abrir(unica)}
                  title="Las guías se generan desde el despacho, eligiendo qué productos van">Generar guía</button>
          <button className="cab-btn" type="button" disabled={unica == null || saliendo != null} onClick={entregar}>Entregado</button>
        </div>
        <RejillaTarjetas vacio="No hay despachos con dirección asignada." anchoTarjeta={ANCHO_TARJETA}>
          {asignados.map((o, i) => (
            <TarjetaAsignada key={o.numero} o={o} tick={tick} style={escalon(i)}
                             seleccionada={seleccion.has(o.numero)} saliendo={saliendo === o.numero}
                             onClick={(e) => tocar(o.numero, e.shiftKey)} onDoubleClick={() => abrir(o.numero)} />
          ))}
        </RejillaTarjetas>
      </section>

      <Dialogo abierto={confirmar} onCerrar={() => setConfirmar(false)} onConfirmar={eliminar} className="dlg--desenfoque">
        <h2 className="dlg__titulo">{seleccion.size === 1 ? "¿Eliminar despacho?" : `¿Eliminar ${seleccion.size} despachos?`}</h2>
        <p className="dlg__texto">Esta acción no se puede deshacer.</p>
        <div className="dlg__acciones">
          <button className="btn btn--fantasma btn--chico" type="button" onClick={() => setConfirmar(false)}>Cancelar</button>
          <button className="btn btn--peligro btn--chico" type="button" onClick={eliminar}>Eliminar</button>
        </div>
      </Dialogo>
      {caja}
    </>
  );
}

/* Un contador que avanza cada ROTAR_CADA ms, el mismo para todas las
   tarjetas: así sus pies cambian a la vez. Solo corre si alguna tiene más de
   una ubicación que mostrar. */
function useTick(activo) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!activo) return;
    const t = setInterval(() => setTick((n) => n + 1), ROTAR_CADA);
    return () => clearInterval(t);
  }, [activo]);
  return tick;
}

/* El pie no muestra el estado ("Pendiente" en casi todas, no distingue una de
   otra): rota entre las comunas (o regiones, fuera de la Metropolitana) de
   sus productos — ver ui/api_menu.py::_ubicaciones. */
function TarjetaAsignada({ o, tick, seleccionada, saliendo, style, onClick, onDoubleClick }) {
  const estado = ESTADOS[o.estado_despacho] || o.estado_despacho || "";
  const ubicaciones = o.ubicaciones || [];
  return (
    <Tarjeta num={fmt.numero(o.numero)} sub={o.empresa || "—"} style={style}
             className={`reg--seleccionable${saliendo ? " reg--saliendo" : ""}`}
             data-seleccionado={seleccionada || undefined} aria-pressed={seleccionada}
             title={`OP ${o.numero} · ${o.empresa || ""} · ${estado}`}
             onClick={onClick} onDoubleClick={onDoubleClick}>
      <PieRotativo texto={ubicaciones.length ? ubicaciones[tick % ubicaciones.length] : estado} />
    </Tarjeta>
  );
}

/* Al cambiar el texto: se esfuma, cambia y vuelve a aparecer. */
function PieRotativo({ texto }) {
  const [mostrado, setMostrado] = useState(texto);
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    if (texto === mostrado) return;
    setVisible(false);
    const t = setTimeout(() => { setMostrado(texto); setVisible(true); }, 160);
    return () => clearTimeout(t);
  }, [texto]);
  return <span className="reg__pie" data-oculto={!visible || undefined}>{mostrado}</span>;
}
