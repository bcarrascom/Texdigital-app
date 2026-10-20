import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { AnimatePresence, motion, useAnimate } from "motion/react";
import { api } from "@/services/api";
import { useAtajo } from "@/hooks/useAtajo";
import { useCarrusel } from "@/hooks/useCarrusel";
import { rutas } from "@/router/rutas";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import Etiqueta from "@/components/Etiqueta/Etiqueta";
import VisorProducto from "@/components/VisorProducto/VisorProducto";
import { DialogoAprobar, DialogoEliminar, DialogoMaterialesBloqueado } from "./DialogosCotizacion";
import * as fmt from "@/utils/formato";
import "./VerCotizacion.css";

/* Ver una cotización guardada.

   Dos columnas:
     · izquierda, scrollea: la hoja con los datos + los montos por concepto, y
       debajo las tarjetas de producto (3 por fila).
     · derecha, fija: la figura del producto —que va ciclando— y el desglose
       de plata.

   Los montos NO son un gráfico: no hay magnitud codificada, son las cifras de
   un documento comercial. Por eso van como texto con jerarquía y en tinta
   neutra — el color se reserva para el total.

   ←/→ pasan a la cotización siguiente/anterior (más nueva → más antigua, con
   vuelta) REEMPLAZANDO esta en el historial: "Volver" desde cualquiera de
   ellas vuelve adonde se entró, no retrocede de a una.

   Ese paso es un slide de verdad, como si una cotización estuviera al lado
   de la otra: la página NO se desmonta (ver MISMA_PAGINA en
   router/RutasAnimadas.jsx), la vieja sale por un costado mientras la nueva
   entra por el otro, pegadas. Mientras tanto la cabecera se atenúa y el
   título sale hacia arriba; cuando el slide termina, la cabecera vuelve y el
   título nuevo entra bajando. Los datos de la vecina se piden ANTES de
   arrancar, para que entre ya llena. */

const SLIDE = { duration: 0.55, ease: [0.65, 0, 0.35, 1] };   // simétrica: arranca y frena suave
const TITULO_SALE = { duration: 0.16, ease: [0.55, 0, 1, 0.45] };
const TITULO_ENTRA = { duration: 0.28, ease: [0.22, 1, 0.36, 1] };

async function cargarCotizacion(numero) {
  const cot = await api.obtener_cotizacion(numero);
  return cot && { ...cot, productos: cot.productos || [] };
}

const tituloDe = (cot, numero) =>
  `Cotización ${fmt.numero(cot?.numero ?? numero)}` + (cot?.empresa ? ` · ${cot.empresa}` : "");

