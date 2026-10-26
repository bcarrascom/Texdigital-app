import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { api } from "@/services/api";
import { useAvisos } from "@/context/AvisosContext";
import { useAtajo } from "@/hooks/useAtajo";
import { useVolver } from "@/hooks/useVolver";
import { rutas } from "@/router/rutas";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Cargando from "@/components/Cargando/Cargando";
import ZonaDatos from "./ZonaDatos";
import Mapa from "./Mapa";
import PanelProducto from "./PanelProducto";
import Resumen from "./Resumen";
import { DialogoMateriales, DialogoQuitar } from "./DialogosNuevaCotizacion";
import { completo, esVacio, firma, normalizar, productoVacio } from "./producto";
import * as fmt from "@/utils/formato";
import "./NuevaCotizacion.css";

/* ═══════════════════════════════════════════════════════════════════════════
   Nueva cotización — "la pizarra". Una sola superficie continua por la que
   la vista se mueve, en vez de una pantalla por paso:

     ┌─ zona 0 ─────────────────────────────┐
     │  [ trabajo + documento ] [ cliente ]  │   ← arriba
     └──────────────────────────────────────┘
     ┌─ zona 1 ─────────────────────────────┐
     │  mapa fijo:  1  2  3  +   │  Resumen  │
     │  ┌────────┐┌────────┐┌────────┐       │   ← abajo, se mueve de lado
     │  │ prod 1 ││ prod 2 ││ resumen│  ...  │
     └──────────────────────────────────────┘

   Los dos movimientos son el mismo truco (ver NuevaCotizacion.css): un
   contenedor más grande que su marco, corrido con translate. Vertical =
   --zona, horizontal = --p.

   Tres entradas, la misma página (ver router/rutas.js):
     /cotizaciones/nueva              una nueva
     /cotizaciones/:numero/editar     editar una guardada
     /cotizaciones/pendientes/:id     retomar una incompleta
   ═══════════════════════════════════════════════════════════════════════════ */

const CLIENTE_VACIO = {
  empresa: "", rut: "", razon_social: "", contacto: "", email: "",
  descuento: "0", condicion: "", fecha: "", numero: "", descripcion: "",
};
const SIN_EXTRA = { marcado: false, texto: "" };
// Se recalcula con retardo, para no llamar a Python en cada tecla.
const RETARDO_CALCULO_MS = 140;
const RETARDO_NUMERO_MS = 250;

const montoDe = (extra) => (extra.marcado ? parseFloat(fmt.soloDigitos(extra.texto)) || 0 : null);
const extraDe = (monto) => (monto != null ? { marcado: true, texto: String(monto) } : SIN_EXTRA);

/* Carga los catálogos y el punto de partida (vacía, la guardada a editar o
   la pendiente a retomar) y recién ahí monta la pizarra, ya con todo. */
export default function NuevaCotizacion({ modo = "nueva" }) {
  const { numero: numeroRuta, id: idRuta } = useParams();
  const [inicio, setInicio] = useState(null);

  useEffect(() => {
    let vigente = true;
    setInicio(null);
    const argumentos = modo === "editar" ? { editar: Number(numeroRuta) }
                     : modo === "pendiente" ? { pendiente: idRuta } : {};
    Promise.all([api.obtener_catalogos(), api.obtener_contexto("nueva-cotizacion", argumentos)])
      .then(([catalogos, ctx]) => {
        if (!vigente) return;
        const cat = catalogos || {};
        // Retomar una pendiente / editar: Python manda el estado tal cual.
        const base = ctx?.estado || {};
        let productos = (base.productos || []).map((p) => normalizar({ ...productoVacio(p.tipo), ...p }, cat));
        if (!productos.length) productos = [normalizar(productoVacio(), cat)];
        const cliente = { ...CLIENTE_VACIO, ...base.cliente };
        if (!cliente.numero && ctx?.numero_sugerido) cliente.numero = ctx.numero_sugerido;
        if (!cliente.fecha && ctx?.fecha_iso) cliente.fecha = ctx.fecha_iso;
        setInicio({
          cat,
          estado: { id: base.id ?? null, nombre_trabajo: base.nombre_trabajo || "", cliente, productos },
          extras: { despacho: extraDe(base.despacho), instalacion: extraDe(base.instalacion) },
          numeroEditando: ctx?.numero_editando || null,
        });
      });
    return () => { vigente = false; };
  }, [modo, numeroRuta, idRuta]);

  if (!inicio) {
    return (
      <Pagina tema="cotizaciones" titulo="Nueva cotización">
        <Cabecera titulo="Nueva cotización" />
        <Cargando />
      </Pagina>
    );
  }
  return <Pizarra {...inicio} />;
}

