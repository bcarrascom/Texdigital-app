import { AnimatePresence, motion } from "motion/react";
import IconoFlecha from "@/assets/svg/chevron-right.svg?react";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";

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

/* Las páginas que se editan enteras y se guardan con un botón (los precios,
   las reglas): la barra de abajo aparece mientras haya cambios. Con
   `error`, dice por qué no se puede guardar y apaga el botón. */
export function BarraGuardar({ visible, error, guardando, onDescartar, onGuardar }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div className="barra-guardar" role="region" aria-label="Cambios sin guardar"
                    initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 16 }}
                    transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}>
          <span className={`barra-guardar__texto${error ? " barra-guardar__texto--error" : ""}`}>
            {error ? `No se puede guardar: ${error}` : "Hay cambios sin guardar."}
          </span>
          <button className="btn btn--fantasma btn--chico" type="button" disabled={guardando} onClick={onDescartar}>
            Descartar
          </button>
          <button className="btn btn--primario btn--chico" type="button" disabled={!!error || guardando} onClick={onGuardar}>
            Guardar cambios
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* El archivo lo guardó una versión más nueva de la app: se ve, no se edita
   (ver core/ajustes_globales.py). */
export function NotaSoloLectura({ visible, que = "Estos precios" }) {
  if (!visible) return null;
  return (
    <p className="ajustes-nota ajustes-nota--aviso" role="status">
      <IconoAviso aria-hidden="true" />
      {que} los guardó una versión más nueva de la app. Se pueden ver, pero para cambiarlos hay que actualizar esta instalación.
    </p>
  );
}
