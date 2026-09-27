from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.test_definition import TestDefinition
from backend.app.models.user import User
from backend.app.schemas.test_session_test import (
    TestSessionTestCreate,
    TestSessionTestResponse
)
from backend.app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/api/test-sessions",
    tags=["Test Session Tests"]
)


@router.post(
    "/{test_session_id}/tests",
    response_model=TestSessionTestResponse,
    status_code=status.HTTP_201_CREATED
)
def add_test_to_session(
    test_session_id: UUID,
    data: TestSessionTestCreate,
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

    test_definition = db.query(TestDefinition).filter(
        TestDefinition.test_definition_id == data.test_definition_id,
        TestDefinition.standard_id == session.standard_id,
        TestDefinition.active == True
    ).first()

    if not test_definition:
        raise HTTPException(
            status_code=404,
            detail="Test definition not found for this standard"
        )

    existing = db.query(TestSessionTest).filter(
        TestSessionTest.test_session_id == test_session_id,
        TestSessionTest.test_definition_id == data.test_definition_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Test already added to this session"
        )

    session_test = TestSessionTest(
        test_session_id=test_session_id,
        test_definition_id=data.test_definition_id,
        applicability_status=data.applicability_status,
        na_reason=data.na_reason,
        status="PENDING"
    )

    db.add(session_test)
    db.commit()
    db.refresh(session_test)

    return session_test