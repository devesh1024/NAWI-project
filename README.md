# TulaSetu

OIML R-76 test report platform for legal-metrology labs. SIH 2026, Problem
Statement 26035 (Ministry of Consumer Affairs, DoCA).

## Structure

```
.
├── frontend/   React + Vite UI, deployed on Vercel. See frontend/README.md.
├── backend/    FastAPI + PostgreSQL (Supabase-hosted), deployed on Render.
│               See backend/README.md — includes CORS setup + env vars.
└── docs/       Reference material both sides build against.
```

## Current status (fill in your two deployed URLs as you go)

- **Frontend (Vercel)**: `TODO — paste your production Vercel URL here`
- **Backend (Render)**: `TODO — paste your Render service URL here`
- **Backend Swagger**: `<above Render URL>/docs`

Once both URLs exist, each side is told about the other through **environment
variables only** — there is no placeholder left in the code to edit:

1. **Render** (backend service → Environment):
   `DATABASE_URL`, `JWT_SECRET_KEY`, and `CORS_ORIGINS` = your Vercel URL.
   See `backend/.env.example` for the exact format of each.
2. **Vercel** (project → Settings → Environment Variables):
   `VITE_API_URL` = your Render URL, then **redeploy** (Vite bakes it in at
   build time). See `frontend/.env.example`.

## Running locally

From the **repo root** (the backend imports as `backend.app...`):

```bash
cp backend/.env.example backend/.env      # then fill in DATABASE_URL + JWT_SECRET_KEY
pip install -r backend/requirements.txt
python -m backend.create_tables           # or: python backend/create_tables.py
uvicorn backend.app.main:app --reload     # API on http://127.0.0.1:8000

cd frontend && cp .env.example .env && npm install && npm run dev   # UI on :5173
```

Backend tests run from either the repo root or `backend/`: `python -m pytest`.

## Demo laboratory (one login per role)

`python -m backend.seed_demo_lab` creates a demo laboratory with **one person
for every role** (Lab Head, Technical Manager, Quality Manager, Reviewer,
Authorised Signatory, Tester, Assistant, Records Officer, Standards Custodian,
Auditor), some instruments and reference weights, and sessions at every stage
of the workflow, so each role's dashboard has real work on it. Everything is
created through the application's own API, so it obeys the same rules as real
data. Safe to run twice.

All accounts use the password `demo1234`; the login page has a
"see the lab as another role" picker. The Lab Head is `demo@nawitest.com`,
a **real account that must be seeded in the production database**, not a
frontend-only bypass. See `frontend/src/lib/devAuth.js` and
[`docs/roles-and-permissions.md`](docs/roles-and-permissions.md).

## Roles and responsibilities

Roles follow how an ISO/IEC 17025 laboratory is staffed, and the central rule
is **maker-checker**: whoever tested a session can never review or sign it.
Each role gets its own dashboard and only the screens it works in; the backend
enforces every rule, the frontend just mirrors it. Full details:
[`docs/roles-and-permissions.md`](docs/roles-and-permissions.md).

Who works where

- **Frontend** (`frontend/`): UI/UX, all React components, the design
  system, the motion layer, calling the backend's REST API.
- **Backend** (`backend/`): FastAPI routes, the Postgres schema, and the
  OIML calculation engine (MPE lookup + pass/fail + applicability),
  currently in progress separately — see `backend/README.md` for exactly
  what's real vs. still a pass-through.