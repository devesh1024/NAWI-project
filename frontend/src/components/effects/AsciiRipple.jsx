import React, { useEffect, useRef } from "react";

const CHARS = " .:-=+*#%@";

/**
 * A grid of monospace characters whose density ripples outward from
 * pointer position/clicks — a "signal / interference pattern" motif,
 * which fits a metrology product thematically. Confined to one section;
 * not meant to run inside dense data tables.
 */
export function AsciiRipple({ className = "", cell = 14 }) {
  const canvasRef = useRef(null);
  const rippleRef = useRef([]); // {x, y, t}

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let width, height, cols, rows;
    let raf;
    const start = performance.now();

    function resize() {
      width = canvas.offsetWidth;
      height = canvas.offsetHeight;
      canvas.width = width * window.devicePixelRatio;
      canvas.height = height * window.devicePixelRatio;
      ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
      cols = Math.ceil(width / cell);
      rows = Math.ceil(height / cell);
    }

    function addRipple(x, y) {
      rippleRef.current.push({ x, y, t: performance.now() });
      if (rippleRef.current.length > 6) rippleRef.current.shift();
    }

    function handleMove(e) {
      const rect = canvas.getBoundingClientRect();
      addRipple(e.clientX - rect.left, e.clientY - rect.top);
    }

    function draw(now) {
      ctx.clearRect(0, 0, width, height);
      ctx.font = `${cell - 2}px "IBM Plex Mono", monospace`;
      ctx.textBaseline = "top";

      const elapsed = (now - start) / 1000;

      for (let ry = 0; ry < rows; ry++) {
        for (let rx = 0; rx < cols; rx++) {
          const x = rx * cell;
          const y = ry * cell;

          // Ambient slow wave so the grid isn't static even without pointer input.
          let intensity =
            (Math.sin(rx * 0.25 + elapsed * 0.6) + Math.cos(ry * 0.25 + elapsed * 0.4)) / 4 + 0.35;

          for (const r of rippleRef.current) {
            const age = (now - r.t) / 1000;
            if (age > 2.2) continue;
            const dist = Math.hypot(x - r.x, y - r.y);
            const wave = Math.sin(dist * 0.12 - age * 8) * Math.exp(-age * 1.4) * Math.exp(-dist * 0.006);
            intensity += wave * 0.7;
          }

          intensity = Math.max(0, Math.min(1, intensity));
          const charIdx = Math.floor(intensity * (CHARS.length - 1));
          if (charIdx <= 0) continue;

          ctx.fillStyle = `hsl(173 60% 30% / ${0.15 + intensity * 0.55})`;
          ctx.fillText(CHARS[charIdx], x, y);
        }
      }
      raf = requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener("resize", resize);
    canvas.addEventListener("pointermove", handleMove);
    canvas.addEventListener("pointerdown", handleMove);
    raf = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("pointermove", handleMove);
      canvas.removeEventListener("pointerdown", handleMove);
      cancelAnimationFrame(raf);
    };
  }, [cell]);

  return <canvas ref={canvasRef} className={`h-full w-full ${className}`} />;
}
