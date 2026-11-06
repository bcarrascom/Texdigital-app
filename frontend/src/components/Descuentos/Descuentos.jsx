import { useState } from "react";
import Dialogo from "@/components/Dialogo/Dialogo";
import * as fmt from "@/utils/formato";
import "./Descuentos.css";

/* Descuentos puestos a mano (pedido de Bruno, 2026-11-06; las reglas están en
   core/precios.py, "Descuentos puestos a mano"). Lo usan ver-cotización (se
   guarda al tiro) y el resumen del cotizador (queda en el estado hasta
   Guardar).

   Un descuento manual es { tipo: "pct" | "monto", valor }. El usuario edita
   el % o los $ y el otro se calcula; se guarda el que escribió.

     DialogoDescuentoLinea   el de un producto, del despacho o de la instalación
     DialogoDescuentoPedido  el mismo descuento en todas las líneas y/o un
                             adicional sobre el total
     DialogoRestablecer      confirmar "Restablecer descuentos"
     textoRazon / RAZON      "−10 % (contacto)" */

export const RAZON = { contacto: "contacto", volumen: "volumen", manual: "manual", pedido: "pedido" };

const unDecimal = (v) => Math.round(v * 10) / 10;
export const pct = (v) => `${fmt.cantidad(unDecimal(v))} %`;
export const textoRazon = (pctV, razon) => `−${pct(pctV)} (${RAZON[razon] || razon})`;

/* Los $ de un manual sobre `base`, como core.precios.monto_manual. */
export function montoManual(manual, base) {
  if (!manual) return null;
  const v = Number(manual.valor) || 0;
  const m = manual.tipo === "pct" ? (base * v) / 100 : v;
  return base > 0 ? Math.max(0, Math.min(m, base)) : 0;
}

/* Estado de los dos campos enlazados: los textos de % y $, y cuál escribió
   el usuario (ese es el que se guarda). */
function enlazado(manual, base) {
  if (!manual) return { tipo: null, pctTxt: "", montoTxt: "" };
  const monto = montoManual(manual, base) ?? 0;
  return manual.tipo === "pct"
    ? { tipo: "pct", pctTxt: fmt.cantidad(manual.valor), montoTxt: fmt.clp(Math.round(monto)) }
    : { tipo: "monto", pctTxt: base ? fmt.cantidad(unDecimal((monto / base) * 100)) : "", montoTxt: fmt.clp(manual.valor) };
}

const manualDe = (e) => {
  if (!e.tipo) return null;
  if (e.tipo === "pct") return e.pctTxt.trim() === "" ? null : { tipo: "pct", valor: fmt.aNumero(e.pctTxt) };
  const v = fmt.leerClp(e.montoTxt);
  return v == null ? null : { tipo: "monto", valor: v };
};

function errorDe(e, base) {
  const m = manualDe(e);
  if (!m) return null;
  if (m.tipo === "pct" && m.valor > 100) return "No puede pasar de 100 %.";
  if (m.tipo === "monto" && m.valor > base) return `No puede pasar de ${fmt.pesos(base)}.`;
  return null;
}

/* Los dos campos, % y $: escribir en uno calcula el otro sobre `base`. El
   calculado se deriva en cada render, así sigue a la base si cambia. */
