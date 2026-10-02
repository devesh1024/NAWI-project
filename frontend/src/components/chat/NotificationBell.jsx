import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { Avatar } from "./Avatar";
import { listTime, preview } from "./chatUtils";

export function NotificationBell() {
  const { notifications, unreadTotal } = useChat();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return undefined;
    const onPointer = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const go = (cid) => {
    setOpen(false);
    navigate(`/app/teamdesk/${cid}`);
  };

  return (
    <div className="relative" ref={wrapRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border text-foreground hover:bg-muted"
        aria-label={unreadTotal ? `Notifications, ${unreadTotal} unread` : "Notifications"}
        aria-expanded={open}
        aria-haspopup="true"
        data-cursor-hover
      >
        <Bell className="h-4 w-4" />
        {unreadTotal > 0 && (
          <span className="font-num absolute -right-1.5 -top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold text-accent-foreground">
            {unreadTotal > 99 ? "99+" : unreadTotal}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-[22rem] max-w-[92vw] overflow-hidden rounded-xl border border-border bg-surface shadow-raised">
          <div className="border-b border-border px-4 py-3">
            <p className="font-heading text-sm font-semibold">Notifications</p>
          </div>

          {notifications.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-muted-foreground">You&apos;re all caught up.</p>
          ) : (
            <ul className="max-h-96 overflow-y-auto">
              {notifications.map((n) => (
                <li key={n.conversation_id}>
                  <button
                    type="button"
                    onClick={() => go(n.conversation_id)}
                    className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-muted"
                    data-cursor-hover
                  >
                    <Avatar user={n.other_user} size="sm" />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-baseline justify-between gap-2">
                        <span className="truncate text-sm font-medium">{n.other_user.name}</span>
                        <span className="font-num shrink-0 text-[11px] text-muted-foreground">
                          {listTime(n.last_message_at)}
                        </span>
                      </span>
                      <span className="block break-words text-sm text-muted-foreground">
                        {preview(n.last_message?.body)}
                      </span>
                      <span className="mt-1 inline-block text-xs font-medium text-primary">
                        {n.unread_count > 1 ? `${n.unread_count} new messages · ` : ""}View more
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
