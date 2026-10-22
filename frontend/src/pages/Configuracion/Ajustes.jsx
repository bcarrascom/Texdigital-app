import IconoFlecha from "@/assets/svg/chevron-right.svg?react";

/* Las piezas de una página de Configuración, al estilo de los Ajustes de
   macOS: un encabezado con el ícono grande de la categoría y grupos de filas
   en tarjetas redondeadas.

       <Encabezado categoria={c} />
       <Grupo pie="Texto de ayuda debajo del grupo.">
         <Fila icono={IconoInfo} color="#8E8E93" etiqueta="Versión" detalle="v1.2.0" />
         <Fila etiqueta="Manual de uso" onClick={abrir} />          ← con flecha, toda la fila es el botón
         <Fila etiqueta="Tamaño del texto"><ControlTexto /></Fila>  ← un control a la derecha
       </Grupo> */

/* El ícono en su cuadrado de color, con el dibujo en blanco. */
export function IconoCategoria({ Icono, color, grande = false }) {
  return (
    <span className={`icono-ajuste${grande ? " icono-ajuste--grande" : ""}`} style={{ "--color-icono": color }} aria-hidden="true">
      <Icono />
    </span>
  );
}

export function Encabezado({ categoria }) {
  return (
    <header className="ajustes-encabezado">
      <IconoCategoria Icono={categoria.Icono} color={categoria.color} grande />
      <h1 className="ajustes-encabezado__titulo">{categoria.titulo}</h1>
      <p className="ajustes-encabezado__desc">{categoria.desc}</p>
    </header>
  );
}

export function Grupo({ titulo, pie, children }) {
  return (
    <section className="ajustes-grupo">
      {titulo && <h2 className="ajustes-grupo__titulo">{titulo}</h2>}
      <div className="ajustes-grupo__filas">{children}</div>
      {pie && <p className="ajustes-grupo__pie">{pie}</p>}
    </section>
  );
}

export function Fila({ icono, color = "#8E8E93", etiqueta, detalle, onClick, className = "", children }) {
  const contenido = (
    <>
      {icono && <IconoCategoria Icono={icono} color={color} />}
      <span className="fila-ajuste__etiqueta">{etiqueta}</span>
      {detalle != null && <span className="fila-ajuste__detalle">{detalle}</span>}
      {children && <span className="fila-ajuste__control">{children}</span>}
      {onClick && <IconoFlecha className="fila-ajuste__flecha" aria-hidden="true" />}
    </>
  );
  return onClick
    ? <button type="button" className={`fila-ajuste fila-ajuste--boton ${className}`} onClick={onClick}>{contenido}</button>
    : <div className={`fila-ajuste ${className}`}>{contenido}</div>;
}
