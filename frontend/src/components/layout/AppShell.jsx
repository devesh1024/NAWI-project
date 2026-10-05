import React from "react";
import { Link, Outlet } from "react-router-dom";
import { MessagesSquare } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { NotificationBell } from "@/components/chat/NotificationBell";
import { useAuth } from "@/hooks/useAuth";
import { roleTone } from "@/lib/roles";
import { cn } from "@/lib/utils";

export default function AppShell() {
  const { email, role, roleLabel, name, can, profileReady, signOut } = useAuth();

  // Wait for the server to say who this is, so a person never briefly sees
  // screens that belong to another role.
  if (!profileReady) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        Loading your workspace…
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar role={role} can={can} />
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
              <p className="text-sm font-medium leading-tight">{name || email}</p>
              <p className="mt-0.5 flex justify-end">
                <span className={cn("rounded-full px-2 py-px text-[11px] font-medium leading-snug", roleTone(role))}>
                  {roleLabel || "—"}
                </span>
              </p>
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
