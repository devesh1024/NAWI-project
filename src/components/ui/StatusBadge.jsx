import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const STYLES = {
  pass: "bg-status-pass/10 text-status-pass ring-1 ring-status-pass/25",
  fail: "bg-status-fail/10 text-status-fail ring-1 ring-status-fail/25",
  na: "bg-status-na/10 text-status-na ring-1 ring-status-na/25",
  pending: "bg-status-pending/10 text-status-pending ring-1 ring-status-pending/25",
};

const LABELS = {
  pass: "PASS",
  fail: "FAIL",
  na: "N/A",
  pending: "PENDING",
};

/** Status chip with a small settle-in animation — used when a calculation just resolved. */
export function StatusBadge({ status, animate = false, className }) {
  return (
    <motion.span
      initial={animate ? { scale: 0.7, opacity: 0 } : false}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 20 }}
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-mono font-semibold tracking-wide",
        STYLES[status],
        className
      )}
    >
      {LABELS[status]}
    </motion.span>
  );
}
