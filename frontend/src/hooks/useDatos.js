import { useCallback, useEffect, useState } from "react";

/* Carga datos de Python al montar (y cada vez que cambian las dependencias).

       const { datos: op, cargando, error, recargar } =
         useDatos(() => api.obtener_despacho(numero), [numero]);

   `recargar()` vuelve a pedir sin pasar por el estado de "cargando", para
   que la pantalla no parpadee después de guardar algo. */
export function useDatos(cargar, deps) {
  const [estado, setEstado] = useState({ datos: null, cargando: true, error: null });

  // Las dependencias las pasa quien llama, igual que en un useEffect.
  const pedir = useCallback(cargar, deps);

  useEffect(() => {
    let vigente = true; // si la página se desmonta antes de que Python responda
    setEstado((e) => ({ ...e, cargando: true, error: null }));
    Promise.resolve(pedir())
      .then((datos) => vigente && setEstado({ datos, cargando: false, error: null }))
      .catch((error) => {
        console.error(error);
        if (vigente) setEstado({ datos: null, cargando: false, error });
      });
    return () => { vigente = false; };
  }, [pedir]);

  const recargar = useCallback(async () => {
    const datos = await pedir();
    setEstado({ datos, cargando: false, error: null });
    return datos;
  }, [pedir]);

  return { ...estado, recargar };
}
