import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";

export default defineConfig({
  plugins: [
    react(),
    // import Lapiz from "@/assets/svg/pencil.svg?react"  →  <Lapiz />
    svgr(),
  ],
  // Rutas relativas en el build: pywebview sirve frontend/dist/ desde una
  // subcarpeta de su servidor interno, no desde la raíz (ver ui/api_app.py).
  base: "./",
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: { port: 5173, strictPort: true },
  // El aviso de 500 kB es para sitios web que se bajan por red: acá el
  // bundle se lee del disco (pywebview), su tamaño no se nota. Si algún día
  // hay versión web, conviene partirlo con import() por página en vez de
  // subir este número.
  build: { chunkSizeWarningLimit: 1500 },
});
