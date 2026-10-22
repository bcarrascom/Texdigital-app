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
  const { ficha: cot, direccion, deslizando, alTerminarSlide } = useFichaPaginada({
    numero, cargar: cargarCotizacion, adyacente: api.cotizacion_adyacente, ruta: rutas.verCotizacion,
  });

  // Solo la primera cotización que se abre hace la aparición en escalón de
  // sus fichas; las que llegan de costado entran ya armadas.
  const primera = useRef(null);
  if (cot && primera.current === null) primera.current = cot.numero;

  // "eliminar" | "bloqueado" | "aprobar" | null
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
                                 hoja={<Hoja cot={c} />} lateral={<Plata t={c.totales || {}} />}
                                 pieFicha={(p) => <><span>Total</span><b>{p.total != null ? fmt.pesos(p.total) : "—"}</b></>} />
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
          <DialogoAprobar abierto={dialogo === "aprobar"} cot={cot} manuales={manuales}
                          onCerrar={cerrarDialogo} onEditar={editar}
                          onAprobada={() => navigate(rutas.ops(), { replace: true })} />
        </>
      )}
    </Pagina>
  );
}

/* ── La hoja de datos ───────────────────────────────────────────────────── */

function Hoja({ cot }) {
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
        <span className="hoja__num">{fmt.numero(cot.numero)}</span>
        <span className="hoja__nombre">{cot.nombre}</span>
        <span className="hoja__meta">{[cot.empresa, cot.fecha].filter(Boolean).join(" · ")}</span>
      </div>
      <Datos lista={[
        ["Empresa", cot.empresa],
        ["RUT", cot.rut, { mono: true }],
        ["Razón social", cot.razon_social],
        ["Contacto", cot.contacto],
        ["Email", cot.email],
        ["Condición de pago", cot.condicion],
        ["Fecha", cot.fecha, { mono: true }],
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
