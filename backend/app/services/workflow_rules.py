# backend/app/services/workflow_rules.py
"""
The test-session workflow and who may move it, as pure functions.

    DRAFT -> IN PROGRESS -> SUBMITTED -> UNDER REVIEW -> (report) PENDING_APPROVAL -> APPROVED
                 ^   ^         |  ^            |                       |
                 |   +- recall-+  +- (no)      +-> REJECTED <----------+
                 +------------ rework ---------------+

  tester                      reviewer                    signatory
  ----------------------      ------------------------    ---------------------
  start work, submit,         start review,               approve / reject the
  recall, rework              return for correction,      report (creates the
                              forward for approval        approval signature)

Every review / sign-off step also enforces the maker-checker rule from
services/permissions.py. APPROVED is never set through the status endpoint:
only the approve-report step creates the signature and the permanent record.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.services import permissions as perm

DRAFT = "DRAFT"
IN_PROGRESS = "IN PROGRESS"
SUBMITTED = "SUBMITTED"
UNDER_REVIEW = "UNDER REVIEW"
APPROVED = "APPROVED"
REJECTED = "REJECTED"

ALL_STATUSES = (DRAFT, IN_PROGRESS, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED)

# Backward-compatible spellings people send ("in_progress", "Under Review").
def normalize(value: str | None) -> str:
    return (value or "").strip().upper().replace("_", " ").replace("-", " ")


@dataclass(frozen=True)
class Transition:
    key: str                 # stable id used by the API and the UI
    label: str               # button text
    source: str
    target: str
    capability: str
    owner_only: bool         # must be the session's own tester
    independent: bool        # maker-checker applies
    needs_reason: bool = False


# Moves made through PATCH /api/test-sessions/{id}/status
TRANSITIONS: tuple[Transition, ...] = (
    Transition("start_work", "Start testing", DRAFT, IN_PROGRESS,
               perm.SESSIONS_SUBMIT, True, False),
    Transition("submit", "Submit for review", IN_PROGRESS, SUBMITTED,
               perm.SESSIONS_SUBMIT, True, False),
    Transition("recall", "Recall to edit", SUBMITTED, IN_PROGRESS,
               perm.SESSIONS_SUBMIT, True, False),
    Transition("start_review", "Start review", SUBMITTED, UNDER_REVIEW,
               perm.SESSIONS_REVIEW, False, True),
    Transition("return_for_correction", "Return for correction", UNDER_REVIEW, REJECTED,
               perm.SESSIONS_REVIEW, False, True, needs_reason=True),
    Transition("rework", "Rework and resubmit", REJECTED, IN_PROGRESS,
               perm.SESSIONS_SUBMIT, True, False),
)

BY_PAIR = {(t.source, t.target): t for t in TRANSITIONS}


def find(source: str, target: str) -> Transition | None:
    return BY_PAIR.get((source, target))


def check(transition: Transition, user, session, participants) -> str | None:
    """Why `user` may not make this move right now, or None if they may."""
    if not perm.user_can(user, transition.capability):
        return (
            f"Your role ({perm.label_for(user.role)}) cannot "
            f"'{transition.label.lower()}'."
        )
    if transition.owner_only and not perm.is_owner(user, session):
        return "Only the tester who owns this session can do this."
    if transition.independent:
        return perm.independence_problem(user, participants)
    return None


def available_actions(user, session, participants, report_status: str | None, has_report: bool):
    """
    Everything the UI may offer this user on this session, with a reason when
    an action exists in the workflow but is blocked for them. The frontend
    renders exactly this list, so what is shown always matches what the
    backend will accept.
    """
    status = session.status
    out = []

    for t in TRANSITIONS:
        if t.source != status:
            continue
        reason = check(t, user, session, participants)
        # Hide moves that belong to other roles entirely; show a blocked
        # one only when the role could do it but is barred by independence.
        if reason and not perm.user_can(user, t.capability):
            continue
        if reason and t.owner_only:
            continue
        out.append({
            "key": t.key, "label": t.label, "enabled": reason is None,
            "reason": reason, "needs_reason": t.needs_reason, "to": t.target,
        })

    # Report-level steps (they live on the report, not the session status).
    if status == UNDER_REVIEW and perm.user_can(user, perm.SESSIONS_REVIEW):
        reason = perm.independence_problem(user, participants)
        if not has_report:
            reason = reason or "Generate the report first, then forward it for approval."
        elif report_status == "PENDING_APPROVAL":
            reason = reason or "Already forwarded for approval."
        out.append({
            "key": "forward_for_approval", "label": "Forward for approval",
            "enabled": reason is None, "reason": reason, "needs_reason": False,
            "to": None,
        })

    if status == UNDER_REVIEW and perm.user_can(user, perm.SESSIONS_APPROVE):
        reason = perm.independence_problem(user, participants)
        if report_status != "PENDING_APPROVAL":
            reason = reason or "Waiting for the reviewer to forward the report for approval."
        for key, label, needs in (("approve", "Approve and sign", False), ("reject", "Reject report", True)):
            out.append({
                "key": key, "label": label, "enabled": reason is None,
                "reason": reason, "needs_reason": needs, "to": None,
            })

    return out
