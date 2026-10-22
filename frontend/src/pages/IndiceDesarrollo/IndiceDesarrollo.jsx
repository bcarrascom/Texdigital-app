import { useState } from "react";
import { Link } from "react-router";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Segmento from "@/components/Segmento/Segmento";
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
          <Muestrario />
        </div>
      </main>
    </Pagina>
  );
}

/* Componentes reutilizables en sus variantes, para revisarlos sin tener que
   llegar a la pantalla que los usa. */
const SWITCHES = [
  { titulo: "Textos parecidos", opciones: [{ valor: "Estándar" }, { valor: "Backlight" }] },
  { titulo: "Textos muy distintos", opciones: [{ valor: "Sí" }, { valor: "Solo si el cliente lo pide por escrito" }] },
  { titulo: "Vertical", vertical: true, opciones: [{ valor: "Caja terminada" }, { valor: "Área visual (medida interior)" }] },
  { titulo: "Bloque (todo el ancho)", bloque: true, opciones: [{ valor: "Por unidad" }, { valor: "Por metro" }] },
];

function Muestrario() {
  return (
    <section className="muestrario" data-tema="cotizaciones">
      <h2 className="seccion-titulo">Componentes · Segmento</h2>
      {SWITCHES.map((s) => <MuestraSegmento key={s.titulo} {...s} />)}
    </section>
  );
}

function MuestraSegmento({ titulo, opciones, vertical, bloque }) {
  const [valor, setValor] = useState(opciones[0].valor);
  return (
    <div className="muestrario__fila">
      <span className="muestrario__titulo">{titulo}</span>
      <Segmento opciones={opciones} valor={valor} onCambiar={setValor} etiqueta={titulo}
                vertical={vertical} bloque={bloque} />
    </div>
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
