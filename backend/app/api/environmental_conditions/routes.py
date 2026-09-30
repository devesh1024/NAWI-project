from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.environmental_condition import EnvironmentalCondition
from backend.app.models.test_session import TestSession
from backend.app.models.user import User
from backend.app.schemas.environmental_condition import (
    EnvironmentalConditionCreate,
    EnvironmentalConditionUpdate,
    EnvironmentalConditionResponse,
)
from backend.app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/api/environmental-conditions",
    tags=["Environmental Conditions"],
)


# ============================================================
# CREATE ENVIRONMENTAL CONDITION
# ============================================================

@router.post(
    "",
    response_model=EnvironmentalConditionResponse,
)
def create_environmental_condition(
    data: EnvironmentalConditionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # --------------------------------------------------------
    # Check that the test session belongs to the user's lab
    # --------------------------------------------------------

    session = (
        db.query(TestSession)
        .filter(
            TestSession.test_session_id == data.test_session_id,
            TestSession.laboratory_id
            == current_user.laboratory_id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found",
        )

    # --------------------------------------------------------
    # Create record
    # --------------------------------------------------------

    condition = EnvironmentalCondition(
        test_session_id=data.test_session_id,
        temperature=data.temperature,
        humidity=data.humidity,
        pressure=data.pressure,
        recorded_by=current_user.user_id,
        source=data.source,
        remarks=data.remarks,
    )

    db.add(condition)
    db.commit()
    db.refresh(condition)

    return condition


# ============================================================
# GET ALL CONDITIONS FOR A TEST SESSION
# ============================================================

@router.get(
    "/session/{test_session_id}",
    response_model=list[EnvironmentalConditionResponse],
)
def get_environmental_conditions(
    test_session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # --------------------------------------------------------
    # Check session belongs to user's laboratory
    # --------------------------------------------------------

    session = (
        db.query(TestSession)
        .filter(
            TestSession.test_session_id == test_session_id,
            TestSession.laboratory_id
            == current_user.laboratory_id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found",
        )

    conditions = (
        db.query(EnvironmentalCondition)
        .filter(
            EnvironmentalCondition.test_session_id
            == test_session_id
        )
        .order_by(
            EnvironmentalCondition.recorded_at.asc()
        )
        .all()
    )

    return conditions


# ============================================================
# GET SINGLE ENVIRONMENTAL CONDITION
# ============================================================

@router.get(
    "/{environment_id}",
    response_model=EnvironmentalConditionResponse,
)
def get_environmental_condition(
    environment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = (
        db.query(EnvironmentalCondition)
        .join(
            TestSession,
            EnvironmentalCondition.test_session_id
            == TestSession.test_session_id,
        )
        .filter(
            EnvironmentalCondition.environment_id
            == environment_id,
            TestSession.laboratory_id
            == current_user.laboratory_id,
        )
        .first()
    )

    if not condition:
        raise HTTPException(
            status_code=404,
            detail="Environmental condition not found",
        )

    return condition


# ============================================================
# UPDATE ENVIRONMENTAL CONDITION
# ============================================================

@router.put(
    "/{environment_id}",
    response_model=EnvironmentalConditionResponse,
)
def update_environmental_condition(
    environment_id: UUID,
    data: EnvironmentalConditionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = (
        db.query(EnvironmentalCondition)
        .join(
            TestSession,
            EnvironmentalCondition.test_session_id
            == TestSession.test_session_id,
        )
        .filter(
            EnvironmentalCondition.environment_id
            == environment_id,
            TestSession.laboratory_id
            == current_user.laboratory_id,
        )
        .first()
    )

    if not condition:
        raise HTTPException(
            status_code=404,
            detail="Environmental condition not found",
        )

    if data.temperature is not None:
        condition.temperature = data.temperature

    if data.humidity is not None:
        condition.humidity = data.humidity

    if data.pressure is not None:
        condition.pressure = data.pressure

    if data.source is not None:
        condition.source = data.source

    if data.remarks is not None:
        condition.remarks = data.remarks

    db.commit()
    db.refresh(condition)

    return condition


# ============================================================
# DELETE ENVIRONMENTAL CONDITION
# ============================================================

@router.delete("/{environment_id}")
def delete_environmental_condition(
    environment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = (
        db.query(EnvironmentalCondition)
        .join(
            TestSession,
            EnvironmentalCondition.test_session_id
            == TestSession.test_session_id,
        )
        .filter(
            EnvironmentalCondition.environment_id
            == environment_id,
            TestSession.laboratory_id
            == current_user.laboratory_id,
        )
        .first()
    )

    if not condition:
        raise HTTPException(
            status_code=404,
            detail="Environmental condition not found",
        )

    db.delete(condition)
    db.commit()

    return {
        "message": "Environmental condition deleted successfully"
    }