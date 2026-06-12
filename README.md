# Sistema de Gestión — Cotizador

Aplicación de escritorio (Tkinter) para generar cotizaciones de productos textiles
y backlight, y exportarlas a Excel a partir de una plantilla.

## Estructura del proyecto

```
main.py               Punto de entrada de la app
core/
  rutas.py            Resolución de rutas (recursos vs datos de usuario)
  escala.py           Escalado de la interfaz según resolución de pantalla
  repositorio.py      Acceso a datos: catálogos (productos, textiles) y
                       datos de usuario (clientes, contactos)
ui/                   Pantallas de la interfaz (Tkinter)
excel/                Generación de documentos Excel (openpyxl)
recursos/             Catálogos, plantilla Excel, assets y datos de ejemplo
docs/                 Documentación de referencia (mapeo de celdas del Excel)
build_mac.sh          Script de empaquetado para macOS (PyInstaller)
```

Los datos editables por el usuario (`clientes.txt`, `contactos.txt`) se guardan
en la carpeta de datos de la aplicación del sistema operativo (no en el repo).
La primera vez que se ejecuta la app, se copian las versiones de ejemplo desde
`recursos/` a esa carpeta.

## Requisitos

- Python 3.11+

## Instalación y ejecución

```bash
pip install -r requirements.txt
python main.py
```

## Generar build de macOS

```bash
bash build_mac.sh
```

Genera `dist/Sistema de Gestion.app` y crea un acceso directo en el Escritorio.

Los scripts de empaquetado para Windows y Linux están pendientes.
