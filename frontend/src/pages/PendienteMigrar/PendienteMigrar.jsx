import { useLocation } from "react-router";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";

/* Destino de toda ruta que todavía no tiene su página de React (y de los
   módulos mientras no se migran, con su tema y título). Se borra cuando
   termine la migración (ver router/RutasAnimadas.jsx). */
export default function PendienteMigrar({ tema, titulo = "Pantalla pendiente" }) {
  const { pathname } = useLocation();
  return (
    <Pagina tema={tema} titulo={titulo}>
      <Cabecera titulo={titulo} />
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
