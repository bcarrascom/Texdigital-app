import { Component } from "react";
import { useNavigate } from "react-router";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import "./FallaPantalla.css";

/* Red de seguridad para cuando una pantalla falla al dibujarse. Sin esto,
   React desmonta todo y la ventana queda en blanco y sin forma de salir (se
   vio con una cotización de backlight con caja: había que cerrar la app
   desde el Administrador de tareas). Con esto, la pantalla dice que falló y
   deja volver.

       <FallaPantalla clave={location.pathname}>…las rutas…</FallaPantalla>

   `clave` cambia al navegar: así, volver o ir al menú desarma el aviso y
   la pantalla siguiente se dibuja normal. */
export default class FallaPantalla extends Component {
  state = { error: null, clave: this.props.clave };

  static getDerivedStateFromError(error) {
    return { error };
  }

  static getDerivedStateFromProps(props, state) {
    return props.clave !== state.clave ? { error: null, clave: props.clave } : null;
  }

  componentDidCatch(error, info) {
    console.error("Falló al dibujar la pantalla:", error, info.componentStack);
  }

  render() {
    return this.state.error ? <AvisoFalla error={this.state.error} /> : this.props.children;
  }
}

function AvisoFalla({ error }) {
  const navigate = useNavigate();
  return (
    <Pagina titulo="Algo falló">
      <Cabecera titulo="Algo falló" />
      <main className="contenido contenido--centrado">
        <div className="tarjeta limite--sm">
          <h1 className="titulo">Algo falló al mostrar esta pantalla</h1>
          <p className="subtitulo">
            No se perdió nada de lo guardado. Vuelve atrás o al menú; si se repite, avisa
            qué estabas abriendo y este detalle:
          </p>
          <code className="falla__detalle">{String(error?.message || error)}</code>
          <button className="btn btn--primario falla__boton" onClick={() => navigate("/", { replace: true })}>
            Ir al menú
          </button>
        </div>
      </main>
    </Pagina>
  );
}
