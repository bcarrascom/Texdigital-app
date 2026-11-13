/* Mocks de los correos (ver ui/api_correos.py): Configuración › Correos y el
   "Enviar correo" de una cotización. Como en la app, no sale nada. */

const POR_DEFECTO = {
  asunto: "Cotización {numero} - {cliente}",
  mensaje: "Hola {contacto}:\n\nTe enviamos la cotización N° {numero}, por un total de {total} (IVA incluido). Va adjunta en PDF.\n\nPara aprobarla o pedirnos cambios, basta con responder este correo.\n\nSaludos,\nTexdigital",
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
  areas: { ops: [{ correo: "produccion@texdigital.cl", nombre: "Producción" }], inventario: [], despachos: [] },
  automaticos: { activo: true, cotizaciones: true, ops: true, inventario: true, despachos: true },
};

const envios = {};   // numero → último envío

/* Como core.correos.enviar: cada correo que "sale" pide la animación. */
const salio = () => window.TD?.correoEnviado?.();

export const correoAlCliente = () => !!ajustes.cotizaciones.al_cliente;

export default {
  obtener_ajustes_correos: () => ({
    ajustes: structuredClone(ajustes), por_defecto: POR_DEFECTO, solo_lectura: false, contrasena_guardada: true, prueba_forzada: true,
    variables: [
      { clave: "numero", texto: "El N° de la cotización" }, { clave: "cliente", texto: "La empresa" },
      { clave: "contacto", texto: "El contacto (o la empresa, si no tiene)" }, { clave: "trabajo", texto: "El nombre del trabajo" },
      { clave: "total", texto: "El total con IVA" }, { clave: "fecha", texto: "La fecha de la cotización" },
    ],
    con_correo: { clientes: 1, clientes_total: 3, contactos: 1, contactos_total: 2 },
  }),
  guardar_ajustes_correos(d) {
    ajustes = { ...ajustes, ...structuredClone(d), cuenta: { ...d.cuenta, puerto: Number(d.cuenta.puerto) } };
    return { ok: true };
  },
  abrir_carpeta_correos: () => undefined,
  guardar_contrasena_correo: (clave) => (clave === "mala" ? { ok: false, error: "El servidor no aceptó la contraseña." } : { ok: true }),
  olvidar_contrasena_correo: () => undefined,
  enviar_correo_de_prueba: () => (salio(), { ok: true, a: [ajustes.prueba.direccion] }),
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
  correo_al_crear: () => {
    const inscritos = ajustes.cotizaciones_nuevas.para;
    const guardados = [...ajustes.cotizaciones.copia, ...ajustes.areas.ops]
      .filter((f) => !inscritos.some((i) => i.correo === f.correo));
    const activo = ajustes.automaticos.activo && ajustes.automaticos.cotizaciones;
    return { activo, inscritos, guardados, prueba: ajustes.prueba, contrasena_guardada: true };
  },
  enviar_aviso_cotizacion_nueva: (numero, para) => (salio(), {
    ok: true, prueba: ajustes.prueba.activo, a: ajustes.prueba.activo ? [ajustes.prueba.direccion] : para,
  }),
  ver_pdf_cotizacion: () => ({ ok: true }),
  enviar_correo_cotizacion(numero, d) {
    salio();
    const ahora = new Date();
    const fecha = `${ahora.toLocaleDateString("es-CL")} ${ahora.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" })}`;
    envios[numero] = { fecha, para: d.para, copia: d.copia, asunto: d.asunto, prueba: ajustes.prueba.activo, simulado: false };
    return { ok: true, prueba: ajustes.prueba.activo,
             a: ajustes.prueba.activo ? [ajustes.prueba.direccion] : [...d.para, ...d.copia],
             archivo: "Correos/2026/11/…eml", ultimo: envios[numero] };
  },
};
