import { useState } from "react";
import { Link } from "react-router";
import Pagina from "@/components/Pagina/Pagina";
import { ControlTexto } from "@/components/Cabecera/Cabecera";
import { useApp } from "@/context/AppContext";
import { rutas } from "@/router/rutas";
import "./Inicio.css";

/* TEMPORAL: índice de desarrollo mientras el menú principal no esté migrado
   (es la última pantalla del plan). Permite abrir cada página ya migrada con
   un número/ID a mano. Se reemplaza por pages/Menu en esa etapa. */

const MIGRADAS = [
  { nombre: "Ver despacho", tema: "despachos", ruta: rutas.verDespacho, etiqueta: "N° de OP" },
];

export default function Inicio() {
  const { contexto } = useApp();
  return (
    <Pagina titulo="TexDigital" className="pag-inicio">
      <header className="cabecera">
        <img className="cabecera__logo" src="./img/logo_texdigital.png" alt="TexDigital" />
        <span className="cabecera__version">v{contexto.version}</span>
        <span className="cabecera__sep" />
        <ControlTexto />
      </header>
      <main className="contenido">
        <div className="limite--sm indice">
          <div>
            <p className="antetitulo">Migración a React · temporal</p>
            <h1 className="titulo">Pantallas migradas</h1>
            <p className="subtitulo">El menú principal llega al final; mientras tanto, se entra por acá.</p>
          </div>
          <ul className="indice__lista">
            {MIGRADAS.map((p) => <Entrada key={p.nombre} {...p} />)}
          </ul>
        </div>
      </main>
    </Pagina>
  );
}

function Entrada({ nombre, tema, ruta, etiqueta }) {
  const [valor, setValor] = useState("");
  return (
    <li className="indice__item" data-tema={tema}>
      <span className="indice__nombre">{nombre}</span>
      <input className="entrada" placeholder={etiqueta} value={valor}
             onChange={(e) => setValor(e.target.value.trim())} />
      <Link className={`btn btn--primario btn--chico${valor ? "" : " indice__btn--off"}`}
            to={valor ? ruta(valor) : "#"}>Abrir</Link>
    </li>
  );
}
