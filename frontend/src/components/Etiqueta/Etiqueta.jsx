/* Pastilla de estado. tipo: "ok" | "aviso" | "error" | "neutra" | "tema" */
export default function Etiqueta({ tipo = "neutra", children }) {
  return <span className={`etiqueta etiqueta--${tipo}`}>{children}</span>;
}
