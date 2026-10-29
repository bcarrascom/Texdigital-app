import { useCallback, useEffect, useState } from "react";
import { api } from "@/services/api";

/* El estado de la búsqueda de versiones nuevas (ver ui/api_actualizacion.py):
   la app busca sola al abrir, y esto lo va leyendo.

       const { estado, buscar, instalar } = useActualizacion();
       estado.fase  "buscando" | "al_dia" | "disponible" | "descargando"
                    | "listo" | "error" | "no_disponible"

   Mientras Python está buscando o descargando, se le vuelve a preguntar
   seguido; el resto del tiempo, nada. `alActualizarse` se llama si la app
   se abrió recién actualizada (Python lo dice una sola vez). */
const EN_CURSO = ["buscando", "descargando", "listo"];
const CADA_MS = 600;

export function useActualizacion({ alActualizarse } = {}) {
  const [estado, setEstado] = useState(null);

  useEffect(() => {
    let vigente = true;
    api.estado_actualizacion().then((e) => {
      if (!e) return;
      // Aunque la página ya se haya ido: Python lo dice una sola vez.
      if (e.recien_actualizado) alActualizarse?.(e.version);
      if (vigente) setEstado(e);
    });
    return () => { vigente = false; };
  }, []);  // solo al montar: el aviso de "se actualizó" sale una vez

  const fase = estado?.fase;
  useEffect(() => {
    if (!EN_CURSO.includes(fase)) return;
    const id = setInterval(() => api.estado_actualizacion().then((e) => e && setEstado(e)), CADA_MS);
    return () => clearInterval(id);
  }, [fase]);

  const buscar = useCallback(async () => setEstado(await api.buscar_actualizacion()), []);
  const instalar = useCallback(async () => setEstado(await api.instalar_actualizacion()), []);

  return { estado, buscar, instalar };
}
