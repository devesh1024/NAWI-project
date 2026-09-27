from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_session import TestSession
from backend.app.models.instrument import Instrument
from backend.app.models.user import User
from backend.app.schemas.test_session_status import TestSessionStatusUpdate
from backend.app.schemas.test_session import (
    TestSessionCreate,
    TestSessionResponse
)
from backend.app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/api/test-sessions",
    tags=["Test Sessions"]
)


@router.post(
    "",
    response_model=TestSessionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_test_session(
    data: TestSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    instrument = db.query(Instrument).filter(
        Instrument.instrument_id == data.instrument_id,
        Instrument.laboratory_id == current_user.laboratory_id
    ).first()

    if not instrument:
        raise HTTPException(
            status_code=404,
            detail="Instrument not found"
        )

    session = TestSession(
        laboratory_id=current_user.laboratory_id,
        instrument_id=data.instrument_id,
        tester_id=current_user.user_id,
        standard_id=data.standard_id,
        session_number=data.session_number,
        application_number=data.application_number,
        test_type=data.test_type,
        remarks=data.remarks,
        status="DRAFT"
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get(
    "",
    response_model=list[TestSessionResponse]
)
def get_test_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(TestSession).filter(
        TestSession.laboratory_id == current_user.laboratory_id
    ).all()

    return sessions


@router.get(
    "/{test_session_id}",
    response_model=TestSessionResponse
)
def get_test_session(
    test_session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(TestSession).filter(
        TestSession.test_session_id == test_session_id,
        TestSession.laboratory_id == current_user.laboratory_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found"
        )

    return session
@router.patch("/{test_session_id}/status")
def update_test_session_status(
    test_session_id: str,
    data: TestSessionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = (
        db.query(TestSession)
        .filter(
            TestSession.test_session_id == test_session_id,
            TestSession.laboratory_id == current_user.laboratory_id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found"
        )

    allowed_statuses = {
        "DRAFT",
        "IN PROGRESS",
        "SUBMITTED",
        "UNDER REVIEW",
        "APPROVED",
        "REJECTED"
    }

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {sorted(allowed_statuses)}"
        )

    session.status = data.status
    db.commit()
    db.refresh(session)

    return {
        "message": "Test session status updated successfully",
        "test_session_id": str(session.test_session_id),
        "status": session.status
    }