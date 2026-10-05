import React from "react";
import { Link } from "react-router-dom";
import { Lock } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { canOpen } from "@/lib/roles";

/** Shows a page only to roles that work in it; anyone else gets a clear explanation. */
export function RouteGuard({ page, children }) {
  const auth = useAuth();

  if (!auth.profileReady) return null;
  if (canOpen({ role: auth.role, can: auth.can }, page)) return children;

  return (
    <div className="mx-auto mt-16 max-w-md rounded-xl border border-border bg-surface p-8 text-center shadow-soft">
      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
        <Lock className="h-5 w-5 text-muted-foreground" />
      </span>
      <h1 className="mt-4 font-heading text-lg font-semibold">Not part of your role</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        As {auth.roleLabel}, you don&apos;t work in this area. Your dashboard shows what is yours to do.
      </p>
      <Link
        to="/app/dashboard"
        className="mt-5 inline-block rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:brightness-110"
        data-cursor-hover
      >
        Back to dashboard
      </Link>
    </div>
  );
}
