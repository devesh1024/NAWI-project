import React from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useChat } from "@/hooks/useChat";

/**
 * New-message cards, top right.
 *   title: who sent it   body: first 25 characters   action: View more -> that chat
 */
export function ToastStack() {
  const { toasts, dismissToast } = useChat();
  const navigate = useNavigate();

  return (
    <div
      className="pointer-events-none fixed right-4 top-[4.75rem] z-[60] flex w-[min(92vw,22rem)] flex-col gap-2"
      aria-live="polite"
    >
      <AnimatePresence initial={false}>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, x: 48 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 48, transition: { duration: 0.15 } }}
            transition={{ type: "spring", stiffness: 420, damping: 34 }}
            role="status"
            className="pointer-events-auto overflow-hidden rounded-xl border border-border bg-surface shadow-raised"
          >
            <div className="flex">
              <span className="w-1 shrink-0 bg-primary" aria-hidden="true" />
              <div className="min-w-0 flex-1 px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="truncate font-heading text-sm font-semibold">{toast.title}</p>
                  <button
                    type="button"
                    onClick={() => dismissToast(toast.id)}
                    className="-mr-1 -mt-1 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Dismiss notification"
                    data-cursor-hover
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
                <p className="mt-0.5 break-words text-sm text-muted-foreground">{toast.body}</p>
                <button
                  type="button"
                  onClick={() => {
                    dismissToast(toast.id);
                    navigate(`/app/teamdesk/${toast.conversation_id}`);
                  }}
                  className="mt-2 rounded-lg bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:brightness-110"
                  data-cursor-hover
                >
                  View more
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