function CamposEnlazados({ id, base, valor, onCambiar, autofoco }) {
  const cambiarPct = (txt) => onCambiar({ tipo: "pct", pctTxt: txt.replace(/[^\d.,]/g, ""), montoTxt: "" });
  const cambiarMonto = (txt) => onCambiar({ tipo: "monto", montoTxt: fmt.clp(txt), pctTxt: "" });
  const m = manualDe(valor);
  if (valor.tipo === "pct") {
    valor = { ...valor, montoTxt: m ? fmt.clp(Math.round(montoManual(m, base) ?? 0)) : "" };
  } else if (valor.tipo === "monto") {
    valor = { ...valor, pctTxt: m && base ? fmt.cantidad(unDecimal((m.valor / base) * 100)) : "" };
  }
  return (
    <div className="desc-campos">
      <label className="desc-campo">
        <span>%</span>
        <input className="entrada" id={`${id}-pct`} inputMode="decimal" autoComplete="off" placeholder="0"
               data-autofoco={autofoco || undefined} data-escrito={valor.tipo === "pct" || undefined}
               value={valor.pctTxt} onChange={(e) => cambiarPct(e.target.value)} />
      </label>
      <label className="desc-campo">
        <span>$</span>
        <input className="entrada" id={`${id}-monto`} inputMode="numeric" autoComplete="off" placeholder="$0"
               data-escrito={valor.tipo === "monto" || undefined}
               value={valor.montoTxt} onChange={(e) => cambiarMonto(e.target.value)} />
      </label>
    </div>
  );
}

/* ── Una línea: producto, despacho o instalación ───────────────────────────
   `linea`: { titulo, precio, monto, manual, automatico: {monto, pct, razon} } */
export function DialogoDescuentoLinea({ abierto, linea, onCerrar, onGuardar }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} className="dlg--desenfoque dlg-descuento">
      {linea && <FormularioLinea linea={linea} onCerrar={onCerrar} onGuardar={onGuardar} />}
    </Dialogo>
  );
}

function FormularioLinea({ linea, onCerrar, onGuardar }) {
  // Sin manual, parte del descuento que tiene hoy (el automático), en $.
  const inicial = linea.manual || (linea.monto > 0 ? { tipo: "monto", valor: Math.round(linea.monto) } : null);
  const [valor, setValor] = useState(() => enlazado(inicial, linea.precio));
  const error = errorDe(valor, linea.precio);
  const auto = linea.automatico || {};

  function guardar(e) {
    e.preventDefault();
    if (error) return;
    onGuardar(manualDe(valor) || { tipo: "pct", valor: 0 });
  }

  return (
    <form onSubmit={guardar} noValidate>
      <h2 className="dlg__titulo">Descuento · {linea.titulo}</h2>
      <p className="dlg__texto">Precio {fmt.pesos(linea.precio)}. Escribe el % o los $; el otro se calcula.</p>
      <CamposEnlazados id="desc-linea" base={linea.precio} valor={valor} onCambiar={setValor} autofoco />
      {error && <p className="desc-error">{error}</p>}
      <p className="desc-auto">
        Automático: {auto.monto > 0 ? <>{textoRazon(auto.pct, auto.razon)} · −{fmt.pesos(auto.monto)}</> : "sin descuento"}
      </p>
      <div className="dlg__acciones">
        {linea.manual && (
          <button className="btn btn--fantasma btn--chico desc-volver" type="button" onClick={() => onGuardar(null)}>
            Volver al automático
          </button>
        )}
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit" disabled={!!error}>Guardar</button>
      </div>
    </form>
  );
}

/* ── El pedido entero ──────────────────────────────────────────────────────
   Dos cosas, las dos opcionales (decisión de Bruno):
     · el mismo descuento en todas las líneas: un % se pone tal cual en cada
       una; unos $ se reparten proporcional al precio de cada una. Después
       cualquier línea se puede ajustar suelta.
     · un adicional del pedido, sobre lo que queda después de las líneas.
   `lineas`: [{ clave: "p0" | "despacho" | "instalacion", precio, monto }]
   `pedido`: { manual, base }.
   onGuardar recibe los cambios como los pide guardar_descuentos_cotizacion. */
export function DialogoDescuentoPedido({ abierto, lineas, pedido, onCerrar, onGuardar }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} className="dlg--desenfoque dlg-descuento">
      {abierto && <FormularioPedido lineas={lineas} pedido={pedido} onCerrar={onCerrar} onGuardar={onGuardar} />}
    </Dialogo>
  );
}

