import * as fmt from "@/utils/formato";

/* Las 9 cifras del modelo económico de un rollo o un material (las calcula
   Python: core.repositorio_inventario.metricas_rollo y
   core.repositorio_materiales.metricas_material — acá solo se formatean),
   en tres celdas de tabla (Gastos / Valor / Ganancias) con tres cifras
   apiladas cada una: la unitaria arriba y sus dos derivados abajo, en chico.
   Las dos tablas de Inventario reciben las mismas 9 claves.

   Dos reglas de lectura:
     · null es "todavía no se sabe" y se muestra "—", no "$0": un material
       sin precio de venta no vale $0, no se sabe cuánto vale.
     · solo la unitaria lleva el sufijo de la unidad (/un. o /m); las otras
       dos ya son montos totales, y cada una dice de qué total es. */

export const GRUPOS_PLATA = [
  { unitaria: "gasto_unitario",    derivados: [["gasto_mes", "este mes"], ["gasto_total", "total"]] },
  { unitaria: "valor_unitario",    derivados: [["valor_restante", "restante"], ["valor_vendido", "vendido"]] },
  // Una ganancia negativa es el único número de la tabla que hay que ver sin
  // buscarlo: se está vendiendo por menos de lo que costó.
  { unitaria: "ganancia_unitaria", derivados: [["ganancia_mes", "este mes"], ["ganancia_total", "total"]], resaltar: true },
];

function Linea({ valor, sufijo, principal, resaltar }) {
  const clase = principal ? "celda-combo__principal" : "celda-combo__detalle";
  if (valor == null) return <span className={`${clase} sin-dato`}>—</span>;
  return <span className={`${clase}${resaltar && valor < 0 ? " negativo" : ""}`}>{fmt.pesosConSigno(valor)}{sufijo}</span>;
}

export default function CeldasPlata({ obj, sufijo }) {
  return GRUPOS_PLATA.map(({ unitaria, derivados, resaltar }) => (
    <td key={unitaria}>
      <div className="celda-combo celda-combo--plata">
        <Linea valor={obj[unitaria]} sufijo={sufijo} principal resaltar={resaltar} />
        {derivados.map(([campo, etiqueta]) => (
          <Linea key={campo} valor={obj[campo]} sufijo={" " + etiqueta} resaltar={resaltar} />
        ))}
      </div>
    </td>
  ));
}
