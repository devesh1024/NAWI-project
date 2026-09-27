import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { BrandLogo } from "@/components/layout/BrandLogo";

export function MarketingNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="container flex h-16 items-center justify-between">
        <BrandLogo />
        <nav className="hidden items-center gap-8 text-sm font-medium text-muted-foreground md:flex">
          <a href="#workflow" className="hover:text-foreground">How it works</a>
          <a href="#capabilities" className="hover:text-foreground">Capabilities</a>
          <a href="#compliance" className="hover:text-foreground">Compliance</a>
        </nav>
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link to="/login">Login to your lab</Link>
          </Button>
          <Button asChild variant="primary" size="sm">
            <Link to="/register">Register laboratory</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
