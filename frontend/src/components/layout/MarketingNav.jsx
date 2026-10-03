import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { BrandLogo } from "@/components/layout/BrandLogo";
import { useAuth } from "@/hooks/useAuth";

export function MarketingNav() {
  // Without this check, a signed-in user landing here (e.g. via the
  // sidebar's "Visit Home Page" button) would still see "Login to your
  // lab" and naturally click it — their session was never actually
  // cleared, but ending up back on the login form reads exactly like
  // being logged out. Showing "Go to dashboard" instead fixes that.
  const { session } = useAuth();

  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="container flex h-16 items-center justify-between">
        <BrandLogo />
        <nav className="hidden items-center gap-8 text-sm font-medium text-muted-foreground md:flex">
          <a href="/#workflow" className="hover:text-foreground">How it works</a>
          <a href="/#capabilities" className="hover:text-foreground">Capabilities</a>
          <a href="/#compliance" className="hover:text-foreground">Compliance</a>
          <Link to="/verify" className="hover:text-foreground">Verify a report</Link>
        </nav>
        <div className="flex items-center gap-3">
          {session ? (
            <Button asChild variant="primary" size="sm">
              <Link to="/app/dashboard">Go to dashboard</Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link to="/login">Login to your lab</Link>
              </Button>
              <Button asChild variant="primary" size="sm">
                <Link to="/register">Register laboratory</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
