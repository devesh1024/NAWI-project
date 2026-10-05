# backend/app/services/session_access.py
"""Database helpers behind the role rules: who took part in a session, and
which sessions a user is allowed to see."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.models.test_observation import TestObservation
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.user import User
from backend.app.services import permissions as perm


def session_participants(db: Session, session: TestSession) -> set[str]:
    """
    Ids of everyone who tested this session: its tester plus anyone who entered
    an observation on it. These people can never review or sign it.
    """
    ids = {str(session.tester_id)} if session.tester_id else set()

    rows = (
        db.query(TestObservation.entered_by)
        .join(
            TestSessionTest,
            TestSessionTest.session_test_id == TestObservation.session_test_id,
        )
        .filter(TestSessionTest.test_session_id == session.test_session_id)
        .distinct()
        .all()
    )
    ids.update(str(r[0]) for r in rows if r[0])
    return ids


def apply_visibility(query, user: User):
    """Restrict a TestSession query to what this user's role works with."""
    role = (user.role or "").upper()

    if role == "TESTER":
        return query.filter(TestSession.tester_id == user.user_id)

    statuses = perm.visible_status_filter(role)
    if statuses is None:
        return query

    if role == "REVIEWER":
        return query.filter(
            or_(
                TestSession.status.in_(statuses),
                TestSession.reviewer_id == user.user_id,
            )
        )

    return query.filter(TestSession.status.in_(statuses))


# ---------------------------------------------------------------------------
# Guards used by the data-entry endpoints
# ---------------------------------------------------------------------------
from fastapi import HTTPException  # noqa: E402


def ensure_open(session: TestSession) -> None:
    """Data can only change while the session is the tester's working copy."""
    if session.status not in perm.OPEN_STATES:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This session is {session.status} and is locked. Data can only "
                f"change while it is DRAFT or IN PROGRESS."
            ),
        )


def ensure_may_enter_data(user: User, session: TestSession) -> None:
    if not perm.may_enter_data(user, session):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only the session's tester, or a lab assistant working under "
                "supervision, can enter data on it."
                if perm.user_can(user, perm.SESSIONS_ENTER_DATA)
                else f"Your role ({perm.label_for(user.role)}) does not enter test data."
            ),
        )


def ensure_may_run(user: User, session: TestSession) -> None:
    if not perm.may_run_session(user, session):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only the tester who owns this session can plan its tests and "
                "run calculations."
            ),
        )


def ensure_authorised_for_test(user: User, test_code: str | None) -> None:
    """
    ISO 17025 competence: if the Technical Manager restricted this person to a
    list of tests (users.authorization_scope = {"test_codes": [...]}), they may
    only plan and calculate those. No list = authorised for all.
    """
    scope = user.authorization_scope or {}
    codes = scope.get("test_codes") if isinstance(scope, dict) else None
    if codes and test_code and test_code not in codes:
        raise HTTPException(
            status_code=403,
            detail=(
                f"You are not authorised for test '{test_code}'. Ask the "
                f"Technical Manager to add it to your authorisation."
            ),
        )
