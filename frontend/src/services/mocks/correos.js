/* Mocks de los correos (ver ui/api_correos.py): Configuración › Correos y el
   "Enviar correo" de una cotización. Como en la app, no sale nada. */

const POR_DEFECTO = {
  asunto: "Cotización {numero} - {cliente}",
  mensaje: "Hola {contacto}:\n\nTe enviamos la cotización N° {numero}, por un total de {total} (IVA incluido). Va adjunta en PDF.\n\nPara aprobarla o pedirnos cambios, basta con responder este correo.\n\nSaludos,\nTexdigital",
  ops: {
    asunto: "OP {numero} - {cliente}",
    mensaje: "Se aprobó la cotización N° {numero} de {cliente} ({trabajo}) y pasó a OP.\n\nIngreso: {ingreso}\nEntrega: {entrega}\n\nVa adjunta la OP en PDF.\n\nCorreo automático del Sistema de Gestión.",
  },
  recotizada: {
    asunto: "OP {numero} recotizada - {cliente}",
    mensaje: "La OP {numero} de {cliente} ({trabajo}) se recotizó: volvió a Cotizaciones y ya no está en producción.\n\nNo sigan trabajando en ella hasta que se apruebe de nuevo.\n\nCorreo automático del Sistema de Gestión.",
  },
  nuevas: {
    asunto: "Nueva cotización {numero} - {cliente}",
    mensaje: "Se creó la cotización N° {numero} de {cliente} ({trabajo}), por un total de {total} (IVA incluido).\n\nVa adjunta en PDF.\n\nCorreo automático del Sistema de Gestión.",
  },
};

let ajustes = {
  cuenta: { remitente: "sistema@texdigital.cl", nombre: "Texdigital", servidor: "mail.texdigital.cl", puerto: 465 },
  prueba: { activo: true, direccion: "brosky.spam@gmail.com" },
  cotizaciones: { al_cliente: true, asunto: POR_DEFECTO.asunto, mensaje: POR_DEFECTO.mensaje, copia: [{ correo: "jefe@texdigital.cl", nombre: "Jefe de ventas" }] },
  cotizaciones_nuevas: { ...POR_DEFECTO.nuevas, para: [{ correo: "ventas@texdigital.cl", nombre: "Ventas" }] },
  ops: { ...POR_DEFECTO.ops },
  ops_recotizada: { ...POR_DEFECTO.recotizada },
  areas: { ops: [{ correo: "produccion@texdigital.cl", nombre: "Producción" }], inventario: [], despachos: [] },
  automaticos: { activo: true, cotizaciones: true, ops: true, inventario: true, despachos: true },
};

const envios = {};   // numero → último envío

/* Como la bandeja (core/bandeja.py): el correo "sale" un momento después. */
export function simularEnvio(para, asunto) {
  setTimeout(() => salio(ajustes.prueba.activo ? [ajustes.prueba.direccion] : para, asunto), 600);
}

/* Como core.correos.enviar: cada correo que "sale" pide la animación. */
const salio = (a, asunto) => window.TD?.correoEnviado?.(`Enviado a ${a.join(", ")}: ${asunto}`);

export const correoAlCliente = () => !!ajustes.cotizaciones.al_cliente;

