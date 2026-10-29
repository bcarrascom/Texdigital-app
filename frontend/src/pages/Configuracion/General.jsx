import { useState } from "react";
import { api } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { useActualizacion } from "@/hooks/useActualizacion";
import { ControlTexto } from "@/components/Cabecera/Cabecera";
import DialogoActualizacion from "@/components/Actualizacion/DialogoActualizacion";
import IconoInfo from "@/assets/svg/info.svg?react";
import IconoActualizar from "@/assets/svg/refresh-cw.svg?react";
import IconoTexto from "@/assets/svg/a-large-small.svg?react";
import IconoManual from "@/assets/svg/book-open.svg?react";
import { Fila, Grupo } from "./Ajustes";

/* Lo que dice la fila de actualizaciones según cómo va la búsqueda. */
const DETALLE = {
  buscando: "Buscando…",
  al_dia: "Al día",
  disponible: (e) => `Hay una nueva: ${e.nueva}`,
  descargando: "Descargando…",
  listo: "Reiniciando…",
  error: "No se pudo buscar",
};

/* General: la versión, buscar actualizaciones, el tamaño del texto y el
   manual. Lo mismo que el pie del menú, reunido en un solo lugar. */
export default function General() {
  const { contexto } = useApp();
  const actualizacion = useActualizacion();
  const [dialogo, setDialogo] = useState(false);
  const { estado } = actualizacion;
  const detalle = DETALLE[estado?.fase];

  function buscar() {
    // Con una versión ya encontrada, no hace falta volver a buscar.
    if (!["disponible", "descargando", "listo"].includes(estado?.fase)) actualizacion.buscar();
    setDialogo(true);
  }

  return (
    <>
      <Grupo>
        <Fila icono={IconoInfo} etiqueta="Versión" detalle={contexto.version ? `v${contexto.version}` : "—"} />
        <Fila icono={IconoActualizar} color="#3478F6" etiqueta="Buscar actualizaciones"
              detalle={typeof detalle === "function" ? detalle(estado) : detalle} onClick={buscar} />
      </Grupo>
      <Grupo pie="También con Ctrl + y Ctrl −, desde cualquier pantalla. Se guarda en esta computadora.">
        <Fila icono={IconoTexto} color="#5E6AD2" etiqueta="Tamaño del texto"><ControlTexto /></Fila>
      </Grupo>
      <Grupo>
        <Fila icono={IconoManual} color="#E8772E" etiqueta="Manual de uso" onClick={() => api.abrir_manual()} />
      </Grupo>
      <DialogoActualizacion abierto={dialogo} {...actualizacion} onCerrar={() => setDialogo(false)} />
    </>
  );
}
