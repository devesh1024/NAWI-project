import React from "react";
import { Pencil, Trash2 } from "lucide-react";

/**
 * Edit / Delete icon buttons for a table row.
 * Pass onEdit / onDelete as null to hide a button; pass editDisabled /
 * deleteDisabled (with a reason string) to show it greyed out with a tooltip.
 */
export function RowActions({ onEdit, onDelete, editDisabled, deleteDisabled }) {
  const base = "rounded-md p-1.5 transition-colors disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div className="flex items-center justify-end gap-1">
      {onEdit && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onEdit(); }}
          disabled={Boolean(editDisabled)}
          title={editDisabled || "Edit"}
          aria-label="Edit"
          data-cursor-hover
          className={`${base} text-muted-foreground hover:bg-muted hover:text-foreground`}
        >
          <Pencil className="h-4 w-4" />
        </button>
      )}
      {onDelete && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          disabled={Boolean(deleteDisabled)}
          title={deleteDisabled || "Delete"}
          aria-label="Delete"
          data-cursor-hover
          className={`${base} text-status-fail hover:bg-status-fail/10`}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
