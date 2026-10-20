import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { useExpansion } from "@/context/ExpansionContext";
import { useAtajo } from "@/hooks/useAtajo";
import { useDatos } from "@/hooks/useDatos";
import { MODULOS, rutas } from "@/router/rutas";
import Pagina from "@/components/Pagina/Pagina";
import { ControlTexto } from "@/components/Cabecera/Cabecera";
import { TarjetaCotizacion, TarjetaDespacho, TarjetaOp, TarjetaPendiente, TarjetaRollo } from "@/components/Tarjeta/Tarjeta";
import Modulo, { varsMazo } from "./Modulo";
import AvisoMenu from "./AvisoMenu";
import { fechaDMAaTime, plural } from "@/utils/formato";
import "./Menu.css";

/* Menú principal: logo, los módulos (con su mazo de tarjetas) y los avisos
   de stock/producción. Entrar a un módulo es navegar a OTRA página
   (/inventario, /cotizaciones, ...) con la expansión de color de
   context/ExpansionContext; volver de ahí contrae el color de vuelta a la
   caja del módulo. Los módulos apagados en core/config.py::
   MODULOS_HABILITADOS se ven grises ("Próximamente") y no se pueden abrir. */

/* Cuántas tarjetas asoman por detrás de cada módulo: con 2 por fila, 3 filas. */
const MAX_TARJETAS = 6;

/* Esta pantalla puede quedar abierta un buen rato sin que nadie la toque, y
   mientras tanto el panel de producción (otra ventana) puede completar OPs
   sin avisarle: se refresca sola si la ventana tiene foco. */
const REFRESCO_MS = 60000;

const SEVERIDAD_ORDEN = { roja: 3, naranja: 2, amarilla: 1 };
// Amarilla usa un amarillo propio, no --c-aviso: esa variable es compartida
// con las etiquetas y avisos flotantes de otras pantallas.
const SEVERIDAD_COLOR = { amarilla: "#FFCE1B", naranja: "var(--c-alerta)", roja: "var(--c-error)" };
const SEVERIDAD_MENSAJE = {
  amarilla: (x) => `No se encuentra un rollo activo con al menos ${x} metros restantes.`,
  naranja:  (x) => `No se encuentra un rollo con al menos ${x} metros restantes.`,
  roja:     (x) => `No quedan al menos ${x} metros restantes de este textil.`,
};

const mazo = (items, Componente, prop) =>
  items.slice(0, MAX_TARJETAS).map((x, i) => (
    <Componente key={`${prop}-${x.id ?? x.numero}`} {...{ [prop]: x }} style={varsMazo(i)} />
  ));

