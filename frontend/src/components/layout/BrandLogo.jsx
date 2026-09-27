import React from "react";
import { Link } from "react-router-dom";
import { Scale } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

/**
 * Clicking the brand mark goes to the marketing home page if signed out,
 * or straight to the dashboard if signed in — used on the landing nav and
 * the auth pages. (Inside the app shell, the sidebar's own logo always
 * goes to the dashboard, since you can only see the sidebar while signed in.)
 */
export function BrandLogo({ className = "" }) {
  const { session } = useAuth();
  const to = session ? "/app/dashboard" : "/";

  return (
    <Link
      to={to}
      data-cursor-hover
      className={`flex items-center gap-2 font-heading text-lg font-semibold ${className}`}
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-rail text-rail-foreground">
        <Scale className="h-4 w-4" />
      </span>
      NAWI TestSuite
    </Link>
  );
}
