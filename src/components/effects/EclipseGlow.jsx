import React from "react";

/**
 * Slow-drifting radial glow behind the hero — an "eclipse" of soft light
 * rather than a flat gradient rectangle. Pure CSS, no canvas needed.
 */
export function EclipseGlow({ className = "" }) {
  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
    >
      <div
        className="absolute left-1/2 top-1/3 h-[560px] w-[560px] -translate-x-1/2 -translate-y-1/2
                   rounded-full opacity-40 blur-3xl animate-drift"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, hsl(var(--primary) / 0.55), transparent 65%)",
        }}
      />
      <div
        className="absolute left-[60%] top-[55%] h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/2
                   rounded-full opacity-30 blur-3xl animate-drift"
        style={{
          animationDelay: "-6s",
          background:
            "radial-gradient(circle at 50% 50%, hsl(var(--accent) / 0.5), transparent 65%)",
        }}
      />
      {/* soft ring, like the edge of an eclipsed disc */}
      <div
        className="absolute left-1/2 top-1/3 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2
                   rounded-full border border-primary/20"
      />
    </div>
  );
}
