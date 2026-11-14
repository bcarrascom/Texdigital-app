import { useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { api } from "@/services/api";
import { useFichaPaginada } from "@/hooks/useFichaPaginada";
import { rutas } from "@/router/rutas";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import Pista from "@/components/Pista/Pista";
import TituloDeslizante from "@/components/TituloDeslizante/TituloDeslizante";
import { Datos, VistaDetalle } from "@/components/Detalle/Detalle";
import { DialogoAprobar, DialogoEliminar, DialogoMaterialesBloqueado } from "./DialogosCotizacion";
import { AvisoPrecios, DialogoPrecios } from "./CambiosPrecios";
import { lineaParaDialogo, PieProducto, PlataAjustes } from "./Descuentos";
import { DialogoDescuentoLinea, DialogoDescuentoPedido, DialogoRestablecer } from "@/components/Descuentos/Descuentos";
import DialogoEnviarCorreo from "./EnviarCorreo";
import IconoCorreo from "@/assets/svg/mail.svg?react";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import IconoListo from "@/assets/svg/check.svg?react";
import { useAvisos } from "@/context/AvisosContext";
import * as fmt from "@/utils/formato";
import "./VerCotizacion.css";

/* Ver una cotización guardada.

   Dos columnas (components/Detalle, las mismas de ver-OP):
     · izquierda, scrollea: la hoja con los datos + los montos por concepto, y
       debajo las tarjetas de producto (3 por fila).
     · derecha, fija: la figura del producto —que va ciclando— y el desglose
       de plata.

   Los montos NO son un gráfico: no hay magnitud codificada, son las cifras de
   un documento comercial. Por eso van como texto con jerarquía y en tinta
   neutra — el color se reserva para el total.

   ←/→ pasan a la cotización siguiente/anterior (más nueva → más antigua, con
   vuelta) con un slide de verdad, como si una estuviera al lado de la otra
   (hooks/useFichaPaginada + components/Pista). Mientras tanto los botones de
   la cabecera no responden, y el título sale hacia arriba y el nuevo entra
   subiendo cuando termina el slide (components/TituloDeslizante). */

const SLIDE = { duration: 0.35, ease: [0.65, 0, 0.35, 1] };   // simétrica: arranca y frena suave

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
  const aviso = useAvisos();
  const { ficha: cot, direccion, deslizando, alTerminarSlide, actualizar } = useFichaPaginada({
    numero, cargar: cargarCotizacion, adyacente: api.cotizacion_adyacente, ruta: rutas.verCotizacion,
  });

  // Solo la primera cotización que se abre hace la aparición en escalón de
  // sus fichas; las que llegan de costado entran ya armadas.
  const primera = useRef(null);
  if (cot && primera.current === null) primera.current = cot.numero;

  // "eliminar" | "bloqueado" | "aprobar" | "precios" | "restablecer" | "correo" | null
  const [dialogo, setDialogo] = useState(null);
  const [faltantes, setFaltantes] = useState([]);
  const [manuales, setManuales] = useState([]);
  const cerrarDialogo = () => setDialogo(null);

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

  /* "Cambiaron precios": actualizarla a los de hoy o mantener los suyos. Se
     vuelve a pedir la cotización para mostrar cómo quedó. */
  async function decidirPrecios(actualizarPrecios) {
    if (actualizarPrecios) await api.actualizar_precios_cotizacion(numero);
    else await api.mantener_precios_cotizacion(numero);
    const nueva = await cargarCotizacion(numero);
    if (nueva) actualizar(() => nueva);
    setDialogo(null);
    aviso(actualizarPrecios ? "Cotización actualizada a los precios de hoy." : "Se mantienen los precios de la cotización.", "info");
  }

  /* Descuentos puestos a mano, sin entrar a Editar (components/Descuentos):
     `editando` es "p0", "p1"… (un producto), "despacho", "instalacion" o
     "pedido". Se guardan al tiro y la cotización vuelve recalculada. */
  const [editando, setEditando] = useState(null);
  const lineaEditando = editando && editando !== "pedido" ? lineaDeClave(cot, editando) : null;

  async function guardarDescuentos(cambios) {
    setEditando(null);
    const nueva = await api.guardar_descuentos_cotizacion(numero, cambios);
    if (nueva) actualizar(() => ({ ...nueva, productos: nueva.productos || [] }));
    aviso("Descuentos guardados.", "info");
  }

  async function restablecer() {
    setDialogo(null);
    const nueva = await api.restablecer_descuentos_cotizacion(numero);
    if (nueva) actualizar(() => ({ ...nueva, productos: nueva.productos || [] }));
    aviso("Se volvió a los descuentos automáticos.", "info");
  }

  /* El correo salió (ver ui/api_correos.py): la hoja muestra el último envío,
     el sobre se cierra y se va (components/CorreoEnviado) y después el aviso. */
  function correoEnviado(r) {
    setDialogo(null);
    actualizar((c) => ({ ...c, ultimo_correo: r.ultimo, estado_correo: "al_dia" }));
    // La animación y el aviso "Enviado a …" los muestra components/CorreoEnviado.
  }

  const editar = () => navigate(rutas.editarCotizacion(numero));
  const titulo = tituloDe(cot, numero);

  return (
    <Pagina tema="cotizaciones" titulo={titulo} className="pag-detalle pag-ver-cotizacion">
      <Cabecera titulo={<TituloDeslizante texto={titulo} clave={cot?.numero ?? numero} esperar={SLIDE.duration} />}
                bloqueada={deslizando}>
        {cot && (
          <>
            <button className="cab-btn" onClick={() => setDialogo("eliminar")}>Eliminar</button>
            <button className="cab-btn" onClick={editar}>Editar</button>
            <button className="cab-btn" onClick={() => api.imprimir_cotizacion(numero)}>Imprimir</button>
            {cot.correo_al_cliente && <button className="cab-btn" onClick={() => setDialogo("correo")}>Enviar correo</button>}
            <button className="btn btn--primario btn--chico" onClick={intentarAprobar}>Aprobar →</button>
          </>
        )}
      </Cabecera>

      <main className="contenido">
        {cot === undefined ? <Cargando /> : cot === null ? (
          <p className="seccion-titulo">No se pudo cargar la cotización {fmt.numero(numero)}.</p>
        ) : (
          <Pista elemento={cot} clave={(c) => c.numero} direccion={direccion} transicion={SLIDE}
                 onTerminar={alTerminarSlide}
                 render={(c) => (
                   <VistaDetalle productos={c.productos} aparecer={c.numero === primera.current}
                                 hoja={<>
                                   {c.cambios_precios && <AvisoPrecios onRevisar={() => setDialogo("precios")} />}
                                   <Hoja cot={c} onCorreo={() => setDialogo("correo")} />
                                 </>}
                                 lateral={<PlataAjustes t={c.totales || {}} d={c.descuento} productos={c.productos}
                                                        onEditar={setEditando}
                                                        onRestablecer={() => setDialogo("restablecer")} />}
                                 pieFicha={(p, i) => <PieProducto p={p} onEditar={() => setEditando(`p${i}`)} />} />
                 )} />
        )}
      </main>

      {cot && (
        <>
          <DialogoEliminar abierto={dialogo === "eliminar"} cot={cot}
                           onCerrar={cerrarDialogo} onConfirmar={eliminar} />
          <DialogoMaterialesBloqueado abierto={dialogo === "bloqueado"} faltantes={faltantes}
                                      onCerrar={cerrarDialogo}
                                      onNuevoRollo={(textil) => navigate(rutas.inventario({ nuevo_textil: textil }))} />
          <DialogoPrecios abierto={dialogo === "precios"} cambios={cot.cambios_precios}
                          onCerrar={cerrarDialogo} onDecidir={decidirPrecios} />
          <DialogoDescuentoLinea abierto={!!lineaEditando} linea={lineaEditando}
                                 onCerrar={() => setEditando(null)}
                                 onGuardar={(manual) => guardarDescuentos(cambioDeLinea(editando, manual))} />
          <DialogoDescuentoPedido abierto={editando === "pedido"} lineas={lineasDelPedido(cot)}
                                  pedido={cot.descuento?.pedido} onCerrar={() => setEditando(null)}
                                  onGuardar={guardarDescuentos} />
          <DialogoRestablecer abierto={dialogo === "restablecer"} onCerrar={cerrarDialogo} onConfirmar={restablecer} />
          <DialogoEnviarCorreo abierto={dialogo === "correo"} numero={cot.numero} onCerrar={cerrarDialogo} onEnviado={correoEnviado} />
          <DialogoAprobar abierto={dialogo === "aprobar"} cot={cot} manuales={manuales}
                          onCerrar={cerrarDialogo} onEditar={editar}
                          onAprobada={() => navigate(rutas.ops(), { replace: true })} />
        </>
      )}
    </Pagina>
  );
}

