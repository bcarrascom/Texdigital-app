# Guía de Usuario — Sistema de Gestión

Guía completa de uso del Sistema de Gestión: cotizaciones, Cotizador Backlight, aprobación de Órdenes de Producción (OP), panel de producción en TV, historial de OPs y revisión de cotizaciones guardadas.

Esta guía describe **todo lo que se puede hacer** en el programa, pantalla por pantalla, incluyendo los atajos de teclado disponibles. Está pensada como material de referencia para cualquier persona que use el sistema, tenga o no experiencia previa con él.

---

## Índice

1. [Introducción](#1-introducción)
2. [Menú principal](#2-menú-principal)
3. [Crear una cotización — flujo general](#3-crear-una-cotización--flujo-general)
4. [Cotizador Backlight — lo específico de este flujo](#4-cotizador-backlight--lo-específico-de-este-flujo)
5. [Ingresar Cotización (estándar) — lo específico de este flujo](#5-ingresar-cotización-estándar--lo-específico-de-este-flujo)
6. [Cómo se calculan los precios](#6-cómo-se-calculan-los-precios)
7. [Revisar Cotizaciones](#7-revisar-cotizaciones)
8. [Aprobar una cotización (convertirla en OP)](#8-aprobar-una-cotización-convertirla-en-op)
9. [Revisar OPs — Panel de producción (TV)](#9-revisar-ops--panel-de-producción-tv)
10. [Historial de OPs](#10-historial-de-ops)
11. [Editar una cotización ya guardada](#11-editar-una-cotización-ya-guardada)
12. [Atajos de teclado — resumen completo](#12-atajos-de-teclado--resumen-completo)
13. [Preguntas frecuentes](#13-preguntas-frecuentes)

---

## 1. Introducción

El Sistema de Gestión es el programa que acompaña todo el ciclo de un trabajo: desde que se cotiza un producto para un cliente, hasta que esa cotización se aprueba y se convierte en una Orden de Producción (OP) que la planta sigue en un panel de TV, hasta que el trabajo queda completado y pasa al historial.

Todo lo que se guarda (cotizaciones, OPs, catálogos, clientes y contactos) se almacena en una carpeta compartida de Dropbox — por eso lo que se hace en un computador aparece automáticamente en los demás apenas Dropbox termina de sincronizar.

**Actualizaciones**: el programa se actualiza solo. Al abrirlo, si hay una versión más nueva disponible, aparece un aviso breve ("Descargando la versión...") y el programa se reinicia solo con la versión al día. Si no hay conexión a internet en ese momento, el programa simplemente abre con la versión que ya estaba instalada — no hace falta hacer nada.

---

## 2. Menú principal

Al abrir el programa aparece el menú principal, con estos botones:

| Botón | Qué hace |
|---|---|
| **Cotizador Backlight** | Abre el flujo para cotizar productos backlight (telas retroiluminadas, con o sin caja). |
| **Ingresar Cotización** | Abre el flujo para cotizar productos estándar (no backlight): banderas, lienzos, etc. |
| **Revisar OPs** | Abre el panel de producción (pensado para quedar en una pantalla/TV de planta) con las Órdenes de Producción activas. |
| **Historial OPs** | Abre una ventana para buscar y reimprimir cualquier OP guardada, organizada por mes. |
| **Revisar Cotizaciones** | Abre la lista de cotizaciones guardadas que todavía no se aprobaron — para editarlas, aprobarlas, verlas o eliminarlas. |
| **Próximamente** | Espacio reservado para una futura función, todavía sin definir. |

La fecha de hoy y la versión instalada del programa se muestran arriba de la ventana.

Cerrar la ventana principal (la ✕ de la esquina) cierra el programa por completo.

---

## 3. Crear una cotización — flujo general

Tanto el **Cotizador Backlight** como **Ingresar Cotización** siguen la misma estructura general de pantallas. Las diferencias específicas de cada uno están en las secciones [4](#4-cotizador-backlight--lo-específico-de-este-flujo) y [5](#5-ingresar-cotización-estándar--lo-específico-de-este-flujo).

### 3.1. Pantalla inicial

Lo primero que se pide:

- **Nombre del trabajo**: texto libre, obligatorio.
- **Cantidad de productos**: cuántos productos va a tener esta cotización (se piden las medidas de cada uno, uno por uno, después).
- **Casilla "Despacho"**: si se marca, más adelante (después de cargar todos los productos) se va a pedir el valor del despacho, y ese monto se va a sumar al total de la cotización y a aparecer en el documento impreso.
- **Casilla "Instalación"**: funciona exactamente igual que Despacho, pero para el valor de la instalación. Se pueden marcar las dos, una sola, o ninguna.

El botón **"Comenzar →"** se habilita recién cuando el nombre no está vacío y la cantidad es de al menos 1. Presionar **Enter** en esta pantalla equivale a hacer clic en "Comenzar →".

### 3.2. Pantalla de Medidas (una por cada producto)

Esta pantalla se repite tantas veces como productos se hayan indicado. En la parte de arriba hay una **barra de navegación** con un cuadrado numerado por cada producto:

- El cuadrado del producto actual aparece resaltado.
- Los productos ya cargados se ven de un color distinto a los que faltan.
- Se puede hacer clic en cualquier cuadrado ya cargado para volver a ese producto y editarlo.
- Si se marcó Despacho y/o Instalación en la pantalla inicial, aparece un cuadrado extra al final de la barra, con las letras **"D"**, **"I"** o **"D/I"** según cuál se haya marcado — clic ahí lleva a la pantalla para ingresar esos valores (ver [3.3](#33-pantalla-de-despacho--instalación)).

Debajo de la selección de producto (que cambia según el flujo, ver secciones 4 y 5) están los campos de **Medidas**, comunes a ambos flujos:

- **Ancho (m)** y **Alto (m)**: acepta coma o punto decimal.
- **Cantidad**: número de unidades de este producto.
- **Tema**: texto libre, opcional (para anotar el diseño/tema del producto).
- **Obs**: texto libre, opcional, para cualquier observación.

A la derecha se dibuja un rectángulo a escala con las medidas ingresadas, para tener una referencia visual de la proporción del producto.

**Si las medidas exceden el ancho máximo de la tela/textil elegido**, aparece un aviso en rojo y el rectángulo se pinta de rojo — el botón para avanzar queda deshabilitado. Hay dos salidas:

- Si el lado corto entra pero el producto queda más eficiente girado, aparece un aviso "↺ La impresión será rotada para ajustarse al textil/tela" (esto es solo informativo, no requiere acción).
- Si de verdad no entra, se puede tildar la casilla **"Forzar"** (al lado del botón de abajo) para confirmar el producto de todas formas — el rectángulo se pinta amarillo y el botón para avanzar se pinta amarillo también, como señal de que se está forzando una medida fuera de lo normal.

El botón inferior dice **"Siguiente →"** en todos los productos menos el último, donde dice **"Confirmar ✓"**. Presionar **Enter** equivale a hacer clic en ese botón (si está habilitado).

### 3.3. Pantalla de Despacho / Instalación

Se muestra automáticamente después de cargar el último producto, **solo si** se marcó Despacho y/o Instalación en la pantalla inicial (o si se entra a propósito desde el cuadrado "D/I" de la barra de navegación).

- Si se marcó solo una de las dos, se pide solo ese valor.
- Si se marcaron ambas, aparecen los dos campos en la misma pantalla.
- El valor se puede escribir como número simple ("15000"), con puntos de miles ("15.000") o con el signo peso ("$15.000") — el programa lo interpreta igual en cualquiera de esos formatos.

El botón **"Confirmar ✓"** se habilita cuando todos los campos visibles tienen un valor válido. **Enter** equivale a hacer clic en ese botón.

### 3.4. Ventana de Resumen

Al terminar todos los productos (y el despacho/instalación si corresponde), se abre una ventana aparte con la tabla resumen de la cotización completa:

- **Hacer clic en cualquier fila de producto** la abre para editarla (vuelve a la pantalla de medidas de ese producto).
- Si se marcó Despacho y/o Instalación, aparece una fila extra de solo lectura para cada uno, con su monto — no se puede hacer clic en esas filas para editarlas ahí (para eso hay que usar el cuadrado "D"/"I"/"D/I" de la barra de navegación, ver 3.2).
- **"+ Agregar producto"** (abajo a la izquierda): agrega un producto más al final, mostrando su pantalla de medidas.
- **✕** (a la derecha de cada fila): elimina ese producto, pidiendo confirmación antes. No se puede eliminar si solo queda un producto en la cotización.
- La fila de **TOTAL**, al final, suma cantidades, metros y el valor total de la cotización.
- **"Confirmar ✓"** (abajo a la derecha): continúa al formulario de datos del cliente. **Enter** equivale a este botón.
- Cerrar la ventana (la ✕) sin confirmar vuelve a la pantalla de medidas del último producto, sin perder lo ya cargado.

> Los dos botones para agregar/quitar Despacho o Instalación **después de guardada** la cotización (útil si al cliente se le olvidó pedir despacho, por ejemplo) solo aparecen al editar una cotización ya guardada — ver [sección 11](#11-editar-una-cotización-ya-guardada).

### 3.5. Formulario de datos del cliente

Última pantalla antes de guardar. Los campos:

- **Empresa**: con autocompletado — si ya se cotizó antes para esa empresa, al elegirla de la lista se rellenan solos el **RUT** y la **Razón Social**.
- **RUT**: se formatea automáticamente mientras se escribe (puntos y guión).
- **Razón Social**.
- Botón **"Guardar Datos"**: guarda Empresa/RUT/Razón Social en la lista de clientes, para que la próxima cotización a esa empresa autocomplete sola. Solo se puede usar una vez por cotización (se deshabilita después de guardar).
- **Contacto**: también con autocompletado — al elegir un contacto ya guardado, se rellenan solos **Email**, **Descuento** y **Condición de pago**.
- **Email**.
- **Descuento** (%): porcentaje de descuento sobre el neto de la cotización. Si se deja vacío, se toma como 0%.
- **Condición de pago**: texto libre (ej. "Contado", "30 días").
- Botón **"Guardar Contacto"**: guarda Contacto/Email/Descuento/Condición en la lista de contactos, para autocompletar la próxima vez. También se puede usar una sola vez por cotización.
- **Fecha**: viene con la fecha de hoy por defecto, editable.
- **N° Cotización**: 4 dígitos, viene pre-llenado con el próximo número disponible (no se recomienda cambiarlo salvo que se sepa bien por qué).
- **TERMINACIONES CAJA** (switch, *solo aparece en el Cotizador Backlight*): "CAJA TERMINADA" o "AREA VISUAL" — ver [sección 4](#4-cotizador-backlight--lo-específico-de-este-flujo).
- **Descripción**: texto libre.

Botones al final:

- **"Guardar y abrir"**: guarda la cotización y abre automáticamente el documento HTML imprimible en el navegador.
- **"Guardar"**: guarda la cotización sin abrir el documento.
- **"← Cancelar"**: cierra sin guardar y vuelve al menú principal.

Al guardar con éxito, el programa vuelve al menú principal, listo para una nueva cotización.

---

## 4. Cotizador Backlight — lo específico de este flujo

En la pantalla de Medidas de este flujo, la sección de selección de producto tiene:

- **Tela**: lista desplegable con las telas disponibles para backlight (Popelina 155, Popelina 310, Pearl 155, Pearl 310, Pearl 160 HP).
- **Caja / Perfil**: lista desplegable — "Sin caja" o uno de los perfiles del catálogo. Debajo aparece el ancho máximo de impresión de la tela elegida.

**Si se elige un perfil de caja** (distinto de "Sin caja"), aparece una sección adicional:

- **Luces 1** y **Luces 2**: listas desplegables con los tipos de luces disponibles. El programa sugiere un valor por defecto para Luces 1 según el perfil y las medidas — si se elige algo distinto a mano, esa elección queda fija y ya no se pisa sola aunque cambien las medidas.
- Si se elige **"Malla 12V"** en Luces 1 o Luces 2, aparece un campo extra **"Cant. x caja"** para indicar la cantidad manualmente.
- Debajo, una **tabla de materiales** se recalcula en vivo con cada cambio de medida, perfil o luces: Perfil, Traseras, Luces 1, Luces 2 y Fuente de Poder (FP), con su tipo y cantidad. También se muestran los **watts totales** de la caja.

### Corte de tela y "TERMINACIONES CAJA"

En el Formulario de datos del cliente (ver 3.5), el switch **"TERMINACIONES CAJA"** define cómo se calcula la medida de corte de la tela para cada producto backlight de esta cotización:

- **CAJA TERMINADA**: se corta la tela con un margen de **1,3 cm** por sobre la medida final (Ancho/Alto) del producto.
- **AREA VISUAL**: se corta con un margen de **2,3 cm**.

Esta elección aplica a **toda la cotización** (no se elige producto por producto). El resultado ("Corte ancho" y "Corte alto") aparece automáticamente en la OP impresa y en el panel de producción una vez que la cotización se aprueba — ver secciones [9](#9-revisar-ops--panel-de-producción-tv) y [10](#10-historial-de-ops).

### Resumen (Cotizador Backlight)

La tabla de resumen de este flujo muestra: N°, Textil, Tema, Cantidad, Ancho, Alto y **M² impresos** (Backlight se mide siempre en metros cuadrados, no en metros lineales — ver [sección 6](#6-cómo-se-calculan-los-precios)).

---

## 5. Ingresar Cotización (estándar) — lo específico de este flujo

En la pantalla de Medidas de este flujo, la sección de selección de producto tiene:

- **Producto**: con autocompletado, de la lista de productos del catálogo (ej. banderas, lienzos).
- **Textil**: con autocompletado, de la lista de telas/textiles disponibles.
- **Estructuras**: lista de estructuras a agregar al producto (ej. "Asta 2 mts"). Se escribe o busca el nombre y se hace clic en **"+ Agregar"** (o Enter dos veces: la primera autocompleta, la segunda agrega). Se pueden agregar varias. Cada una agregada se muestra con su nombre y un botón **✕** para quitarla.
- **Terminaciones**: funciona exactamente igual que Estructuras, pero para la lista de terminaciones (ej. "Bolsillos", "Basta").
- **Impresión**: switch de dos opciones, **"Cara única"** o **"Tiro y retiro"** (imprime ambas caras — usa el doble de tela).

**Ajuste manual de precio**: en vez de elegir una estructura o terminación del catálogo, se puede escribir directamente un monto en pesos (ej. "10000", "10.000" o "$10.000") y agregarlo igual que cualquier otra — ese monto se suma tal cual al total, sin buscarlo en ningún catálogo. Sirve para casos puntuales que no calzan con los precios estándar del catálogo.

Debajo de Estructuras/Terminaciones/Impresión se muestra, en vivo, el desglose del precio del producto actual: **Impresión**, **Estructuras + Terminaciones**, **Total producto** y **Valor unitario** — se recalcula automáticamente con cada cambio.

### Resumen (Ingresar Cotización)

La tabla de resumen de este flujo muestra: N°, Producto, Textil, Tema, Cantidad, Ancho, Alto, **ML impresos**, Valor unitario y Total.

---

## 6. Cómo se calculan los precios

Esta sección explica las reglas detrás de los números que aparecen en pantalla, para poder interpretarlos correctamente.

- **Metros lineales (ML) vs. metros cuadrados (M²)**: los productos estándar (Ingresar Cotización) se cobran por **ML** de tela impresa — el programa calcula cuántas unidades entran a lo ancho del rollo de tela y a partir de eso cuánta tela se usa realmente (puede ser menos que Alto × Cantidad si entra más de una unidad por pasada). Los productos **Backlight** se cobran por **M²** (Alto × Ancho × Cantidad), sin ese ajuste de ancho de rollo — cada backlight se imprime en su tamaño exacto.

- **Piso mínimo de facturación**: ningún producto se cobra por menos del equivalente a **2 ML** (estándar) o **2 M²** (Backlight). Si las medidas de un producto dan menos que eso, el programa igual cobra como si fueran 2 — esto aplica al **total de esa línea completa** (con su Cantidad ya incluida), no a cada unidad por separado. Este piso solo afecta lo que se **cobra** — la Orden de Producción sigue mostrando la medida real de tela a cortar, no la "inflada" para el cobro.

- **Tiro y retiro** duplica tanto el ML impreso como la cantidad de estructuras/terminaciones aplicadas (imprimir las dos caras implica el doble de tela y el doble de costura/remate).

- **Descuento**: se aplica como porcentaje sobre el neto total de la cotización (definido en el Formulario de datos del cliente).

- **IVA**: se aplica siempre al 19% sobre el neto después de descuento.

- **Despacho e Instalación**: son montos fijos aparte, que no son "productos" (no tienen medidas ni cantidad) — se suman directo al neto de la cotización, y quedan sujetos al mismo descuento e IVA que el resto.

---

## 7. Revisar Cotizaciones

Lista todas las cotizaciones guardadas que **todavía no fueron aprobadas** (una vez aprobada, una cotización pasa a ser una OP y se deja de ver acá — se puede seguir viendo/reimprimiendo desde [Historial de OPs](#10-historial-de-ops)).

La tabla muestra N°, Empresa y Fecha de cada cotización.

- **Doble clic sobre una fila**: abre esa cotización para editarla (vuelve al cotizador correspondiente, ver [sección 11](#11-editar-una-cotización-ya-guardada)).
- **Clic en una fila**: la selecciona (queda resaltada).
- **"Seleccionar múltiples"**: activa un modo en el que hacer clic en varias filas las va agregando a la selección (en vez de reemplazar la selección anterior); también se puede arrastrar el mouse sobre varias filas para seleccionarlas todas de una vez. Al desactivar este modo, si había más de una fila seleccionada, se conserva solo la primera.
- **"Eliminar"** (abajo a la izquierda): borra la(s) cotización(es) seleccionada(s), pidiendo confirmación. Esta acción no se puede deshacer.
- **"Ver/Imprimir"**: genera y abre en el navegador el documento HTML de cada cotización seleccionada (con precios, el documento para el cliente).
- **"Aprobar"**: convierte la(s) cotización(es) seleccionada(s) en Orden(es) de Producción — ver [sección 8](#8-aprobar-una-cotización-convertirla-en-op).
- **📁** (arriba a la derecha): abre la carpeta de Dropbox donde se guardan las cotizaciones, en el explorador de archivos.

---

## 8. Aprobar una cotización (convertirla en OP)

Al presionar **"Aprobar"** con una o más cotizaciones seleccionadas, se abre un diálogo por cada una (si se aprueban varias a la vez, un diálogo después del otro, en orden):

- **Fecha de ingreso**: viene con la fecha de hoy por defecto. Se puede cambiar con el botón "Cambiar" al lado, si la fecha real de ingreso a producción es otra.
- **Fecha de entrega**: se debe ingresar a mano (no tiene un valor por defecto). El botón "Aprobar" del diálogo se habilita recién cuando esta fecha es válida.
- **"Editar"**: en vez de aprobar, abre la cotización para editarla.
- **"Cancelar"**: cierra el diálogo sin hacer nada.
- **"Aprobar"** (del diálogo): confirma. La cotización desaparece de "Revisar Cotizaciones" y pasa a aparecer como OP activa en "Revisar OPs" y en "Historial OPs".

**Enter** confirma el diálogo si ambas fechas ya son válidas; **Escape** lo cancela.

---

## 9. Revisar OPs — Panel de producción (TV)

Pensado para quedar abierto en una pantalla o TV en planta, mostrando las Órdenes de Producción activas. Tiene dos pantallas: el **Listado** (con el que siempre abre) y el **Detalle** de una OP puntual.

> En Mac, el panel de producción se abre como una ventana/proceso aparte de la ventana principal del programa — se puede seguir usando el resto del programa con normalidad mientras el panel queda abierto.

### 9.1. Pantalla de Listado

Elementos principales:

- **Contadores** (arriba a la derecha): cantidad de OPs activas y de OPs pendientes.
- **Calendario** (columna izquierda): muestra 5 semanas (2 antes y 2 después de hoy). Cada día con OPs con fecha de entrega ese día muestra puntos de colores:
  - 🔴 **Rojo**: atrasada (la fecha de entrega ya pasó).
  - 🟠 **Naranjo**: entrega es hoy.
  - 🟡 **Amarillo**: entrega es mañana.
  - ⚪ **Blanco**: entrega más adelante.
  - 🟢 **Verde**: completada a tiempo.
  - 🟢 **Verde oscuro**: completada, pero después de la fecha de entrega.
  - **Clic en un día** con OPs filtra la lista principal a solo ese día (se puede hacer clic en varios días para filtrar por varios a la vez); volver a hacer clic en un día ya filtrado lo saca del filtro.
  - **"×"** (bajo el calendario): quita todos los filtros de fecha aplicados.
- **Módulo deslizable** (arriba de la lista de pendientes/carga): dos paneles que se recorren con las flechas de los costados o los puntos de abajo:
  - **OPs pendientes**: "pastillas" con las OPs marcadas como pendientes (ver más abajo). **Doble clic** en una abre el diálogo para reactivarla con una fecha de entrega definitiva.
  - **Carga de producción**: un medidor circular (0–100%) que resume qué tan cargada está la producción según las fechas de entrega de las OPs activas (colores de verde a rojo según el nivel).
- **Lista principal**: cada fila muestra N° de OP, Nombre del trabajo (con una etiqueta del perfil de caja si es backlight), Empresa, Fecha de entrega y un punto de color (mismo código que el calendario).
  - **Clic en una fila**: la selecciona/deselecciona (se puede seleccionar más de una).
  - **Doble clic en una fila**: abre el Detalle de esa OP.
  - **"Mostrar completadas"**: además de las activas, muestra también las OPs recientemente completadas al final de la lista (de solo lectura, no se pueden seleccionar).

Botones de acción (se habilitan al seleccionar al menos una OP):

| Botón | Qué hace |
|---|---|
| **📁** (Marcar como pendiente) | Mueve la(s) OP(s) seleccionada(s) a "Pendientes" (para cuando todavía no hay fecha de entrega definitiva). |
| **Cambiar entrega** | Abre un diálogo para cambiar la fecha de entrega de la(s) OP(s) seleccionada(s). |
| **🖨 Imprimir** | Genera y abre el documento HTML (sin precios) de cada OP seleccionada, listo para imprimir en planta. |
| **↻ Recargar** | Vuelve a leer las carpetas de OPs, por si se hicieron cambios desde la pantalla principal mientras tanto. |
| **Completar OP(s)** | Marca la(s) OP(s) seleccionada(s) como completadas (pide confirmación) — pasan al historial. |

### 9.2. Pantalla de Detalle (una OP)

Se llega con doble clic sobre una fila del listado. Muestra:

- N° de OP, nombre del trabajo, cliente, fechas de ingreso y entrega, descripción.
- Contadores de productos totales y metros totales (ML o M² según el tipo de OP).
- Una **tarjeta por producto**, con: tipo y tela, cantidad, medidas, y —para backlight— la medida de **Corte** (ancho y alto, con el margen de costura ya aplicado según "CAJA TERMINADA"/"AREA VISUAL", ver [sección 4](#4-cotizador-backlight--lo-específico-de-este-flujo)), el detalle de materiales de caja si corresponde, estructuras/terminaciones si es un producto estándar, observaciones, tema, y los metros de ese producto.
- **Clic en una tarjeta**: la marca como "lista" (se pone en un tono más apagado) — o la desmarca si ya estaba lista.
- **Puntos abajo**: uno por cada OP activa, para saltar directo a otra sin volver al listado. El punto de la OP actual con todos sus productos listos se ve marcado como completo.

Botones:

| Botón | Qué hace |
|---|---|
| **← Listado** | Vuelve a la pantalla de Listado. |
| **🖨 Imprimir** | Genera y abre el documento HTML de esta OP. |
| **↻ Recargar** | Vuelve a leer los datos de las OPs. |
| **Confirmar todos** / **Completar OP** | Mientras falten productos por marcar como listos, este botón los marca todos de una vez ("Confirmar todos"). Cuando todos los productos ya están listos, el mismo botón cambia a "Completar OP" y, al presionarlo, pide confirmación para mover la OP al historial. |

Si no quedan OPs activas, la pantalla muestra un aviso y los botones "↻ Recargar" y "← Listado".

---

## 10. Historial de OPs

Muestra **todas** las OPs guardadas —activas, pendientes, completadas e históricas— organizadas por mes, para poder reimprimir cualquier OP pasada sin tener que revisar archivo por archivo.

- **Selector de mes**, arriba: `« ◀  Mes Año  ▶ »`
  - **◀ / ▶**: avanzan un mes hacia atrás/adelante (solo entre meses que tengan al menos una OP guardada).
  - **« / »**: saltan directo al año anterior/siguiente que tenga datos, sin tener que recorrer mes por mes.
- La tabla del mes elegido muestra: N°, Empresa, Trabajo, Fecha de ingreso, Fecha de entrega y **Estado** (Activa / Completada / Pendiente / Historial).
- **Selección múltiple**: clic normal, Ctrl+clic o Shift+clic para seleccionar varias filas (igual que en cualquier lista de Windows/Mac).

Botones (se habilitan con al menos una fila seleccionada):

| Botón | Qué hace |
|---|---|
| **Eliminar** | Borra la(s) OP(s) seleccionada(s), sea cual sea su estado — pide confirmación. No se puede deshacer. |
| **Buscar cotización** | Busca la cotización original de cada OP seleccionada (con precios) en los últimos 3 meses de historial de cotizaciones y, si la encuentra, la abre en el navegador. Si no la encuentra, avisa con el número de OP correspondiente. |
| **Imprimir** | Genera y abre el documento HTML (sin precios) de cada OP seleccionada. |

---

## 11. Editar una cotización ya guardada

Se accede con **doble clic** sobre una fila en "Revisar Cotizaciones". El cotizador correspondiente (Backlight o estándar, según el tipo de productos) se abre directo en la ventana de Resumen con todos los productos ya cargados.

Desde ahí se puede editar cualquier producto (clic en su fila), agregar uno nuevo, eliminar alguno, o **agregar/quitar Despacho e Instalación** — en modo edición, aparecen dos casillas extra en la ventana de Resumen (junto a "Haz clic en una fila para editarla") para activar o desactivar cada uno:

- Si se **activa** una que estaba apagada, se abre la pantalla para ingresar su valor (igual que en 3.3).
- Si se **desactiva** una que estaba prendida, se borra directo (sin pedir confirmación) y desaparece del resumen y del total.

> Estas dos casillas **solo aparecen al editar** — al crear una cotización nueva, Despacho e Instalación se deciden en la pantalla inicial (ver 3.1).

Al confirmar el resumen en modo edición, los cambios se guardan directo (no vuelve a pasar por el Formulario de datos del cliente) y el programa vuelve a "Revisar Cotizaciones".

---

## 12. Atajos de teclado — resumen completo

| Tecla | Dónde | Qué hace |
|---|---|---|
| **Enter** | Cualquier pantalla de cotización, formulario de cliente, diálogos de confirmación | Equivale a hacer clic en el botón principal habilitado de esa pantalla (Comenzar, Siguiente/Confirmar, Confirmar despacho/instalación, Confirmar resumen, Guardar Datos, Aprobar, Eliminar, etc.). |
| **Escape** | Menús de autocompletado (Empresa, Contacto, Producto, Textil, Estructuras, Terminaciones) | Cierra el menú desplegable de sugerencias sin elegir nada. |
| **Escape** | Diálogos de confirmación (Aprobar, Eliminar) | Cancela el diálogo. |
| **Escape** | Panel de producción (TV) | Cierra un diálogo abierto si hay uno; si no, cierra el panel. |
| **↑ / ↓** | Menús de autocompletado | Mueve la sugerencia resaltada. |
| **↑ / ↓** | Tabla de "Revisar Cotizaciones" | Mueve la selección a la fila anterior/siguiente. |
| **Shift + ↑ / ↓** | Tabla de "Revisar Cotizaciones" | Extiende la selección a la fila anterior/siguiente, sin perder lo ya seleccionado. |
| **↑ / ↓** | Panel de producción, pantalla de Listado | Mueve el cursor entre las OPs de la lista (con Shift, extiende la selección). |
| **← / →** | Panel de producción, pantalla de Detalle | Salta a la OP anterior/siguiente. |
| **Clic + arrastrar** | Tabla de "Revisar Cotizaciones", con "Seleccionar múltiples" activo | Selecciona todas las filas entre el punto donde se empezó a arrastrar y donde se soltó. |
| **Doble clic** | Filas de tablas (Revisar Cotizaciones, Listado del panel de producción) | Abre esa fila (editar cotización / ver detalle de OP). |
| **Rueda del mouse** | Formulario de datos del cliente (solo en Mac) | Se puede desplazar el formulario verticalmente si no entra completo en la pantalla. |

---

## 13. Preguntas frecuentes

**¿Dónde se guarda todo?**
En una carpeta compartida de Dropbox. Mientras Dropbox esté instalado y sincronizando en el computador, cualquier cotización u OP que se cree, edite o apruebe en un equipo va a aparecer en los demás apenas termine de sincronizar.

**¿Qué pasa si no hay internet?**
El programa funciona igual con los datos que ya estén sincronizados localmente — lo único que no va a pasar es la búsqueda de actualizaciones al abrir (falla en silencio y abre la versión instalada) y, obviamente, la sincronización de Dropbox se retoma sola apenas vuelva la conexión.

**Cambié algo por error y quiero recuperar una cotización u OP que eliminé — ¿se puede?**
El programa no tiene una función de "deshacer" para eliminar. Dropbox guarda un historial de versiones de los archivos por un tiempo — para recuperar algo eliminado por error hay que hacerlo desde la web de Dropbox (dropbox.com), no desde este programa.

**¿Por qué el precio de un producto me dio más bajo de lo que esperaba, o incluso $0?**
Puede ser por dos motivos típicos: (1) el textil elegido no tiene un valor cargado en el catálogo (revisar con quien administra los catálogos), o (2) las medidas son muy chicas y el programa está calculando el ML/M² real, no el piso mínimo de facturación de 2 ML/2 M² — ver [sección 6](#6-cómo-se-calculan-los-precios).

**¿Se puede cambiar el tamaño de las ventanas?**
La mayoría de las ventanas tienen tamaño fijo. La excepción es la pantalla de Medidas de "Ingresar Cotización" (estándar), que sí se puede agrandar si hace falta ver más contenido sin recortes.
