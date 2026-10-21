import "./SwitchIconos.css";

/* Switch de íconos (2, 3 o más posiciones): una pastilla gris que abraza los
   círculos de cada opción, con un círculo blanco que se desliza por debajo
   del ícono elegido. Para elegir entre vistas u órdenes donde el ícono ya lo
   dice todo (el texto va en el title).

       <SwitchIconos valor={vista} onCambiar={setVista} etiqueta="Vista de inventario"
                     opciones={[{ valor: "textiles", Icono: Spiral, titulo: "Rollos de tela" },
                                { valor: "materiales", Icono: Boxes, titulo: "Materiales" }]} />

   A diferencia de components/Segmento (texto, siempre dos opciones), acá
   todas las opciones miden lo mismo, así que el desplazamiento es fijo. */
export default function SwitchIconos({ opciones, valor, onCambiar, etiqueta }) {
  const i = Math.max(0, opciones.findIndex((o) => o.valor === valor));
  return (
    <div className="switch-iconos" role="radiogroup" aria-label={etiqueta} style={{ "--i": i }}>
      <span className="switch-iconos__thumb" aria-hidden="true" />
      {opciones.map(({ valor: v, Icono, titulo }) => (
        <button key={v} type="button" className="switch-iconos__opt" role="radio"
                aria-checked={v === valor} title={titulo} onClick={() => onCambiar(v)}>
          <Icono aria-hidden="true" />
        </button>
      ))}
    </div>
  );
}