export default {
  obtener_ajustes_correos: () => ({
    ajustes: structuredClone(ajustes), por_defecto: POR_DEFECTO, pendientes: 1, solo_lectura: false, contrasena_guardada: true, prueba_forzada: true,
    variables: [
      { clave: "numero", texto: "El N° de la cotización" }, { clave: "cliente", texto: "La empresa" },
      { clave: "contacto", texto: "El contacto (o la empresa, si no tiene)" }, { clave: "trabajo", texto: "El nombre del trabajo" },
      { clave: "total", texto: "El total con IVA" }, { clave: "fecha", texto: "La fecha de la cotización" },
    ],
    variables_op: [
      { clave: "numero", texto: "El N° de la OP" }, { clave: "cliente", texto: "La empresa" },
      { clave: "contacto", texto: "El contacto (o la empresa, si no tiene)" }, { clave: "trabajo", texto: "El nombre del trabajo" },
      { clave: "ingreso", texto: "La fecha de ingreso" }, { clave: "entrega", texto: "La fecha de entrega" },
    ],
    con_correo: { clientes: 1, clientes_total: 3, contactos: 1, contactos_total: 2 },
  }),
  guardar_ajustes_correos(d) {
    ajustes = { ...ajustes, ...structuredClone(d), cuenta: { ...d.cuenta, puerto: Number(d.cuenta.puerto) } };
    return { ok: true };
  },
  abrir_carpeta_correos: () => undefined,
  historial_correos(anio, mes) {
    const meses = [{ anio: 2026, mes: 11, cantidad: 4 }, { anio: 2026, mes: 10, cantidad: 1 }];
    const a = anio ?? 2026, m = mes ?? 11;
    const correos = a === 2026 && m === 11 ? [
      { archivo: "2026/11/a.eml", fecha: "2026-11-13T21:36:02", asunto: "OP 9015 - Tiendas Ejemplo SpA", operacion: "aprobación",
        para: ["produccion@texdigital.cl"], copia: [], prueba: true },
      { archivo: "2026/11/b.eml", fecha: "2026-11-13T18:02:40", asunto: "OP 9011 recotizada - Café Las Rosas", operacion: "recotización",
        para: ["produccion@texdigital.cl", "jefe@texdigital.cl"], copia: [], prueba: true },
      { archivo: "2026/11/c.eml", fecha: "2026-11-12T10:15:00", asunto: "Nueva cotización 1008 - Cliente de prueba", operacion: "cotización nueva",
        para: ["ventas@texdigital.cl"], copia: [], prueba: true },
      { archivo: "2026/11/d.eml", fecha: "2026-11-11T09:00:00", asunto: "Correo de prueba del Sistema de Gestión", operacion: "prueba",
        para: ["brosky.spam@gmail.com"], copia: [], prueba: false },
    ] : a === 2026 && m === 10 ? [
      { archivo: "2026/10/e.eml", fecha: "2026-10-30T16:20:00", asunto: "Cotización 1004 - Galería Norte", operacion: "envío al cliente",
        para: ["rperez@galerianorte.cl"], copia: ["ventas@texdigital.cl"], prueba: true },
    ] : [];
    return { meses, anio: a, mes: m, correos };
  },
  abrir_correo_historial: () => true,
  guardar_contrasena_correo: (clave) => (clave === "mala" ? { ok: false, error: "El servidor no aceptó la contraseña." } : { ok: true }),
  olvidar_contrasena_correo: () => undefined,
  enviar_correo_de_prueba: () => (salio([ajustes.prueba.direccion], "Correo de prueba del Sistema de Gestión"),
                                  { ok: true, a: [ajustes.prueba.direccion] }),
  preparar_correo_cotizacion: (numero) => ({
    numero, empresa: "Café del Puerto", rut: "76.086.428-5", razon_social: "Café del Puerto SpA",
    contacto: "Ana Pérez", trabajo: "Toldo terraza", total: "$1.234.567",
    sugeridos: [
      { origen: "contacto", nombre: "Ana Pérez", correo: "ana@cafedelpuerto.cl" },
      { origen: "cliente", nombre: "Café del Puerto", correo: "compras@cafedelpuerto.cl" },
    ],
    copia: ajustes.cotizaciones.copia.map((f) => f.correo),
    asunto: `Cotización ${numero} - Café del Puerto`,
    mensaje: `Hola Ana Pérez:\n\nTe enviamos la cotización N° ${numero}, por un total de $1.234.567 (IVA incluido). Va adjunta en PDF.\n\nPara aprobarla o pedirnos cambios, basta con responder este correo.\n\nSaludos,\nTexdigital`,
    adjunto: `${numero} • Toldo terraza Café del Puerto.pdf`,
    ultimo: envios[numero] || null, envios: envios[numero] ? 1 : 0, sin_cambios: !!envios[numero],
    remitente: "Texdigital <sistema@texdigital.cl>", prueba: ajustes.prueba, prueba_forzada: true, contrasena_guardada: true,
  }),
  opciones_aviso: (parte) => {
    const inscritos = parte === "ops" ? ajustes.areas.ops : ajustes.cotizaciones_nuevas.para;
    const guardados = [...ajustes.cotizaciones_nuevas.para, ...ajustes.cotizaciones.copia, ...ajustes.areas.ops]
      .filter((f, i, todos) => !inscritos.some((x) => x.correo === f.correo)
        && todos.findIndex((x) => x.correo === f.correo) === i);
    const activo = ajustes.automaticos.activo && ajustes.automaticos[parte];
    return { activo, inscritos, guardados, prueba: ajustes.prueba, contrasena_guardada: true };
  },
  // Como la bandeja: "sale" un momento después.
  enviar_aviso_cotizacion_nueva: (numero, para) => {
    setTimeout(() => salio(ajustes.prueba.activo ? [ajustes.prueba.direccion] : para, `Nueva cotización ${numero}`), 600);
    return { ok: true, para };
  },
  estado_bandeja: () => ({ pendientes: [] }),
  reintentar_bandeja: () => undefined,
  ver_pdf_cotizacion: () => ({ ok: true }),
  enviar_correo_cotizacion(numero, d) {
    salio(ajustes.prueba.activo ? [ajustes.prueba.direccion] : d.para, d.asunto);
    const ahora = new Date();
    const fecha = `${ahora.toLocaleDateString("es-CL")} ${ahora.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" })}`;
    envios[numero] = { fecha, para: d.para, copia: d.copia, asunto: d.asunto, prueba: ajustes.prueba.activo, simulado: false };
    return { ok: true, prueba: ajustes.prueba.activo,
             a: ajustes.prueba.activo ? [ajustes.prueba.direccion] : [...d.para, ...d.copia],
             archivo: "Correos/2026/11/…eml", ultimo: envios[numero] };
  },
};
