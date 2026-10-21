import { useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { api } from "@/services/api";
import { useFichaPaginada } from "@/hooks/useFichaPaginada";
import { rutas } from "@/router/rutas";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import Dialogo from "@/components/Dialogo/Dialogo";
import Pista from "@/components/Pista/Pista";
import TituloDeslizante from "@/components/TituloDeslizante/TituloDeslizante";
import { Dato, Datos, VistaDetalle } from "@/components/Detalle/Detalle";
import * as fmt from "@/utils/formato";
import "./VerOp.css";

/* Ver una OP. Estructuralmente igual a ver-cotización (components/Detalle):
   es la MISMA cotización aprobada, mirada desde el lado de producción. Por
   eso no lleva plata en ningún lado — acá lo que importa es qué se produce,
   cuánto, y cuándo entra y sale:
     · izquierda: la hoja (con la fecha de entrega en grande y los materiales
       de todo el trabajo) + las fichas de producto.
     · derecha: el visor, y la logística (despacho, instalación) en vez de la
       plata.

   ←/→ pasan a la OP vecina entre TODAS las OPs (activas, completadas e
   historial), con el mismo slide que las cotizaciones. Recotizar y Completar
   solo existen para una OP activa. */

const SLIDE = { duration: 0.35, ease: [0.65, 0, 0.35, 1] };

async function cargarOp(numero) {
  const op = await api.obtener_op(numero);
  return op && { ...op, productos: op.productos || [] };
}

const tituloDe = (op, numero) => `OP ${fmt.numero(op?.numero ?? numero)}` + (op?.empresa ? ` · ${op.empresa}` : "");

export default function VerOp() {
  const numero = Number(useParams().numero);
  const navigate = useNavigate();
  const location = useLocation();
  const { ficha: op, direccion, deslizando, alTerminarSlide, actualizar } = useFichaPaginada({
    numero, cargar: cargarOp, adyacente: api.op_adyacente, ruta: rutas.verOp,
  });

  const primera = useRef(null);
  if (op && primera.current === null) primera.current = op.numero;

  const [dialogo, setDialogo] = useState(null);   // "recotizar" | "completar" | null
  const activa = op?.estado === "activa";

  /* Recotizar: vuelve a Cotizaciones para editarla y aprobarla de nuevo. */
  async function recotizar() {
    setDialogo(null);
    if (await api.recotizar_op(numero)) navigate(rutas.cotizaciones(), { replace: true });
    // Si no se pudo, Python ya mostró el aviso.
  }

  /* Completar: sale de las activas. Si se llegó desde el listado de OPs, se
     vuelve a él (sin esta OP); si no, se lo pone en lugar de esta pantalla. */
  async function completar() {
    setDialogo(null);
    if (!(await api.completar_op(numero))) return;
    if (location.state?.desde === rutas.ops()) navigate(-1);
    else navigate(rutas.ops(), { replace: true });
  }

  /* "OP Inser": casilla que decide si el documento impreso lleva un recuadro
     vacío para anotar a mano el N° de ingreso en Inser (se escribe con lápiz
     sobre la hoja: acá no se conoce). Se guarda al instante. */
  function cambiarOpInser(marcado) {
    actualizar((o) => ({ ...o, op_inser: marcado }));
    api.guardar_op_inser(numero, marcado);
  }

  const titulo = tituloDe(op, numero);

  return (
    <Pagina tema="ops" titulo={titulo} className="pag-detalle pag-ver-op">
      <Cabecera titulo={<TituloDeslizante texto={titulo} clave={op?.numero ?? numero} esperar={SLIDE.duration} />}
                bloqueada={deslizando}>
        {op && (
          <>
            {activa && <button className="cab-btn" onClick={() => setDialogo("recotizar")}>Recotizar</button>}
            <button className="cab-btn" onClick={() => api.imprimir_op(numero)}>Imprimir</button>
            {activa && <button className="btn btn--primario btn--chico" onClick={() => setDialogo("completar")}>Completar OP</button>}
          </>
        )}
      </Cabecera>

      <main className="contenido">
        {op === undefined ? <Cargando /> : op === null ? (
          <p className="seccion-titulo">No se pudo cargar la OP {fmt.numero(numero)}.</p>
        ) : (
          <Pista elemento={op} clave={(o) => o.numero} direccion={direccion} transicion={SLIDE}
                 onTerminar={alTerminarSlide}
                 render={(o) => (
                   <VistaDetalle productos={o.productos} aparecer={o.numero === primera.current}
                                 hoja={<Hoja op={o} onOpInser={cambiarOpInser} />}
                                 lateral={<Logistica op={o} />} />
                 )} />
        )}
      </main>

      <Dialogo abierto={dialogo === "recotizar"} onCerrar={() => setDialogo(null)} onConfirmar={recotizar} className="dlg--desenfoque">
        <h2 className="dlg__titulo">¿Recotizar esta OP?</h2>
        <p className="dlg__texto">
          Vuelve a la carpeta de Cotizaciones para editarla y aprobarla de nuevo —
          esta orden de producción deja de estar activa.
        </p>
        <div className="dlg__acciones">
          <button className="btn btn--fantasma btn--chico" type="button" onClick={() => setDialogo(null)}>Cancelar</button>
          <button className="btn btn--primario btn--chico" type="button" onClick={recotizar}>Recotizar</button>
        </div>
      </Dialogo>

      <Dialogo abierto={dialogo === "completar"} onCerrar={() => setDialogo(null)} onConfirmar={completar} className="dlg--desenfoque">
        <h2 className="dlg__titulo">¿Completar esta OP?</h2>
        <p className="dlg__texto">
          Sale de las OPs activas — si tiene despacho y/o instalación pasa al
          módulo Despachos, si no, queda archivada como completada.
        </p>
        <div className="dlg__acciones">
          <button className="btn btn--fantasma btn--chico" type="button" onClick={() => setDialogo(null)}>Cancelar</button>
          <button className="btn btn--primario btn--chico" type="button" onClick={completar}>Completar</button>
        </div>
      </Dialogo>
    </Pagina>
  );
}

/* ── La hoja de datos ───────────────────────────────────────────────────── */

function Hoja({ op, onOpInser }) {
  return (
    <section className="hoja">
      <div className="hoja__cab">
        <div className="hoja__cab-izq">
          <span className="hoja__num">{fmt.numero(op.numero)}</span>
          <span className="hoja__nombre">{op.nombre}</span>
          <span className="hoja__meta">{op.empresa}</span>
        </div>
        <Entrega fecha={op.fecha_entrega} activa={op.estado === "activa"} />
      </div>

      <Datos lista={[
        ["Empresa", op.empresa],
        ["Contacto", op.contacto],
        ["Email", op.email],
        ["Fecha de ingreso", op.fecha_ingreso, { mono: true }],
        ["Descripción", op.descripcion, { ancho: true }],
      ]}>
        {/* Solo para OPs con al menos un producto backlight. */}
        {op.tiene_backlight && (
          <div className="dato">
            <span className="dato__et">OP Inser</span>
            <label className="chip-casilla dato__casilla">
              <input type="checkbox" checked={!!op.op_inser} onChange={(e) => onOpInser(e.target.checked)} />
              <span className="chip-casilla__texto">OP Inser</span>
            </label>
            <span className="dato__ayuda">Imprime un recuadro vacío para anotar el número a mano.</span>
          </div>
        )}
      </Datos>

      <Materiales productos={op.productos} />
    </section>
  );
}

/* El dato que más importa de la pantalla: grande, a la altura del número de
   OP, con el subtítulo de urgencia coloreado según cercanía — así se lee de
   un vistazo sin tener que restar fechas. Solo en una OP activa: en una ya
   completada o cancelada, "atrasada por 9 días" no dice nada útil. */
function Entrega({ fecha, activa }) {
  const n = activa ? fmt.diasHasta(fecha) : null;
  const [texto, urgencia] =
    n == null ? ["", undefined]
    : n > 1 ? [`Entrega en ${n} días`, "futuro"]
    : n === 1 ? ["Entrega mañana", "manana"]
    : n === 0 ? ["Entrega hoy", "hoy"]
    : [`Entrega atrasada por ${-n} ${-n === 1 ? "día" : "días"}`, "atrasada"];
  return (
    <div className="entrega">
      <span className="entrega__fecha">{fecha || "—"}</span>
      <span className="entrega__estado" data-urgencia={urgencia}>{texto}</span>
    </div>
  );
}

/* Todo lo que el trabajo consume, sumado entre productos: textiles,
   materiales de caja y estructuras. Siempre las tres columnas, en el mismo
   orden — una sin nada que listar queda en blanco, no le cede su lugar a la
   de al lado. Sin nada en ninguna, el bloque no aparece. */
function Materiales({ productos }) {
  const textiles = new Map();     // nombre → { ml, m2 }
  const cajas = new Map();        // nombre → cantidad de cajas
  const estructuras = new Map();  // nombre → cantidad
  productos.forEach((p) => {
    const cant = parseInt(p.cantidad, 10) || 0;
    const bl = p.tipo === "backlight";
    const tela = bl ? p.tela : p.textil;
    if (tela) {
      const acc = textiles.get(tela) || { ml: 0, m2: 0 };
      if (p.ml != null) acc.ml += p.ml;
      if (p.m2 != null) acc.m2 += p.m2;
      textiles.set(tela, acc);
    }
    if (bl && p.caja && p.caja !== "Sin caja") cajas.set(p.caja, (cajas.get(p.caja) || 0) + cant);
    if (!bl) (p.estructuras || []).forEach((e) => estructuras.set(e, (estructuras.get(e) || 0) + cant));
  });
  if (!textiles.size && !cajas.size && !estructuras.size) return null;

  const metros = (v) => [v.ml && `${fmt.cantidad(v.ml)} ML`, v.m2 && `${fmt.cantidad(v.m2)} M²`].filter(Boolean).join(" · ") || "—";
  // "×N" en vez de "N cajas": la cantidad se lee sola y así entra sin apretar el nombre.
  const veces = (n) => `×${n}`;

  return (
    <div className="materiales">
      <GrupoMateriales titulo="Textiles" mapa={textiles} formatear={metros} />
      <GrupoMateriales titulo="Materiales de caja" mapa={cajas} formatear={veces} />
      <GrupoMateriales titulo="Estructuras" mapa={estructuras} formatear={veces} />
    </div>
  );
}

function GrupoMateriales({ titulo, mapa, formatear }) {
  return (
    <div className="materiales__grupo">
      {mapa.size > 0 && (
        <>
          <span className="materiales__titulo">{titulo}</span>
          {[...mapa].map(([nombre, valor]) => (
            <div key={nombre} className="materiales__fila"><span>{nombre}</span><b>{formatear(valor)}</b></div>
          ))}
        </>
      )}
    </div>
  );
}

/* Logística en vez de plata. Despacho e instalación no aparecen si el
   trabajo no los lleva: un "No incluye" solo sería ruido. */
function Logistica({ op }) {
  return (
    <div className="produccion">
      {op.despacho && <Dato etiqueta="Despacho">Incluye despacho</Dato>}
      {op.instalacion && <Dato etiqueta="Instalación">Incluye instalación</Dato>}
    </div>
  );
}
