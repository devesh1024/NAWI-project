# NAWI TestSuite — Phase 1

React + Vite + **plain JavaScript** (no TypeScript), Tailwind, Framer Motion,
Supabase (client wired, schema/RLS not yet created).

## Run it

```bash
npm install
npm run dev
```

### Logging in right now (no Supabase project yet)

Without a `.env`, the app auto-detects there's no Supabase project connected
and switches to a **temporary hardcoded demo login** so you can actually click
through the authenticated app:

```
demo@nawitest.local / demo1234
```

This is shown on the login screen itself while it's active. It's a *dev-mode
switch*, not a separate code path you'll need to rip out by hand:

- `src/lib/devAuth.js` — the hardcoded user + a tiny localStorage-backed "session"
- `src/hooks/useAuth.jsx` — the only file that branches on `isDevMode()`; every
  other component (Login, Register, AppShell) calls `signIn()` / `signOut()`
  from `useAuth()` and has no idea whether it's talking to Supabase or the demo user

**To switch to real Supabase**: just fill in `.env` (copy `.env.example`) with
your project's URL and anon key. `isDevMode()` returns `false` automatically
the moment `VITE_SUPABASE_URL` is set — no file needs to be touched, deleted,
or reverted. The demo credentials simply stop being offered.

## What's built in this pass

- Landing page: hero with Eclipse glow + particle field + ASCII ripple, workflow
  timeline, capabilities grid, compliance strip.
- Design system: Tailwind tokens (`src/index.css`), Button/Card/StatusBadge/
  AnimatedNumber components — not the default shadcn theme.
- Custom cursor (desktop only, disabled on touch, respects `prefers-reduced-motion`).
- Login + Laboratory Registration pages, wired to Supabase Auth + inserts into
  `laboratories` / `users` (will work once your Supabase project has those
  tables — see "Not built yet" below).
- Authenticated app shell: icon-rail sidebar with sliding active indicator,
  role-aware nav items, topbar with signed-in user + role.
- Dashboard: KPI counters, pass/fail donut, monthly trend line, recent
  sessions table, pending-approvals panel — all on sample data for now.
- Instruments: searchable list + a "Register instrument" modal form, fields
  matched to the `instruments` table.
- Test Sessions / Reports / Equipment / Standards / Users / Audit Log /
  Settings: placeholder screens (styled, not broken) marking what's backed by
  which schema tables, ready to be built out next.

## Not built yet (next phases)

1. **Supabase schema + RLS** — the 21 tables from the schema doc don't exist
   in a database yet; I don't have Supabase project credentials to create
   them. Once you create a project, send me the SQL editor access or ask me
   for a migration script and I'll generate the full `CREATE TABLE` +
   `Row-Level Security policy` SQL to paste in.
2. **New Test Session wizard** — the 6-step flow (instrument → applicability
   check → environment → observations/import → calculated results → submit).
3. **Reports repository**, **Equipment**, **Standards & Rules (admin)**,
   **Users (admin)**, **Audit Log** — currently placeholders.
4. Report generation itself (PDF/DOCX assembly + OIML calculation engine) is
   out of scope for the UI pass, per the agreed plan.

## Notes on the motion layer

ReactBits' actual Pro components (Eclipse, ASCII Ripple, particle text,
custom cursor) live behind a registry I don't have network access to install
from in this environment, so `EclipseGlow`, `AsciiRipple`, `ParticleField`,
and `CustomCursor` are hand-built equivalents (CSS + canvas + Framer Motion)
matching the same visual/interaction intent. If you do get the real ReactBits
packages installed locally, these four files are the ones to swap out — the
rest of the app doesn't depend on their internals.
