from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.test_session import TestSession
from backend.app.models.test_calculation import TestCalculation
from backend.app.models.test_result import TestResult
from backend.app.models.user import User
from backend.app.schemas.calculation import (
    CalculationResultCreate,
    CalculationResponse,
    ResultResponse
)
from backend.app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/api/test-sessions",
    tags=["Calculations"]
)


@router.post(
    "/{session_test_id}/calculation-result",
    response_model=dict,
    status_code=status.HTTP_201_CREATED
)
def save_calculation_result(
    session_test_id: UUID,
    data: CalculationResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find session-test
    session_test = db.query(TestSessionTest).filter(
        TestSessionTest.session_test_id == session_test_id
    ).first()

    if not session_test:
        raise HTTPException(
            status_code=404,
            detail="Session test not found"
        )

    # Verify laboratory isolation
    session = db.query(TestSession).filter(
        TestSession.test_session_id == session_test.test_session_id,
        TestSession.laboratory_id == current_user.laboratory_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found"
        )

    # Store calculation
    calculation = TestCalculation(
        session_test_id=session_test_id,
        calculation_type=data.calculation_type,
        input_values=data.input_values,
        formula=data.formula,
        calculated_value=data.calculated_value,
        unit=data.unit,
        calculation_version=data.calculation_version
    )

    db.add(calculation)

    # Store result
    result = TestResult(
        session_test_id=session_test_id,
        measured_value=data.measured_value,
        mpe_value=data.mpe_value,
        error_value=data.error_value,
        corrected_error=data.corrected_error,
        acceptance_condition=data.acceptance_condition,
        pass_fail=data.pass_fail,
        result_summary=data.result_summary,
        calculation_version=data.calculation_version
    )

    db.add(result)

    # Update session-test result
    session_test.result = data.pass_fail
    session_test.status = "COMPLETED"

    db.commit()

    db.refresh(calculation)
    db.refresh(result)

    return {
        "message": "Calculation and result saved successfully",
        "calculation": {
            "calculation_id": str(calculation.calculation_id),
            "session_test_id": str(calculation.session_test_id),
            "calculation_type": calculation.calculation_type,
            "calculated_value": calculation.calculated_value,
            "unit": calculation.unit,
            "calculation_version": calculation.calculation_version
        },
        "result": {
            "result_id": str(result.result_id),
            "session_test_id": str(result.session_test_id),
            "measured_value": result.measured_value,
            "mpe_value": result.mpe_value,
            "error_value": result.error_value,
            "corrected_error": result.corrected_error,
            "acceptance_condition": result.acceptance_condition,
            "pass_fail": result.pass_fail,
            "result_summary": result.result_summary,
            "calculation_version": result.calculation_version
        }
    }