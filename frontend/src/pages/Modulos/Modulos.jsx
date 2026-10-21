import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { api } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { useExpansion } from "@/context/ExpansionContext";
import { useAtajo } from "@/hooks/useAtajo";
import { useVolver } from "@/hooks/useVolver";
import { MODULOS } from "@/router/rutas";
import Pagina from "@/components/Pagina/Pagina";
import Cargando from "@/components/Cargando/Cargando";
import Pista from "@/components/Pista/Pista";
import Cotizaciones from "@/pages/Cotizaciones/Cotizaciones";
import Ops from "@/pages/Ops/Ops";
import ModuloPendiente from "./ModuloPendiente";
import "@/components/CuerpoModulo/CuerpoModulo.css";

/* La página de los módulos (/inventario, /cotizaciones, /ops, /despachos) —
   lo que antes eran sus paneles dentro de menu.html. Se llega desde el menú
   con la expansión de color (context/ExpansionContext).

   Es UNA sola página para los cuatro (ver MISMA_PAGINA en
   router/RutasAnimadas.jsx): ←/→ pasan al módulo anterior/siguiente, en el
   orden del menú y con vuelta, saltando los apagados en
   core/config.py::MODULOS_HABILITADOS. El paso es un slide (components/
   Pista): la cabecera se queda, el cuerpo del módulo que sale y el del que
   entra viajan pegados, y el fondo cambia al color del nuevo. Reemplaza la
   entrada del historial, así "Volver" siempre va al menú — y el color se
   contrae hacia la caja del módulo en que se está.

   Cada módulo declara cómo carga sus datos y qué pinta con ellos. Los datos
   del vecino se piden ANTES de deslizar, para que entre ya lleno. */

const CONTENIDOS = {
  inventario:   { cargar: async () => null, Contenido: ModuloPendiente },
  cotizaciones: { cargar: () => api.obtener_resumen(), Contenido: Cotizaciones },
  ops:          { cargar: () => api.obtener_resumen(), Contenido: Ops },
  despachos:    { cargar: async () => null, Contenido: ModuloPendiente },
};

const claveDe = (pathname) => MODULOS.find((m) => pathname === m.ruta().split("?")[0])?.clave;

export default function Modulos() {
  const { pathname, state } = useLocation();
  const navigate = useNavigate();
  const volver = useVolver();
  const { contexto } = useApp();
  const { fijarModuloAbierto } = useExpansion();
  const clave = claveDe(pathname);
  const habilitado = (c) => contexto.modulos_habilitados?.[c] !== false;

  const [vista, setVista] = useState(null);        // { clave, datos } — lo que se muestra
  const [deslizando, setDeslizando] = useState(false);
  const precargados = useRef(new Map());           // clave → datos pedidos antes de deslizar
  const pidiendo = useRef(false);

  useEffect(() => {
    if (!clave) return;
    if (precargados.current.has(clave)) {
      setVista({ clave, datos: precargados.current.get(clave) });
      precargados.current.delete(clave);
      return;
    }
    let vigente = true;
    Promise.resolve(CONTENIDOS[clave].cargar()).then((datos) => vigente && setVista({ clave, datos }));
    return () => { vigente = false; };
  }, [clave]);

  async function recargar() {
    const datos = await CONTENIDOS[vista.clave].cargar();
    setVista((v) => (v && v.clave === clave ? { clave, datos } : v));
  }

  async function irAModuloAdyacente(paso) {
    if (deslizando || pidiendo.current || !vista) return;  // uno a la vez
    const lista = MODULOS.filter((m) => habilitado(m.clave));
    const i = lista.findIndex((m) => m.clave === clave);
    if (i === -1 || lista.length < 2) return;
    const destino = lista[(i + paso + lista.length) % lista.length];
    pidiendo.current = true;
    try {
      precargados.current.set(destino.clave, await CONTENIDOS[destino.clave].cargar());
      setDeslizando(true);
      fijarModuloAbierto(destino.clave);
      navigate(destino.ruta(), { replace: true, state: { ...state, deslizar: paso } });
    } finally {
      pidiendo.current = false;
    }
  }

  // Sin flechas en pantalla a propósito (como en menu.html): solo el teclado.
  useAtajo("arrowleft", () => irAModuloAdyacente(-1));
  useAtajo("arrowright", () => irAModuloAdyacente(1));
  useAtajo("escape", volver, !deslizando);
  useAtajo("f5", recargar);

  // Un módulo apagado (típicamente uno sin terminar al sacar un release) no
  // se abre ni llegando por URL: vuelve al menú.
  if (!clave || !habilitado(clave)) return <Navigate to="/" replace />;

  const modulo = MODULOS.find((m) => m.clave === clave);

  return (
    <Pagina tema={clave} titulo={modulo.titulo} className="pagina-modulo">
      <header className="modulo-cab">
        <button className="cab-btn cab-btn--fantasma" onClick={volver} disabled={deslizando}>← Volver</button>
        <span className="cabecera__sep" />
        {contexto.version && <span className="cabecera__version">v{contexto.version}</span>}
      </header>
      <main className="modulo-contenido">
        {!vista ? <Cargando /> : (
          <Pista elemento={vista} clave={(v) => v.clave} direccion={state?.deslizar ?? 1}
                 onTerminar={() => setDeslizando(false)}
                 render={(v) => <CuerpoDe vista={v} />} />
        )}
      </main>
    </Pagina>
  );
}

function CuerpoDe({ vista }) {
  const { Contenido } = CONTENIDOS[vista.clave];
  const { titulo } = MODULOS.find((m) => m.clave === vista.clave);
  return (
    <div className="modulo-cuerpo" data-tema={vista.clave}>
      <h1 className="modulo-cuerpo__titulo">{titulo}</h1>
      <Contenido datos={vista.datos} />
    </div>
  );
}
