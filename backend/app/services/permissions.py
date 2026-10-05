# backend/app/services/permissions.py
"""
Roles and permissions: the single source of truth.

The roles follow how an ISO/IEC 17025 testing laboratory (for example a
government Regional Reference Standards Laboratory) is actually staffed. The
backend enforces them on every endpoint, and the frontend reads the same
catalogue (GET /api/users/roles and the `capabilities` list on GET
/api/users/me) so the screens a person sees match what they are allowed to do.

Core principle: MAKER-CHECKER. Whoever tested a session (the tester, and anyone
who entered observations on it) can never review or sign off the same session.
That is the impartiality requirement of ISO/IEC 17025, and the reason roles
exist in this application.

Role codes are stored in users.role. The first four are the original codes and
are unchanged, so existing accounts keep working.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

# --------------------------------------------------------------------------
# Capabilities (what a role may do). Viewing lab data is open to every signed-in
# member of the laboratory; these are the things that CHANGE data.
# --------------------------------------------------------------------------
USERS_VIEW = "users.view"
USERS_MANAGE = "users.manage"            # add users, change role / status
USERS_AUTHORIZE = "users.authorize"      # set which tests a person is authorised for
LAB_MANAGE = "lab.manage"                # laboratory profile
INSTRUMENTS_REGISTER = "instruments.register"   # receive / record / edit instruments
INSTRUMENTS_DELETE = "instruments.delete"
EQUIPMENT_MANAGE = "equipment.manage"    # reference weights, calibration records
EQUIPMENT_DELETE = "equipment.delete"
METHODS_MANAGE = "methods.manage"        # standards, test methods, MPE and applicability rules
SESSIONS_CREATE = "sessions.create"      # plan a session and its tests
SESSIONS_ENTER_DATA = "sessions.enter_data"   # observations, environment, equipment usage
SESSIONS_CALCULATE = "sessions.calculate"
SESSIONS_SUBMIT = "sessions.submit"      # hand work over for review
SESSIONS_REVIEW = "sessions.review"      # check a submitted session / report
SESSIONS_APPROVE = "sessions.approve"    # sign: approve or reject the report
REPORTS_GENERATE = "reports.generate"
REPORTS_DELETE = "reports.delete"
AUDIT_VIEW = "audit.view"

ALL_CAPABILITIES = frozenset(
    {
        USERS_VIEW, USERS_MANAGE, USERS_AUTHORIZE, LAB_MANAGE,
        INSTRUMENTS_REGISTER, INSTRUMENTS_DELETE,
        EQUIPMENT_MANAGE, EQUIPMENT_DELETE, METHODS_MANAGE,
        SESSIONS_CREATE, SESSIONS_ENTER_DATA, SESSIONS_CALCULATE, SESSIONS_SUBMIT,
        SESSIONS_REVIEW, SESSIONS_APPROVE,
        REPORTS_GENERATE, REPORTS_DELETE, AUDIT_VIEW,
    }
)


@dataclass(frozen=True)
class RoleDef:
    code: str
    label: str            # the designation people recognise
    level: int            # 1 = top of the laboratory ... 5 = bench; 0 = outside the lab line
    group: str            # for grouping in pickers
    summary: str          # one-line description of the real job
    capabilities: frozenset[str]
    assignable: bool = True   # can a Lab Head give this role to a new user?


ROLES: dict[str, RoleDef] = {r.code: r for r in [
    RoleDef(
        "LAB_ADMIN", "Lab Head / In-charge", 1, "Management",
        "Answerable for the whole laboratory. Manages staff, signs off final "
        "reports and forwards them to the Director. Does not test.",
        frozenset({
            USERS_VIEW, USERS_MANAGE, USERS_AUTHORIZE, LAB_MANAGE,
            INSTRUMENTS_REGISTER, INSTRUMENTS_DELETE,
            EQUIPMENT_MANAGE, EQUIPMENT_DELETE, METHODS_MANAGE,
            SESSIONS_REVIEW, SESSIONS_APPROVE, REPORTS_GENERATE, REPORTS_DELETE,
            AUDIT_VIEW,
        }),
        assignable=False,   # created once, when the laboratory is registered
    ),
    RoleDef(
        "TECHNICAL_MANAGER", "Technical Manager", 2, "Management",
        "Owns test methods, equipment and the competence of testers. May review "
        "and sign reports.",
        frozenset({
            USERS_VIEW, USERS_AUTHORIZE, INSTRUMENTS_REGISTER,
            EQUIPMENT_MANAGE, METHODS_MANAGE,
            SESSIONS_REVIEW, SESSIONS_APPROVE, REPORTS_GENERATE,
        }),
    ),
    RoleDef(
        "QUALITY_MANAGER", "Quality Manager", 2, "Management",
        "Looks after the quality system, audits and the calibration schedule. "
        "Stays independent of testing, so cannot test, review or sign.",
        frozenset({USERS_VIEW, EQUIPMENT_MANAGE, AUDIT_VIEW}),
    ),
    RoleDef(
        "REVIEWER", "Reviewer", 3, "Technical",
        "Checks a tester's completed work and report. Returns it for correction "
        "or forwards it for signature. Never reviews their own tests.",
        frozenset({SESSIONS_REVIEW, REPORTS_GENERATE}),
    ),
    RoleDef(
        "APPROVER", "Authorised Signatory", 3, "Technical",
        "Signs the reviewed report: approves or rejects it. Never signs their "
        "own tests.",
        frozenset({SESSIONS_APPROVE}),
    ),
    RoleDef(
        "TESTER", "Senior Tester / Evaluator", 4, "Technical",
        "Plans and runs the tests, analyses the results and drafts the report.",
        frozenset({
            INSTRUMENTS_REGISTER, SESSIONS_CREATE, SESSIONS_ENTER_DATA,
            SESSIONS_CALCULATE, SESSIONS_SUBMIT, REPORTS_GENERATE,
        }),
    ),
    RoleDef(
        "ASSISTANT", "Technician / Lab Assistant", 5, "Technical",
        "Sets up the instrument, places weights, takes readings and enters data "
        "under a tester's supervision. Cannot calculate, submit or approve.",
        frozenset({SESSIONS_ENTER_DATA}),
    ),
    RoleDef(
        "RECORDS_OFFICER", "Receiving / Records Officer", 0, "Support",
        "Receives instruments from applicants and keeps their records.",
        frozenset({INSTRUMENTS_REGISTER, INSTRUMENTS_DELETE}),
    ),
    RoleDef(
        "STANDARDS_CUSTODIAN", "Standards Custodian", 0, "Support",
        "Keeps the reference weights and test equipment, and their calibration.",
        frozenset({EQUIPMENT_MANAGE, EQUIPMENT_DELETE}),
    ),
    RoleDef(
        "AUDITOR", "Auditor (read-only)", 0, "External",
        "An assessor (for example from NABL) or viewer. Can read everything, "
        "including the audit trail, but cannot change anything.",
        frozenset({USERS_VIEW, AUDIT_VIEW}),
    ),
]}

ASSIGNABLE_ROLES = tuple(code for code, r in ROLES.items() if r.assignable)

# Sessions in these states are the tester's working copy (data may change).
OPEN_STATES = ("DRAFT", "IN PROGRESS")


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------
def role_def(role: str | None) -> RoleDef | None:
    return ROLES.get((role or "").upper())


def label_for(role: str | None) -> str:
    r = role_def(role)
    return r.label if r else (role or "").replace("_", " ").title()


def capabilities_for(role: str | None) -> frozenset[str]:
    r = role_def(role)
    return r.capabilities if r else frozenset()


def has(role: str | None, capability: str) -> bool:
    return capability in capabilities_for(role)


def user_can(user: Any, capability: str) -> bool:
    return has(getattr(user, "role", None), capability)


def catalogue() -> list[dict]:
    """What the frontend needs to render pickers, badges and explanations."""
    return [
        {
            "code": r.code,
            "label": r.label,
            "level": r.level,
            "group": r.group,
            "summary": r.summary,
            "assignable": r.assignable,
            "capabilities": sorted(r.capabilities),
        }
        for r in ROLES.values()
    ]


# --------------------------------------------------------------------------
# Session ownership, independence and visibility
# --------------------------------------------------------------------------
def same_user(a: Any, b: Any) -> bool:
    return a is not None and b is not None and str(a) == str(b)


def is_owner(user: Any, session: Any) -> bool:
    return same_user(getattr(user, "user_id", None), getattr(session, "tester_id", None))


def may_enter_data(user: Any, session: Any) -> bool:
    """
    Testers work on their own sessions. Assistants enter data on any open
    session in the laboratory, under supervision.
    """
    if not user_can(user, SESSIONS_ENTER_DATA):
        return False
    if user_can(user, SESSIONS_CREATE):
        return is_owner(user, session)
    return True


def may_run_session(user: Any, session: Any) -> bool:
    """Plan tests, calculate, submit, rework: the session's own tester only."""
    return user_can(user, SESSIONS_CREATE) and is_owner(user, session)


