import React from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useAuth } from "@/hooks/useAuth";

export default function AppShell() {
  const { email, role, signOut } = useAuth();

  return (
    <div className="flex h-screen bg-background">
      <Sidebar role={role} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b border-border px-6">
          <div />
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-medium leading-tight">{email}</p>
              <p className="text-xs capitalize leading-tight text-muted-foreground">
                {role?.toLowerCase().replace("_", " ") || "—"}
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