/* ── Descuentos: de la clave del diálogo a la línea y de vuelta ─────────── */

function lineaDeClave(cot, clave) {
  if (!cot) return null;
  if (clave.startsWith("p")) {
    const i = Number(clave.slice(1));
    const d = cot.productos[i]?.descuento;
    return d ? lineaParaDialogo(d, `${i + 1}. ${d.nombre}`) : null;
  }
  const d = cot.descuento?.[clave];
  return d ? lineaParaDialogo(d, d.nombre) : null;
}

function cambioDeLinea(clave, manual) {
  return clave.startsWith("p") ? { productos: { [clave.slice(1)]: manual } } : { [clave]: manual };
}

/* Todas las líneas que se pueden descontar, para "el mismo descuento en
   todas" del diálogo del pedido. */
function lineasDelPedido(cot) {
  const lineas = cot.productos.map((p, i) => ({ clave: `p${i}`, precio: p.descuento?.precio ?? p.total }));
  for (const k of ["despacho", "instalacion"]) {
    if (cot.descuento?.[k]) lineas.push({ clave: k, precio: cot.descuento[k].precio });
  }
  return lineas;
}

/* ── La hoja de datos ───────────────────────────────────────────────────── */

/* "09/11/2026 10:32 a cliente@x.cl (prueba)" — vacío si nunca se envió. */
const textoCorreo = (c) =>
  c ? `${c.fecha} a ${c.para.join(", ")}${c.simulado ? " (no salió)" : c.prueba ? " (prueba)" : ""}` : "";

