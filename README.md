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
build_windows.ps1     Script de empaquetado para Windows (PyInstaller)
.github/workflows/    Workflow de GitHub Actions para releases automáticas
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

## Interfaz en React (en migración, rama `refactor/react`)

La interfaz nueva vive en `frontend/` (Vite + React + React Router + Motion).
Requiere Node.js 20+.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 en el navegador, con datos de prueba (mocks)
npm run build      # genera frontend/dist/, lo que carga la app
```

```bash
python main.py --react         # la app con la interfaz nueva (usa frontend/dist/)
python main.py --react --dev   # ídem, pero cargando `npm run dev` (recarga en caliente)
python main.py                 # la interfaz anterior, sin cambios
```

```
frontend/src/
  pages/        una carpeta por pantalla (Pagina.jsx + Pagina.css)
  components/   piezas reutilizables (Cabecera, Pagina, Cargando, ...)
  hooks/        useDatos, useAtajo, useVolver
  context/      estado global: contexto de la app, escala de texto, avisos
  services/     api.js (puente a Python) y mocks/ (datos de prueba)
  router/       rutas.js (todas las URLs) y RutasAnimadas.jsx (transiciones)
  utils/        formato.js (pesos, medidas, fechas)
  assets/       styles/base.css (sistema de diseño) y svg/ (íconos Lucide)
```

## Generar build de macOS

```bash
bash build_mac.sh
```

Genera `dist/Sistema de Gestion.app` y crea un acceso directo en el Escritorio.

## Generar build de Windows (local)

```powershell
powershell -ExecutionPolicy Bypass -File build_windows.ps1
```

Genera `dist\Sistema de Gestion\Sistema de Gestion.exe` y crea un acceso directo
en el Escritorio.

## Releases automáticas

Al crear y subir un tag de versión, GitHub Actions compila la app para Windows,
macOS y Linux y publica los tres builds en la pestaña
[Releases](https://github.com/bcarrascom/Texdigital-app/releases) del repositorio:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Para los usuarios de la empresa

1. Ir a la pestaña [Releases](https://github.com/bcarrascom/Texdigital-app/releases)
   y descargar el archivo correspondiente al sistema operativo:
   - **Windows**: `SistemaGestion-windows.zip`
   - **macOS**: `SistemaGestion-macos.zip`
   - **Linux**: `SistemaGestion-linux.tar.gz`
2. Descomprimir el archivo.
3. Ejecutar la app:
   - **Windows**: abrir la carpeta y hacer doble clic en
     `Sistema de Gestion.exe`. Si aparece "Windows protegió tu PC" (SmartScreen,
     porque el ejecutable no está firmado), hacer clic en "Más información" →
     "Ejecutar de todas formas".
   - **macOS**: hacer **clic derecho** sobre `Sistema de Gestion.app` → "Abrir"
     (la primera vez; doble clic puede ser bloqueado por Gatekeeper al no estar
     la app firmada/notarizada) y confirmar. El build de macOS es Intel (corre
     nativo en Mac con procesador Intel); en un Mac con chip Apple (M1/M2/M3...)
     puede aparecer un cartel pidiendo instalar **Rosetta** la primera vez —
     es normal, hay que aceptarlo y la app abre igual.
   - **Linux**: ejecutar `./Sistema de Gestion/Sistema de Gestion` desde una
     terminal, o marcarlo como ejecutable y abrirlo desde el explorador de archivos.