export default function Menu() {
  const { contexto } = useApp();
  const habilitado = (clave) => contexto.modulos_habilitados?.[clave] !== false;
  const navigate = useNavigate();
  const { abrir, contraer, expandiendo, moduloAbierto } = useExpansion();
  const { datos, recargar } = useDatos(() => api.obtener_resumen(), []);

  const cajas = useRef({});          // clave de módulo → <button> de su caja
  const botonesAviso = useRef({});   // clave de módulo → <button> de su aviso (si se ve)
  const [avisoAbierto, setAvisoAbierto] = useState(null);
  const cerrarAviso = useCallback(() => setAvisoAbierto(null), []);

  // Volviendo de un módulo: el color se contrae hasta su caja. Se captura
  // al montar, antes de que contraer() lo limpie.
  const volviendoDe = useRef(moduloAbierto());
  useLayoutEffect(() => {
    const caja = cajas.current[volviendoDe.current];
    if (!caja) return;
    // Al terminar, el foco queda en la caja del módulo del que se volvió:
    // así se puede seguir con las flechas sin tener que volver a elegirlo.
    contraer(caja, () => caja.focus({ preventScroll: true }));
  }, [contraer]);

  const entrarA = (clave, ruta) => {
    const caja = cajas.current[clave];
    if (caja && habilitado(clave)) abrir(caja, clave, ruta);
  };

  useAtajo("f5", recargar);
  useEffect(() => {
    const t = setInterval(() => {
      if (!document.hidden && document.hasFocus()) recargar();
    }, REFRESCO_MS);
    return () => clearInterval(t);
  }, [recargar]);

  /* ←/→ SELECCIONAN (foco, no click) un módulo; el foco ya despliega su mazo
     por :focus-within y Enter lo abre (es un <button>). Sin nada
     seleccionado, ← va al primero y → al último; desde una punta dan la
     vuelta. ↑ sobre un módulo con aviso sube al ícono del aviso. Con un
     aviso abierto, las flechas son suyas (rotan los ítems). */
  useEffect(() => {
    const tecla = (e) => {
      if (avisoAbierto || document.querySelector("dialog[open]")) return;
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        const lista = MODULOS.filter((m) => habilitado(m.clave)).map((m) => cajas.current[m.clave]).filter(Boolean);
        if (!lista.length) return;
        e.preventDefault();
        const i = lista.indexOf(document.activeElement);
        const delta = e.key === "ArrowLeft" ? -1 : 1;
        const destino = i === -1
          ? (delta < 0 ? lista[0] : lista[lista.length - 1])
          : lista[(i + delta + lista.length) % lista.length];
        destino.focus({ preventScroll: true });
      } else if (e.key === "ArrowUp") {
        const clave = Object.keys(cajas.current).find((k) => cajas.current[k] === document.activeElement);
        const boton = clave && botonesAviso.current[clave];
        if (!boton) return;
        e.preventDefault();
        boton.focus({ preventScroll: true });
      }
    };
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  });

  const r = datos || {};
  const cargado = !!datos;
  const pendientes = r.pendientes || [];
  const cotizaciones = r.cotizaciones || [];
  const ops = r.ops || [];
  const despachos = r.despachos || [];
  const rollos = r.rollos || [];

  /* Si no hay nada que contar, el texto no aparece — nunca "0 incompletas":
     un cero no es información, es ruido. */
  const metaCotizaciones = [
    cotizaciones.length && plural(cotizaciones.length, "guardada", "guardadas"),
    pendientes.length && plural(pendientes.length, "incompleta", "incompletas"),
  ].filter(Boolean).join(" · ");

  const contenido = {
    inventario: {
      meta: rollos.length ? plural(rollos.length, "rollo", "rollos") : "",
      tarjetas: mazo(rollos, TarjetaRollo, "r"),
      vacio: "Todavía no hay rollos de tela.",
    },
    cotizaciones: {
      meta: metaCotizaciones,
      // Las incompletas primero: son las que hay que terminar, y así su canto
      // de color queda en la fila que más asoma.
      tarjetas: [
        ...pendientes.map((p) => ({ tipo: "p", x: p })),
        ...cotizaciones.map((c) => ({ tipo: "c", x: c })),
      ].slice(0, MAX_TARJETAS).map(({ tipo, x }, i) => tipo === "p"
        ? <TarjetaPendiente key={`p-${x.id}`} p={x} style={varsMazo(i)} />
        : <TarjetaCotizacion key={`c-${x.numero}`} c={x} style={varsMazo(i)} />),
      vacio: "Todavía no hay cotizaciones.",
    },
    ops: {
      meta: ops.length ? plural(ops.length, "activa", "activas") : "",
      tarjetas: mazo(ops, TarjetaOp, "o"),
      vacio: "No hay OPs activas.",
    },
    despachos: {
      meta: despachos.length ? plural(despachos.length, "pendiente", "pendientes") : "",
      tarjetas: mazo(despachos, TarjetaDespacho, "d"),
      vacio: "No hay despachos pendientes.",
    },
  };

  const avisos = {
    inventario: habilitado("inventario") && avisoStock(r.avisos_inventario || [], contexto.stock_minimo_ml ?? 25,
      (textil, severidad) => entrarA("inventario", severidad === "amarilla"
        ? rutas.inventario({ buscar: textil })
        : rutas.inventario({ nuevo_textil: textil }))),
    ops: habilitado("ops") && avisoProduccion(r.avisos_produccion || [], (numero) => navigate(rutas.verOp(numero))),
  };

  return (
    <Pagina titulo="TexDigital" className="pag-menu" animarEntrada={!volviendoDe.current}>
      <div className="menu" data-saliendo={expandiendo || undefined} data-regreso={volviendoDe.current ? "" : undefined}>
        <div className="menu__marca">
          <img className="menu__logo" src="./img/logo_texdigital.png" alt="TexDigital" />
          <p className="menu__sub">Sistema de Gestión</p>
        </div>

        <div className="menu__modulos">
          {MODULOS.map((m, i) => {
            const aviso = avisos[m.clave];
            return (
              <div className="menu__columna" key={m.clave}>
                {aviso && (
                  <AvisoMenu
                    {...aviso}
                    tema={m.clave}
                    abierto={avisoAbierto === m.clave}
                    onAbrir={() => setAvisoAbierto(m.clave)}
                    onCerrar={cerrarAviso}
                    onBajar={() => cajas.current[m.clave]?.focus({ preventScroll: true })}
                    botonRef={(el) => { botonesAviso.current[m.clave] = el; }}
                  />
                )}
                <Modulo
                  clave={m.clave}
                  titulo={m.titulo}
                  indice={i}
                  deshabilitado={!habilitado(m.clave)}
                  meta={cargado ? contenido[m.clave].meta : null}
                  tarjetas={cargado ? contenido[m.clave].tarjetas : null}
                  vacio={contenido[m.clave].vacio}
                  registrarCaja={(el) => { cajas.current[m.clave] = el; }}
                  onAbrir={() => entrarA(m.clave, m.ruta())}
                />
              </div>
            );
          })}
        </div>

        <footer className="menu__pie">
          <span>{contexto.fecha}</span>
          {contexto.version && <span>v{contexto.version}</span>}
          <ControlTexto />
          <button className="cab-btn cab-btn--icono" title="Manual de uso" onClick={() => api.abrir_manual()}>?</button>
          <button className="cab-btn cab-btn--icono" title="Buscar actualizaciones"
                  onClick={() => api.buscar_actualizacion()}>⟳</button>
          {import.meta.env.DEV && (
            <Link className="cab-btn" to={rutas.desarrollo()} title="Pantallas migradas (solo en desarrollo)">dev</Link>
          )}
        </footer>
      </div>
    </Pagina>
  );
}

