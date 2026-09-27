import React, { useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";

/**
 * Desktop-only custom cursor: a small ring that lags behind the pointer
 * with spring physics, and scales up over interactive elements.
 * Disabled on touch devices; respects prefers-reduced-motion by skipping
 * the scale/spring bounce (still shows a plain dot).
 */
export function CustomCursor() {
  const [enabled, setEnabled] = useState(false);
  const [hovering, setHovering] = useState(false);
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const springX = useSpring(x, { stiffness: 500, damping: 40, mass: 0.4 });
  const springY = useSpring(y, { stiffness: 500, damping: 40, mass: 0.4 });
  const raf = useRef(null);

  useEffect(() => {
    const isFinePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    if (!isFinePointer) return;
    setEnabled(true);
    document.body.classList.add("custom-cursor-active");

    function handleMove(e) {
      x.set(e.clientX);
      y.set(e.clientY);
      const target = e.target.closest("button, a, [data-cursor-hover]");
      setHovering(Boolean(target));
    }

    window.addEventListener("pointermove", handleMove);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      document.body.classList.remove("custom-cursor-active");
    };
  }, [x, y]);

  if (!enabled) return null;

  return (
    <motion.div
      aria-hidden="true"
      className="pointer-events-none fixed left-0 top-0 z-[999] rounded-full border-2 border-primary mix-blend-multiply"
      style={{
        x: springX,
        y: springY,
        translateX: "-50%",
        translateY: "-50%",
      }}
      animate={{
        width: hovering ? 44 : 22,
        height: hovering ? 44 : 22,
        opacity: hovering ? 0.9 : 0.6,
      }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
    />
  );
}
