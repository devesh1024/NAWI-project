from fastapi import FastAPI

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