export default function VerCotizacion() {
  const numero = Number(useParams().numero);
  const navigate = useNavigate();
  const location = useLocation();
  const direccion = location.state?.deslizar ?? 1;

  /* Cotizaciones ya pedidas a Python, por número: paginar() deja acá la
     vecina antes de navegar, así el slide arranca con los datos listos. */
  const cache = useRef(new Map());
  const [cot, setCot] = useState(undefined);   // undefined: cargando · null: no existe
  const [deslizando, setDeslizando] = useState(false);
  const pidiendo = useRef(false);

  /* El slide: durante el paso, la pista tiene las DOS cotizaciones lado a
     lado ([vieja, nueva] hacia la derecha, [nueva, vieja] hacia la
     izquierda) y lo que se anima es la pista entera, no cada una por su
     lado — así viajan pegadas, sin que una arranque un cuadro antes que la
     otra. Al terminar queda solo la nueva. */
  const [anterior, setAnterior] = useState(null);
  const enPar = !!(anterior && cot && anterior.numero !== cot.numero);
  const [pista, animar] = useAnimate();

  useLayoutEffect(() => {
    if (!enPar) return;
    const ida = direccion > 0;
    const reducido = matchMedia("(prefers-reduced-motion: reduce)").matches;
    // La posición de partida se fija a mano ANTES del primer cuadro: si no,
    // yendo hacia la izquierda se vería un instante la pista sin correr.
    pista.current.style.transform = `translateX(${ida ? 0 : -100}%)`;
    const animacion = animar(pista.current, { x: ida ? ["0%", "-100%"] : ["-100%", "0%"] },
                             reducido ? { duration: 0 } : SLIDE);
    animacion.then(() => {
      setAnterior(null);
      setDeslizando(false);
    });
    return () => animacion.stop();
  }, [enPar]);  // solo al empezar un paso, no en cada render del mismo

  // Ya sin la vieja, la pista vuelve a su lugar en el mismo cuadro en que se
  // saca la vieja (useLayoutEffect: antes de pintar). Las dos cosas hacen
  // falta: motion recuerda el último `x` que animó y lo volvería a escribir
  // encima si solo se toca el estilo, pero su reset recién llega al cuadro
  // siguiente — y ese único cuadro mostraba la cotización fuera de lugar.
  useLayoutEffect(() => {
    if (anterior || !pista.current) return;
    animar(pista.current, { x: "0%" }, { duration: 0 });
    pista.current.style.transform = "none";
  }, [anterior, pista, animar]);
  // Solo la primera cotización que se abre hace la aparición en escalón de
  // sus fichas; las que llegan de costado entran ya armadas.
  const primera = useRef(null);
  if (cot && primera.current === null) primera.current = cot.numero;

  useEffect(() => {
    if (cache.current.has(numero)) {
      setCot(cache.current.get(numero));
      return;
    }
    let vigente = true;
    cargarCotizacion(numero).then((c) => {
      cache.current.set(numero, c);
      if (vigente) setCot(c);
    });
    return () => { vigente = false; };
  }, [numero]);

  // "eliminar" | "bloqueado" | "aprobar" | null
  const [dialogo, setDialogo] = useState(null);
  const [faltantes, setFaltantes] = useState([]);
  const [manuales, setManuales] = useState([]);
  const cerrarDialogo = () => setDialogo(null);

  async function paginar(sentido) {
    if (deslizando || pidiendo.current || !cot) return;  // una a la vez
    pidiendo.current = true;
    try {
      const vecina = await api.cotizacion_adyacente(numero, sentido);
      if (vecina == null || vecina === numero) return;
      if (!cache.current.has(vecina)) cache.current.set(vecina, await cargarCotizacion(vecina));
      setAnterior(cot);
      setDeslizando(true);
      navigate(rutas.verCotizacion(vecina), {
        replace: true,
        state: { ...location.state, deslizar: sentido === "siguiente" ? 1 : -1 },
      });
    } finally {
      pidiendo.current = false;
    }
  }
  useAtajo("arrowleft", () => paginar("anterior"));
  useAtajo("arrowright", () => paginar("siguiente"));

  /* Después de eliminar: si se llegó desde el listado del módulo, alcanza con
     volver a él; si no (p. ej. desde el mazo del menú), se lo reemplaza por
     el listado, para no dejar en el historial una cotización que ya no existe. */
  function irAlListado() {
    if (location.state?.desde === rutas.cotizaciones()) navigate(-1);
    else navigate(rutas.cotizaciones(), { replace: true });
  }

  async function eliminar() {
    setDialogo(null);
    await api.eliminar_cotizacion(numero);
    irAlListado();
  }

  /* El chequeo de stock va ANTES de abrir el diálogo de fechas: si falta
     tela, se avisa al toque en vez de dejar elegir fechas para nada. */
  async function intentarAprobar() {
    const f = (await api.verificar_materiales_cotizacion(numero)) || [];
    if (f.length) {
      setFaltantes(f);
      setDialogo("bloqueado");
      return;
    }
    setManuales((await api.materiales_manuales_pendientes(numero)) || []);
    setDialogo("aprobar");
  }

  const editar = () => navigate(rutas.editarCotizacion(numero));
  const titulo = tituloDe(cot, numero);

  return (
    <Pagina tema="cotizaciones" titulo={titulo} className="pag-ver-cotizacion">
      <Cabecera titulo={<TituloDeslizante texto={titulo} clave={cot?.numero ?? numero} />} atenuada={deslizando}>
        {cot && (
          <>
            <button className="cab-btn" onClick={() => setDialogo("eliminar")}>Eliminar</button>
            <button className="cab-btn" onClick={editar}>Editar</button>
            <button className="cab-btn" onClick={() => api.imprimir_cotizacion(numero)}>Imprimir</button>
            <button className="btn btn--primario btn--chico" onClick={intentarAprobar}>Aprobar →</button>
          </>
        )}
      </Cabecera>

      <main className="contenido">
        {cot === undefined ? <Cargando /> : cot === null ? (
          <p className="seccion-titulo">No se pudo cargar la cotización {fmt.numero(numero)}.</p>
        ) : (
          <div ref={pista} className="pista">
            {(enPar ? (direccion > 0 ? [anterior, cot] : [cot, anterior]) : [cot]).map((c) => (
              // key por número: la nueva conserva su estado (carrusel) al
              // quedar sola en la pista cuando termina el paso.
              <div key={c.numero} className="diapositiva" aria-hidden={c === anterior || undefined}>
                <VistaCotizacion cot={c} aparecer={c.numero === primera.current} />
              </div>
            ))}
          </div>
        )}
      </main>

      {cot && (
        <>
          <DialogoEliminar abierto={dialogo === "eliminar"} cot={cot}
                           onCerrar={cerrarDialogo} onConfirmar={eliminar} />
          <DialogoMaterialesBloqueado abierto={dialogo === "bloqueado"} faltantes={faltantes}
                                      onCerrar={cerrarDialogo}
                                      onNuevoRollo={(textil) => navigate(rutas.inventario({ nuevo_textil: textil }))} />
          <DialogoAprobar abierto={dialogo === "aprobar"} cot={cot} manuales={manuales}
                          onCerrar={cerrarDialogo} onEditar={editar}
                          onAprobada={() => navigate(rutas.ops(), { replace: true })} />
        </>
      )}
    </Pagina>
  );
}