def visible_status_filter(role: str | None) -> tuple[str, ...] | None:
    """
    Statuses a role works with. None = every status. Used for the 'my work'
    lists; the Lab Head, managers, records, custodian and auditors see all.
    """
    role = (role or "").upper()
    if role == "ASSISTANT":
        return OPEN_STATES
    if role == "REVIEWER":
        return ("SUBMITTED", "UNDER REVIEW", "APPROVED", "REJECTED")
    if role == "APPROVER":
        return ("UNDER REVIEW", "APPROVED", "REJECTED")
    return None


def session_visible_to(user: Any, session: Any) -> bool:
    role = (getattr(user, "role", "") or "").upper()
    if role == "TESTER":
        return is_owner(user, session)
    allowed = visible_status_filter(role)
    if allowed is None:
        return True
    if role == "REVIEWER" and same_user(getattr(session, "reviewer_id", None), user.user_id):
        return True
    return getattr(session, "status", None) in allowed


def independence_problem(user: Any, participants: Iterable[Any]) -> str | None:
    """
    Maker-checker. `participants` are the ids of everyone who tested the session
    (its tester plus anyone who entered observations). Returns the reason a
    review / sign-off must be refused, or None if the person is independent.
    """
    me = getattr(user, "user_id", None)
    if any(same_user(me, p) for p in participants):
        return (
            "You took part in testing this session, so you cannot review or "
            "sign it. A different person must check the work (ISO/IEC 17025 "
            "impartiality: the maker never checks their own work)."
        )
    return None
