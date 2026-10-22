import { forwardRef, useState } from "react";
import { useAvisos } from "@/context/AvisosContext";
import Segmento from "@/components/Segmento/Segmento";
import * as fmt from "@/utils/formato";
import { CAJA_TERMINADA, SIN_CAJA, esMonto } from "./producto";

/* Un panel del carril de productos: el formulario (izquierda) y la figura
   con las cifras que calcula Python (derecha). Todo número sale de Python
   (ver NuevaCotizacion.jsx::recalcular): acá NO se replica ni una fórmula. */

const TIPOS = [{ valor: "estandar", etiqueta: "Estándar" }, { valor: "backlight", etiqueta: "Backlight" }];
const IMPRESIONES = [{ valor: "Cara única" }, { valor: "Tiro y retiro" }];
const TERMINACIONES_CAJA = [{ valor: CAJA_TERMINADA, etiqueta: "Caja terminada" }, { valor: "AREA VISUAL", etiqueta: "Área visual" }];

const PanelProducto = forwardRef(function PanelProducto(
  { p, i, total, cat, onCambiar, onTipo, onDuplicar, onQuitar, onSiguiente }, ref,
) {
  const bl = p.tipo === "backlight";
  const conPerfil = bl && p.perfil !== SIN_CAJA;
  const c = p.calc || {};
  const anchoMax = c.ancho_max != null ? `Ancho máximo de impresión: ${c.ancho_max} m` : "";

  // Campo de texto simple: el estado se actualiza en cada tecla.
  const campo = (clave) => ({ value: p[clave] ?? "", onChange: (e) => onCambiar({ [clave]: e.target.value }) });

  return (
    <div className="tablero" ref={ref}>
      <article className="prod">
        <header className="prod__cab">
          <span className="prod__num">Producto <b>{i + 1}</b> <small>de {total}</small></span>
          <Segmento opciones={TIPOS} valor={p.tipo} onCambiar={onTipo} etiqueta="Tipo de producto" />
          <span className="barra__sep" />
          <button className="cab-btn" type="button" onClick={onDuplicar}>Duplicar</button>
          <button className="cab-btn" type="button" onClick={onQuitar}>Eliminar</button>
          <button className="btn btn--primario btn--chico" type="button" onClick={onSiguiente}>Siguiente →</button>
        </header>

        <div className="prod__cuerpo">
          <div className="hoja">
            {!bl ? (
              <div className="grupo">
                <div className="fila-prod">
                  <div className="campo">
                    <label className="campo__etiqueta" data-requerido>Producto</label>
                    <input className="entrada" type="text" list="lista-productos" autoComplete="off" {...campo("producto")} />
                  </div>
                  <div className="campo">
                    <label className="campo__etiqueta" data-requerido>Textil</label>
                    <input className="entrada" type="text" list="lista-textiles" autoComplete="off" {...campo("textil")} />
                    <span className="campo__ayuda">{anchoMax}</span>
                  </div>
                  <div className="campo campo--switch">
                    <span className="campo__etiqueta" aria-hidden="true">&nbsp;</span>
                    <Segmento opciones={IMPRESIONES} valor={p.impresion} etiqueta="Impresión"
                              onCambiar={(v) => onCambiar({ impresion: v })} />
                  </div>
                </div>
              </div>
            ) : (
              <div className="grupo">
                <div className="fila fila--2">
                  <div className="campo">
                    <label className="campo__etiqueta" data-requerido>Tela</label>
                    {/* "Sin tela" es una opción de verdad: un backlight puede
                        venderse solo por su caja, sin tela impresa. */}
                    <Selector valor={p.tela} opciones={[["", "— Sin tela —"], ...(cat.telas_backlight || [])]}
                              onCambiar={(v) => onCambiar({ tela: v })} />
                    <span className="campo__ayuda">{anchoMax}</span>
                  </div>
                  <div className="campo">
                    <label className="campo__etiqueta">Caja / perfil</label>
                    {/* Con perfil, el margen es SIEMPRE caja terminada: el
                        switch deja de verse, y dejarle un "área visual" viejo
                        haría que dos productos iguales se cortaran distinto. */}
                    <Selector valor={p.perfil} opciones={[SIN_CAJA, ...(cat.perfiles || [])]}
                              onCambiar={(v) => onCambiar(v !== SIN_CAJA
                                ? { perfil: v, terminaciones_caja: CAJA_TERMINADA } : { perfil: v })} />
                  </div>
                </div>
                {conPerfil ? (
                  <div className="caja-bl">
                    <div className="fila fila--2">
                      <div className="campo">
                        <label className="campo__etiqueta">Luces 1</label>
                        <Selector valor={p.luces_1} opciones={cat.luces || []} onCambiar={(v) => onCambiar({ luces_1: v })} />
                      </div>
                      <div className="campo">
                        <label className="campo__etiqueta">Luces 2</label>
                        <Selector valor={p.luces_2} opciones={cat.luces || []} onCambiar={(v) => onCambiar({ luces_2: v })} />
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Solo sin perfil: el switch dice qué midió el cliente, y
                     eso solo es una pregunta cuando la caja no la armamos
                     nosotros. */
                  <div className="sin-caja-bl">
                    <div className="campo campo--switch">
                      <span className="campo__etiqueta">¿Qué medida entregó el cliente?</span>
                      <Segmento opciones={TERMINACIONES_CAJA} valor={p.terminaciones_caja} etiqueta="Terminaciones de caja"
                                onCambiar={(v) => onCambiar({ terminaciones_caja: v })} />
                      <span className="campo__ayuda">Define el margen de costura del corte: caja terminada +1,5 cm, área visual +2,5 cm.</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Medidas: comunes a los dos tipos */}
            <div className="grupo">
              <div className="fila">
                <div className="campo">
                  <label className="campo__etiqueta" data-requerido>Ancho (m)</label>
                  <input className="entrada entrada--num" type="text" inputMode="decimal" autoComplete="off" {...campo("ancho")} />
                </div>
                <div className="campo">
                  <label className="campo__etiqueta" data-requerido>Alto (m)</label>
                  <input className="entrada entrada--num" type="text" inputMode="decimal" autoComplete="off" {...campo("alto")} />
                </div>
                <div className="campo">
                  <label className="campo__etiqueta" data-requerido>Cantidad</label>
                  <input className="entrada entrada--num" type="text" inputMode="numeric" autoComplete="off" {...campo("cantidad")} />
                </div>
              </div>
              <div className="fila fila--2">
                <div className="campo">
                  <label className="campo__etiqueta">Tema</label>
                  <input className="entrada" type="text" autoComplete="off" {...campo("tema")} />
                </div>
                <div className="campo">
                  <label className="campo__etiqueta">Observaciones</label>
                  <input className="entrada" type="text" autoComplete="off" {...campo("obs")} />
                </div>
              </div>
              {c.error && (
                <>
                  <div className="aviso aviso--error">{c.error}</div>
                  <label className="chip-casilla">
                    <input type="checkbox" checked={!!p.forzar} onChange={(e) => onCambiar({ forzar: e.target.checked })} />
                    <span className="chip-casilla__texto">Forzar igual</span>
                  </label>
                </>
              )}
            </div>

            {/* Estructuras y terminaciones: solo estándar, lado a lado */}
            {!bl && (
              <div className="grupo fila-listas">
                <ListaAditiva titulo="Estructuras" lista="lista-estructuras" items={p.estructuras}
                              montos={c.detalle_estructuras} permitidasSinTextil={cat.estructuras_unit}
                              sinTextil={!p.textil.trim()} onCambiar={(v) => onCambiar({ estructuras: v })} />
                <ListaAditiva titulo="Terminaciones" lista="lista-terminaciones" items={p.terminaciones}
                              montos={c.detalle_terminaciones} permitidasSinTextil={cat.terminaciones_unit}
                              sinTextil={!p.textil.trim()} onCambiar={(v) => onCambiar({ terminaciones: v })} />
              </div>
            )}
          </div>

          <Figura p={p} c={c} />
        </div>
      </article>
    </div>
  );
});

export default PanelProducto;

/* <select> de valores simples (o pares [valor, etiqueta]). */
function Selector({ valor, opciones, onCambiar }) {
  return (
    <select className="entrada" value={valor} onChange={(e) => onCambiar(e.target.value)}>
      {opciones.map((o) => {
        const [v, et] = Array.isArray(o) ? o : [o, o];
        return <option key={v} value={v}>{et}</option>;
      })}
    </select>
  );
}

/* ── Lista aditiva (Estructuras, Terminaciones) ───────────────────────────
   0..N ítems de un catálogo, sin duplicados, o un monto escrito a mano en vez
   de un nombre (ver core.precios.parsear_valor_manual). Cada pastilla muestra
   lo que cobra ese ítem, según el último cálculo de Python. */
function ListaAditiva({ titulo, lista, items, montos, permitidasSinTextil, sinTextil, onCambiar }) {
  const aviso = useAvisos();
  const [texto, setTexto] = useState("");

  function agregar() {
    const t = texto.trim();
    if (!t) return;
    if (items.includes(t)) { setTexto(""); return; }  // sin duplicados
    /* Sin textil no hay de dónde sacar ML impresos — un ítem que se cobra por
       ML quedaría gratis. Los montos escritos a mano se suman directo. */
    if (!esMonto(t) && sinTextil && !(permitidasSinTextil || []).includes(t)) {
      aviso("Sin textil, este producto solo admite ítems que se cobren por unidad.", "aviso");
      return;
    }
    onCambiar([...items, t]);
    setTexto("");
  }

  return (
    <div className="aditiva-bloque">
      <span className="grupo__titulo">{titulo}</span>
      <div className="aditiva">
        <div className="aditiva__alta">
          <input className="entrada" type="text" list={lista} autoComplete="off" value={texto}
                 onChange={(e) => setTexto(e.target.value)}
                 onKeyDown={(e) => {
                   if (e.key !== "Enter") return;
                   // Que el Enter de "pasar al producto siguiente" no lo vea.
                   e.preventDefault(); e.stopPropagation();
                   agregar();
                 }} />
          <button className="btn btn--secundario" type="button" onClick={agregar}>+</button>
        </div>
        <div className="aditiva__items">
          {items.map((nombre, k) => (
            <div key={nombre} className={`pastilla${esMonto(nombre) ? " pastilla--manual" : ""}`} style={{ "--i": k }}>
              <span className="pastilla__nombre">{nombre}</span>
              {montos?.[nombre] != null && <span className="pastilla__monto">{fmt.pesos(montos[nombre])}</span>}
              <button className="pastilla__quitar" type="button" aria-label="Quitar"
                      onClick={() => onCambiar(items.filter((_, j) => j !== k))}>✕</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── La figura y las cifras ───────────────────────────────────────────────
   El lado largo siempre ocupa el alto disponible: es una PROPORCIÓN, no una
   escala en metros. El contorno se pone rojo con error de medida, ámbar si se
   forzó igual. */
function Figura({ p, c }) {
  const ancho = fmt.aNumero(p.ancho), alto = fmt.aNumero(p.alto);
  const hay = ancho > 0 && alto > 0;
  const largo = Math.max(ancho, alto), corto = Math.min(ancho, alto);
  const w = hay ? 70 * (corto / largo) : 60;
  const xCota = 50 - w / 2 - 6;   // la cota del alto acompaña al borde izquierdo
  const estado = c.error ? (p.forzar ? "forzado" : "error") : "ok";

  return (
    <aside className="figura" data-estado={estado}>
      {hay ? (
        <div className="figura__marco">
          <svg viewBox="0 0 100 100" role="img" aria-label="Proporción del paño impreso">
            <rect className="figura__rect" x={50 - w / 2} y="15" width={w} height="70" rx="2" />
            <text className="figura__cota" x="50" y="10" textAnchor="middle">{corto} m</text>
            <text className="figura__cota" x={xCota} y="50" textAnchor="middle" transform={`rotate(-90 ${xCota} 50)`}>
              {largo} m
            </text>
          </svg>
        </div>
      ) : (
        <p className="figura__vacio">Ingresá las medidas para ver la proporción.</p>
      )}
      <div className="cifras">
        <Cifras p={p} c={c} />
      </div>
    </aside>
  );
}

const Cifra = ({ et, val, total }) => (
  <div className={`cifra${total ? " cifra--total" : ""}`}>
    <span className="cifra__et">{et}</span><span className="cifra__val">{val}</span>
  </div>
);

function Cifras({ p, c }) {
  if (p.tipo === "estandar") {
    return (
      <>
        {c.ml != null && <Cifra et="Metros impresos" val={`${fmt.cantidad(c.ml)} ML`} />}
        {c.costo_impresion != null && <Cifra et="Impresión" val={fmt.pesos(c.costo_impresion)} />}
        {c.costo_extras != null && <Cifra et="Estructuras + terminaciones" val={fmt.pesos(c.costo_extras)} />}
        {c.valor_unitario != null && <Cifra et="Valor unitario" val={fmt.pesos(c.valor_unitario)} />}
        {c.total != null && <Cifra et="Total producto" val={fmt.pesos(c.total)} total />}
      </>
    );
  }
  const conCaja = p.perfil && p.perfil !== SIN_CAJA;
  const materiales = c.materiales || [];
  return (
    <>
      {c.m2 != null && <Cifra et="Superficie" val={`${fmt.cantidad(c.m2)} M²`} />}
      {/* Sin caja no hay luces ni fuente: los watts no significan nada ahí. */}
      {conCaja && c.watts != null && <Cifra et="Watts por caja" val={`${c.watts} W`} />}
      {materiales.map((m) => <Cifra key={`${m.material}-${m.tipo}`} et={`${m.material} · ${m.tipo}`} val={fmt.cantidad(m.cantidad_total)} />)}
      {/* Sin caja no hay materiales de caja que listar: un "—" confundiría. */}
      {!materiales.length && conCaja && <Cifra et="Materiales" val="—" />}
      {/* Materiales de Inventario que gasta (la silicona de los bordes, p. ej.):
          cuánto se usa y cuánto se cobra, en la misma línea. */}
      {(c.materiales_inventario || []).map((m) => (
        <Cifra key={m.nombre} et={m.nombre} val={`${fmt.cantidad(m.consumo)} ${m.unidad} · ${fmt.pesos(m.monto)}`} />
      ))}
      {c.valor_unitario != null && <Cifra et="Valor unitario" val={fmt.pesos(c.valor_unitario)} />}
      {c.total != null && <Cifra et="Total producto" val={fmt.pesos(c.total)} total />}
    </>
  );
}
