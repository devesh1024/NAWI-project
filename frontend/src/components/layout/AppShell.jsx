import React from "react";
import { Link, Outlet } from "react-router-dom";
import { MessagesSquare } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { NotificationBell } from "@/components/chat/NotificationBell";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import { roleLabel } from "@/components/chat/chatUtils";

export default function AppShell() {
  const { email, role, signOut } = useAuth();
  const { me } = useChat();

  return (
    <div className="flex h-screen bg-background">
      <Sidebar role={role} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b border-border px-6">
          <div />
          {/* notifications, TeamDesk, user (role), sign out */}
          <div className="flex items-center gap-3">
            <NotificationBell />

            <Link
              to="/app/teamdesk"
              className="flex h-9 items-center gap-2 rounded-lg border border-border px-3 text-xs font-medium hover:bg-muted"
              data-cursor-hover
            >
              <MessagesSquare className="h-4 w-4" />
              TeamDesk
            </Link>

            <div className="text-right" title={email || undefined}>
              <p className="text-sm font-medium leading-tight">{me?.name || email}</p>
              <p className="text-xs leading-tight text-muted-foreground">{roleLabel(role) || "—"}</p>
            </div>

            <button
              onClick={signOut}
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted"
              data-cursor-hover
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
