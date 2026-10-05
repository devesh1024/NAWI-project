from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.instrument import Instrument
from backend.app.models.test_calculation import TestCalculation
from backend.app.models.test_definition import TestDefinition
from backend.app.models.test_result import TestResult
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.user import User
from backend.app.schemas.calculation import (
    CalculationResultCreate,
    CalculationResponse,
    ResultResponse,
)
from backend.app.services.calculation_engine.context import EvaluationContext
from backend.app.services.calculation_engine.engine import CalculationRequest
from backend.app.services.calculation_engine.instrument_context_adapter import (
    instrument_to_context,
)
from backend.app.services.calculation_engine.registry import (
    create_r76_calculation_engine,
)
from backend.app.services import permissions as perm
from backend.app.services.session_access import (
    ensure_authorised_for_test,
    ensure_may_run,
    ensure_open,
)
from backend.app.utils.dependencies import require_capability


router = APIRouter(
    prefix="/api/test-sessions",
    tags=["Calculations"],
)


def _json_safe(value: Any) -> Any:
    """
    Convert calculation inputs/details into values that can safely
    be stored in a PostgreSQL JSON column.
    """
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    return value

def _to_decimal(value: Any) -> Any:
    """JSON has only int/float; the engine requires Decimal."""
    if isinstance(value, bool) or value is None or isinstance(value, (str, Decimal)):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))          # str() keeps the digits the tester typed
    if isinstance(value, dict):
        return {str(k): _to_decimal(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_decimal(v) for v in value]
    return value

def _result_to_float(value: Any) -> float | None:
    """
    Convert Decimal/numeric result values to a database-compatible float.
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    return float(value)


@router.post(
    "/{session_test_id}/calculation-result",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
def calculate_and_save_result(
    session_test_id: UUID,
    data: CalculationResultCreate,
    current_user: User = Depends(require_capability(perm.SESSIONS_CALCULATE)),
    db: Session = Depends(get_db),
):
    """
    Execute an R76 calculation for a session test and persist the result.

    The client supplies only raw calculation inputs.

    The backend determines:
        - test code
        - instrument configuration
        - applicable R76 rules
        - MPE
        - error
        - acceptance
        - PASS/FAIL/N/A
    """

    # ---------------------------------------------------------
    # 1. Find the session-test
    # ---------------------------------------------------------
    session_test = (
        db.query(TestSessionTest)
        .filter(
            TestSessionTest.session_test_id == session_test_id
        )
        .first()
    )

    if not session_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session test not found",
        )

    # ---------------------------------------------------------
    # 2. Find the parent test session
    # ---------------------------------------------------------
    session = (
        db.query(TestSession)
        .filter(
            TestSession.test_session_id == session_test.test_session_id,
            TestSession.laboratory_id == current_user.laboratory_id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test session not found",
        )

    # ---------------------------------------------------------
    # 3. Find the instrument used by the session
    # ---------------------------------------------------------
    instrument = (
        db.query(Instrument)
        .filter(
            Instrument.instrument_id == session.instrument_id,
            Instrument.laboratory_id == current_user.laboratory_id,
        )
        .first()
    )

    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrument not found",
        )

    # ---------------------------------------------------------
    # 4. Find the test definition
    # ---------------------------------------------------------
    test_definition = (
        db.query(TestDefinition)
        .filter(
            TestDefinition.test_definition_id
            == session_test.test_definition_id,
            TestDefinition.active.is_(True),
        )
        .first()
    )

    if not test_definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active test definition not found",
        )

    ensure_may_run(current_user, session)
    ensure_open(session)

    test_code = test_definition.test_code

    ensure_authorised_for_test(current_user, test_code)

    # ---------------------------------------------------------
    # 5. Convert database instrument → calculation context
    # ---------------------------------------------------------
    try:
        instrument_context = instrument_to_context(instrument)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid instrument configuration: {exc}",
        ) from exc

    # ---------------------------------------------------------
    # 6. Create evaluation context
    # ---------------------------------------------------------
    evaluation = EvaluationContext(
        mode="TYPE_EVALUATION",
        mpe_basis="INITIAL_VERIFICATION",
    )

    # ---------------------------------------------------------
    # 7. Create the R76 calculation engine
    # ---------------------------------------------------------
    try:
        engine = create_r76_calculation_engine(
            instrument=instrument_context,
            evaluation=evaluation,
        )
    except (ValueError, TypeError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to initialize R76 calculation engine: {exc}",
        ) from exc

    # ---------------------------------------------------------
    # 8. Execute the calculation
    # ---------------------------------------------------------
    try:
        calculation_request = CalculationRequest(
            test_code=test_code,
            inputs=_to_decimal(data.inputs),
        )

        result = engine.calculate(
            request=calculation_request,
        )

    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Calculation input validation failed: {exc}",
        ) from exc

    # ---------------------------------------------------------
    # 9. Prepare database-safe values
    # ---------------------------------------------------------
    input_values = _json_safe(data.inputs)
    result_details = _json_safe(result.details)

    measured_value = _result_to_float(result.measured_value)
    mpe_value = _result_to_float(result.limit)
    error_value = _result_to_float(result.error)

    # The calculation engine currently exposes a single error field.
    # Do not invent a separate corrected-error value unless the
    # calculation result explicitly provides one.
    corrected_error = None

    calculation_version = evaluation.calculation_version

    # ---------------------------------------------------------
    # 10. Store calculation
    # ---------------------------------------------------------
    calculation = TestCalculation(
        session_test_id=session_test_id,
        calculation_type=(
            test_definition.calculation_type
            or test_code
        ),
        input_values=input_values,
        formula=None,
        calculated_value=measured_value,
        unit=result.unit,
        calculation_version=calculation_version,
    )

    db.add(calculation)

    # ---------------------------------------------------------
    # 11. Store test result
    # ---------------------------------------------------------
    result_record = TestResult(
        session_test_id=session_test_id,
        measured_value=measured_value,
        mpe_value=mpe_value,
        error_value=error_value,
        corrected_error=corrected_error,
        acceptance_condition=result.message,
        pass_fail=result.status,
        result_summary=result.message,
        calculation_version=calculation_version,
    )

    db.add(result_record)

    # ---------------------------------------------------------
    # 12. Update session-test status
    # ---------------------------------------------------------
    session_test.result = result.status
    session_test.status = "COMPLETED"

    # ---------------------------------------------------------
    # 13. Commit everything atomically
    # ---------------------------------------------------------
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(calculation)
    db.refresh(result_record)

    # ---------------------------------------------------------
    # 14. Return calculation + result
    # ---------------------------------------------------------
    return {
        "message": "Calculation executed and result saved successfully",
        "test": {
            "test_code": test_code,
            "test_name": test_definition.test_name,
        },
        "calculation": {
            "calculation_id": str(calculation.calculation_id),
            "session_test_id": str(calculation.session_test_id),
            "calculation_type": calculation.calculation_type,
            "calculated_value": calculation.calculated_value,
            "unit": calculation.unit,
            "calculation_version": calculation.calculation_version,
        },
        "result": {
            "result_id": str(result_record.result_id),
            "session_test_id": str(result_record.session_test_id),
            "status": result.status,
            "measured_value": result_record.measured_value,
            "mpe_value": result_record.mpe_value,
            "error_value": result_record.error_value,
            "corrected_error": result_record.corrected_error,
            "acceptance_condition": result_record.acceptance_condition,
            "pass_fail": result_record.pass_fail,
            "result_summary": result_record.result_summary,
            "calculation_version": result_record.calculation_version,
            "details": result_details,
        },
    }