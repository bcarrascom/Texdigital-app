# Cajas de backlight — cálculo de materiales

Rama: `feature/cajas`. Agrega el cálculo automático de materiales (perfil,
traseras, luces, fuente de poder) para productos backlight con caja, y lo
integra en el cotizador y en el panel de producción.

## Qué había antes

El campo `Caja` de un producto backlight era un string simple con el
perfil elegido (`"PERFIL 80 MM"`, `"Sin caja"`), sin más detalle. Todo el
resto de los materiales (traseras, luces, fuente de poder) se calculaba a
mano fuera del sistema.

## Qué agrega esta rama

- **`core/calculo_cajas.py`** — módulo puro (sin UI ni I/O) que calcula la
  tabla completa de materiales de una caja a partir de Ancho/Alto/Cantidad/
  Perfil/Luces. Sin dependencias de Tkinter ni de archivos: recibe los
  catálogos ya cargados.
- **Catálogos nuevos** (`recursos/perfiles.json`, `luces.json`,
  `fuentes_poder.json`), con el mismo mecanismo que `productos.json`/
  `textiles.json`: viven en `Dropbox/SGTD/Conf/`, editables sin recompilar
  la app (ver `core/repositorio.py`).
- **UI del cotizador backlight** (`ui/cotizador_backlight.py`) — al elegir
  un perfil aparecen los combos de Luces 1/Luces 2 (autocompletados desde
  el catálogo) y una tabla de materiales que se recalcula en vivo con cada
  cambio de medida o de luz.
- **Panel de producción** (`recursos/panel_tv/*.html`) — el listado
  muestra un badge con el perfil de cada OP; el detalle de producto usa el
  doble de alto de tarjeta para los productos con caja, mostrando el
  detalle completo de materiales.
- **33 tests unitarios** (`tests/test_calculo_cajas.py`) cubriendo todas
  las reglas de cálculo y los casos borde.
- **Exportación a Excel desactivada temporalmente** (`EXPORTAR_EXCEL =
  False` en `ui/formulario_cliente.py`): el generador actual no sabe
  escribir el nuevo campo `Caja` cuando es un objeto (antes siempre era un
  string). Guardar la cotización/OP en JSON sigue funcionando igual;
  reactivar cuando se actualice `excel/generador_documentos.py`.

## Esquema de datos

El campo `Caja` de un producto puede ser:

- `"Sin caja"` — producto backlight sin caja (como antes).
- Un string con el nombre de un perfil — formato viejo, se sigue
  aceptando para no romper cotizaciones ya guardadas (se muestra sin
  detalle de materiales).
- Un objeto con el detalle completo, que arma `_valor_caja_guardado()`:

```json
{
  "perfil": "PERFIL 80 MM",
  "watts": 42.0,
  "traseras": {"tipo": "Trovicel 122", "cantidad_x_caja": 1, "cantidad_total": 2},
  "luces_1":  {"tipo": "M12", "cantidad_x_caja": 2, "cantidad_total": 4},
  "luces_2":  {"tipo": "sin luces", "cantidad_x_caja": 0, "cantidad_total": 0},
  "fp":       {"tipo": "FP 50 watts- 24v MEAN WELL", "cantidad_x_caja": 1, "cantidad_total": 2},
  "obs": ""
}
```

`Traseras`, `Luces 1`, `Luces 2` y `FP` siempre traen `{tipo,
cantidad_x_caja, cantidad_total}`. Un material en 0 (mallas sin traseras,
"sin luces", watts 0 sin FP) se sigue guardando en el JSON, pero el panel
de producción no lo muestra.

## Reglas de negocio (y correcciones sobre la especificación original)

Basado en `logica_cajas_backlight.md` (documento de referencia, no vive en
el repo), con dos correcciones encontradas durante las pruebas:

- **Traseras se redondea hacia arriba, por caja, dentro del cálculo** (no
  solo para mostrar). No existe "0.4 planchas": si 2 cajas necesitan 0.4
  cada una, el total correcto es 1+1=2 planchas, no `techo(0.4×2)=1`. Por
  eso el redondeo tiene que pasar *antes* de sumar, y quedar guardado en
  el JSON — así el archivo refleja cuánto material hay que pedir de
  verdad.
- **Las mallas (Malla 150 y Malla 12v) nunca llevan traseras.** La
  especificación original proponía "Alucobond 122x244" para ese caso; en
  la práctica no se usa — la malla misma cubre el fondo. Ahora da "Sin
  traseras" con cantidad 0, igual que un perfil doble.
- **Malla 150 y Malla 12v se cuentan y cobran EXACTAMENTE igual que
  cualquier led lateral** (M12, M6, ...): su propio ancho físico ("medida"
  en `luces.json` — 0.3 m y 1.0 m respectivamente) en la misma fórmula de
  "cuántas unidades entran a lo largo del lado más largo" (`led_x_lado`).
  La única diferencia real es que su cantidad final NO se multiplica por
  `lados_a_cubrir` — a diferencia de un led lateral (que se repite
  simétricamente en los lados que corresponda), una malla no "se aplica
  por lado". Una versión anterior de este módulo las trataba como una
  grilla de LEDs individuales cubriendo todo el fondo de la caja
  (`luces_x_caja_grilla`/`plan_tiras`, ya eliminados) — esa interpretación
  se probó contra el Excel original con dos ejemplos reales y no daba
  resultados compatibles ni ajustando el precio proporcionalmente (con una
  caja de 1.5×0.45 m, "Malla 12v" da literalmente 1 sola unidad usada, algo
  que una grilla de área nunca podría dar).
- **El default de Luces 1 para PERFIL 60 MM no depende de Ancho/Alto** (es
  siempre Malla 150). La UI lo aplica apenas se elige el perfil, sin
  esperar a que se completen las medidas — antes, si se elegía el perfil
  antes que las medidas, el combo se quedaba mostrando el valor anterior
  hasta que se tipeaban Ancho/Alto (se autocorregía, pero parecía que no
  había pasado nada).
- FP siempre resulta en un número entero por construcción (§6: 1 unidad,
  o `techo(watts/350)` unidades de 350W sobre 450W) — no requiere
  redondeo aparte.

## Pendiente (fuera del alcance de esta rama)

- **Exportación a Excel**: desactivada, ver arriba.

## Cómo probar

```bash
python tests/test_calculo_cajas.py -v
```

Para probar la UI manualmente: Cotizador Backlight → elegir un perfil →
revisar que la tabla de materiales se actualice en vivo → guardar una
cotización → revisar el JSON en `Dropbox/SGTD/Cotizaciones/JSON/` → abrir
el panel de producción y confirmar que las tarjetas con caja muestran el
detalle correcto.

## Archivos tocados

```
core/calculo_cajas.py               (nuevo, 390 líneas)
core/repositorio.py                 (+31, catálogos de cajas)
recursos/perfiles.json              (nuevo)
recursos/luces.json                 (nuevo)
recursos/fuentes_poder.json         (nuevo)
recursos/panel_tv/display_op.html   (+76, tarjetas de 2 filas + detalle)
recursos/panel_tv/panel_lista.html  (+26, badge de perfil)
tests/test_calculo_cajas.py         (nuevo, 33 tests)
ui/cotizador_backlight.py           (+298, formulario de caja en vivo)
ui/formulario_cliente.py            (+50/-25, EXPORTAR_EXCEL desactivado)
```
