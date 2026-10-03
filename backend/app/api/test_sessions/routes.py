from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
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

    if (instrument.status or "").upper() == "INACTIVE":
        raise HTTPException(
            status_code=409,
            detail="This instrument is INACTIVE; reactivate it before "
                   "creating new test sessions."
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
    test_session_id: UUID,
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

    current_status = session.status
    new_status = data.status
    role = current_user.role

    # A tester can only update sessions assigned to them.
    if role == "TESTER" and str(session.tester_id) != str(current_user.user_id):
        raise HTTPException(
            status_code=403,
            detail="Only the assigned tester can change this test session status"
        )

    # Define role-based workflow transitions.
    if role == "TESTER":
        allowed_transitions = {
            "DRAFT": {"IN PROGRESS"},
            "IN PROGRESS": {"SUBMITTED"},
        }

    elif role == "REVIEWER":
        allowed_transitions = {
            "SUBMITTED": {"UNDER REVIEW"},
        }

    elif role == "APPROVER":
        allowed_transitions = {
            "UNDER REVIEW": {"APPROVED", "REJECTED"},
        }

    elif role == "LAB_ADMIN":
        # Lab Admin can manage the complete workflow.
        allowed_transitions = {
            "DRAFT": allowed_statuses - {"DRAFT"},
            "IN PROGRESS": allowed_statuses - {"IN PROGRESS"},
            "SUBMITTED": allowed_statuses - {"SUBMITTED"},
            "UNDER REVIEW": allowed_statuses - {"UNDER REVIEW"},
            "APPROVED": allowed_statuses - {"APPROVED"},
            "REJECTED": allowed_statuses - {"REJECTED"},
        }

    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to change test session status"
        )

    if new_status not in allowed_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Role '{role}' cannot change session status "
                f"from '{current_status}' to '{new_status}'"
            )
        )

    session.status = new_status

    # Calculate overall result when the tester submits the session.
    if new_status == "SUBMITTED":

        session_tests = db.query(TestSessionTest).filter(
            TestSessionTest.test_session_id == session.test_session_id
        ).all()

        applicable_tests = [
            test
            for test in session_tests
            if test.applicability_status != "NOT_APPLICABLE"
        ]

        if not applicable_tests:
            session.overall_result = None

        elif any(
            test.result == "FAIL"
            for test in applicable_tests
        ):
            session.overall_result = "FAIL"

        elif all(
            test.result == "PASS"
            for test in applicable_tests
        ):
            session.overall_result = "PASS"

        else:
            session.overall_result = None

    db.commit()
    db.refresh(session)

    return {
        "message": "Test session status updated successfully",
        "test_session_id": str(session.test_session_id),
        "status": session.status,
        "overall_result": session.overall_result
    }