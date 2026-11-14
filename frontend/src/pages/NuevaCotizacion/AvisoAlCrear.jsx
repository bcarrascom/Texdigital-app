import { api } from "@/services/api";
import * as fmt from "@/utils/formato";

/* Aviso de cotización nueva, en el pie del Resumen (Bruno, 2026-11-11): al
   crear una cotización, la gente de Texdigital inscrita en Configuración ›
   Correos › Cotizaciones recibe el PDF. Es OTRO correo que el del cliente
   (ese sale con "Enviar correo" de Ver cotización), con su propio asunto y
   mensaje. Al editar una cotización no aparece: es solo al crearla.

   La lista es components/ListaDestinatarios (la misma del diálogo Aprobar).
   Acá solo queda el envío. */

/* Después de guardar: deja el aviso en la bandeja (core/bandeja.py), que lo
   envía en segundo plano. Cuando sale, la animación "Correo enviado" y su
   aviso de texto aparecen solos; si no sale, Python avisa y lo reintenta.
   Acá solo se avisa si ni siquiera se pudo preparar (p. ej. sin PDF). */
export async function enviarAvisoCreacion(numero, para, avisar) {
  const r = (await api.enviar_aviso_cotizacion_nueva(numero, para)) || {};
  if (!r.ok && !r.apagado) {
    avisar(`No se pudo preparar el aviso de la cotización ${fmt.numero(numero)}: ${r.error || "error desconocido"} `
           + "La cotización quedó guardada.", "error", 10000);
  }
}
