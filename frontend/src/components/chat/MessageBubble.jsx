import React from "react";
import { AlertCircle, Check, CheckCheck, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { clock } from "./chatUtils";

function Ticks({ message }) {
  if (message.status === "failed") return <AlertCircle className="h-3.5 w-3.5 text-status-fail" aria-label="Not sent" />;
  if (message.status === "sending") return <Clock className="h-3 w-3 opacity-70" aria-label="Sending" />;
  if (message.read_at) return <CheckCheck className="h-3.5 w-3.5 text-accent" aria-label="Read" />;
  return <Check className="h-3.5 w-3.5 opacity-70" aria-label="Sent" />;
}

export function MessageBubble({ message, mine, endOfGroup, onRetry }) {
  const failed = message.status === "failed";

  return (
    <div className={cn("flex", mine ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[82%] md:max-w-[68%]", mine && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl px-3.5 py-2 text-sm shadow-soft",
            mine ? "bg-primary text-primary-foreground" : "border border-border bg-surface text-foreground",
            endOfGroup && (mine ? "rounded-br-md" : "rounded-bl-md"),
            failed && "opacity-70"
          )}
        >
          <p className="whitespace-pre-wrap break-words">{message.body}</p>
          <span
            className={cn(
              "font-num mt-1 flex items-center justify-end gap-1 text-[11px] leading-none",
              mine ? "text-primary-foreground/70" : "text-muted-foreground"
            )}
          >
            {clock(message.created_at)}
            {mine && <Ticks message={message} />}
          </span>
        </div>

        {failed && (
          <p className="mt-1 text-xs text-status-fail">
            {message.error || "Not sent"} ·{" "}
            <button
              type="button"
              onClick={onRetry}
              className="font-medium underline underline-offset-2"
              data-cursor-hover
            >
              Retry
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
