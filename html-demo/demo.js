/* ═══════════════════════════════════════════════════════════════════════════
   demo.js — el "programa" de mentira que conecta las tres pantallas.

   Reemplaza a los tres mocks sueltos (mocks/menu.js, mocks/cotizacion.js,
   mocks/ver-cotizacion.js) por uno solo que además GUARDA: las cotizaciones
   que creás quedan en localStorage, así el menú las lista y ver-cotizacion.html
   las puede abrir.

   OJO — esto NO es la app. Es andamiaje para poder recorrer el flujo completo
   en el navegador y ver si los diseños calzan entre sí:

     · las cifras salen de una fórmula inventada (`calcular_producto` acá
       abajo). En la app salen de core/precios.py y core/calculo_cajas.py, y
       el HTML no calcula nada;
     · la navegación es `location.href`. En la app la ventana la maneja
       pywebview desde Python;
     · el almacenamiento es localStorage. En la app son los JSON de Dropbox.

   Cuando Claude Code integre las pantallas, este archivo se borra entero y en
   su lugar van las clases `Api` de Python. Nada de lo que hay acá se migra.

   Para empezar de cero:  abrí la consola del navegador y escribí  TDdemo.reset()
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ── Almacén ──────────────────────────────────────────────────────────────
     localStorage anda sobre file:// en Chrome y Edge (probado). Si algún día
     no anduviera, `window.name` sobrevive a la navegación dentro de la misma
     pestaña y sirve de red. */

  const CLAVE = "texdigital_demo_v1";

  function leerCrudo() {
    try {
      const v = localStorage.getItem(CLAVE);
      if (v) return v;
    } catch (e) { /* file:// con almacenamiento bloqueado */ }
    return window.name && window.name.startsWith("{") ? window.name : null;
  }

  function escribirCrudo(txt) {
    try { localStorage.setItem(CLAVE, txt); } catch (e) { /* ídem */ }
    window.name = txt;
  }

  let bd = null;

  function cargar() {
    if (bd) return bd;
    const crudo = leerCrudo();
    if (crudo) {
      try { bd = JSON.parse(crudo); } catch (e) { bd = null; }
    }
    if (!bd || !bd.cotizaciones) bd = semilla();
    return bd;
  }

  function guardar() {
    escribirCrudo(JSON.stringify(bd));
  }

  /* ── Utilidades ─────────────────────────────────────────────────────────── */

  const num = (v) => { const x = parseFloat(String(v).replace(",", ".")); return isNaN(x) ? 0 : x; };
  const ent = (v) => parseInt(v, 10) || 0;
  const suma = (o) => Object.values(o || {}).reduce((a, b) => a + b, 0);

  function hoyISO() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  function aFechaLarga(iso) {
    if (!iso) return "";
    const [a, m, d] = String(iso).split("-");
    return d && m && a ? `${d}-${m}-${a}` : iso;
  }

  /* El parámetro de la URL: ver-cotizacion.html?n=6708 */
  function parametro(nombre) {
    const m = new RegExp("[?&]" + nombre + "=([^&]*)").exec(location.search);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function irA(pagina) { location.href = pagina; }

  /* ── Catálogos (recortes de recursos/*.json) ─────────────────────────────── */

  const TEXTILES = {
    "Bistretch": 1.48, "Mesh": 2.80, "Denim crudo 6 onzas": 1.48,
    "Lino": 1.50, "Popelina 155": 1.55, "Popelina 310": 3.10,
    "Pearl 155": 1.55, "Pearl 310": 3.10, "Pearl 160 HP": 1.60,
    "Gabardina": 1.50, "Raso": 1.45, "Microfibra": 1.60,
  };

  const CATALOGOS = {
    productos: [
      "Solo estructura", "Bandera 2,3x1,5", "Textil panel araña 3 cuerpos (228x230 cms)",
      "Roller", "Pendón", "Backing 3x2", "Mesón cubre textil", "Lienzo",
    ],
    textiles: Object.keys(TEXTILES),
    textiles_anchos: TEXTILES,
    telas_backlight: ["Popelina 155", "Popelina 310", "Pearl 155", "Pearl 310", "Pearl 160 HP"],
    estructuras: [
      "Base auto", "Estructura panel araña 3 cuerpos", "Tubo aluminio",
      "Estructura roller", "Marco de aluminio", "Base cruz",
    ],
    terminaciones: ["Basta", "Ojetillos", "Panel araña", "Velcro", "Bolsillo", "Refuerzo"],
    perfiles: ["PERFIL 60 MM", "PERFIL 100 MM DOBLE", "PERFIL 120 MM DOBLE",
               "PERFIL 80 MM", "PERFIL 150 MM DOBLE"],
    luces: ["sin luces", "M12", "Malla 12v", "Malla 150", "M8", "Tira 24v"],
    clientes: [
      { empresa: "KFC Belloto", rut: "76.123.456-7", razon_social: "Inversiones Belloto SpA" },
      { empresa: "Falabella Retail S.A.", rut: "77.261.280-K", razon_social: "Falabella Retail S.A." },
      { empresa: "Sodimac", rut: "96.792.430-K", razon_social: "Sodimac S.A." },
    ],
    contactos: [
      { contacto: "Loreto Olguín", email: "loreto.olguin@ejemplo.cl", descuento: "10", condicion: "30 días" },
      { contacto: "Marcelo Díaz", email: "mdiaz@ejemplo.cl", descuento: "0", condicion: "Contado" },
    ],
  };

  /* ── El "core/precios.py" de mentira ─────────────────────────────────────── */

  function calcular(p) {
    const ancho = num(p.ancho), alto = num(p.alto), cant = ent(p.cantidad);
    if (!ancho || !alto || !cant) return null;

    const tela = p.tipo === "backlight" ? p.tela : p.textil;
    const anchoMax = TEXTILES[tela];
    const corto = Math.min(ancho, alto);
    const error = anchoMax && corto > anchoMax
      ? `El lado corto (${corto} m) excede el ancho máximo del textil (${anchoMax} m).`
      : null;

    if (p.tipo === "backlight") {
      const materiales = [];
      if (p.perfil && p.perfil !== "Sin caja") {
        materiales.push({ material: "Traseras", tipo: "Alucobond 3 mm", cantidad_x_caja: 1, cantidad_total: cant });
        if (p.luces_1 && p.luces_1 !== "sin luces")
          materiales.push({ material: "Luces 1", tipo: p.luces_1, cantidad_x_caja: 6, cantidad_total: 6 * cant });
        if (p.luces_2 && p.luces_2 !== "sin luces")
          materiales.push({ material: "Luces 2", tipo: p.luces_2, cantidad_x_caja: 4, cantidad_total: 4 * cant });
        materiales.push({ material: "FP", tipo: "FP 150 watts- 24v MEAN WELL", cantidad_x_caja: 1, cantidad_total: cant });
      }
      return {
        m2: +(ancho * alto * cant).toFixed(4),
        watts: materiales.length ? 126 : 0,
        materiales,
        ancho_max: anchoMax || null,
        error,
      };
    }

    const doble = p.impresion === "Tiro y retiro" ? 2 : 1;
    const ml = +(Math.max(ancho, alto) * cant * doble).toFixed(2);
    const costo_impresion = Math.round(ml * 9800);
    const detalle_estructuras = {}, detalle_terminaciones = {};
    (p.estructuras || []).forEach((n, i) => { detalle_estructuras[n] = 11000 + i * 2500; });
    (p.terminaciones || []).forEach((n, i) => { detalle_terminaciones[n] = Math.round(ml * (1140 + i * 360)); });
    const costo_extras = suma(detalle_estructuras) + suma(detalle_terminaciones);
    const total = costo_impresion + costo_extras;

    return {
      ml, costo_impresion, costo_extras,
      detalle_estructuras, detalle_terminaciones,
      total, valor_unitario: Math.round(total / cant),
      ancho_max: anchoMax || null,
      error,
    };
  }

  /* ── estado (pizarra) → cotización guardada (la que lee ver-cotizacion) ──── */

  function aCotizacion(estado) {
    const c = estado.cliente || {};
    const productos = (estado.productos || []).map((p) => {
      const k = p.calc || calcular(p) || {};
      const bl = p.tipo === "backlight";
      return {
        tipo: p.tipo,
        producto: bl ? "" : p.producto,
        textil: bl ? "" : p.textil,
        impresion: bl ? "" : p.impresion,
        estructuras: bl ? [] : (p.estructuras || []).slice(),
        terminaciones: bl ? [] : (p.terminaciones || []).slice(),
        tela: bl ? p.tela : "",
        caja: bl ? p.perfil : "",
        tema: p.tema, obs: p.obs,
        ancho: num(p.ancho), alto: num(p.alto), cantidad: ent(p.cantidad),
        ml: k.ml != null ? k.ml : null,
        m2: k.m2 != null ? k.m2 : null,
        total: k.total != null ? k.total : null,
      };
    });

    const calcs = (estado.productos || []).map((p) => p.calc || calcular(p) || {});
    const impresion    = calcs.reduce((a, k) => a + (k.costo_impresion || 0), 0);
    const estructuras  = calcs.reduce((a, k) => a + suma(k.detalle_estructuras), 0);
    const terminaciones = calcs.reduce((a, k) => a + suma(k.detalle_terminaciones), 0);
    const productosNeto = calcs.reduce((a, k) => a + (k.total || 0), 0);

    const despacho = estado.despacho || null;
    const instalacion = estado.instalacion || null;
    const neto = productosNeto + (despacho || 0) + (instalacion || 0);
    const pct = num(c.descuento);
    const descuento_monto = Math.round(neto * pct / 100);
    const neto_total = neto - descuento_monto;
    const iva = Math.round(neto_total * 0.19);

    return {
      numero: ent(c.numero),
      nombre: estado.nombre_trabajo || "",
      empresa: c.empresa || "", rut: c.rut || "", razon_social: c.razon_social || "",
      contacto: c.contacto || "", email: c.email || "", condicion: c.condicion || "",
      fecha: aFechaLarga(c.fecha) || aFechaLarga(hoyISO()),
      fecha_iso: c.fecha || hoyISO(),
      descripcion: c.descripcion || "",
      totales: {
        impresion: impresion || null,
        estructuras: estructuras || null,
        terminaciones: terminaciones || null,
        despacho, instalacion,
        neto,
        descuento_pct: pct || 0,
        descuento_monto: descuento_monto || 0,
        fuente_descuento: "normal",
        neto_total,
        iva_pct: 19, iva,
        total: neto_total + iva,
      },
      productos,
      /* El `estado` crudo se guarda al lado para que "Editar" pueda volver a
         la pizarra sin perder nada. En la app esto no existe: allá se
         reconstruye con core/repositorio_cotizaciones.producto_desde_json. */
      _estado: estado,
    };
  }

  /* ── cotización aprobada → OP (la que lee ver-op) ────────────────────────
     Una OP es para producción, no para plata: nada de montos, descuentos ni
     IVA. Lleva las dos fechas del diálogo de aprobar y, de cada producto,
     todo menos el total — layer/precio no le sirve a la estación de
     impresión. `direccion` no tiene de dónde salir todavía (no hay campo de
     dirección de despacho en ningún lado de la cotización): queda en null a
     propósito, no es un dato que se está perdiendo.

     `estado` es uno de "activa" | "entregada" | "entregada_atrasada" |
     "cancelada" — lo que lee el historial para la etiqueta de cada fila.
     Toda OP nace "activa"; los otros tres solo los pone la semilla acá
     abajo (todavía no hay pantalla que cierre o cancele una OP). */
  function aOp(cot, ingresoISO, entregaISO, estado) {
    return {
      numero: cot.numero,
      nombre: cot.nombre || "",
      empresa: cot.empresa || "",
      contacto: cot.contacto || "",
      email: cot.email || "",
      descripcion: cot.descripcion || "",
      fecha_ingreso: aFechaLarga(ingresoISO),
      fecha_entrega: aFechaLarga(entregaISO),
      estado: estado || "activa",
      despacho: !!(cot.totales && cot.totales.despacho != null),
      instalacion: !!(cot.totales && cot.totales.instalacion != null),
      direccion: null,
      productos: (cot.productos || []).map((p) => {
        const copia = Object.assign({}, p);
        delete copia.total;
        return copia;
      }),
    };
  }

  function isoOffset(dias) {
    const d = new Date(); d.setDate(d.getDate() + dias);
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  /* ── Semilla: sin esto el menú arranca vacío y no se ve nada ─────────────── */

  function semilla() {
    const cot = (numero, empresa, dias, productos, extras) => {
      const d = new Date(); d.setDate(d.getDate() - dias);
      const p = (n) => String(n).padStart(2, "0");
      const iso = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
      const estado = Object.assign({
        id: null, nombre_trabajo: "", despacho: null, instalacion: null,
        cliente: {
          empresa, rut: "77.261.280-K", razon_social: empresa,
          contacto: "Loreto Olguín", email: "loreto.olguin@ejemplo.cl",
          descuento: "10", condicion: "30 días",
          fecha: iso, numero: String(numero), descripcion: "",
        },
        productos, actual: 0,
      }, extras || {});
      estado.productos.forEach((x) => { x.calc = calcular(x); });
      return aCotizacion(estado);
    };

    const prod = (o) => Object.assign({
      tipo: "estandar", producto: "", textil: "Bistretch", impresion: "Cara única",
      estructuras: [], terminaciones: [], tela: "", perfil: "Sin caja",
      luces_1: "", luces_2: "sin luces", terminaciones_caja: "CAJA TERMINADA",
      ancho: "", alto: "", cantidad: "1", tema: "", obs: "", forzar: false, calc: null,
    }, o);

    const c1 = cot(6708, "Falabella Retail S.A.", 7, [
      prod({ producto: "Backing 3x2", ancho: "3", alto: "2", cantidad: "4",
             tema: "Primavera 2026", estructuras: ["Marco de aluminio"],
             terminaciones: ["Basta", "Ojetillos"] }),
      prod({ producto: "Pendón", impresion: "Tiro y retiro", ancho: "0,9", alto: "2,1",
             cantidad: "12", tema: "Ofertas fin de semana", estructuras: ["Tubo aluminio"],
             terminaciones: ["Bolsillo", "Refuerzo"], obs: "Entregar enrollados, no doblados." }),
      prod({ tipo: "backlight", tela: "Pearl 310", perfil: "PERFIL 100 MM DOBLE",
             luces_1: "M12", ancho: "2,4", alto: "1,2", cantidad: "2", tema: "Vitrina principal" }),
      prod({ producto: "Lienzo", textil: "Mesh", ancho: "8", alto: "1,2", cantidad: "1",
             tema: "Fachada calle Valparaíso", terminaciones: ["Basta", "Ojetillos"] }),
      prod({ producto: "Textil panel araña 3 cuerpos (228x230 cms)", ancho: "2,28", alto: "2,3",
             cantidad: "3", tema: "Isla de atención",
             estructuras: ["Estructura panel araña 3 cuerpos"], terminaciones: ["Panel araña"] }),
    ], { nombre_trabajo: "Renovación gráfica sucursal Viña Centro", despacho: 85000, instalacion: 240000 });
    c1.descripcion = "Cambio de imagen temporada primavera. Incluye instalación en horario nocturno.";
    c1._estado.cliente.descripcion = c1.descripcion;

    const c2 = cot(6711, "KFC Belloto", 4, [
      prod({ producto: "Roller", ancho: "1,2", alto: "2", cantidad: "2", tema: "Combos 2026",
             estructuras: ["Estructura roller"], terminaciones: ["Basta"] }),
    ], { nombre_trabajo: "Señalética local Belloto" });

    const c3 = cot(6712, "Sodimac", 2, [
      prod({ producto: "Bandera 2,3x1,5", ancho: "1,5", alto: "2,3", cantidad: "6",
             tema: "Liquidación jardín", estructuras: ["Base auto"], terminaciones: ["Bolsillo"] }),
      prod({ tipo: "backlight", tela: "Popelina 155", perfil: "PERFIL 60 MM",
             ancho: "1,5", alto: "0,45", cantidad: "6", tema: "Cenefa caja central" }),
    ], { nombre_trabajo: "Campaña jardín primavera", despacho: 45000 });

    /* Las OP se arman igual que una cotización (mismo helper `cot`, mismos
       `prod`) y después se les pasa por `aOp`, que les saca la plata y les
       pone las dos fechas — es el mismo camino que sigue una aprobación de
       verdad, solo que con fechas relativas a hoy en vez de al diálogo. */
    const op1 = aOp(cot(6710, "KFC Belloto", 15, [
      prod({ producto: "Roller", ancho: "1,2", alto: "2", cantidad: "2", tema: "Combos 2026",
             estructuras: ["Estructura roller"], terminaciones: ["Basta"] }),
    ], { nombre_trabajo: "Señalética local Belloto" }), isoOffset(-10), isoOffset(-1));

    const op2 = aOp(cot(6707, "Falabella Retail S.A.", 12, [
      prod({ producto: "Backing 3x2", ancho: "3", alto: "2", cantidad: "4",
             tema: "Primavera 2026", estructuras: ["Marco de aluminio"],
             terminaciones: ["Basta", "Ojetillos"] }),
      prod({ tipo: "backlight", tela: "Pearl 310", perfil: "PERFIL 100 MM DOBLE",
             luces_1: "M12", ancho: "2,4", alto: "1,2", cantidad: "2", tema: "Vitrina principal" }),
    ], { nombre_trabajo: "Renovación gráfica sucursal Viña Centro", despacho: 85000, instalacion: 240000 }),
      isoOffset(-6), isoOffset(0));

    /* Las que siguen ya no están activas: entregadas (a tiempo o atrasadas)
       y una cancelada, repartidas en los meses de atrás — es lo que hace
       que el selector de mes/año del historial tenga algo real que mostrar
       al moverse fuera del mes actual. */
    const op3 = aOp(cot(6701, "Sodimac", 40, [
      prod({ producto: "Mesón cubre textil", ancho: "1,8", alto: "0,9", cantidad: "3",
             tema: "Feria del hogar", estructuras: ["Base cruz"], terminaciones: ["Velcro"] }),
    ], { nombre_trabajo: "Feria del hogar — mesones" }),
      isoOffset(-45), isoOffset(-35), "entregada");

    const op4 = aOp(cot(6695, "KFC Belloto", 60, [
      prod({ producto: "Pendón", ancho: "0,9", alto: "2,1", cantidad: "8",
             tema: "Verano 2026", estructuras: ["Tubo aluminio"], terminaciones: ["Bolsillo"] }),
      prod({ tipo: "backlight", tela: "Popelina 310", perfil: "PERFIL 80 MM",
             ancho: "1,8", alto: "0,6", cantidad: "3", tema: "Cenefa entrada" }),
    ], { nombre_trabajo: "Campaña verano Belloto" }),
      isoOffset(-70), isoOffset(-55), "entregada_atrasada");

    const op5 = aOp(cot(6688, "Falabella Retail S.A.", 75, [
      prod({ producto: "Lienzo", textil: "Gabardina", ancho: "6", alto: "1,5", cantidad: "1",
             tema: "Fachada Costanera", terminaciones: ["Ojetillos"] }),
    ], { nombre_trabajo: "Fachada Falabella Costanera" }),
      isoOffset(-90), isoOffset(-75), "cancelada");

    const op6 = aOp(cot(6675, "Entel Chile", 100, [
      prod({ producto: "Roller", ancho: "1", alto: "1,8", cantidad: "5",
             tema: "Planes empresa", estructuras: ["Estructura roller"], terminaciones: ["Basta"] }),
    ], { nombre_trabajo: "Señalética tiendas Entel" }),
      isoOffset(-115), isoOffset(-102), "entregada");

    return {
      siguiente: 6713,
      cotizaciones: [c3, c2, c1],
      pendientes: [
        { id: "a1c9f2e40b77", nombre_trabajo: "Falabella Costanera — vitrinas", completos: 3, total: 7, estado: null },
      ],
      /* Todas las OP alguna vez, cualquiera sea su estado — "OPs activas" en
         el menú es un filtro sobre esta misma lista, no una lista aparte. */
      historial: [op1, op2, op3, op4, op5, op6],
      escala_ui: 1,
    };
  }

  /* ── Acceso ─────────────────────────────────────────────────────────────── */

  function buscar(numero) {
    return cargar().cotizaciones.find((c) => c.numero === ent(numero)) || null;
  }

  function buscarOp(numero) {
    return cargar().historial.find((o) => o.numero === ent(numero)) || null;
  }

  function opsActivas() {
    return cargar().historial.filter((o) => o.estado === "activa");
  }

  /* "DD-MM-AAAA" → { anio, mes } (mes 1-12), para agrupar por carpeta sin
     tocar el formato que ya usa toda la pantalla. */
  function anioMesDe(fechaDMA) {
    const [d, m, a] = String(fechaDMA || "").split("-").map(Number);
    return d && m && a ? { anio: a, mes: m } : null;
  }

  /* Sí o sí un textil, un material de caja o una estructura de alguno de los
     productos — es lo que busca el filtro de "materiales" del historial. */
  function opTieneMaterial(op, termino) {
    const t = termino.toLowerCase();
    return (op.productos || []).some((p) => {
      const bl = p.tipo === "backlight";
      const candidatos = bl ? [p.tela, p.caja] : [p.textil, ...(p.estructuras || [])];
      return candidatos.some((c) => c && c.toLowerCase().includes(t));
    });
  }

  function ordenar() {
    bd.cotizaciones.sort((a, b) => b.numero - a.numero);
  }

  const contextoBase = () => ({
    version: "demo",
    escala_ui: cargar().escala_ui || 1,
    hoy_iso: hoyISO(),
    fecha: aFechaLarga(hoyISO()),
  });

  const preferencia = (clave, valor) => {
    cargar();
    if (clave === "escala_ui") { bd.escala_ui = valor; guardar(); }
    return true;
  };

  /* ═══ Pantalla: menu ═════════════════════════════════════════════════════ */

  TD.mock("menu", {
    obtener_contexto: contextoBase,

    obtener_resumen: () => {
      const d = cargar();
      return {
        pendientes: d.pendientes.map((p) => ({
          id: p.id, nombre_trabajo: p.nombre_trabajo, completos: p.completos, total: p.total,
        })),
        cotizaciones: d.cotizaciones.map((c) => ({
          numero: c.numero, empresa: c.empresa, fecha: c.fecha,
        })),
        ops: opsActivas(),
      };
    },

    ir: (destino) => {
      if (destino === "nueva_cotizacion") return irA("nueva-cotizacion.html");
      if (destino === "historial_ops") return irA("historial-ops.html");
      TD.aviso(`Todavía no hay pantalla para "${destino}".`, "aviso");
    },

    abrir_cotizacion: (n) => irA("ver-cotizacion.html?n=" + n),
    abrir_pendiente: (id) => irA("nueva-cotizacion.html?pendiente=" + encodeURIComponent(id)),
    abrir_op: (n) => irA("ver-op.html?n=" + n),
    buscar_actualizacion: () => TD.aviso("En la app esto busca una versión nueva.", "info"),
    abrir_manual: () => TD.aviso("En la app esto abre el manual en PDF.", "info"),
    guardar_preferencia: preferencia,
  });

  /* ═══ Pantalla: cotizacion (nueva-cotizacion.html) ════════════════════════ */

  TD.mock("cotizacion", {
    obtener_contexto: () => {
      const d = cargar();
      const ctx = contextoBase();
      ctx.fecha_iso = hoyISO();
      ctx.numero_sugerido = String(d.siguiente);
      ctx.estado = null;

      /* Retomar una incompleta, o editar una guardada: las dos cosas son
         "arrancar con un estado ya hecho". */
      const idPend = parametro("pendiente");
      if (idPend) {
        const p = d.pendientes.find((x) => x.id === idPend);
        if (p && p.estado) ctx.estado = p.estado;
      }
      const nEdit = parametro("editar");
      if (nEdit) {
        const c = buscar(nEdit);
        if (c && c._estado) {
          ctx.estado = c._estado;
          ctx.numero_sugerido = String(c.numero);
        }
      }
      return ctx;
    },

    obtener_catalogos: () => CATALOGOS,
    calcular_producto: calcular,

    guardar_progreso: (estado) => {
      const d = cargar();
      const completos = (estado.productos || []).filter(
        (p) => num(p.ancho) > 0 && num(p.alto) > 0 && ent(p.cantidad) > 0).length;
      const id = estado.id || ("p" + Date.now().toString(36));
      const fila = {
        id,
        nombre_trabajo: estado.nombre_trabajo || "Sin nombre",
        completos,
        total: (estado.productos || []).length,
        estado: estado,
      };
      const i = d.pendientes.findIndex((p) => p.id === id);
      if (i >= 0) d.pendientes[i] = fila; else d.pendientes.push(fila);
      guardar();
      const ahora = new Date();
      const p2 = (n) => String(n).padStart(2, "0");
      return { id, guardado_en: `${aFechaLarga(hoyISO())} ${p2(ahora.getHours())}:${p2(ahora.getMinutes())}` };
    },

    guardar_cotizacion: (estado) => {
      const d = cargar();
      const cot = aCotizacion(estado);
      if (!cot.numero) return { error: "Falta el N° de cotización." };

      const i = d.cotizaciones.findIndex((c) => c.numero === cot.numero);
      if (i >= 0) d.cotizaciones[i] = cot; else d.cotizaciones.push(cot);
      ordenar();

      if (cot.numero >= d.siguiente) d.siguiente = cot.numero + 1;
      /* Al guardar, la incompleta de la que venía deja de estar incompleta. */
      if (estado.id) d.pendientes = d.pendientes.filter((p) => p.id !== estado.id);
      guardar();

      /* Guardar siempre lleva a la vista de la cotización: es lo que se quiere
         mirar después de guardarla, y de paso encadena las tres pantallas. */
      setTimeout(() => irA("ver-cotizacion.html?n=" + cot.numero), 450);
      return { numero: cot.numero };
    },

    guardar_cliente: () => TD.aviso("Cliente guardado en la libreta.", "info", 2000),
    guardar_contacto: () => TD.aviso("Contacto guardado en la libreta.", "info", 2000),
    /* Igual que ver-cotizacion/ver-op: volver lleva al panel de Cotizaciones
       del menú, no al menú principal — es de "Nueva cotización" ahí que se
       vino, sea desde cero o retomando una incompleta. */
    volver: () => irA("menu.html?panel=cotizaciones"),
    abrir_manual: () => TD.aviso("En la app esto abre el manual en PDF.", "info"),
    guardar_preferencia: preferencia,
  });

  /* ═══ Pantalla: ver-cotizacion ═══════════════════════════════════════════ */

  TD.mock("ver-cotizacion", {
    obtener_contexto: () => {
      const ctx = contextoBase();
      const n = parametro("n");
      const d = cargar();
      /* Sin ?n=, abre la más nueva: así el archivo se puede abrir suelto de un
         doble clic y muestra algo. */
      ctx.numero = n ? ent(n) : (d.cotizaciones[0] ? d.cotizaciones[0].numero : 0);
      return ctx;
    },

    obtener_cotizacion: (numero) => buscar(numero),

    eliminar_cotizacion: (numero) => {
      const d = cargar();
      d.cotizaciones = d.cotizaciones.filter((c) => c.numero !== ent(numero));
      guardar();
      irA("menu.html");
    },

    editar_cotizacion: (numero) => irA("nueva-cotizacion.html?editar=" + numero),

    imprimir_cotizacion: () => TD.aviso(
      "En la app esto genera el HTML de impresión (core/presentar_cotizacion.py) y lo abre en el navegador. Esa plantilla todavía no está rediseñada.",
      "aviso", 7000),

    aprobar_cotizacion: (numero, ingreso, entrega) => {
      const d = cargar();
      const c = buscar(numero);
      if (c) {
        d.historial.unshift(aOp(c, ingreso, entrega));
        d.cotizaciones = d.cotizaciones.filter((x) => x.numero !== c.numero);
        guardar();
      }
      irA("menu.html");
    },

    /* Volver de ver una cotización lleva de nuevo al panel de Cotizaciones
       del menú, no al menú principal: es de ahí que se vino. */
    volver: () => irA("menu.html?panel=cotizaciones"),
    abrir_manual: () => TD.aviso("En la app esto abre el manual en PDF.", "info"),
    guardar_preferencia: preferencia,
  });

  /* ═══ Pantalla: ver-op ═══════════════════════════════════════════════════ */

  TD.mock("ver-op", {
    obtener_contexto: () => {
      const ctx = contextoBase();
      const n = parametro("n");
      const d = cargar();
      /* Mismo criterio que ver-cotizacion: sin ?n=, la más nueva — de las
         activas si hay alguna, porque es la que tiene sentido mirar de
         entrada; si no, la que sea. */
      const activas = opsActivas();
      ctx.numero = n ? ent(n) : (activas[0] || d.historial[0] || {}).numero || 0;
      return ctx;
    },

    obtener_op: (numero) => buscarOp(numero),

    imprimir_op: () => TD.aviso(
      "En la app esto genera la orden de producción (core/presentar_op.py) y la abre en el navegador. Esa plantilla todavía no está rediseñada.",
      "aviso", 7000),

    /* "Volver" tiene que devolver a donde se vino: al panel de Ops del menú
       si se abrió desde ahí, o al historial si se abrió desde ahí — la
       pantalla que abre pasa `?volver=` para decirlo (ver historial-ops). */
    volver: () => irA(parametro("volver") === "historial" ? "historial-ops.html" : "menu.html?panel=ops"),
    abrir_manual: () => TD.aviso("En la app esto abre el manual en PDF.", "info"),
    guardar_preferencia: preferencia,
  });

  /* ═══ Pantalla: historial-ops ═════════════════════════════════════════════
     En la app real cada OP es un JSON en carpetas/AÑO/MES: no se cargan los
     miles de archivos juntos. Acá el "historial" completo ya está en
     memoria (es una demo), pero la API se comporta como si no lo estuviera:
     obtener_historial pide un año y un mes puntuales — es la carpeta — y
     buscar_historial es la única que mira más allá de esa carpeta, porque
     buscar por cliente/material/rango no tiene sentido acotado a un mes. */

  function claveFecha(fechaDMA) {
    const [d, m, a] = String(fechaDMA || "").split("-").map(Number);
    return (a || 0) * 10000 + (m || 0) * 100 + (d || 0);
  }
  function claveISO(iso) {
    const [a, m, d] = String(iso || "").split("-").map(Number);
    return (a || 0) * 10000 + (m || 0) * 100 + (d || 0);
  }
  const porFechaDesc = (a, b) => claveFecha(b.fecha_entrega) - claveFecha(a.fecha_entrega);

  TD.mock("historial-ops", {
    obtener_contexto: () => {
      const ctx = contextoBase();
      const hoy = new Date();
      ctx.anio_actual = hoy.getFullYear();
      ctx.mes_actual = hoy.getMonth() + 1;
      return ctx;
    },

    /* La "carpeta" de un año y un mes, ordenada por fecha de entrega. */
    obtener_historial: (anio, mes) => {
      const d = cargar();
      return d.historial
        .filter((o) => { const am = anioMesDe(o.fecha_entrega); return am && am.anio === ent(anio) && am.mes === ent(mes); })
        .sort(porFechaDesc);
    },

    /* Cruza todo el historial, sin importar mes — el texto busca en número
       y nombre; los demás filtros son cada uno opcional y se combinan
       todos (Y, no O). */
    buscar_historial: (filtros) => {
      const d = cargar();
      const f = filtros || {};
      const texto = String(f.texto || "").trim().toLowerCase();
      const cliente = String(f.cliente || "").trim().toLowerCase();
      const material = String(f.material || "").trim();
      const desde = f.desde ? claveISO(f.desde) : null;
      const hasta = f.hasta ? claveISO(f.hasta) : null;

      return d.historial.filter((o) => {
        if (texto && !(String(o.numero).includes(texto) || (o.nombre || "").toLowerCase().includes(texto))) return false;
        if (cliente && !(o.empresa || "").toLowerCase().includes(cliente)) return false;
        if (material && !opTieneMaterial(o, material)) return false;
        const clave = claveFecha(o.fecha_entrega);
        if (desde != null && clave < desde) return false;
        if (hasta != null && clave > hasta) return false;
        return true;
      }).sort(porFechaDesc);
    },

    abrir_op: (n) => irA("ver-op.html?n=" + n + "&volver=historial"),

    /* El historial se abre desde el panel de Ops del menú: volver es
       volver ahí, no al menú principal. */
    volver: () => irA("menu.html?panel=ops"),
    abrir_manual: () => TD.aviso("En la app esto abre el manual en PDF.", "info"),
    guardar_preferencia: preferencia,
  });

  /* La marca de esquina la pone api.js cuando no encuentra pywebview. Acá dice
     algo más útil: que lo que ves quedó guardado en el navegador. */
  document.addEventListener("DOMContentLoaded", function () {
    const revisar = setInterval(function () {
      const m = document.querySelector(".marca-mock");
      if (!m) return;
      clearInterval(revisar);
      m.textContent = "demo · guardado en este navegador";
      m.title = "Para volver al ejemplo inicial: TDdemo.reset() en la consola.";
    }, 200);
    setTimeout(function () { clearInterval(revisar); }, 5000);
  });

  /* ── Escotilla para la consola ──────────────────────────────────────────── */

  window.TDdemo = {
    bd: cargar,
    reset() {
      bd = semilla();
      guardar();
      location.reload();
    },
  };
})();
