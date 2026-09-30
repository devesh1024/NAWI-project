import React from "react";
import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutGrid,
  Gauge,
  FlaskConical,
  FileText,
  Wrench,
  BookMarked,
  Users2,
  ScrollText,
  Settings,
  Scale,
  Home,
} from "lucide-react";

// role gate: null = visible to everyone signed in
const NAV_ITEMS = [
  { to: "/app/dashboard", icon: LayoutGrid, label: "Dashboard", roles: null },
  { to: "/app/instruments", icon: Gauge, label: "Instruments", roles: null },
  { to: "/app/test-sessions", icon: FlaskConical, label: "Test Sessions", roles: null },
  { to: "/app/reports", icon: FileText, label: "Reports", roles: null },
  { to: "/app/equipment", icon: Wrench, label: "Equipment", roles: null },
  { to: "/app/standards", icon: BookMarked, label: "Standards & Rules", roles: ["LAB_ADMIN"] },
  { to: "/app/users", icon: Users2, label: "Users", roles: ["LAB_ADMIN"] },
  { to: "/app/audit-log", icon: ScrollText, label: "Audit Log", roles: ["LAB_ADMIN"] },
];

/**
 * `role` is currently read from the users table lookup (see AppShell); pass
 * null while that hasn't resolved yet to show the common items only.
 */
export function Sidebar({ role }) {
  const items = NAV_ITEMS.filter((item) => !item.roles || (role && item.roles.includes(role)));

  return (
    <aside className="flex h-screen w-[76px] flex-col items-center gap-1 bg-rail py-5">
      <NavLink
        to="/app/dashboard"
        className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-rail-foreground"
        data-cursor-hover
      >
        <Scale className="h-5 w-5" />
      </NavLink>

      <nav className="flex flex-1 flex-col items-center gap-1">
        {items.map((item) => (
          <NavLink key={item.to} to={item.to} className="relative" data-cursor-hover>
            {({ isActive }) => (
              <div className="group relative flex h-11 w-11 items-center justify-center">
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active-pill"
                    className="absolute inset-0 rounded-xl bg-white/12"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <item.icon
                  className={`relative h-5 w-5 ${
                    isActive ? "text-white" : "text-rail-foreground/60 group-hover:text-rail-foreground"
                  }`}
                />
                <span className="pointer-events-none absolute left-full ml-3 whitespace-nowrap rounded-md bg-rail px-2 py-1 text-xs text-rail-foreground opacity-0 shadow-raised transition-opacity group-hover:opacity-100">
                  {item.label}
                </span>
              </div>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Only way back to the marketing site while signed in — the logo above
          intentionally goes to the dashboard instead, per the agreed logo behavior. */}
      <NavLink to="/" data-cursor-hover className="group relative mb-1 flex h-11 w-11 items-center justify-center">
        <Home className="h-5 w-5 text-rail-foreground/60 group-hover:text-rail-foreground" />
        <span className="pointer-events-none absolute left-full ml-3 whitespace-nowrap rounded-md bg-rail px-2 py-1 text-xs text-rail-foreground opacity-0 shadow-raised transition-opacity group-hover:opacity-100">
          Visit Home Page
        </span>
      </NavLink>

      <NavLink to="/app/settings" data-cursor-hover>
        {({ isActive }) => (
          <div className="flex h-11 w-11 items-center justify-center rounded-xl hover:bg-white/10">
            <Settings className={`h-5 w-5 ${isActive ? "text-white" : "text-rail-foreground/60"}`} />
          </div>
        )}
      </NavLink>
    </aside>
  );
}
