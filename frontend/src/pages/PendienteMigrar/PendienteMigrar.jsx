import { useLocation } from "react-router";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";

/* Destino de toda ruta que todavía no tiene su página de React. Se borra
   cuando termine la migración (ver router/RutasAnimadas.jsx). */
export default function PendienteMigrar() {
  const { pathname } = useLocation();
  return (
    <Pagina titulo="Pendiente">
      <Cabecera titulo="Pantalla pendiente" />
      <main className="contenido contenido--centrado">
        <div className="tarjeta limite--sm">
          <p className="antetitulo">Migración a React</p>
          <h1 className="titulo">Esta pantalla todavía no se migró</h1>
          <p className="subtitulo">
            No hay página para <code>{pathname}</code>. Mientras tanto, sigue
            disponible en la interfaz anterior (<code>python main.py</code> sin <code>--react</code>).
          </p>
        </div>
      </main>
    </Pagina>
  );
}
