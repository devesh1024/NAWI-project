from fastapi import FastAPI

from backend.app.api.auth.routes import router as auth_router
from backend.app.api.instruments.routes import router as instruments_router
from backend.app.api.test_sessions.routes import router as test_sessions_router
from backend.app.api.test_sessions.test_routes import router as test_session_tests_router
from backend.app.api.observations.routes import router as observations_router
from backend.app.api.test_sessions.calculation_routes import router as calculation_router
from backend.app.api.reports.routes import router as reports_router


app = FastAPI(
    title="NAWI Test Report Generation API",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(instruments_router)
app.include_router(test_sessions_router)
app.include_router(test_session_tests_router)
app.include_router(observations_router)
app.include_router(calculation_router)
app.include_router(reports_router)

@app.get("/")
def root():
    return {
        "message": "NAWI Backend is running"
    }