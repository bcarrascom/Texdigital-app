import { motion } from "motion/react";

/* Un círculo que gira: el indicador de "trabajando en eso". Viene del
   componente LoaderSpinner que trajo Bruno (2026-11-14), pasado a JSX y sin
   Tailwind (la app no lo usa): dos lados del borde con color y dos
   transparentes, girando sin pausa.

       <Girador size={18} borderWidth={2} />

   Con "reducir movimiento" (MotionConfig en App) queda quieto. */
export default function Girador({ size = 40, color = "currentColor", borderWidth = 4, duration = 1, style, ...props }) {
  return (
    <motion.div
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        flex: "none",
        borderRadius: "50%",
        border: `${borderWidth}px solid transparent`,
        borderTopColor: color,
        borderRightColor: color,
        ...style,
      }}
      animate={{ rotate: 360 }}
      transition={{ duration, ease: "linear", repeat: Infinity }}
      {...props}
    />
  );
}
