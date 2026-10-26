import { api } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { ControlTexto } from "@/components/Cabecera/Cabecera";
import IconoInfo from "@/assets/svg/info.svg?react";
import IconoTexto from "@/assets/svg/a-large-small.svg?react";
import IconoManual from "@/assets/svg/book-open.svg?react";
import { Fila, Grupo } from "./Ajustes";

/* General: la versión, el tamaño del texto y el manual. Lo mismo que el pie
   del menú, reunido en un solo lugar. (El botón de buscar actualizaciones se
   sacó en v2.1: no estaba conectado; los usuarios actualizan bajando la
   versión nueva de GitHub.) */
export default function General() {
  const { contexto } = useApp();
  return (
    <>
      <Grupo>
        <Fila icono={IconoInfo} etiqueta="Versión" detalle={contexto.version ? `v${contexto.version}` : "—"} />
      </Grupo>
      <Grupo pie="También con Ctrl + y Ctrl −, desde cualquier pantalla. Se guarda en esta computadora.">
        <Fila icono={IconoTexto} color="#5E6AD2" etiqueta="Tamaño del texto"><ControlTexto /></Fila>
      </Grupo>
      <Grupo>
        <Fila icono={IconoManual} color="#E8772E" etiqueta="Manual de uso" onClick={() => api.abrir_manual()} />
      </Grupo>
    </>
  );
}