function Pizarra({ cat, estado: estadoInicial, extras: extrasIniciales, numeroEditando }) {
  const navigate = useNavigate();
  const location = useLocation();
  const volverAtras = useVolver();
  const aviso = useAvisos();

  const [estado, setEstado] = useState(estadoInicial);   // { id, nombre_trabajo, cliente, productos }
  const [extras, setExtras] = useState(extrasIniciales);
  const [cantidadTexto, setCantidadTexto] = useState(String(estadoInicial.productos.length));
  const [zona, setZona] = useState(0);
  const [actual, setActual] = useState(0);      // índice de producto, o "resumen"
  const [guardadoEn, setGuardadoEn] = useState("");
  const [faltanMateriales, setFaltanMateriales] = useState(false);
  const [quitando, setQuitando] = useState(null);
  const [faltantesDialogo, setFaltantesDialogo] = useState(null);

  /* N° de cotización: null = todavía no se confirmó contra Python (recién
     tipeado, o esperando la respuesta) — cuenta como "no ok". El número con
     el que arrancó esta pantalla (editando) no cuenta como choque. */
  const [numeroDisponible, setNumeroDisponible] = useState(null);

  const nombreRef = useRef(null);
  const paneles = useRef([]);
  const decidir = useRef(null);
  const guardando = useRef(false);

  useEffect(() => { nombreRef.current?.focus(); }, []);

  // ── Cálculo en vivo ──────────────────────────────────────────────────────
  /* TODO número sale de Python (precios, ML, M², materiales de la caja, el
     aviso de ancho máximo). Se recalcula SIEMPRE la cotización entera, no el
     producto que se tocó: el piso mínimo de facturación es por grupo de
     textil (ver core/precios.py), así que cambiar un producto puede cambiarle
     el precio a otro del mismo textil. Si mientras Python calculaba algo
     cambió, la respuesta ya es vieja y se descarta (viene otra detrás). */
  const firmaActual = firma(estado.productos);
  useEffect(() => {
    const pedida = firmaActual;
    const t = setTimeout(async () => {
      const calcs = (await api.calcular_productos(estado.productos)) || [];
      setEstado((e) => (firma(e.productos) !== pedida ? e : {
        ...e, productos: e.productos.map((p, i) => ({ ...p, calc: calcs[i] || null })),
      }));
    }, RETARDO_CALCULO_MS);
    return () => clearTimeout(t);
  }, [firmaActual]);  // solo cuando cambia algo que afecta el cálculo

  /* El aviso "Materiales insuficientes" del resumen: se consulta al llegar al
     resumen y cada vez que cambian los productos estando ahí. */
  const enResumen = actual === "resumen";
  useEffect(() => {
    if (!enResumen) return;
    let vigente = true;
    api.verificar_materiales(estado.productos).then((f) => vigente && setFaltanMateriales((f || []).length > 0));
    return () => { vigente = false; };
  }, [enResumen, firmaActual]);

  // ── N° de cotización: disponibilidad en vivo ─────────────────────────────

  const numero = estado.cliente.numero || "";
  const numeroCompleto = /^\d{4}$/.test(numero);
  useEffect(() => {
    setNumeroDisponible(null);
    if (!numeroCompleto) return;
    if (numero === numeroEditando) { setNumeroDisponible(true); return; }
    let vigente = true;
    // El formato se revisa al toque; la disponibilidad, con retardo.
    const t = setTimeout(async () => {
      const disponible = await api.numero_disponible(numero, numeroEditando);
      if (vigente) setNumeroDisponible(!!disponible);
    }, RETARDO_NUMERO_MS);
    return () => { vigente = false; clearTimeout(t); };
  }, [numero, numeroCompleto]);

  // ── Navegación dentro de la pizarra ──────────────────────────────────────

  const enfocarPanel = useCallback((destino) => {
    const panel = paneles.current[destino === "resumen" ? paneles.current.length - 1 : destino];
    panel?.querySelector("input:not([type=radio]), select")?.focus({ preventScroll: true });
  }, []);

  function irAZona(z) {
    setZona(z);
    if (z === 1) setTimeout(() => enfocarPanel(actual), 260);
  }

  function irA(destino) {
    setActual(destino);
    setTimeout(() => enfocarPanel(destino), 120);
  }

  /* Desde los productos, "Volver" sube a la zona de datos — no sale de la
     pantalla, el estado no se pierde. Recién desde ahí se va. */
  function volver() {
    if (zona === 1) irAZona(0);
    else volverAtras();
  }

  const productos = estado.productos;
  const indiceCarril = actual === "resumen" ? productos.length : actual;

  // ── Cambios de estado ────────────────────────────────────────────────────

  const cambiarEstado = (cambios) => setEstado((e) => ({ ...e, ...cambios }));
  const cambiarCliente = (cambios) => setEstado((e) => ({ ...e, cliente: { ...e.cliente, ...cambios } }));
  const cambiarProductos = (fn) => setEstado((e) => ({ ...e, productos: fn(e.productos) }));
  const cambiarProducto = (i, cambios) =>
    cambiarProductos((lista) => lista.map((p, j) => (j === i ? { ...p, ...cambios } : p)));

  /* Las cotizaciones mixtas existen pero son la excepción: los productos que
     siguen a este y todavía están sin tocar (ver esVacio) heredan el tipo. Se
     corta apenas aparece uno que ya tiene algo cargado. */
  function cambiarTipo(i, tipo) {
    cambiarProductos((lista) => {
      const nueva = lista.map((p, j) => (j === i ? normalizar({ ...p, tipo }, cat) : p));
      for (let j = i + 1; j < nueva.length && esVacio(nueva[j], cat); j++) nueva[j] = { ...nueva[j], tipo };
      return nueva;
    });
  }

  const nuevoProducto = (lista) => normalizar(productoVacio(lista.length ? lista[lista.length - 1].tipo : "estandar"), cat);

  function fijarProductos(lista) {
    cambiarProductos(() => lista);
    setCantidadTexto(String(lista.length));
  }

  function agregarProducto() {
    fijarProductos([...productos, nuevoProducto(productos)]);
    irA(productos.length);
  }

  function duplicarProducto(i) {
    const copia = { ...structuredClone(productos[i]), calc: null };
    fijarProductos([...productos.slice(0, i + 1), copia, ...productos.slice(i + 1)]);
    irA(i + 1);
  }

  function pedirQuitar(i) {
    if (productos.length <= 1) {
      aviso("La cotización tiene que tener al menos un producto.", "aviso");
      return;
    }
    setQuitando(i);
  }

  function quitarProducto() {
    const i = quitando;
    setQuitando(null);
    fijarProductos(productos.filter((_, j) => j !== i));
    irA(Math.min(i, productos.length - 2));
  }

  /* El número de productos de la zona de datos manda: agrega vacíos (del
     tipo del último) o saca los del final. */
  function cambiarCantidad(texto) {
    setCantidadTexto(texto);
    const n = Math.max(1, parseInt(texto, 10) || 1);
    cambiarProductos((lista) => {
      const nueva = lista.slice(0, n);
      while (nueva.length < n) nueva.push(nuevoProducto(nueva));
      return nueva;
    });
    if (typeof actual === "number" && actual >= n) setActual(n - 1);
  }

  function cambiarExtra(clave, cambios, enfocar) {
    setExtras((x) => ({ ...x, [clave]: { ...x[clave], ...cambios } }));
    if (enfocar) setTimeout(() => document.getElementById(`${clave}-monto`)?.focus(), 0);
  }

  // ── Validación de la zona de datos ───────────────────────────────────────
  /* N° y Empresa se revisan ACÁ, antes de dejar bajar a productos — no recién
     al guardar: si estaban mal, el usuario habría cargado TODOS los productos
     para nada. */

  const numeroOk = numeroCompleto && numeroDisponible === true;
  const empresaOk = estado.cliente.empresa.trim() !== "";
  const puedeBajar = estado.nombre_trabajo.trim() !== "" && productos.length > 0 && numeroOk && empresaOk;
  const faltan = [];
  if (!estado.nombre_trabajo.trim()) faltan.push("el nombre del trabajo");
  if (!numeroCompleto) faltan.push("el N° de cotización");
  else if (numeroDisponible !== true) faltan.push("un N° de cotización disponible");
  if (!empresaOk) faltan.push("la empresa");
  // Solo un N° completo y tomado es un error (rojo): uno a medio tipear es
  // simplemente "todavía no", y eso ya lo dice la nota de abajo.
  const errorNumero = numeroCompleto && numeroDisponible === false ? "Ese N° de cotización ya está en uso." : "";

  // ── Guardado ─────────────────────────────────────────────────────────────

  const paraPython = () => ({
    ...estado, despacho: montoDe(extras.despacho), instalacion: montoDe(extras.instalacion), actual,
  });

  async function guardarProgreso() {
    const r = (await api.guardar_progreso(paraPython())) || {};
    if (r.id) cambiarEstado({ id: r.id });
    if (r.guardado_en) setGuardadoEn("Guardado " + r.guardado_en);
    aviso(`Progreso guardado — ${productos.filter(completo).length} de ${productos.length} productos completos.`, "info");
    return r.id;
  }

  /* El diálogo de materiales devuelve una promesa con lo que se eligió. */
  const pedirDecision = (faltantes) => new Promise((resolver) => {
    decidir.current = resolver;
    setFaltantesDialogo(faltantes);
  });
  function alDecidir(decision) {
    setFaltantesDialogo(null);
    decidir.current?.(decision);
    decidir.current = null;
  }

  /* Si se llegó desde el listado del módulo, se vuelve a él; si no, se lo
     pone en lugar de esta pantalla (igual que al eliminar, ver VerCotizacion). */
  function irAlListado() {
    if (location.state?.desde === rutas.cotizaciones()) navigate(-1);
    else navigate(rutas.cotizaciones(), { replace: true });
  }

  async function guardarCotizacion(abrir) {
    if (guardando.current) return;
    const incompletos = productos.filter((p) => !completo(p)).length;
    if (incompletos) {
      aviso(`Falta completar ${incompletos} producto${incompletos > 1 ? "s" : ""}.`, "error");
      return;
    }
    if (!numeroCompleto) {
      aviso("El N° de cotización tiene que tener 4 dígitos.", "error");
      irAZona(0);
      setTimeout(() => document.getElementById("numero")?.focus(), 0);
      return;
    }
    if (!empresaOk) {
      aviso("Falta la empresa.", "error");
      irAZona(0);
      setTimeout(() => document.getElementById("empresa")?.focus(), 0);
      return;
    }

    /* Stock insuficiente no bloquea guardar, solo avisa: lo que se elija
       DENTRO del diálogo pisa el botón que se apretó primero. */
    const faltantes = (await api.verificar_materiales(productos)) || [];
    if (faltantes.length) {
      const decision = await pedirDecision(faltantes);
      if (decision === "cancelar") return;
      if (decision === "progreso") { await guardarProgreso(); return; }
      abrir = decision === "guardar-abrir";
    }

    guardando.current = true;
    const r = (await api.guardar_cotizacion(paraPython(), !!abrir)) || {};
    guardando.current = false;
    if (r.error) { aviso(r.error, "error", 8000); return; }
    aviso(`Cotización ${fmt.numero(r.numero ?? numero)} guardada.`, "info");
    irAlListado();
  }

  /* "+ Nuevo rollo" desde el diálogo de materiales: se guarda el progreso y
     esta entrada del historial pasa a ser la de ESE borrador — así "Volver"
     desde Inventario reabre la cotización tal como quedó. */
  async function nuevoRollo(textil) {
    const id = await guardarProgreso();
    alDecidir("cancelar");
    if (id) navigate(rutas.retomarPendiente(id), { replace: true, state: location.state });
    navigate(rutas.inventario({ nuevo_textil: textil }));
  }

  // ── Atajos ───────────────────────────────────────────────────────────────

  const siguiente = () => irA(actual < productos.length - 1 ? actual + 1 : "resumen");
  useAtajo("mod+s", guardarProgreso);
  useAtajo("enter", () => {
    if (zona === 0) { if (puedeBajar) irAZona(1); return; }
    if (actual !== "resumen") siguiente();
  });
  // Con Ctrl, no a secas: las flechas solas mueven el cursor en los campos.
  useAtajo("mod+arrowright", () => { if (zona === 1 && actual !== "resumen") siguiente(); });
  useAtajo("mod+arrowleft", () => {
    if (zona !== 1) return;
    if (actual === "resumen") irA(productos.length - 1);
    else if (actual > 0) irA(actual - 1);
    else irAZona(0);
  });

  const titulo = estado.nombre_trabajo.trim() || "Nueva cotización";

  return (
    <Pagina tema="cotizaciones" titulo={titulo} className="pag-nueva-cotizacion">
      <Cabecera titulo={titulo} onVolver={volver}>
        <span className="barra__guardado">{guardadoEn}</span>
        <button className="cab-btn" title="Ctrl + S" onClick={guardarProgreso}>💾 Guardar progreso</button>
      </Cabecera>

      <div className="escena">
        <div className="lienzo" data-zona={zona} style={{ "--zona": zona }}>
          <ZonaDatos
            ref={nombreRef}
            nombre={estado.nombre_trabajo} onNombre={(v) => cambiarEstado({ nombre_trabajo: v })}
            cantidad={cantidadTexto} onCantidad={cambiarCantidad}
            extras={extras} onExtra={cambiarExtra}
            cliente={estado.cliente} onCliente={cambiarCliente}
            errorNumero={errorNumero} cat={cat}
            nota={faltan.length ? `Falta ${faltan.join(", ")}.` : ""}
            puedeBajar={puedeBajar} onBajar={() => irAZona(1)}
            onGuardarCliente={async () => {
              const c = estado.cliente;
              if (!c.empresa.trim()) { aviso("El campo Empresa es obligatorio para guardar.", "error"); return; }
              const r = await api.guardar_cliente(c.empresa, c.rut, c.razon_social);
              if (r?.ok) aviso("Cliente guardado.", "info");
              else aviso(r?.error || "No se pudo guardar el cliente.", "error", 6000);
            }}
            onGuardarContacto={async () => {
              const c = estado.cliente;
              if (!c.contacto.trim()) { aviso("Escribí un contacto antes de guardarlo.", "error"); return; }
              await api.guardar_contacto(c.contacto, c.email, c.descuento, c.condicion);
              aviso("Contacto guardado.", "info");
            }}
          />

          <section className="zona productos">
            <Mapa productos={productos} actual={actual} onIr={irA} onAgregar={agregarProducto} />
            <div className="carril-marco">
              <div className="carril" style={{ "--p": indiceCarril }}>
                {productos.map((p, i) => (
                  <PanelProducto
                    key={i} ref={(el) => { paneles.current[i] = el; }}
                    p={p} i={i} total={productos.length} cat={cat}
                    onCambiar={(cambios) => cambiarProducto(i, cambios)}
                    onTipo={(tipo) => cambiarTipo(i, tipo)}
                    onDuplicar={() => duplicarProducto(i)}
                    onQuitar={() => pedirQuitar(i)}
                    onSiguiente={() => irA(i + 1 < productos.length ? i + 1 : "resumen")}
                    onNuevoRollo={nuevoRollo}
                  />
                ))}
                <Resumen
                  ref={(el) => { paneles.current[productos.length] = el; paneles.current.length = productos.length + 1; }}
                  productos={productos}
                  despacho={montoDe(extras.despacho)} instalacion={montoDe(extras.instalacion)}
                  faltanMateriales={faltanMateriales}
                  onIr={irA} onQuitar={pedirQuitar} onAgregar={agregarProducto} onGuardar={guardarCotizacion}
                />
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* Catálogos compartidos por todos los paneles */}
      <Datalist id="lista-productos" valores={cat.productos} />
      <Datalist id="lista-textiles" valores={cat.textiles} />
      <Datalist id="lista-estructuras" valores={cat.estructuras} />
      <Datalist id="lista-terminaciones" valores={cat.terminaciones} />
      <Datalist id="lista-empresas" valores={(cat.clientes || []).map((c) => c.empresa)} />
      <Datalist id="lista-contactos" valores={(cat.contactos || []).map((c) => c.contacto)} />

      <DialogoQuitar indice={quitando} onCerrar={() => setQuitando(null)} onConfirmar={quitarProducto} />
      <DialogoMateriales faltantes={faltantesDialogo} onDecidir={alDecidir} onNuevoRollo={nuevoRollo} />
    </Pagina>
  );
}

function Datalist({ id, valores }) {
  return (
    <datalist id={id}>
      {(valores || []).map((v) => <option key={v} value={v} />)}
    </datalist>
  );
}
