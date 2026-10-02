import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

/** Same look as the existing "Register instrument" dialog, reusable. */
export function Modal({ open, title, onClose, children, maxWidth = "max-w-lg" }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            onClick={(e) => e.stopPropagation()}
            className={`max-h-[85vh] w-full ${maxWidth} overflow-y-auto rounded-2xl border border-border bg-surface p-6 shadow-raised`}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-heading text-lg font-semibold">{title}</h2>
              <button type="button" onClick={onClose} aria-label="Close" data-cursor-hover>
                <X className="h-5 w-5 text-muted-foreground" />
              </button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