/* Si el cliente tiene la cotización tal como está (ui/api_correos.estado_envio;
   pedido de Bruno, 2026-11-11): arriba a la derecha de la hoja, y abre
   "Enviar correo". Los dos avisos en ámbar; al día, en verde. */
const ESTADOS_CORREO = {
  sin_enviar:  { tipo: "aviso", Icono: IconoCorreo, texto: "Sin enviar al cliente",
                 ayuda: "Esta cotización todavía no se le ha enviado al cliente. Clic para enviarla." },
  con_cambios: { tipo: "aviso", Icono: IconoAviso, texto: "Cambió desde el último envío",
                 ayuda: "El cliente tiene una versión anterior: la cotización cambió después del último correo. Clic para enviarla de nuevo." },
  al_dia:      { tipo: "ok", Icono: IconoListo, texto: "Enviada al cliente",
                 ayuda: "El último correo lleva la cotización tal como está ahora." },
};

function EstadoCorreo({ cot, onCorreo }) {
  if (!cot.correo_al_cliente) return null;   // los correos a clientes, desactivados
  const e = ESTADOS_CORREO[cot.estado_correo];
  if (!e) return null;
  const texto = e === ESTADOS_CORREO.al_dia && cot.ultimo_correo?.prueba ? "Enviada (prueba)" : e.texto;
  return (
    <button type="button" className={`etiqueta etiqueta--${e.tipo} estado-correo`} title={e.ayuda} onClick={onCorreo}>
      <e.Icono className="estado-correo__icono" aria-hidden="true" />
      {texto}
    </button>
  );
}

function Hoja({ cot, onCorreo }) {
  const t = cot.totales || {};
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
        <div className="hoja__cab-izq">
          <span className="hoja__num">{fmt.numero(cot.numero)}</span>
          <span className="hoja__nombre">{cot.nombre}</span>
          <span className="hoja__meta">{[cot.empresa, cot.fecha].filter(Boolean).join(" · ")}</span>
        </div>
        <EstadoCorreo cot={cot} onCorreo={onCorreo} />
      </div>
      <Datos lista={[
        ["Empresa", cot.empresa],
        ["RUT", cot.rut, { mono: true }],
        ["Razón social", cot.razon_social],
        ["Contacto", cot.contacto],
        ["Email", cot.email],
        ["Condición de pago", cot.condicion],
        ["Fecha", cot.fecha, { mono: true }],
        ["Último correo", textoCorreo(cot.ultimo_correo)],
        ["Descripción", cot.descripcion, { ancho: true }],
      ]} />
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
