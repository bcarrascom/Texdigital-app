import { useState } from "react";
import { api } from "@/services/api";
import Dialogo from "@/components/Dialogo/Dialogo";
import Campo, { enterGuarda } from "@/components/Campo/Campo";
import Segmento from "@/components/Segmento/Segmento";
import IconoAviso from "@/assets/svg/circle-alert.svg?react";
import * as fmt from "@/utils/formato";

/* Agregar o editar lo que EXISTE en el catálogo (ver core/catalogo.py): un
   textil nuevo, renombrar uno, una estructura o terminación nueva. Se aplica
   al confirmar, no con la barra de "Guardar cambios" de la página. Los
   errores los decide Python ({campo: mensaje}) y se muestran en su campo. */

const SI_NO = [{ valor: false, etiqueta: "No" }, { valor: true, etiqueta: "Sí" }];
const UNIDADES = [{ valor: "un.", etiqueta: "Por unidad" }, { valor: "ML", etiqueta: "Por metro lineal" }];

const anchoTexto = (n) => (n == null ? "" : String(n).replace(".", ","));

export function useEnvio(enviar, onHecho) {
  const [errores, setErrores] = useState({});
  const [enviando, setEnviando] = useState(false);
  async function confirmar(e) {
    e?.preventDefault();
    if (enviando) return;
    setEnviando(true);
    try {
      const r = await enviar();
      if (r?.ok) await onHecho(r);
      else setErrores(r?.errores || { general: "No se pudo guardar." });
    } finally {
      setEnviando(false);
    }
  }
  return { errores, enviando, confirmar };
}

export function ErrorGeneral({ texto }) {
  return texto ? <p className="ajustes-nota ajustes-nota--aviso dlg-catalogo__nota" role="alert"><IconoAviso aria-hidden="true" />{texto}</p> : null;
}

// ── Textil: agregar (textil = null) o editar ───────────────────────────────

export function DialogoTextil({ abierto, textil, modoCobro, onCerrar, onHecho }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} className="dlg--desenfoque dlg-catalogo">
      <FormularioTextil textil={textil} modoCobro={modoCobro} onCerrar={onCerrar} onHecho={onHecho} />
    </Dialogo>
  );
}

function FormularioTextil({ textil, modoCobro, onCerrar, onHecho }) {
  const nuevo = !textil;
  const [f, setF] = useState({
    nombre: textil?.nombre ?? "", ancho: anchoTexto(textil?.ancho), backlight: !!textil?.backlight, valor: "",
  });
  const set = (clave, valor) => setF((x) => ({ ...x, [clave]: valor }));
  const { errores, enviando, confirmar } = useEnvio(
    () => (nuevo
      ? api.agregar_textil({ nombre: f.nombre, ancho: f.ancho, backlight: f.backlight, valor: fmt.leerClp(f.valor) })
      : api.editar_textil(textil.nombre, { nombre: f.nombre, ancho: f.ancho, backlight: f.backlight })),
    onHecho,
  );
  const renombra = !nuevo && f.nombre.trim() && f.nombre.trim() !== textil.nombre;
  const rollos = textil?.rollos?.rollos || 0;
  const valorOpcional = modoCobro === "rollo";

  return (
    <form onSubmit={confirmar} onKeyDown={enterGuarda} noValidate>
      <h2 className="dlg__titulo">{nuevo ? "Agregar textil" : "Editar textil"}</h2>
      <div className="dlg-catalogo__campos">
        <Campo id="cat-nombre" etiqueta="Nombre" requerido invalido={!!errores.nombre} error={errores.nombre}>
          <input className="entrada" id="cat-nombre" type="text" autoComplete="off" data-autofoco
                 value={f.nombre} onChange={(e) => set("nombre", e.target.value)} />
        </Campo>
        <Campo id="cat-ancho" etiqueta="Ancho de la tela (m)" requerido invalido={!!errores.ancho} error={errores.ancho}
               ayuda="El ancho del rollo: con él se calculan los metros lineales y el ancho máximo de impresión.">
          <input className="entrada entrada--num" id="cat-ancho" type="text" inputMode="decimal" autoComplete="off"
                 placeholder="1,48" value={f.ancho} onChange={(e) => set("ancho", e.target.value.replace(/[^\d,.]/g, ""))} />
        </Campo>
        <div className="campo">
          <span className="campo__etiqueta">Sirve para Backlight</span>
          <Segmento etiqueta="Sirve para Backlight" opciones={SI_NO} valor={f.backlight} onCambiar={(v) => set("backlight", v)} />
          <span className="campo__ayuda">Aparece en la lista de telas de Backlight del cotizador (tiene que ser translúcida).</span>
        </div>
        {nuevo && (
          <Campo id="cat-valor" etiqueta={valorOpcional ? "Valor por metro (opcional)" : "Valor por metro"} requerido={!valorOpcional}
                 invalido={!!errores.valor} error={errores.valor}
                 ayuda={valorOpcional ? "Los textiles se cobran por rollo: este valor se usa solo si no tiene rollos con valor." : "Por metro lineal; en Backlight, por m²."}>
            <input className="entrada entrada--num" id="cat-valor" type="text" inputMode="numeric" autoComplete="off"
                   placeholder="$0" value={f.valor} onChange={(e) => set("valor", fmt.clp(e.target.value))} />
          </Campo>
        )}
      </div>
      {renombra && (
        <p className="ajustes-nota ajustes-nota--aviso dlg-catalogo__nota" role="status">
          <IconoAviso aria-hidden="true" />
          <span>
            {rollos ? `${rollos === 1 ? "El rollo" : `Los ${rollos} rollos`} de ${textil.nombre} en Inventario pasan a llamarse «${f.nombre.trim()}». ` : ""}
            Las cotizaciones y OPs ya hechas conservan el nombre anterior y siguen funcionando: la app lo reconoce como el mismo textil.
          </span>
        </p>
      )}
      {/* Un campo opcional no muestra su error abajo (ver Campo): va acá. */}
      <ErrorGeneral texto={errores.general || (valorOpcional && errores.valor)} />
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit" disabled={enviando}>
          {nuevo ? "Agregar" : renombra ? "Renombrar" : "Guardar"}
        </button>
      </div>
    </form>
  );
}

