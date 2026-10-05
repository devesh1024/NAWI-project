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
from backend.app.services import permissions as perm
from backend.app.services.session_access import (
    ensure_authorised_for_test,
    ensure_may_run,
    ensure_open,
)
from backend.app.utils.dependencies import require_capability


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
    current_user: User = Depends(require_capability(perm.SESSIONS_CREATE)),
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

    ensure_may_run(current_user, session)
    ensure_open(session)

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

    ensure_authorised_for_test(current_user, test_definition.test_code)

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