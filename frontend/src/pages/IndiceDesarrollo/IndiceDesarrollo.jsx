import { useState } from "react";
import { useMotionValue } from "motion/react";
import { Link } from "react-router";
import Pagina from "@/components/Pagina/Pagina";
import Cabecera from "@/components/Cabecera/Cabecera";
import Segmento from "@/components/Segmento/Segmento";
import { rutas } from "@/router/rutas";
import { CUADROS, ETAPAS, Sobre, TIEMPOS, animarCorreoEnviado } from "@/components/CorreoEnviado/CorreoEnviado";
import "./IndiceDesarrollo.css";

/* TEMPORAL (solo mientras dura la migración): abre cada página ya migrada
   con un número/ID a mano, para las que todavía no tienen cómo llegarse
   desde la app (su módulo no está migrado). Se entra desde el botón "dev"
   del pie del menú, que aparece con `npm run dev` y en la versión de
   desarrollo de la app (v0.0.0-dev), nunca en una publicada.

   Abajo, el muestrario de componentes y la animación "Correo enviado" para
   verla cuando se quiera y probar otros tiempos. */

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
          <MuestraCorreoEnviado />
          <Muestrario />
        </div>
      </main>
    </Pagina>
  );
}

/* "Correo enviado" (components/CorreoEnviado): reproducirla con los tiempos
   de la app u otros, más lento, y el sobre en grande cuadro a cuadro. Los
   tiempos de acá no se guardan: para dejarlos, se cambian en TIEMPOS. */
const VELOCIDADES = [{ valor: 1, etiqueta: "Normal" }, { valor: 0.5, etiqueta: "×½" }, { valor: 0.25, etiqueta: "×¼" }];

function MuestraCorreoEnviado() {
  const [tiempos, setTiempos] = useState(TIEMPOS);
  const [velocidad, setVelocidad] = useState(1);
  const [cuadro, setCuadro] = useState(CUADROS);
  const valorCuadro = useMotionValue(CUADROS);
  const cambiados = ETAPAS.filter((e) => tiempos[e.clave] !== TIEMPOS[e.clave]);
  const total = Object.values(tiempos).reduce((a, b) => a + b, 0);

  function moverCuadro(f) {
    setCuadro(f);
    valorCuadro.set(f);
  }

  return (
    <section className="muestrario muestra-correo" data-tema="cotizaciones">
      <h2 className="seccion-titulo">Animación · Correo enviado</h2>
      <div className="muestrario__fila">
        <span className="muestrario__titulo">Reproducir</span>
        <div className="muestra-correo__acciones">
          <button className="btn btn--primario btn--chico" type="button"
                  onClick={() => animarCorreoEnviado({ tiempos, velocidad })}>Reproducir</button>
          <Segmento etiqueta="Velocidad" opciones={VELOCIDADES} valor={velocidad} onCambiar={setVelocidad} />
          <span className="muestrario__titulo">{(total / velocidad / 1000).toFixed(2).replace(".", ",")} s</span>
        </div>
      </div>
      {ETAPAS.map((e) => (
        <label key={e.clave} className="muestrario__fila">
          <span className="muestrario__titulo">{e.nombre}</span>
          <span className="muestra-correo__rango">
            <input type="range" min={0} max={2000} step={10} value={tiempos[e.clave]}
                   onChange={(ev) => setTiempos({ ...tiempos, [e.clave]: Number(ev.target.value) })} />
            <span className="muestra-correo__ms" data-cambiado={tiempos[e.clave] !== TIEMPOS[e.clave] || undefined}>
              {tiempos[e.clave]} ms
            </span>
          </span>
        </label>
      ))}
      {cambiados.length > 0 && (
        <div className="muestrario__fila">
          <span className="muestrario__titulo">Cambiados</span>
          <span className="muestra-correo__acciones">
            <code className="muestra-correo__codigo">
              {cambiados.map((e) => `${e.clave}: ${tiempos[e.clave]}`).join(", ")}
            </code>
            <button className="btn btn--fantasma btn--chico" type="button" onClick={() => setTiempos(TIEMPOS)}>
              Volver a los de la app
            </button>
          </span>
        </div>
      )}
      <label className="muestrario__fila">
        <span className="muestrario__titulo">Cuadro a cuadro</span>
        <span className="muestra-correo__rango">
          <input type="range" min={0} max={CUADROS} step={0.25} value={cuadro}
                 onChange={(ev) => moverCuadro(Number(ev.target.value))} />
          <span className="muestra-correo__ms">
            {cuadro === CUADROS ? "abierto" : cuadro === 0 ? "cerrado" : `cuadro ${cuadro}`}
          </span>
        </span>
      </label>
      <div className="muestra-correo__grande">
        <Sobre cuadro={valorCuadro} className="muestra-correo__sobre" />
      </div>
    </section>
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
