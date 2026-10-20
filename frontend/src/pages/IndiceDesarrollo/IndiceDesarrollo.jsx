import { useState } from "react";
import { Link } from "react-router";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import { rutas } from "@/router/rutas";
import "./IndiceDesarrollo.css";

/* TEMPORAL (solo mientras dura la migración): abre cada página ya migrada
   con un número/ID a mano, para las que todavía no tienen cómo llegarse
   desde la app (su módulo no está migrado). Se entra desde el botón "dev"
   del pie del menú, que solo aparece con `npm run dev`. */

const MIGRADAS = [
  { nombre: "Ver despacho", tema: "despachos", ruta: rutas.verDespacho, etiqueta: "N° de OP" },
];

export default function IndiceDesarrollo() {
  return (
    <Pagina titulo="Desarrollo" className="pag-indice-desarrollo">
      <Cabecera titulo="Pantallas migradas" />
      <main className="contenido">
        <div className="limite--sm indice">
          <div>
            <p className="antetitulo">Migración a React · temporal</p>
            <h1 className="titulo">Pantallas migradas</h1>
            <p className="subtitulo">Para abrir las que todavía no se alcanzan desde su módulo.</p>
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