/* El título de la cabecera: al cambiar de cotización sale hacia arriba
   desvaneciéndose, y el nuevo entra bajando recién cuando el slide del
   contenido ya terminó. `clave` es lo que cambia entre cotizaciones (el
   texto solo, no: al terminar de cargar la primera, el texto se completa con
   la empresa y eso no tiene que animarse). */
function TituloDeslizante({ texto, clave }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={clave}
        className="cabecera__titulo-texto"
        initial={{ y: "-110%", opacity: 0 }}
        animate={{ y: 0, opacity: 1, transition: { ...TITULO_ENTRA, delay: SLIDE.duration - TITULO_SALE.duration } }}
        exit={{ y: "-110%", opacity: 0, transition: TITULO_SALE }}
      >
        {texto}
      </motion.span>
    </AnimatePresence>
  );
}

/* Una cotización entera (lo que se desliza): cada una tiene su propio visor
   y su propio carrusel, así la que sale sigue mostrando lo suyo hasta irse. */
function VistaCotizacion({ cot, aparecer }) {
  const carrusel = useCarrusel(cot.productos.length);
  return (
    <div className="vista" data-sin-aparecer={aparecer ? undefined : ""}>
      <div className="vista__izq">
        <Hoja cot={cot} />
        <section>
          <h2 className="seccion-titulo">Productos · {cot.productos.length}</h2>
          <div className="productos">
            {cot.productos.map((p, i) => (
              <FichaProducto key={i} p={p} i={i} mirando={i === carrusel.indice}
                             onMirar={() => carrusel.mirar(i)} onSoltar={carrusel.soltar} />
            ))}
          </div>
        </section>
      </div>

      <aside className="vista__der">
        <div className="lateral">
          <VisorProducto producto={cot.productos[carrusel.indice]} indice={carrusel.indice}
                         total={cot.productos.length} />
          <Plata t={cot.totales || {}} />
        </div>
      </aside>
    </div>
  );
}

/* ── La hoja de datos ───────────────────────────────────────────────────── */

