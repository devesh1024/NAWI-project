# TulaSetu — Frontend

React + Vite + plain JavaScript (no TypeScript), Tailwind, Framer Motion.
Talks to the team's FastAPI backend (see `../backend`) — not Supabase.

## Run it

```bash
npm install
npm run dev
```

By default the app talks to `http://127.0.0.1:8000` (the backend running
locally). To point at a deployed backend instead:

```bash
cp .env.example .env   # local dev works as-is (backend on :8000).
# For Vercel, set VITE_API_URL in the project's environment variables, then redeploy.
```

### Logging in

The demo account (`demo@nawitest.com` / `demo1234`) is a **real seeded
account in the backend database** — not a frontend-only bypass. It's offered
as a one-click fill-in on the login page so judges/testers don't need to
register their own lab. If it's missing from a given backend/environment,
someone with backend access needs to call `POST /api/auth/register` once
with those values (see `../backend/README.md`).

## What's wired to the real backend

- Auth: register/login — real JWT in `localStorage` under `nawi_session`.
- Instruments: list + create.
- Test Sessions: list, create, and a full detail page
  (`TestSessionDetail.jsx`) covering environmental conditions, adding tests,
  observations, manual calculation-result entry, status transitions, report
  generation, PDF/DOCX download, and approval.
- Reports: works off the test sessions list (there's no dedicated
  `GET /api/reports` list endpoint yet — see the note at the top of
  `Reports.jsx`).
- Equipment: full CRUD.
- Standards & Rules: tabbed admin page covering standards, test
  definitions, applicability rules, and MPE rules — all real CRUD.
- Users: list + create (tester/reviewer/approver).
- Settings: real profile + laboratory editing.

## What's still open

- **Dashboard** — still sample data (KPIs, charts, recent sessions). Wiring
  the "recent sessions" table and headline counts to `GET /api/test-sessions`
  would be cheap; the monthly-trend chart needs some real aggregation logic
  first.
- **Audit Log** — genuine backend gap, not a frontend TODO: `audit_logs` is
  being written to server-side (report generation/approval call
  `create_audit_log()`), but there's no `GET` route to read it back yet. See
  the comment in `AuditLog.jsx`.
- **Equipment-to-test assignment** — the backend has
  `POST /api/test-equipment/{id}/assign` ready; no UI calls it yet. Natural
  home would be from within a session-test row in `TestSessionDetail.jsx`.
- **The OIML calculation engine itself** (MPE lookup + pass/fail +
  applicability, computed automatically) is still a backend pass-through —
  `TestSessionDetail.jsx`'s calculation form is manual entry until that
  lands. Once it's server-side, that form can likely be replaced with a
  read-only result display.

## Notes on the motion layer

`EclipseGlow`, `AsciiRipple`, `ParticleField`, and `CustomCursor`
(`src/components/effects/`, `src/components/cursor/`) are hand-built —
ReactBits' actual Pro components live behind a registry not reachable from
this build environment. Same visual/interaction intent, different code.
