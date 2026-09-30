import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.auth.routes import router as auth_router
from backend.app.api.instruments.routes import router as instruments_router
from backend.app.api.test_sessions.routes import router as test_sessions_router
from backend.app.api.test_sessions.test_routes import router as test_session_tests_router
from backend.app.api.observations.routes import router as observations_router
from backend.app.api.test_sessions.calculation_routes import router as calculation_router
from backend.app.api.reports.routes import router as reports_router
from backend.app.api.laboratories.router import router as laboratories_router
from backend.app.api.users.router import router as users_router
from backend.app.api.standards.router import router as standards_router
from backend.app.api.test_definitions.router import router as test_definitions_router
from backend.app.api.test_applicability_rules.router import (
    router as test_applicability_rules_router,
)
from backend.app.api.mpe_rules.router import router as mpe_rules_router
from backend.app.api.environmental_conditions.routes import (
    router as environmental_conditions_router,
)
from backend.app.api.test_equipment.routes import (
    router as test_equipment_router,
)

app = FastAPI(
    title="NAWI Test Report Generation API",
    version="1.0.0"
)

# CORS is configured through environment variables, so deploying needs no code
# edit (set them in backend/.env locally, or in the Render dashboard):
#
#   CORS_ORIGINS       comma-separated exact origins allowed to call the API,
#                      e.g. https://nawi-testsuite.vercel.app
#   CORS_ORIGIN_REGEX  optional regex, for Vercel preview deployments whose URL
#                      changes per branch, e.g. https://nawi-testsuite.*\.vercel\.app
#
# The local Vite dev server origins are always allowed.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # backend/.env; real env vars win

logger = logging.getLogger("uvicorn.error")


def _parse_origins(value: str | None) -> list[str]:
    """'a, b/ ,,c' -> ['a', 'b', 'c'] (trimmed; trailing slashes dropped, since
    browsers send origins without one and a trailing slash would never match)."""
    return [o.strip().rstrip("/") for o in (value or "").split(",") if o.strip()]


LOCAL_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

ALLOWED_ORIGINS = LOCAL_DEV_ORIGINS + _parse_origins(os.getenv("CORS_ORIGINS"))
ALLOWED_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX") or None

if len(ALLOWED_ORIGINS) == len(LOCAL_DEV_ORIGINS) and not ALLOWED_ORIGIN_REGEX:
    logger.info(
        "CORS: only local dev origins are allowed. Set CORS_ORIGINS to your "
        "deployed frontend URL or the browser will block it."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(instruments_router)
app.include_router(laboratories_router)
app.include_router(test_sessions_router)
app.include_router(test_session_tests_router)
app.include_router(observations_router)
app.include_router(calculation_router)
app.include_router(reports_router)
app.include_router(users_router)
app.include_router(standards_router)
app.include_router(test_definitions_router)
app.include_router(test_applicability_rules_router)
app.include_router(mpe_rules_router)
app.include_router(environmental_conditions_router)
app.include_router(test_equipment_router)

@app.get("/")
def root():
    return {
        "message": "NAWI Backend is running"
    }