// ── Estructura o terminación nueva ─────────────────────────────────────────

export function DialogoComponente({ abierto, tipo, singular, onCerrar, onHecho }) {
  return (
    <Dialogo abierto={abierto} onCerrar={onCerrar} className="dlg--desenfoque dlg-catalogo">
      <FormularioComponente tipo={tipo} singular={singular} onCerrar={onCerrar} onHecho={onHecho} />
    </Dialogo>
  );
}

function FormularioComponente({ tipo, singular, onCerrar, onHecho }) {
  const [f, setF] = useState({ nombre: "", unidad: "un.", valor: "" });
  const set = (clave, valor) => setF((x) => ({ ...x, [clave]: valor }));
  const { errores, enviando, confirmar } = useEnvio(
    () => api.agregar_componente(tipo, { nombre: f.nombre, unidad: f.unidad, valor: fmt.leerClp(f.valor) }),
    onHecho,
  );
  return (
    <form onSubmit={confirmar} onKeyDown={enterGuarda} noValidate>
      <h2 className="dlg__titulo">Agregar {singular}</h2>
      <div className="dlg-catalogo__campos">
        <Campo id="cat-nombre" etiqueta="Nombre" requerido invalido={!!errores.nombre} error={errores.nombre}
               ayuda="Así aparece en el cotizador y en la cotización.">
          <input className="entrada" id="cat-nombre" type="text" autoComplete="off" data-autofoco
                 value={f.nombre} onChange={(e) => set("nombre", e.target.value)} />
        </Campo>
        <div className="campo" data-invalido={errores.unidad ? "" : undefined}>
          <span className="campo__etiqueta">Se cobra</span>
          <Segmento etiqueta="Cómo se cobra" opciones={UNIDADES} valor={f.unidad} onCambiar={(v) => set("unidad", v)} />
          <span className="campo__ayuda">
            {f.unidad === "ML" ? "Por cada metro lineal impreso: solo se puede usar en productos con textil." : "Por cada unidad del producto."}
          </span>
        </div>
        <Campo id="cat-valor" etiqueta="Valor" requerido invalido={!!errores.valor} error={errores.valor}>
          <input className="entrada entrada--num" id="cat-valor" type="text" inputMode="numeric" autoComplete="off"
                 placeholder="$0" value={f.valor} onChange={(e) => set("valor", fmt.clp(e.target.value))} />
        </Campo>
      </div>
      <ErrorGeneral texto={errores.general} />
      <div className="dlg__acciones">
        <button className="btn btn--fantasma btn--chico" type="button" onClick={onCerrar}>Cancelar</button>
        <button className="btn btn--primario btn--chico" type="submit" disabled={enviando}>Agregar</button>
      </div>
    </form>
  );
}
