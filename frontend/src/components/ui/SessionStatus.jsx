import React from "react";
import { cn } from "@/lib/utils";
import { STATUS_LABEL } from "@/lib/roles";

// Tone by meaning, drawn from the site's status colours.
const TONES = {
  good: "bg-status-pass/10 text-status-pass ring-1 ring-status-pass/25",
  bad: "bg-status-fail/10 text-status-fail ring-1 ring-status-fail/25",
  warn: "bg-status-pending/10 text-status-pending ring-1 ring-status-pending/25",
  info: "bg-primary/10 text-primary ring-1 ring-primary/25",
  quiet: "bg-muted text-muted-foreground ring-1 ring-border",
};

const TONE_FOR = {
  APPROVED: "good", SIGNED: "good", VALID: "good", ACTIVE: "good", PASS: "good",
  REJECTED: "bad", RETURNED: "bad", OVERDUE: "bad", FAIL: "bad",
  "IN PROGRESS": "warn", "DUE SOON": "warn", "READY TO SIGN": "warn", "NO LIST": "warn",
  SUBMITTED: "info", "UNDER REVIEW": "info", "IN REVIEW": "info", FORWARDED: "info", RECEIVED: "info",
  DRAFT: "quiet", INACTIVE: "quiet",
};

/** A chip for a session status or a work-queue label (e.g. READY TO SIGN). */
export function SessionStatus({ status, className }) {
  if (!status) return null;
  const key = String(status).toUpperCase();
  const text = STATUS_LABEL[key] || key.charAt(0) + key.slice(1).toLowerCase();

  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium",
        TONES[TONE_FOR[key] || "quiet"],
        className
      )}
    >
      {text}
    </span>
  );
}
