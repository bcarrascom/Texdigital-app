/* Tres puntos en onda mientras se espera la respuesta de Python. Toman el
   color del tema de la página (--c-tema-fuerte). */
export default function Cargando() {
  return (
    <div className="cargando" role="status" aria-label="Cargando">
      <span /><span /><span />
    </div>
  );
}
