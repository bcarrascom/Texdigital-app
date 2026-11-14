import SquishSwitch from "@/components/SquishSwitch/SquishSwitch";
import "./Interruptor.css";

/* El switch de encendido / apagado de la app (Bruno, 2026-11-14: reemplaza
   a los Segmento "Encendidos / Apagados" de Configuración). Es el
   SquishSwitch de React Bits con los colores y el tamaño de la app: apagado,
   gris; encendido, el color del tema de la página (grafito en
   Configuración). El pulgar va blanco en los dos.

       <Interruptor etiqueta="Correos automáticos" valor={activo} onCambiar={setActivo} />

   `etiqueta` es el nombre para los lectores de pantalla: el texto que se ve
   lo pone la fila donde va. */
export default function Interruptor({ etiqueta, valor, onCambiar, deshabilitado = false }) {
  return (
    <SquishSwitch
      className="interruptor"
      checked={!!valor}
      onChange={onCambiar}
      disabled={deshabilitado}
      ariaLabel={etiqueta}
      trackColor="var(--c-borde-fuerte)"
      trackOnColor="var(--c-tema-fuerte)"
      thumbColor="#FFFFFF"
      thumbOnColor="#FFFFFF"
      width={46}
      height={26}
      radius={13}
    />
  );
}
