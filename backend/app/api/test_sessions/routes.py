from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from backend.app.models.audit_log import AuditLog
from backend.app.models.report import Report
from backend.app.services import permissions as perm
from backend.app.services import workflow_rules as wf
from backend.app.services.audit_service import create_audit_log
from backend.app.services.session_access import apply_visibility, session_participants
from backend.app.utils.dependencies import get_current_user, require_capability


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
    current_user: User = Depends(require_capability(perm.SESSIONS_CREATE)),
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


def _person_name(user):
    if not user:
        return None
    return " ".join(p for p in (user.first_name, user.last_name) if p) or user.email


def _attach_names(db, current_user, sessions):
    """Put the tester's and reviewer's names on the sessions being returned."""
    people = {
        u.user_id: u
        for u in db.query(User).filter(User.laboratory_id == current_user.laboratory_id).all()
    }
    for s in sessions:
        s.tester_name = _person_name(people.get(s.tester_id))
        s.reviewer_name = _person_name(people.get(s.reviewer_id))


@router.get(
    "",
    response_model=list[TestSessionResponse]
)
def get_test_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(TestSession).filter(
        TestSession.laboratory_id == current_user.laboratory_id
    )

    # Each role sees the sessions it works with (a tester their own, a
    # reviewer the ones awaiting review, ...). Managers and auditors see all.
    sessions = apply_visibility(query, current_user).all()
    _attach_names(db, current_user, sessions)
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

    if not session or not perm.session_visible_to(current_user, session):
        raise HTTPException(
            status_code=404,
            detail="Test session not found"
        )

    _attach_names(db, current_user, [session])
    return session


@router.patch("/{test_session_id}/status")
def update_test_session_status(
    test_session_id: UUID,
    data: TestSessionStatusUpdate,
    request: Request,
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

    new_status = wf.normalize(data.status)

    if new_status not in wf.ALL_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {sorted(wf.ALL_STATUSES)}"
        )

    current_status = session.status

    if new_status == wf.APPROVED:
        raise HTTPException(
            status_code=409,
            detail=(
                "A session is approved by signing its report "
                "(PATCH .../approve-report), not by changing its status."
            )
        )

    transition = wf.find(current_status, new_status)

    if transition is None:
        raise HTTPException(
            status_code=409,
            detail=f"A session cannot move from '{current_status}' to '{new_status}'."
        )

    # Maker-checker: only moves that check someone's work need the list of
    # people who took part in testing.
    participants = (
        session_participants(db, session) if transition.independent else ()
    )

    problem = wf.check(transition, current_user, session, participants)

    if problem:
        raise HTTPException(status_code=403, detail=problem)

    reason = (data.reason or "").strip() or None

    if transition.needs_reason and not reason:
        raise HTTPException(
            status_code=422,
            detail="Please say what needs to be corrected."
        )

    session.status = new_status

    if new_status == wf.UNDER_REVIEW:
        session.reviewer_id = current_user.user_id

    # Calculate overall result when the tester submits the session.
    if new_status == wf.SUBMITTED:

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

    create_audit_log(
        db=db,
        current_user=current_user,
        entity_type="TEST_SESSION",
        entity_id=session.test_session_id,
        action=transition.key.upper(),
        old_value={"status": current_status},
        new_value={"status": new_status},
        remarks=reason,
        request=request,
    )

    db.commit()
    db.refresh(session)

    return {
        "message": "Test session status updated successfully",
        "test_session_id": str(session.test_session_id),
        "status": session.status,
        "overall_result": session.overall_result
    }


@router.get("/{test_session_id}/workflow")
def get_session_workflow(
    test_session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    What this user can do with this session right now (and why not, when an
    action is blocked), plus the session's history. The frontend draws its
    action buttons from `actions`, so the screen always matches the rules.
    """
    session = (
        db.query(TestSession)
        .filter(
            TestSession.test_session_id == test_session_id,
            TestSession.laboratory_id == current_user.laboratory_id
        )
        .first()
    )

    if not session or not perm.session_visible_to(current_user, session):
        raise HTTPException(status_code=404, detail="Test session not found")

    participants = session_participants(db, session)

    reports = (
        db.query(Report)
        .filter(Report.test_session_id == session.test_session_id)
        .order_by(Report.generated_at.desc())
        .all()
    )
    latest = reports[0] if reports else None

    actions = wf.available_actions(
        current_user,
        session,
        participants,
        latest.report_status if latest else None,
        latest is not None,
    )

    entity_ids = [session.test_session_id] + [r.report_id for r in reports]

    logs = (
        db.query(AuditLog, User)
        .outerjoin(User, User.user_id == AuditLog.user_id)
        .filter(
            AuditLog.laboratory_id == current_user.laboratory_id,
            AuditLog.entity_id.in_(entity_ids),
            AuditLog.entity_type.in_(["TEST_SESSION", "REPORT"]),
            AuditLog.action.notin_(["DOWNLOAD_REPORT"]),
        )
        .order_by(AuditLog.timestamp.asc())
        .all()
    )

    history = [
        {
            "action": log.action,
            "entity_type": log.entity_type,
            "by": (
                " ".join(p for p in (u.first_name, u.last_name) if p)
                if u else None
            ),
            "by_role": perm.label_for(u.role) if u else None,
            "at": log.timestamp,
            "from": (log.old_value or {}).get("status")
            or (log.old_value or {}).get("report_status"),
            "to": (log.new_value or {}).get("status")
            or (log.new_value or {}).get("report_status"),
            "remarks": log.remarks,
        }
        for log, u in logs
    ]

    return {
        "status": session.status,
        "report_status": latest.report_status if latest else None,
        "is_owner": perm.is_owner(current_user, session),
        "took_part": str(current_user.user_id) in participants,
        "can_enter_data": (
            perm.may_enter_data(current_user, session)
            and session.status in perm.OPEN_STATES
        ),
        "can_plan_and_calculate": (
            perm.may_run_session(current_user, session)
            and session.status in perm.OPEN_STATES
        ),
        "can_generate_report": (
            perm.user_can(current_user, perm.REPORTS_GENERATE)
            and session.status != wf.APPROVED
            and (
                perm.is_owner(current_user, session)
                if perm.user_can(current_user, perm.SESSIONS_CREATE)
                else session.status not in perm.OPEN_STATES
            )
        ),
        "report_available": latest is not None,
        "actions": actions,
        "history": history,
    }
