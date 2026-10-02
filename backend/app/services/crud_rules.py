# backend/app/services/crud_rules.py
#
# The rules behind the update/delete endpoints for instruments, test sessions,
# reports and equipment. Pure functions (no database, no web framework) so they
# can be unit tested; the route handlers do the queries and call these.

from __future__ import annotations

from typing import Any, Iterable, Mapping

ADMIN_ROLES = frozenset({"LAB_ADMIN"})

# ---- test sessions -----------------------------------------------------------


def normalize_status(raw: str | None) -> str:
    """'IN PROGRESS' / 'in-progress' / 'In_Progress' -> 'IN_PROGRESS'."""
    if not raw:
        return "DRAFT"
    return raw.strip().upper().replace(" ", "_").replace("-", "_")


# A session can be edited or deleted only while it is still the tester's
# working copy. Once it is submitted for review, or approved, it is a record.
EDITABLE_SESSION_STATUSES = frozenset({"DRAFT", "IN_PROGRESS"})
DELETABLE_SESSION_STATUSES = frozenset(
    {"DRAFT", "IN_PROGRESS", "REJECTED", "CANCELLED"}
)


def session_edit_block_reason(status: str | None) -> str | None:
    s = normalize_status(status)
    if s in EDITABLE_SESSION_STATUSES:
        return None
    return (
        f"A session that is {s} can no longer be edited. Only DRAFT or "
        f"IN_PROGRESS sessions can be changed."
    )


def session_delete_block_reason(
    *,
    status: str | None,
    has_approved_report: bool,
    actor_role: str,
    actor_id: Any,
    tester_id: Any,
) -> tuple[int, str] | None:
    """(http_status, message) if the delete must be refused, else None."""
    if actor_role not in ADMIN_ROLES and str(actor_id) != str(tester_id):
        return 403, "Only the session's tester or a Lab Admin can delete a session."

    s = normalize_status(status)

    if has_approved_report or s == "APPROVED":
        return 409, "An approved session and its report are permanent records and cannot be deleted."

    if s not in DELETABLE_SESSION_STATUSES:
        return 409, (
            f"A session that is {s} has been submitted for review and cannot be "
            f"deleted. Only DRAFT, IN_PROGRESS, REJECTED or CANCELLED sessions can be."
        )

    return None


def session_relink_block_reason(
    *, changing_instrument_or_standard: bool, test_count: int
) -> str | None:
    """Instrument/standard decide which tests apply; fixed once tests exist."""
    if changing_instrument_or_standard and test_count > 0:
        return (
            f"The instrument and standard cannot be changed once tests have been "
            f"added ({test_count} so far). Remove the tests or create a new session."
        )
    return None


# ---- instruments --------------------------------------------------------------

# Changing any of these after a session has moved past DRAFT would silently
# change what the stored results and reports were measured against.
INSTRUMENT_LOCKED_FIELDS = (
    "accuracy_class",
    "max_capacity",
    "min_capacity",
    "verification_scale_interval",
    "scale_interval",
    "number_of_intervals",
    "unit",
)

INSTRUMENT_STATUSES = frozenset({"ACTIVE", "INACTIVE"})


def changed_locked_fields(current: Any, update: Mapping[str, Any]) -> list[str]:
    """Locked fields the update would actually CHANGE (unchanged echoes are fine)."""
    return [
        f
        for f in INSTRUMENT_LOCKED_FIELDS
        if f in update and getattr(current, f, None) != update[f]
    ]


def instrument_edit_block_reason(
    changed_locked: Iterable[str], sessions_past_draft: int
) -> str | None:
    changed = list(changed_locked)
    if changed and sessions_past_draft > 0:
        return (
            f"Cannot change {', '.join(changed)}: {sessions_past_draft} test "
            f"session(s) for this instrument are already past DRAFT, so their "
            f"results depend on these values. Register a new instrument instead."
        )
    return None


def instrument_delete_block_reason(session_count: int) -> str | None:
    if session_count > 0:
        return (
            f"This instrument is used by {session_count} test session(s) and "
            f"cannot be deleted. Set its status to INACTIVE instead to retire it."
        )
    return None


def normalize_instrument_status(value: str | None) -> str | None:
    """None stays None; otherwise ACTIVE/INACTIVE or ValueError."""
    if value is None:
        return None
    v = value.strip().upper()
    if v not in INSTRUMENT_STATUSES:
        raise ValueError(f"status must be one of {sorted(INSTRUMENT_STATUSES)}")
    return v


# ---- equipment ----------------------------------------------------------------


def equipment_delete_block_reason(usage_count: int) -> str | None:
    if usage_count > 0:
        return (
            f"This equipment is recorded as used in {usage_count} test(s) and "
            f"cannot be deleted: that would erase the traceability of those "
            f"results. Mark its calibration status OVERDUE instead if it is "
            f"out of service."
        )
    return None


# ---- reports ------------------------------------------------------------------


def report_change_block_reason(report_status: str | None, action: str) -> str | None:
    if (report_status or "").upper() == "APPROVED":
        return f"An approved report is a permanent record and cannot be {action}."
    return None


def session_actor_block_reason(
    *, actor_role: str, actor_id: Any, tester_id: Any, verb: str
) -> str | None:
    if actor_role in ADMIN_ROLES or str(actor_id) == str(tester_id):
        return None
    return f"Only the session's tester or a Lab Admin can {verb} a session."
