/* Contenido de un módulo que todavía no se migró a React: está en el paso
   entre módulos con ←/→ igual que los demás, mostrando solo el aviso. Se
   borra cuando termine la migración. */
export default function ModuloPendiente() {
  return (
    <div className="tarjeta">
      <p className="antetitulo">Migración a React</p>
      <p className="subtitulo">
        Este módulo todavía no se migró. Mientras tanto, sigue disponible en la
        interfaz anterior (<code>python main.py</code> sin <code>--react</code>).
      </p>
    </div>
  );
}
