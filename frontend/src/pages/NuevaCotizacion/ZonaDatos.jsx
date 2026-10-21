import { forwardRef } from "react";
import BotonGuardar from "@/components/BotonGuardar/BotonGuardar";
import * as fmt from "@/utils/formato";

/* Zona de arriba de la pizarra: el trabajo (nombre, cuántos productos,
   despacho/instalación), el documento (N°, fecha, condición, descripción) y
   el cliente (empresa y contacto, con autocompletado de los guardados). El
   estado vive en NuevaCotizacion; acá solo se pinta y se avisa qué cambió. */

const EXTRAS = [["despacho", "Despacho", "Valor del despacho"], ["instalacion", "Instalación", "Valor de la instalación"]];

const ZonaDatos = forwardRef(function ZonaDatos({
  nombre, onNombre, cantidad, onCantidad, extras, onExtra,
  cliente, onCliente, errorNumero, cat,
  nota, puedeBajar, onBajar, onGuardarCliente, onGuardarContacto,
}, nombreRef) {
  const campo = (clave, transformar = (v) => v) => ({
    value: cliente[clave] ?? "",
    onChange: (e) => onCliente({ [clave]: transformar(e.target.value) }),
  });

  /* Elegir una empresa/contacto conocido rellena lo demás. */
  function elegirEmpresa(empresa) {
    const c = (cat.clientes || []).find((x) => x.empresa === empresa);
    onCliente(c ? { empresa, rut: c.rut || "", razon_social: c.razon_social || "" } : { empresa });
  }
  function elegirContacto(contacto) {
    const c = (cat.contactos || []).find((x) => x.contacto === contacto);
    onCliente(c
      ? { contacto, email: c.email || "", descuento: c.descuento || "0", condicion: c.condicion || "" }
      : { contacto });
  }

  const paso = (d) => onCantidad(String(Math.max(1, (parseInt(cantidad, 10) || 0) + d)));

  return (
    <section className="zona datos">
      <div className="datos__paneles">
        <div className="columna">
          <article className="hoja hoja--venta">
            <span className="grupo__titulo">Trabajo</span>
            <div className="campo">
              <label className="campo__etiqueta" htmlFor="nombre" data-requerido>Nombre del trabajo</label>
              <input ref={nombreRef} className="entrada" id="nombre" type="text" autoComplete="off"
                     value={nombre} onChange={(e) => onNombre(e.target.value)} />
              <span className="campo__error">Escribí un nombre para el trabajo.</span>
            </div>

            {/* UNA rejilla de 3 × 2 (no tres columnas apiladas): así la fila de
                etiquetas y la de controles quedan alineadas entre sí. */}
            <div className="fila-trabajo">
              <label className="campo__etiqueta" htmlFor="cantidad" data-requerido>Productos</label>
              {EXTRAS.map(([clave, texto]) => (
                <label key={clave} className="chip-casilla chip-casilla--suelta">
                  <input type="checkbox" id={clave} checked={extras[clave].marcado}
                         onChange={(e) => onExtra(clave, { marcado: e.target.checked }, e.target.checked)} />
                  <span className="chip-casilla__texto">{texto}</span>
                </label>
              ))}

              <div className="stepper">
                <button className="stepper__btn" type="button" aria-label="Uno menos" onClick={() => paso(-1)}>−</button>
                <input className="entrada entrada--num" id="cantidad" type="text" inputMode="numeric" autoComplete="off"
                       value={cantidad} onChange={(e) => onCantidad(fmt.soloDigitos(e.target.value))} />
                <button className="stepper__btn" type="button" aria-label="Uno más" onClick={() => paso(1)}>+</button>
              </div>
              {EXTRAS.map(([clave, , etiqueta]) => (
                /* visibility, no display: la fila conserva su alto y nada salta
                   al marcar o desmarcar (ver NuevaCotizacion.css). */
                <input key={clave} className="entrada entrada--num fila-trabajo__monto" id={`${clave}-monto`}
                       data-visible={extras[clave].marcado || undefined}
                       type="text" inputMode="numeric" autoComplete="off" placeholder="$0" aria-label={etiqueta}
                       value={extras[clave].texto} onChange={(e) => onExtra(clave, { texto: e.target.value })} />
              ))}
            </div>
          </article>

          <article className="hoja hoja--doc">
            <span className="grupo__titulo">Documento</span>
            <div className="fila fila--2">
              <div className="campo" data-invalido={errorNumero ? "" : undefined}>
                <label className="campo__etiqueta" htmlFor="numero" data-requerido>N° cotización</label>
                <input className="entrada entrada--num" id="numero" type="text" inputMode="numeric" maxLength={4}
                       autoComplete="off" {...campo("numero", (v) => fmt.soloDigitos(v).slice(0, 4))} />
                <span className="campo__error">{errorNumero}</span>
              </div>
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="fecha">Fecha</label>
                <input className="entrada" id="fecha" type="date" {...campo("fecha")} />
              </div>
            </div>
            <div className="fila fila--2">
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="condicion">Condición de pago</label>
                <input className="entrada" id="condicion" type="text" autoComplete="off" {...campo("condicion")} />
              </div>
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="descripcion">Descripción</label>
                <input className="entrada" id="descripcion" type="text" autoComplete="off" {...campo("descripcion")} />
              </div>
            </div>
          </article>
        </div>

        <article className="hoja hoja--cliente">
          <div className="grupo">
            <span className="grupo__titulo">Empresa</span>
            <div className="fila fila--2">
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="empresa" data-requerido>Empresa</label>
                <input className="entrada" id="empresa" type="text" list="lista-empresas" autoComplete="off"
                       value={cliente.empresa} onChange={(e) => elegirEmpresa(e.target.value)} />
              </div>
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="rut">RUT</label>
                <input className="entrada" id="rut" type="text" autoComplete="off" placeholder="12.345.678-9"
                       {...campo("rut", fmt.rut)} />
              </div>
            </div>
            <div className="fila fila--2 fila--accion">
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="razon">Razón social</label>
                <input className="entrada" id="razon" type="text" autoComplete="off" {...campo("razon_social")} />
              </div>
              <BotonGuardar onClick={onGuardarCliente}>Guardar datos</BotonGuardar>
            </div>
          </div>

          <div className="grupo">
            <span className="grupo__titulo">Contacto</span>
            <div className="fila fila--2">
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="contacto">Contacto</label>
                <input className="entrada" id="contacto" type="text" list="lista-contactos" autoComplete="off"
                       value={cliente.contacto} onChange={(e) => elegirContacto(e.target.value)} />
              </div>
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="email">Email</label>
                <input className="entrada" id="email" type="email" autoComplete="off" {...campo("email")} />
              </div>
            </div>
            <div className="fila fila--2 fila--accion">
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="descuento">Descuento (%)</label>
                <input className="entrada entrada--num" id="descuento" type="text" inputMode="decimal" autoComplete="off"
                       {...campo("descuento")} />
              </div>
              <BotonGuardar onClick={onGuardarContacto}>Guardar contacto</BotonGuardar>
            </div>
          </div>
        </article>
      </div>

      <div className="pie-datos">
        <span className="pie-datos__nota">{nota}</span>
        <button className="btn btn--primario btn--grande" type="button" disabled={!puedeBajar} onClick={onBajar}>
          Cargar productos <span aria-hidden="true">↓</span>
        </button>
      </div>
    </section>
  );
});

export default ZonaDatos;
