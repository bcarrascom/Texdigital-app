import { useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router";
import { motion } from "motion/react";
import { api } from "@/services/api";
import { rutas } from "@/router/rutas";
import { useDatos } from "@/hooks/useDatos";
import { useAvisos } from "@/context/AvisosContext";
import Cargando from "@/components/Cargando/Cargando";
import Campo from "@/components/Campo/Campo";
import Dialogo from "@/components/Dialogo/Dialogo";
import Segmento from "@/components/Segmento/Segmento";
import NavFlotante from "@/components/NavFlotante/NavFlotante";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import IconoCotizaciones from "@/assets/svg/file-text.svg?react";
import IconoOps from "@/assets/svg/clipboard-list.svg?react";
import IconoCarpeta from "@/assets/svg/folder-open.svg?react";
import IconoHistorial from "@/assets/svg/history.svg?react";
import IconoClientes from "@/assets/svg/users.svg?react";
import IconoCorreo from "@/assets/svg/mail.svg?react";
import IconoCheck from "@/assets/svg/check.svg?react";
import IconoEliminar from "@/assets/svg/trash-2.svg?react";
import IconoMas from "@/assets/svg/plus.svg?react";
import { BarraGuardar, Fila, Grupo, NotaSoloLectura } from "./Ajustes";
import { useCambiosPendientes } from "./cambiosPendientes";
import { correoValido } from "@/utils/formato";
import HistorialCorreos from "./HistorialCorreos";

/* Configuración › Correos (pedido de Bruno, 2026-11-09; ver core/correos.py
   y CLAUDE.md, "Correos automáticos"). Dos partes (orden de Bruno, 2026-11-11):
     · arriba, lo global del correo de la app: la cuenta (sistema@texdigital.cl)
       y su contraseña, el correo de prueba y la carpeta, y el modo de prueba;
     · abajo, lo de cada parte del programa, con el menú flotante
       (components/NavFlotante): Cotizaciones y OPs (a quién le llegan;
       todavía no se envían). Cotizaciones tiene dos correos distintos (Bruno,
       2026-11-11), cada uno con su lista, asunto y mensaje:
         · el aviso de cotización nueva, a la gente de Texdigital, al crearla;
         · el correo al cliente ("Enviar correo"), con su copia a Texdigital. La sección elegida va en la URL
       (?seccion=ops), para que un botón de otro módulo pueda abrirla.
   Los correos automáticos (el aviso de cotización nueva, y las OPs cuando
   se conecten) se apagan con el switch general de arriba y con el de cada
   sección (Bruno, 2026-11-11). Los que se mandan a mano no dependen de ellos.
   Se edita entera y se guarda con la barra de abajo, como las Reglas: los
   cambios de las dos secciones van juntos.

   La contraseña de la casilla NO es un ajuste de la Dropbox: se guarda en
   este computador (Administrador de credenciales / Llavero), con su propio
   diálogo, y se prueba contra el servidor antes de guardarla. Cada correo que
   sale deja una copia .eml en la carpeta Correos. */

/* Las listas de correos de cada área que esta página muestra. Inventario y
   Despachos siguen en correos.json (core.correos.AREAS) pero no se muestran
   todavía; guardar no las toca. */
const AREAS = [{ clave: "ops", titulo: "OPs" }];

const SECCIONES = [
  { clave: "cotizaciones", etiqueta: "Cotizaciones", Icono: IconoCotizaciones },
  { clave: "ops", etiqueta: "OPs", Icono: IconoOps },
];
const FUNDIDO = { duration: 0.18, ease: [0.22, 1, 0.36, 1] };

const PRUEBA = [{ valor: true, etiqueta: "Encendido" }, { valor: false, etiqueta: "Apagado" }];
const ENCENDIDOS = [{ valor: true, etiqueta: "Encendidos" }, { valor: false, etiqueta: "Apagados" }];
const ACTIVADOS = [{ valor: true, etiqueta: "Activados" }, { valor: false, etiqueta: "Desactivados" }];

const aBorrador = (a) => ({
  remitente: a.cuenta.remitente, nombre: a.cuenta.nombre, servidor: a.cuenta.servidor, puerto: String(a.cuenta.puerto ?? ""),
  pruebaActivo: !!a.prueba.activo, pruebaDireccion: a.prueba.direccion || "",
  alCliente: !!a.cotizaciones.al_cliente, asunto: a.cotizaciones.asunto, mensaje: a.cotizaciones.mensaje,
  copia: a.cotizaciones.copia.map((f) => ({ ...f })),
  nuevasAsunto: a.cotizaciones_nuevas.asunto, nuevasMensaje: a.cotizaciones_nuevas.mensaje,
  opsAsunto: a.ops.asunto, opsMensaje: a.ops.mensaje,
  recAsunto: a.ops_recotizada.asunto, recMensaje: a.ops_recotizada.mensaje,
  nuevasPara: a.cotizaciones_nuevas.para.map((f) => ({ ...f })),
  autoActivo: !!a.automaticos.activo, autoCotizaciones: !!a.automaticos.cotizaciones, autoOps: !!a.automaticos.ops,
  areas: Object.fromEntries(AREAS.map(({ clave }) => [clave, (a.areas[clave] || []).map((f) => ({ ...f }))])),
});

const desdeBorrador = (b) => ({
  cuenta: { remitente: b.remitente.trim(), nombre: b.nombre.trim(), servidor: b.servidor.trim(), puerto: b.puerto.trim() },
  prueba: { activo: b.pruebaActivo, direccion: b.pruebaDireccion.trim() },
  cotizaciones: { al_cliente: b.alCliente, asunto: b.asunto, mensaje: b.mensaje, copia: b.copia },
  cotizaciones_nuevas: { asunto: b.nuevasAsunto, mensaje: b.nuevasMensaje, para: b.nuevasPara },
  ops: { asunto: b.opsAsunto, mensaje: b.opsMensaje },
  ops_recotizada: { asunto: b.recAsunto, mensaje: b.recMensaje },
  automaticos: { activo: b.autoActivo, cotizaciones: b.autoCotizaciones, ops: b.autoOps },
  areas: b.areas,
});

/* Misma regla que core.correos.validar: {campo: mensaje}. */
function validar(b) {
  const e = {};
  if (!correoValido(b.remitente)) e["cuenta.remitente"] = "El correo no es válido.";
  if (!b.nombre.trim()) e["cuenta.nombre"] = "Falta el nombre.";
  if (!b.servidor.trim()) e["cuenta.servidor"] = "Falta el servidor.";
  const puerto = Number(b.puerto);
  if (!(Number.isInteger(puerto) && puerto > 0 && puerto < 65536)) e["cuenta.puerto"] = "Un número entre 1 y 65535.";
  if (b.pruebaActivo && !correoValido(b.pruebaDireccion)) e["prueba.direccion"] = "El correo no es válido.";
  if (!b.asunto.trim()) e["cotizaciones.asunto"] = "Falta el asunto.";
  if (!b.mensaje.trim()) e["cotizaciones.mensaje"] = "Falta el mensaje.";
  if (!b.nuevasAsunto.trim()) e["cotizaciones_nuevas.asunto"] = "Falta el asunto.";
  if (!b.nuevasMensaje.trim()) e["cotizaciones_nuevas.mensaje"] = "Falta el mensaje.";
  if (!b.opsAsunto.trim()) e["ops.asunto"] = "Falta el asunto.";
  if (!b.opsMensaje.trim()) e["ops.mensaje"] = "Falta el mensaje.";
  if (!b.recAsunto.trim()) e["ops_recotizada.asunto"] = "Falta el asunto.";
  if (!b.recMensaje.trim()) e["ops_recotizada.mensaje"] = "Falta el mensaje.";
  const lista = (filas, clave) => {
    const vistos = new Set();
    filas.forEach((f, i) => {
      const c = f.correo.trim().toLowerCase();
      if (!correoValido(c)) e[`${clave}:${i}`] = "El correo no es válido.";
      else if (vistos.has(c)) e[`${clave}:${i}`] = "Ese correo ya está en la lista.";
      vistos.add(c);
    });
  };
  lista(b.copia, "cotizaciones.copia");
  lista(b.nuevasPara, "cotizaciones_nuevas.para");
  AREAS.forEach(({ clave }) => lista(b.areas[clave], `areas.${clave}`));
  return e;
}

const correosTexto = (filas) => filas.map((f) => f.correo || "?").join(", ") || "ninguno";
function describirCambios(o, a) {
  const c = [];
  const campo = (et, x, y) => { if (x !== y) c.push(`${et}: ${x || "vacío"} → ${y || "vacío"}`); };
  campo("Correo de la app", o.remitente, a.remitente);
  campo("Nombre que se ve", o.nombre, a.nombre);
  campo("Servidor", o.servidor, a.servidor);
  campo("Puerto", o.puerto, a.puerto);
  if (o.pruebaActivo !== a.pruebaActivo) c.push(`Modo de prueba: ${a.pruebaActivo ? "encendido" : "apagado"}`);
  const auto = (et, x, y) => { if (x !== y) c.push(`${et}: ${y ? "encendidos" : "apagados"}`); };
  auto("Correos automáticos", o.autoActivo, a.autoActivo);
  auto("Correos automáticos de cotizaciones", o.autoCotizaciones, a.autoCotizaciones);
  auto("Correos automáticos de OPs", o.autoOps, a.autoOps);
  campo("Dirección de prueba", o.pruebaDireccion, a.pruebaDireccion);
  if (JSON.stringify(o.nuevasPara) !== JSON.stringify(a.nuevasPara)) {
    c.push(`Reciben las cotizaciones nuevas: ${correosTexto(o.nuevasPara)} → ${correosTexto(a.nuevasPara)}`);
  }
  campo("Asunto del aviso de cotización nueva", o.nuevasAsunto, a.nuevasAsunto);
  if (o.nuevasMensaje !== a.nuevasMensaje) c.push("Mensaje del aviso de cotización nueva");
  campo("Asunto del correo de la OP", o.opsAsunto, a.opsAsunto);
  if (o.opsMensaje !== a.opsMensaje) c.push("Mensaje del correo de la OP");
  campo("Asunto del aviso de OP recotizada", o.recAsunto, a.recAsunto);
  if (o.recMensaje !== a.recMensaje) c.push("Mensaje del aviso de OP recotizada");
  if (o.alCliente !== a.alCliente) c.push(`Correos a clientes: ${a.alCliente ? "activados" : "desactivados"}`);
  campo("Asunto del correo al cliente", o.asunto, a.asunto);
  if (o.mensaje !== a.mensaje) c.push("Mensaje del correo al cliente");
  if (JSON.stringify(o.copia) !== JSON.stringify(a.copia)) c.push(`Copia del correo al cliente: ${correosTexto(o.copia)} → ${correosTexto(a.copia)}`);
  AREAS.forEach(({ clave, titulo }) => {
    if (JSON.stringify(o.areas[clave]) !== JSON.stringify(a.areas[clave])) {
      c.push(`${titulo}: ${correosTexto(o.areas[clave])} → ${correosTexto(a.areas[clave])}`);
    }
  });
  return c;
}

export default function Correos() {
  const aviso = useAvisos();
  const navigate = useNavigate();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const seccion = SECCIONES.some((s) => s.clave === params.get("seccion")) ? params.get("seccion") : SECCIONES[0].clave;
  const elegirSeccion = (clave) => setParams({ seccion: clave }, { replace: true, state: location.state });
  const { datos, cargando, recargar } = useDatos(() => api.obtener_ajustes_correos(), []);
  const [borrador, setBorrador] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [pidiendo, setPidiendo] = useState(false);   // el diálogo de la contraseña
  const [viendoHistorial, setViendoHistorial] = useState(false);
  const [probando, setProbando] = useState(false);
  // Por plantilla, adónde va una variable (el último campo que se tocó de los dos).
  const ultimoCampo = useRef({ nuevasMensaje: "nuevasMensaje", mensaje: "mensaje", opsMensaje: "opsMensaje", recMensaje: "recMensaje" });

  const original = useMemo(() => (datos ? aBorrador(datos.ajustes) : null), [datos]);
  const actual = borrador || original;
  const errores = useMemo(() => (actual ? validar(actual) : {}), [actual]);
  const cantidadErrores = Object.keys(errores).length;
  const textoError = cantidadErrores
    ? (cantidadErrores === 1 ? "hay 1 dato que no es válido." : `hay ${cantidadErrores} datos que no son válidos.`) : null;
  useCambiosPendientes({
    cambios: borrador && original ? describirCambios(original, borrador) : [],
    error: textoError,
    guardar,
  });
  if (cargando || !actual) return <Cargando />;

  const soloLectura = datos.solo_lectura;
  const hayCambios = JSON.stringify(actual) !== JSON.stringify(original);
  const cambiar = (cambio) => setBorrador({ ...actual, ...cambio });

  async function guardar() {
    if (cantidadErrores || guardando) return false;
    setGuardando(true);
    try {
      const r = await api.guardar_ajustes_correos(desdeBorrador(actual));
      if (!r?.ok) {
        aviso(r?.errores?.general || Object.values(r?.errores || {})[0] || "No se pudo guardar.", "error");
        return false;
      }
      await recargar();
      setBorrador(null);
      aviso("Ajustes de correos guardados.", "info");
      return true;
    } finally {
      setGuardando(false);
    }
  }

  /* Tocar una variable la escribe donde estaba el cursor, en el asunto o el
     mensaje de esa plantilla (el último de los dos que se usó). `plantilla`
     es el campo del mensaje: "mensaje" (al cliente) o "nuevasMensaje". */
  function insertarVariable(plantilla, clave) {
    const texto = `{${clave}}`;
    const nombre = ultimoCampo.current[plantilla];
    const campo = document.getElementById(`correo-${nombre}`);
    const valor = actual[nombre];
    const ini = campo?.selectionStart ?? valor.length;
    const fin = campo?.selectionEnd ?? valor.length;
    cambiar({ [nombre]: valor.slice(0, ini) + texto + valor.slice(fin) });
    requestAnimationFrame(() => { campo?.focus(); campo?.setSelectionRange(ini + texto.length, ini + texto.length); });
  }

  /* Ir a Clientes y contactos: con cambios sin guardar, primero hay que
     guardarlos o descartarlos (la página no puede preguntar por su cuenta). */
  function irAClientes(lista, correo) {
    if (hayCambios) { aviso("Guarda o descarta los cambios antes de salir de Correos.", "error"); return; }
    navigate(`${rutas.configuracion("clientes")}?lista=${lista}&correo=${correo}`, { replace: true, state: location.state });
  }

  const conClave = datos.contrasena_guardada;

  async function correoDePrueba() {
    if (probando) return;
    setProbando(true);
    try {
      const r = await api.enviar_correo_de_prueba();
      // Si salió, la animación y el aviso "Enviado a …" los muestra components/CorreoEnviado.
      if (!r?.ok) aviso(r?.error || "No se pudo enviar.", "error", 8000);
    } finally {
      setProbando(false);
    }
  }

  async function olvidar() {
    await api.olvidar_contrasena_correo();
    await recargar();
    aviso("Contraseña borrada de este computador.", "info");
  }

  return (
    <>
      <NotaSoloLectura visible={soloLectura} que="Estos ajustes" />

      {!conClave && (
        <p className="ajustes-nota ajustes-nota--aviso" role="status">
          <IconoAviso aria-hidden="true" />
          <span>Falta la contraseña del correo en este computador: sin ella, desde acá no sale ningún correo.</span>
        </p>
      )}

      <Grupo titulo="Cuenta de la app">
        <FilaCampo id="correo-remitente" etiqueta="Correo" error={errores["cuenta.remitente"]}>
          <input className="entrada" id="correo-remitente" type="email" autoComplete="off" disabled={soloLectura}
                 value={actual.remitente} onChange={(e) => cambiar({ remitente: e.target.value })} />
        </FilaCampo>
        <FilaCampo id="correo-nombre" etiqueta="Nombre que ve quien lo recibe" error={errores["cuenta.nombre"]}>
          <input className="entrada" id="correo-nombre" type="text" autoComplete="off" disabled={soloLectura}
                 value={actual.nombre} onChange={(e) => cambiar({ nombre: e.target.value })} />
        </FilaCampo>
        <div className="fila-ajuste fila-correo fila-correo--doble">
          <FilaCampo id="correo-servidor" etiqueta="Servidor" error={errores["cuenta.servidor"]} suelta>
            <input className="entrada" id="correo-servidor" type="text" autoComplete="off" disabled={soloLectura}
                   value={actual.servidor} onChange={(e) => cambiar({ servidor: e.target.value })} />
          </FilaCampo>
          <FilaCampo id="correo-puerto" etiqueta="Puerto" error={errores["cuenta.puerto"]} suelta>
            <input className="entrada entrada--num" id="correo-puerto" type="text" inputMode="numeric" autoComplete="off" disabled={soloLectura}
                   value={actual.puerto} onChange={(e) => cambiar({ puerto: e.target.value.replace(/\D/g, "") })} />
          </FilaCampo>
        </div>
        <Fila etiqueta="Contraseña" detalle={conClave ? "Guardada en este computador" : "Falta en este computador"}>
          {conClave && <IconoCheck className="correos-ok" aria-hidden="true" />}
          <button className="btn btn--secundario btn--chico" type="button" onClick={() => setPidiendo(true)}>
            {conClave ? "Cambiar" : "Escribir"}
          </button>
          {conClave && <button className="btn btn--fantasma btn--chico" type="button" onClick={olvidar}>Olvidar</button>}
        </Fila>
      </Grupo>

      <Grupo>
        <Fila icono={IconoCorreo} color="#0A84FF" etiqueta={probando ? "Enviando…" : "Enviar un correo de prueba"}
              detalle={actual.pruebaActivo ? `a ${actual.pruebaDireccion || "la dirección de prueba"}` : `a ${actual.remitente}`}
              onClick={conClave && !hayCambios ? correoDePrueba
                : () => aviso(hayCambios ? "Guarda los cambios antes de probar." : "Primero escribe la contraseña.", "error")} />
        <Fila icono={IconoHistorial} color="#5E6AD2" etiqueta="Historial de correos" onClick={() => setViendoHistorial(true)} />
        <Fila icono={IconoCarpeta} color="#8E8E93" etiqueta="Abrir la carpeta de correos" onClick={() => api.abrir_carpeta_correos()} />
        {datos.pendientes > 0 && (
          <Fila icono={IconoAviso} color="#E8772E" etiqueta="Correos sin enviar" detalle={`${datos.pendientes} en este computador`}
                onClick={() => { api.reintentar_bandeja(); aviso("Se está intentando enviarlos de nuevo.", "info"); }} />
        )}
      </Grupo>

      <Grupo titulo="Correos automáticos">
        <Fila etiqueta="Correos automáticos">
          <Segmento etiqueta="Correos automáticos" opciones={ENCENDIDOS} valor={actual.autoActivo} deshabilitado={soloLectura}
                    onCambiar={(v) => cambiar({ autoActivo: v })} />
        </Fila>
      </Grupo>

      <Grupo titulo="Modo de prueba">
        <Fila etiqueta="Modo de prueba">
          <Segmento etiqueta="Modo de prueba" opciones={PRUEBA} valor={actual.pruebaActivo} deshabilitado={soloLectura || datos.prueba_forzada}
                    onCambiar={(v) => cambiar({ pruebaActivo: v })} />
        </Fila>
        {actual.pruebaActivo && (
          <FilaCampo id="correo-prueba" etiqueta="Dirección de prueba" error={errores["prueba.direccion"]}>
            <input className="entrada" id="correo-prueba" type="email" autoComplete="off" disabled={soloLectura}
                   value={actual.pruebaDireccion} onChange={(e) => cambiar({ pruebaDireccion: e.target.value })} />
          </FilaCampo>
        )}
      </Grupo>

      <section className="correos-areas" aria-label="Correos de cada parte del programa">
        <h2 className="correos-areas__titulo">Cada parte del programa</h2>
        <div className="correos-areas__nav">
          <NavFlotante etiqueta="Secciones de Correos" valor={seccion} onCambiar={elegirSeccion}
                       items={SECCIONES.map((s) => ({ ...s, aviso: Object.keys(errores).some((k) => enSeccion(k, s.clave)) }))} />
        </div>
        <motion.div key={seccion} className="correos-areas__contenido"
                    initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={FUNDIDO}>
          {seccion === "cotizaciones" ? (
            <SeccionCotizaciones actual={actual} datos={datos} errores={errores} soloLectura={soloLectura}
                                 cambiar={cambiar} ultimoCampo={ultimoCampo}
                                 insertarVariable={insertarVariable} irAClientes={irAClientes} />
          ) : (
            <>
            <SwitchSeccion etiqueta="Correos automáticos de OPs" valor={actual.autoOps} general={actual.autoActivo}
                           soloLectura={soloLectura} onCambiar={(v) => cambiar({ autoOps: v })} />
            <ListaCorreos titulo="Reciben las OPs" ejemplo="produccion@texdigital.cl"
                          filas={actual.areas.ops} clave="areas.ops" errores={errores} soloLectura={soloLectura}
                          onCambiar={(filas) => cambiar({ areas: { ...actual.areas, ops: filas } })} />
            <h3 className="correos-subtitulo">Al aprobar una cotización</h3>
            <Plantilla titulo="Mensaje de la OP" prefijo="ops" seccion="ops" porDefecto={datos.por_defecto.ops}
                       variables={datos.variables_op} {...{ actual, datos, errores, soloLectura, cambiar, ultimoCampo, insertarVariable }} />
            <h3 className="correos-subtitulo">Al recotizar una OP</h3>
            <Plantilla titulo="Mensaje del aviso" prefijo="rec" seccion="ops_recotizada" porDefecto={datos.por_defecto.recotizada}
                       variables={datos.variables_op} {...{ actual, datos, errores, soloLectura, cambiar, ultimoCampo, insertarVariable }} />
            </>
          )}
        </motion.div>
      </section>

      <BarraGuardar visible={hayCambios} guardando={guardando} onDescartar={() => setBorrador(null)} onGuardar={guardar}
                    error={textoError} />

      <Dialogo abierto={pidiendo} onCerrar={() => setPidiendo(false)} className="dlg--desenfoque dlg-catalogo">
        <FormularioContrasena correo={original.remitente} onCerrar={() => setPidiendo(false)}
                              onHecho={async () => { setPidiendo(false); await recargar(); aviso("Contraseña guardada en este computador.", "info"); }} />
      </Dialogo>
      <Dialogo abierto={viendoHistorial} onCerrar={() => setViendoHistorial(false)} className="dlg--desenfoque dlg-historial-correos">
        <HistorialCorreos onCerrar={() => setViendoHistorial(false)} />
      </Dialogo>
    </>
  );
}

/* A qué sección de abajo pertenece un error de validar() (los de la cuenta y
   el modo de prueba son de arriba: no marcan ninguna). */
const enSeccion = (clave, seccion) =>
  seccion === "cotizaciones" ? clave.startsWith("cotizaciones")
    : clave.startsWith(`areas.${seccion}`) || clave.startsWith(`${seccion}.`) || clave.startsWith(`${seccion}_`);

/* Cotizaciones: dos correos distintos (Bruno, 2026-11-11), cada uno con su
   lista, su asunto y su mensaje.
     · Al crearla: el aviso a la gente de Texdigital, con el PDF. En el
       Resumen del cotizador se ve a quién va y se puede cambiar esa vez.
     · Al enviarla al cliente: el mensaje del botón "Enviar correo", y quienes
       reciben una copia de ese mismo correo para revisarlo. */
function SeccionCotizaciones({ actual, datos, errores, soloLectura, cambiar, ultimoCampo, insertarVariable, irAClientes }) {
  const cc = datos.con_correo;
  return (
    <>
      <SwitchSeccion etiqueta="Correos automáticos de cotizaciones" valor={actual.autoCotizaciones} general={actual.autoActivo}
                     soloLectura={soloLectura} onCambiar={(v) => cambiar({ autoCotizaciones: v })} />
      <h3 className="correos-subtitulo">Al crear una cotización</h3>
      <ListaCorreos titulo="Reciben las cotizaciones nuevas" ejemplo="ventas@texdigital.cl"
                    filas={actual.nuevasPara} clave="cotizaciones_nuevas.para" errores={errores} soloLectura={soloLectura}
                    onCambiar={(nuevasPara) => cambiar({ nuevasPara })} />
      <Plantilla titulo="Mensaje del aviso" prefijo="nuevas" seccion="cotizaciones_nuevas"
                 porDefecto={datos.por_defecto.nuevas} {...{ actual, datos, errores, soloLectura, cambiar, ultimoCampo, insertarVariable }} />

      <h3 className="correos-subtitulo">Al enviarla al cliente</h3>
      <Grupo>
        <Fila etiqueta="Correos a clientes">
          <Segmento etiqueta="Correos a clientes" opciones={ACTIVADOS} valor={actual.alCliente} deshabilitado={soloLectura}
                    onCambiar={(v) => cambiar({ alCliente: v })} />
        </Fila>
      </Grupo>
      <Plantilla titulo="Mensaje al cliente" prefijo="" seccion="cotizaciones"
                 porDefecto={datos.por_defecto} {...{ actual, datos, errores, soloLectura, cambiar, ultimoCampo, insertarVariable }} />
      <ListaCorreos titulo="Reciben una copia" ejemplo="ventas@texdigital.cl"
                    filas={actual.copia} clave="cotizaciones.copia" errores={errores}
                    soloLectura={soloLectura} onCambiar={(copia) => cambiar({ copia })} />
      <Grupo titulo="Clientes y contactos">
        <Fila icono={IconoClientes} color="#30B0C7" etiqueta="Clientes sin correo"
              detalle={`${cc.clientes_total - cc.clientes} de ${cc.clientes_total}`} onClick={() => irAClientes("clientes", "sin")} />
        <Fila icono={IconoClientes} color="#30B0C7" etiqueta="Contactos sin correo"
              detalle={`${cc.contactos_total - cc.contactos} de ${cc.contactos_total}`} onClick={() => irAClientes("contactos", "sin")} />
      </Grupo>
    </>
  );
}

/* Asunto y mensaje de un correo, con sus variables y "Volver al que traía la
   app". `prefijo`: "" (al cliente: asunto, mensaje) o "nuevas" (nuevasAsunto…). */
function Plantilla({ titulo, pie, prefijo, seccion, porDefecto, variables, actual, datos, errores, soloLectura, cambiar, ultimoCampo,
                     insertarVariable }) {
  const kAsunto = prefijo ? `${prefijo}Asunto` : "asunto";
  const kMensaje = prefijo ? `${prefijo}Mensaje` : "mensaje";
  const enFabrica = actual[kAsunto] === porDefecto.asunto && actual[kMensaje] === porDefecto.mensaje;
  const usar = (campo) => () => { ultimoCampo.current[kMensaje] = campo; };
  return (
    <Grupo titulo={titulo} pie={pie}>
      <FilaCampo id={`correo-${kAsunto}`} etiqueta="Asunto" error={errores[`${seccion}.asunto`]}>
        <input className="entrada" id={`correo-${kAsunto}`} type="text" autoComplete="off" disabled={soloLectura}
               value={actual[kAsunto]} onFocus={usar(kAsunto)}
               onChange={(e) => cambiar({ [kAsunto]: e.target.value })} />
      </FilaCampo>
      <FilaCampo id={`correo-${kMensaje}`} etiqueta="Mensaje" error={errores[`${seccion}.mensaje`]}>
        <textarea className="entrada correo-mensaje" id={`correo-${kMensaje}`} rows={prefijo ? 6 : 9} disabled={soloLectura}
                  value={actual[kMensaje]} onFocus={usar(kMensaje)}
                  onChange={(e) => cambiar({ [kMensaje]: e.target.value })} />
      </FilaCampo>
      <div className="fila-ajuste fila-correo">
        <span className="fila-correo__etiqueta">Variables</span>
        <div className="correo-variables">
          {(variables || datos.variables).map((v) => (
            <button key={v.clave} type="button" className="correo-variable" title={v.texto} disabled={soloLectura}
                    onMouseDown={(e) => e.preventDefault()} onClick={() => insertarVariable(kMensaje, v.clave)}>
              <code>{`{${v.clave}}`}</code><span>{v.texto}</span>
            </button>
          ))}
        </div>
      </div>
      {!enFabrica && !soloLectura && (
        <Fila etiqueta="Volver al asunto y mensaje que traía la app"
              onClick={() => cambiar({ [kAsunto]: porDefecto.asunto, [kMensaje]: porDefecto.mensaje })} />
      )}
    </Grupo>
  );
}

/* El switch de los correos automáticos de una sección. Con el general
   apagado, queda apagado y sin poder cambiarse (guarda lo que tenía). */
function SwitchSeccion({ etiqueta, valor, general, soloLectura, onCambiar }) {
  return (
    <Grupo>
      <Fila etiqueta={etiqueta} detalle={general ? null : "Apagados en general"}>
        <Segmento etiqueta={etiqueta} opciones={ENCENDIDOS} valor={general && valor} deshabilitado={soloLectura || !general}
                  onCambiar={onCambiar} />
      </Fila>
    </Grupo>
  );
}

/* Un campo de la página: la etiqueta arriba, el control abajo, ocupando la
   fila entera. `suelta`: sin la fila alrededor (dos campos en una fila). */
function FilaCampo({ id, etiqueta, error, suelta = false, children }) {
  const contenido = (
    <>
      <label className="fila-correo__etiqueta" htmlFor={id}>{etiqueta}</label>
      {children}
      {error && <span className="fila-textil__error">{error}</span>}
    </>
  );
  return suelta
    ? <div className="fila-correo__campo" data-invalido={error ? "" : undefined}>{contenido}</div>
    : <div className="fila-ajuste fila-correo" data-invalido={error ? "" : undefined}>{contenido}</div>;
}

/* Una lista de correos que se edita en el lugar: correo y nombre (opcional)
   en cada fila, "Agregar correo" abajo. */
function ListaCorreos({ titulo, pie, ejemplo, filas, clave, errores, soloLectura, onCambiar }) {
  const cambiarFila = (i, cambio) => onCambiar(filas.map((f, k) => (k === i ? { ...f, ...cambio } : f)));
  return (
    <Grupo titulo={titulo} pie={pie}>
      {filas.map((f, i) => (
        <div key={i} className="fila-ajuste fila-correo fila-correo--lista" data-invalido={errores[`${clave}:${i}`] ? "" : undefined}>
          <div className="fila-correo__entradas">
            <input className="entrada fila-correo__correo" type="email" autoComplete="off" placeholder={ejemplo}
                   aria-label={`${titulo}: correo ${i + 1}`} disabled={soloLectura} value={f.correo}
                   onChange={(e) => cambiarFila(i, { correo: e.target.value })} />
            <input className="entrada fila-correo__nombre" type="text" autoComplete="off" placeholder="Nombre (opcional)"
                   aria-label={`${titulo}: nombre del correo ${i + 1}`} disabled={soloLectura} value={f.nombre}
                   onChange={(e) => cambiarFila(i, { nombre: e.target.value })} />
            <button className="btn-fila-ajuste btn-fila-ajuste--peligro" type="button" title="Quitar" disabled={soloLectura}
                    aria-label={`Quitar ${f.correo || "este correo"}`}
                    onClick={() => onCambiar(filas.filter((_, k) => k !== i))}><IconoEliminar /></button>
          </div>
          {errores[`${clave}:${i}`] && <span className="fila-textil__error">{errores[`${clave}:${i}`]}</span>}
        </div>
      ))}
      {!filas.length && <p className="ajustes-vacio">Ningún correo.</p>}
      {!soloLectura && (
        <Fila etiqueta="Agregar correo" icono={IconoMas} color="#2E9D5B"
              onClick={() => onCambiar([...filas, { correo: "", nombre: "" }])} />
      )}
    </Grupo>
  );
}

/* La contraseña de la casilla: Python la prueba contra el servidor y, si
   entra, la guarda en este computador (ver core.correos.guardar_contrasena). */
function FormularioContrasena({ correo, onCerrar, onHecho }) {
  const [clave, setClave] = useState("");
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function confirmar(e) {
    e.preventDefault();
    if (enviando || !clave) return;
    setEnviando(true);
    try {
      const r = await api.guardar_contrasena_correo(clave);
      if (r?.ok) await onHecho();
      else setError(r?.error || "No se pudo guardar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={confirmar} noValidate>
      <h2 className="dlg__titulo">Contraseña del correo</h2>
      <p className="dlg__texto">
        La de {correo}. Se prueba con el servidor y queda guardada solo en este computador.
      </p>
      <div className="dlg-catalogo__campos">
        <Campo id="correo-clave" etiqueta="Contraseña" requerido invalido={!!error} error={error || ""}>
          <input className="entrada" id="correo-clave" type="password" autoComplete="off" data-autofoco
                 value={clave} onChange={(e) => { setClave(e.target.value); setError(null); }} />
        </Campo>
      </div>
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit" disabled={enviando || !clave}>
          {enviando ? "Probando…" : "Guardar"}
        </button>
      </div>
    </form>
  );
}
