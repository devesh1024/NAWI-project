from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_observation import TestObservation
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.test_session import TestSession
from backend.app.models.user import User
from backend.app.schemas.observation import (
    ObservationCreate,
    ObservationResponse
)
from backend.app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/api/test-sessions",
    tags=["Observations"]
)


@router.post(
    "/{session_test_id}/observations",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED
)
def create_observation(
    session_test_id: UUID,
    data: ObservationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check that the session-test exists
    session_test = db.query(TestSessionTest).filter(
        TestSessionTest.session_test_id == session_test_id
    ).first()

    if not session_test:
        raise HTTPException(
            status_code=404,
            detail="Session test not found"
        )

    # Check laboratory isolation
    session = db.query(TestSession).filter(
        TestSession.test_session_id == session_test.test_session_id,
        TestSession.laboratory_id == current_user.laboratory_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found"
        )

    observation = TestObservation(
        session_test_id=session_test_id,
        parameter_name=data.parameter_name,
        parameter_code=data.parameter_code,
        value_numeric=data.value_numeric,
        value_text=data.value_text,
        unit=data.unit,
        sequence_no=data.sequence_no,
        source=data.source,
        entered_by=current_user.user_id,
        remarks=data.remarks
    )

    db.add(observation)
    db.commit()
    db.refresh(observation)

    return observation