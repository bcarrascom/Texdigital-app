# Reglas y excepciones del sistema

Documento vivo: acá se listan las reglas de negocio "hechas a mano" que
el sistema aplica por encima del cálculo genérico de precios — cosas que
no salen de una fórmula matemática general, sino de una decisión
explícita para mantener precios y orden interno de la empresa (cobros
mínimos, casos especiales, excepciones a cómo se mide o se cobra algo).

No es una lista completa — se va a ir completando con el tiempo. Cada
regla nueva se agrega acá con el mismo formato, para que quede claro qué
hace, dónde vive en el código y por qué existe.

**Formato de cada regla:**
- **Qué hace** — la regla en sí, en una o dos frases.
- **A qué aplica** — qué productos/flujos toca (¿todos? ¿solo backlight?
  ¿solo cotizaciones?).
- **Por qué existe** — el motivo de negocio detrás, si se sabe.
- **Dónde vive** — el archivo/función que la implementa (una vez que esté
  programada).
- **Estado** — implementada, o todavía pendiente.

---

## 1. Piso mínimo de facturación por producto — 2 ML (o 2 M² en backlight)

**Qué hace**: ningún producto (una línea de la cotización, con su
Cantidad ya aplicada) se factura por menos del equivalente a 2 metros
lineales de tela impresa. Si el ML real de esa línea completa (Alto ×
Ancho, resuelto contra el ancho de la tela, × Cantidad) da menos de 2, el
costo de impresión se calcula igual usando 2 ML — no el valor real, más
chico.

**A qué aplica**:
- Productos no-backlight: el mínimo es **2 metros lineales (ML)**.
- Productos backlight: el mínimo es **2 metros cuadrados (M²)**, porque
  backlight se mide por área, no por ML.

**Por qué existe**: cubrir el costo mínimo de producción (tela, tiempo de
máquina, manipulación) de un producto chico — sin este piso, un producto
muy pequeño saldría cobrado muy por debajo de lo que realmente cuesta
producirlo.

**Cómo se aplica exactamente** (corregido — la primera versión de esta
regla lo tenía al revés): el piso se evalúa sobre el **ML/M² total ya
calculado para toda la línea** (Cantidad ya incluida, y en no-backlight
también el ×2 de Tiro y retiro), **no** por cada unidad por separado y
luego multiplicado por Cantidad. Dos unidades de un mismo producto que en
conjunto dan 1 ML no se facturan como "2 × 2 ML = 4 ML" — se facturan
como 2 ML en total, porque 1 ML ya está por debajo del piso.

Este piso **solo afecta lo que se cobra**. El ML/M² real (sin piso) se
sigue usando tal cual para todo lo que no es plata:
- `core/presentar_op.py` (orden de producción) — ahí importa cuánta tela
  se corta de verdad, no cuánto se cobra.
- Las columnas informativas "ML imp." / "M² imp." de la ventana de
  resumen (`ui/cotizacion.py`, `ui/cotizador_backlight.py`) — muestran el
  consumo real, no el facturado.

**Dónde vive**:
- `core/precios.py::_con_piso` — helper que sube un valor al piso si
  queda por debajo (y solo si el valor ya es positivo: 0 = medidas
  incompletas o textil no encontrado en catálogo, no es un "monto chico").
- Constantes `core/precios.py::ML_MINIMO_POR_PRODUCTO` /
  `M2_MINIMO_POR_PRODUCTO`.
- Aplicado dentro de `core/precios.py::costo_producto` (impresión
  no-backlight, impresión backlight, y estructuras `valorML` del modelo
  "aditivo" — las tres se calculan a partir del mismo ML). **No** se
  aplica dentro de `calcular_ml`, a propósito (ver arriba).
- Tests: `tests/test_precios_legado.py` (métodos `test_piso_2ml_*` /
  `test_piso_2m2_*`).

**Estado**: ✅ implementada.