function Hoja({ cot }) {
  const t = cot.totales || {};
  const datos = [
    ["Empresa", cot.empresa],
    ["RUT", cot.rut, { mono: true }],
    ["Razón social", cot.razon_social],
    ["Contacto", cot.contacto],
    ["Email", cot.email],
    ["Condición de pago", cot.condicion],
    ["Fecha", cot.fecha, { mono: true }],
    ["Descripción", cot.descripcion, { ancho: true }],
  ].filter(([, val]) => val || val === 0);

  /* Despacho e instalación solo aparecen si la cotización los lleva: un "$0"
     es ruido, no información. */
  const conceptos = [
    ["Impresión", t.impresion],
    ["Estructuras", t.estructuras],
    ["Terminaciones", t.terminaciones],
    ["Despacho", t.despacho],
    ["Instalación", t.instalacion],
  ].filter(([, v]) => v != null);

  return (
    <section className="hoja">
      <div className="hoja__cab">
        <span className="hoja__num">{fmt.numero(cot.numero)}</span>
        <span className="hoja__nombre">{cot.nombre}</span>
        <span className="hoja__meta">{[cot.empresa, cot.fecha].filter(Boolean).join(" · ")}</span>
      </div>
      <div className="datos">
        {datos.map(([et, val, { mono, ancho } = {}]) => (
          <div key={et} className={`dato${ancho ? " dato--ancho" : ""}`}>
            <span className="dato__et">{et}</span>
            <span className={`dato__val${mono ? " dato__val--mono" : ""}`}>{val}</span>
          </div>
        ))}
      </div>
      <div className="conceptos">
        {conceptos.map(([et, v]) => (
          <div key={et} className="concepto">
            <span className="concepto__et">{et}</span>
            <span className="concepto__val">{fmt.pesos(v)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ── El desglose de plata (panel lateral) ───────────────────────────────── */

const Linea = ({ et, val, total }) => (
  <div className={`plata__linea${total ? " plata__linea--total" : ""}`}><span>{et}</span><b>{val}</b></div>
);

function Plata({ t }) {
  return (
    <div className="plata">
      <Linea et="Neto" val={fmt.pesos(t.neto || 0)} />
      {!!t.descuento_monto && (
        <>
          <Linea et={`Descuento${t.descuento_pct ? ` (${t.descuento_pct}%)` : ""}`}
                 val={"− " + fmt.pesos(t.descuento_monto)} />
          <Linea et="Neto total" val={fmt.pesos(t.neto_total || 0)} />
        </>
      )}
      <Linea et={`IVA (${t.iva_pct ?? 19}%)`} val={fmt.pesos(t.iva || 0)} />
      <Linea et="Total" val={fmt.pesos(t.total || 0)} total />
    </div>
  );
}

/* ── Tarjeta de producto ──────────────────────────────────────────────────
   Mirarla (mouse o foco) congela el visor en ese producto. El JSON guardado
   NO trae lo mismo en los dos tipos: backlight trae Tela + Caja, el estándar
   trae producto + Estructuras + Terminaciones + Impresión (ver
   ui/api_ver_cotizacion.py::_producto_a_json_pantalla). */

function FichaProducto({ p, i, mirando, onMirar, onSoltar }) {
  const bl = p.tipo === "backlight";
  const etiquetas = [
    p.tema && "Tema: " + p.tema,
    ...(bl
      ? [p.caja && p.caja !== "Sin caja" ? p.caja : "Sin caja"]
      : [p.textil || p.tela, p.impresion, ...(p.estructuras || []), ...(p.terminaciones || [])]),
    p.obs && "Obs: " + p.obs,
  ].filter(Boolean);

  return (
    <article className="ficha-prod" style={{ "--i": i }} data-mirando={mirando || undefined}
             onMouseEnter={onMirar} onMouseLeave={onSoltar} onFocus={onMirar} onBlur={onSoltar}>
      <div className="ficha-prod__cab">
        <span className="ficha-prod__n">{i + 1}.</span>
        <span className="ficha-prod__nombre">{bl ? p.tela || "Backlight" : p.producto || "—"}</span>
      </div>
      <span className="ficha-prod__tipo">
        <Etiqueta tipo={bl ? "neutra" : "tema"}>{bl ? "Backlight" : "Estándar"}</Etiqueta>
      </span>
      <div className="ficha-prod__linea">
        <span>Medidas</span><b>{fmt.medida(fmt.aNumero(p.ancho))} × {fmt.medida(fmt.aNumero(p.alto))} m</b>
      </div>
      <div className="ficha-prod__linea"><span>Cantidad</span><b>{parseInt(p.cantidad, 10) || 0}</b></div>
      <div className="ficha-prod__linea">
        <span>Superficie</span>
        <b>{p.ml != null ? `${fmt.cantidad(p.ml)} ML` : p.m2 != null ? `${fmt.cantidad(p.m2)} M²` : "—"}</b>
      </div>
      <div className="ficha-prod__etiquetas">
        {etiquetas.map((e, k) => <Etiqueta key={k}>{e}</Etiqueta>)}
      </div>
      <div className="ficha-prod__pie"><span>Total</span><b>{p.total != null ? fmt.pesos(p.total) : "—"}</b></div>
    </article>
  );
}