export function repartir(lineas, manual) {
  const cambios = { productos: {} };
  const poner = (clave, m) => {
    if (clave.startsWith("p")) cambios.productos[clave.slice(1)] = m;
    else cambios[clave] = m;
  };
  if (manual.tipo === "pct") {
    lineas.forEach((l) => poner(l.clave, { tipo: "pct", valor: manual.valor }));
    return cambios;
  }
  const total = lineas.reduce((s, l) => s + l.precio, 0);
  let resto = Math.min(manual.valor, total);
  lineas.forEach((l, i) => {
    const parte = i === lineas.length - 1 ? resto : Math.round((manual.valor * l.precio) / (total || 1));
    resto -= parte;
    poner(l.clave, { tipo: "monto", valor: Math.max(0, parte) });
  });
  return cambios;
}

function FormularioPedido({ lineas, pedido, onCerrar, onGuardar }) {
  const totalLineas = lineas.reduce((s, l) => s + l.precio, 0);
  const [todas, setTodas] = useState(() => enlazado(null, totalLineas));
  const manualTodas = manualDe(todas);
  // El adicional va sobre lo que queda: con el reparto nuevo, si lo hay.
  const baseAdicional = manualTodas
    ? totalLineas - (montoManual(manualTodas, totalLineas) ?? 0)
    : pedido?.base ?? totalLineas;
  const [adicional, setAdicional] = useState(() => enlazado(pedido?.manual, baseAdicional));
  const errorTodas = errorDe(todas, totalLineas);
  const errorAdicional = errorDe(adicional, baseAdicional);
  const hayError = !!(errorTodas || errorAdicional);

  function guardar(e) {
    e.preventDefault();
    if (hayError) return;
    const cambios = manualTodas ? repartir(lineas, manualTodas) : {};
    cambios.pedido = manualDe(adicional);
    onGuardar(cambios);
  }

  return (
    <form onSubmit={guardar} noValidate>
      <h2 className="dlg__titulo">Descuento del pedido</h2>

      <section className="desc-seccion">
        <h3 className="desc-seccion__titulo">El mismo descuento en todas las líneas</h3>
        <p className="dlg__texto">
          Reemplaza el de cada producto{lineas.some((l) => !l.clave.startsWith("p")) ? ", del despacho y de la instalación" : ""}.
          Unos $ se reparten según el precio de cada uno. Vacío, no cambia nada.
        </p>
        <CamposEnlazados id="desc-todas" base={totalLineas} valor={todas} onCambiar={setTodas} autofoco />
        {errorTodas && <p className="desc-error">{errorTodas}</p>}
      </section>

      <section className="desc-seccion">
        <h3 className="desc-seccion__titulo">Descuento adicional</h3>
        <p className="dlg__texto">
          Sobre lo que queda después de los descuentos de cada línea ({fmt.pesos(baseAdicional)}). Vacío, sin adicional.
        </p>
        <CamposEnlazados id="desc-adicional" base={baseAdicional} valor={adicional} onCambiar={setAdicional} />
        {errorAdicional && <p className="desc-error">{errorAdicional}</p>}
      </section>

      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit" disabled={hayError}>Guardar</button>
      </div>
    </form>
  );
}

/* ── Restablecer ─────────────────────────────────────────────────────────── */
export function DialogoRestablecer({ abierto, onCerrar, onConfirmar }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} onConfirmar={onConfirmar} className="dlg--desenfoque dlg-descuento">
      <h2 className="dlg__titulo">¿Restablecer los descuentos?</h2>
      <p className="dlg__texto">
        Se quitan todos los descuentos puestos a mano (de los productos, del despacho, de la instalación y del
        pedido) y se vuelven a calcular los automáticos: el del contacto o el de volumen.
      </p>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="button" onClick={onConfirmar} data-autofoco>Restablecer</button>
      </div>
    </Dialogo>
  );
}