/* ── Avisos ───────────────────────────────────────────────────────────── */

/* Se muestra la peor gravedad; empatados, el textil con menos tela primero. */
function avisoStock(avisos, minimo, irA) {
  if (!avisos.length) return null;
  const severidad = avisos.reduce(
    (peor, a) => (SEVERIDAD_ORDEN[a.severidad] > SEVERIDAD_ORDEN[peor] ? a.severidad : peor),
    avisos[0].severidad,
  );
  return {
    titulo: "Aviso de stock",
    color: SEVERIDAD_COLOR[severidad],
    items: avisos.filter((a) => a.severidad === severidad).sort((a, b) => a.metros - b.metros),
    texto: SEVERIDAD_MENSAJE[severidad](minimo),
    render: (a) => <p className="aviso-menu__textil">{a.textil}</p>,
    etiquetaAccion: severidad === "amarilla" ? "Ver en Inventario →" : "Cargar rollo nuevo →",
    onAccion: (a) => irA(a.textil, severidad),
  };
}

/* Una sola gravedad (una OP atrasada siempre es igual de urgente): siempre
   roja, la más atrasada primero. */
function avisoProduccion(avisos, abrirOp) {
  if (!avisos.length) return null;
  return {
    titulo: "Aviso de producción",
    color: "var(--c-error)",
    items: avisos.slice().sort((a, b) => fechaDMAaTime(a.fecha_entrega) - fechaDMAaTime(b.fecha_entrega)),
    texto: avisos.length === 1 ? "Hay una OP atrasada." : `Hay ${avisos.length} OPs atrasadas.`,
    render: (o) => (
      <>
        <p className="aviso-menu__op">OP {o.numero}</p>
        <dl className="aviso-menu__datos">
          <dt>Cliente</dt><dd>{o.empresa || "—"}</dd>
          <dt>Entrega</dt><dd>{o.fecha_entrega || "—"}</dd>
        </dl>
      </>
    ),
    etiquetaAccion: "Abrir OP →",
    onAccion: (o) => abrirOp(Number(o.numero)),
  };
}
