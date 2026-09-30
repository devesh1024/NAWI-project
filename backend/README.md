# Backend

FastAPI + PostgreSQL (hosted on Supabase — used purely as a Postgres host
here, not via Supabase's client/Auth/RLS). Deployed on Render.

```
backend/
├── app/            FastAPI application (models, schemas, routers)
├── tests/          calculation-engine tests
├── requirements.txt
├── create_tables.py
└── .env.example    copy to .env for local dev — see below
```

## Deployment (Render)

- **Live URL**: `TODO — paste your Render service URL here once you have it`
  (e.g. `https://nawi-project-xxxx.onrender.com`)
- **Swagger**: `<above URL>/docs`
- **Root Directory**: repo root (blank) — not `backend`. Code imports as
  `backend.app.main`, so the process must run from the repo root.
- **Build Command**: `pip install -r backend/requirements.txt`
- **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Environment variables required**: `DATABASE_URL`, `JWT_SECRET_KEY`,
  `CORS_ORIGINS` — see `.env.example` in this folder for the exact format
  each needs (the `DATABASE_URL` driver prefix in particular — `+psycopg2` is
  required, a bare `postgresql://` will crash on this SQLAlchemy version).

## CORS

CORS is driven by environment variables — no code edit needed:

- `CORS_ORIGINS` — comma-separated exact origins allowed to call the API
  (your production Vercel URL, no trailing slash). The local dev origins
  `http://localhost:5173` and `http://127.0.0.1:5173` are always allowed.
- `CORS_ORIGIN_REGEX` — optional, for Vercel preview deployments whose URL
  changes per branch (e.g. `https://nawi-.*\.vercel\.app`).

If `CORS_ORIGINS` is unset, the API works but the browser will block the
deployed frontend; the startup log says so.

## Running and testing

Always from the **repo root**, because the code imports as `backend.app...`:

```bash
python -m backend.create_tables        # `python backend/create_tables.py` also works
python backend/test_db.py              # connectivity check
uvicorn backend.app.main:app --reload
python -m pytest                       # also works from inside backend/
```

## What's implemented (as of this snapshot)

Real endpoints exist for: auth (register/login), instruments, laboratories,
users, standards, test_definitions, test_applicability_rules, mpe_rules,
environmental_conditions, test_equipment, test_sessions, session tests,
observations, calculation-result, and full report generation (DOCX + PDF).

**Still a pass-through, not yet real logic**: `POST .../calculation-result`
and the `applicability_status`/`na_reason` fields on `POST .../tests` accept
whatever the caller sends — they don't yet compute pass/fail from
`mpe_rules` or applicability from `test_applicability_rules` automatically.
This is the OIML calculation engine, understood to be in progress separately.

See `../docs/Schema_for_all_Data_in_the_Project_SIH26035.pdf` for the full
schema this is built against.
