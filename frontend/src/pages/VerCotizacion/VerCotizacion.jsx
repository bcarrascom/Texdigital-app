import { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { api } from "@/services/api";
import { useAtajo } from "@/hooks/useAtajo";
import { useCarrusel } from "@/hooks/useCarrusel";
import { useDatos } from "@/hooks/useDatos";
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
   ellas vuelve adonde se entró, no retrocede de a una. */

async function cargarCotizacion(numero) {
  const cot = await api.obtener_cotizacion(numero);
  return cot && { ...cot, productos: cot.productos || [] };
}

export default function VerCotizacion() {
  const numero = Number(useParams().numero);
  const navigate = useNavigate();
  const location = useLocation();
  const { datos: cot, cargando } = useDatos(() => cargarCotizacion(numero), [numero]);
  const carrusel = useCarrusel(cot?.productos.length ?? 0);

  // "eliminar" | "bloqueado" | "aprobar" | null
  const [dialogo, setDialogo] = useState(null);
  const [faltantes, setFaltantes] = useState([]);
  const [manuales, setManuales] = useState([]);
  const cerrarDialogo = () => setDialogo(null);

  async function paginar(direccion) {
    const vecina = await api.cotizacion_adyacente(numero, direccion);
    if (vecina == null) return;
    navigate(rutas.verCotizacion(vecina), {
      replace: true,
      state: { ...location.state, deslizar: direccion === "siguiente" ? 1 : -1 },
    });
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
  const titulo = cot
    ? `Cotización ${fmt.numero(cot.numero)}` + (cot.empresa ? ` · ${cot.empresa}` : "")
    : `Cotización ${fmt.numero(numero)}`;

  return (
    <Pagina tema="cotizaciones" titulo={titulo} className="pag-ver-cotizacion">
      <Cabecera titulo={titulo}>
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
        {cargando ? <Cargando /> : !cot ? (
          <p className="seccion-titulo">No se pudo cargar la cotización {fmt.numero(numero)}.</p>
        ) : (
          <div className="vista">
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
