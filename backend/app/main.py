import logging
import os
from pathlib import Path

import socketio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.auth.routes import router as auth_router
from backend.app.api.instruments.routes import router as instruments_router
from backend.app.api.test_sessions.routes import router as test_sessions_router
from backend.app.api.test_sessions.management_routes import router as test_session_management_router
from backend.app.api.test_sessions.test_routes import router as test_session_tests_router
from backend.app.api.observations.routes import router as observations_router
from backend.app.api.test_sessions.calculation_routes import (
    router as calculation_router,
)
from backend.app.api.reports.routes import router as reports_router
from backend.app.api.reports.management_routes import router as report_management_router
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
from backend.app.api.chat.routes import router as chat_router
from backend.app.api.verify.routes import router as verify_router
from backend.app.services.verification.signing import ensure_signing_identity
from backend.app.realtime.socketio_server import sio
from backend.app.database.connection import Base, engine
import backend.app.models

# Load environment variables from backend/.env locally.
# Real environment variables (e.g. Render) take precedence.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Make sure the report-signing key/cert exist (auto-generated on first run, or
# loaded from SIGNING_KEY_PEM / SIGNING_CERT_PEM). Never block app startup on it.
try:
    ensure_signing_identity()
except Exception as exc:  # pragma: no cover
    logging.getLogger("uvicorn.error").error("Report signing key unavailable: %s", exc)

logger = logging.getLogger("uvicorn.error")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NAWI Test Report Generation API",
    version="1.0.0",
)


def _parse_origins(value: str | None) -> list[str]:
    """
    Parse comma-separated CORS origins.

    Example:
        "https://example.com, https://another.com/"
        ->
        ["https://example.com", "https://another.com"]
    """
    return [
        origin.strip().rstrip("/")
        for origin in (value or "").split(",")
        if origin.strip()
    ]


# Local Vite development URLs
LOCAL_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


# Production / deployed frontend URLs are configured through:
#
# CORS_ORIGINS=https://navi-project-zeta.vercel.app
#
# Multiple origins can be comma-separated.
ALLOWED_ORIGINS = (
    LOCAL_DEV_ORIGINS
    + _parse_origins(os.getenv("CORS_ORIGINS"))
)


# Optional regex for Vercel preview deployments.
#
# Example Render environment variable:
# CORS_ORIGIN_REGEX=https://navi-project-zeta-.*\.vercel\.app
#
# Leave unset if only the production Vercel URL is required.
ALLOWED_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX") or None


if len(ALLOWED_ORIGINS) == len(LOCAL_DEV_ORIGINS) and not ALLOWED_ORIGIN_REGEX:
    logger.info(
        "CORS: only local development origins are allowed. "
        "Set CORS_ORIGINS to your deployed frontend URL."
    )
else:
    logger.info(
        "CORS allowed origins: %s",
        ALLOWED_ORIGINS,
    )

    if ALLOWED_ORIGIN_REGEX:
        logger.info(
            "CORS allowed origin regex: %s",
            ALLOWED_ORIGIN_REGEX,
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# API Routers
# -------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(instruments_router)
app.include_router(laboratories_router)
app.include_router(test_sessions_router)
app.include_router(test_session_management_router)
app.include_router(test_session_tests_router)
app.include_router(observations_router)
app.include_router(calculation_router)
app.include_router(reports_router)
app.include_router(report_management_router)
app.include_router(users_router)
app.include_router(standards_router)
app.include_router(test_definitions_router)
app.include_router(test_applicability_rules_router)
app.include_router(mpe_rules_router)
app.include_router(environmental_conditions_router)
app.include_router(test_equipment_router)
app.include_router(chat_router)

# Public report verification - intentionally NO auth dependency (see api/verify/routes.py).
app.include_router(verify_router)


# -------------------------------------------------------------------
# TeamDesk real-time chat (Socket.IO) at /socket.io
#
# Mounted on the FastAPI app so the start command stays
#   uvicorn backend.app.main:app
# CORS for it comes from the CORSMiddleware above.
# -------------------------------------------------------------------

app.mount("/socket.io", socketio.ASGIApp(sio, socketio_path=""))


# -------------------------------------------------------------------
# Root endpoint
# -------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "NAWI Backend is running"
    }