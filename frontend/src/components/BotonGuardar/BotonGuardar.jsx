import IconoGuardar from "@/assets/svg/bookmark.svg?react";
import "./BotonGuardar.css";

/* Botón de guardar con el ícono en un círculo que, al pasar el mouse, crece
   hasta cubrir el botón entero mientras el texto se aparta. Adaptado de
   "bookmarkBtn" de Uiverse (uiverse.io, licencia MIT) a la identidad del
   proyecto: superficie clara y el color del módulo (--c-tema-*), así en
   Cotizaciones sale naranjo y en otro módulo toma el suyo.

       <BotonGuardar onClick={guardarCliente}>Guardar datos</BotonGuardar>

   Llena el ancho de su contenedor, para alinearse con los campos de al lado. */
export default function BotonGuardar({ children, onClick, title, disabled }) {
  return (
    <button type="button" className="boton-guardar" onClick={onClick} title={title} disabled={disabled}>
      <span className="boton-guardar__icono" aria-hidden="true">
        <IconoGuardar />
      </span>
      <span className="boton-guardar__texto">{children}</span>
    </button>
  );
}
