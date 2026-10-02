import React from "react";
import { cn } from "@/lib/utils";
import { avatarTone, initials } from "./chatUtils";

export function Avatar({ user, size = "md", online = false, className }) {
  const dims = size === "sm" ? "h-8 w-8 text-xs" : size === "lg" ? "h-12 w-12 text-base" : "h-11 w-11 text-sm";

  return (
    <span className={cn("relative inline-flex shrink-0", className)}>
      <span
        className={cn(
          "flex items-center justify-center rounded-full font-heading font-semibold",
          dims,
          avatarTone(user?.user_id)
        )}
        aria-hidden="true"
      >
        {initials(user?.name)}
      </span>
      {online && (
        <span
          className="absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-surface bg-status-pass"
          title="Online"
        />
      )}
    </span>
  );
}
