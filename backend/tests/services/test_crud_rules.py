from types import SimpleNamespace

import pytest

from backend.app.services.crud_rules import (
    changed_locked_fields,
    equipment_delete_block_reason,
    instrument_delete_block_reason,
    instrument_edit_block_reason,
    normalize_instrument_status,
    normalize_status,
    report_change_block_reason,
    session_actor_block_reason,
    session_delete_block_reason,
    session_edit_block_reason,
    session_relink_block_reason,
)


def delete_block(status="DRAFT", approved=False, role="TESTER", actor="u1", tester="u1"):
    return session_delete_block_reason(
        status=status, has_approved_report=approved,
        actor_role=role, actor_id=actor, tester_id=tester,
    )


# ---- status normalisation ---------------------------------------------------

def test_status_normalisation_handles_old_and_new_spellings():
    assert normalize_status("IN PROGRESS") == "IN_PROGRESS"
    assert normalize_status("in-progress") == "IN_PROGRESS"
    assert normalize_status("Under Review") == "UNDER_REVIEW"
    assert normalize_status(None) == "DRAFT"


# ---- sessions: edit ---------------------------------------------------------

def test_only_draft_and_in_progress_sessions_are_editable():
    assert session_edit_block_reason("DRAFT") is None
    assert session_edit_block_reason("IN PROGRESS") is None
    assert session_edit_block_reason("IN_PROGRESS") is None
    for s in ("SUBMITTED", "UNDER REVIEW", "APPROVED", "REJECTED", "COMPLETED", "CANCELLED"):
        assert "can no longer be edited" in session_edit_block_reason(s)


def test_instrument_and_standard_are_fixed_once_tests_exist():
    assert session_relink_block_reason(changing_instrument_or_standard=True, test_count=0) is None
    assert "3 so far" in session_relink_block_reason(changing_instrument_or_standard=True, test_count=3)
    assert session_relink_block_reason(changing_instrument_or_standard=False, test_count=3) is None


def test_edit_actor_must_be_tester_or_admin():
    assert session_actor_block_reason(actor_role="TESTER", actor_id="a", tester_id="a", verb="edit") is None
    assert session_actor_block_reason(actor_role="LAB_ADMIN", actor_id="b", tester_id="a", verb="edit") is None
    assert "tester or a Lab Admin" in session_actor_block_reason(actor_role="TESTER", actor_id="b", tester_id="a", verb="edit")


# ---- sessions: delete -------------------------------------------------------

def test_tester_can_delete_own_unsubmitted_session():
    for s in ("DRAFT", "IN PROGRESS", "IN_PROGRESS", "REJECTED", "CANCELLED"):
        assert delete_block(status=s) is None, s


def test_submitted_review_and_approved_sessions_cannot_be_deleted():
    for s in ("SUBMITTED", "UNDER REVIEW", "UNDER_REVIEW", "COMPLETED"):
        code, msg = delete_block(status=s, role="LAB_ADMIN")
        assert code == 409 and "cannot be deleted" in msg, s
    code, _ = delete_block(status="APPROVED", role="LAB_ADMIN")
    assert code == 409


def test_session_with_approved_report_cannot_be_deleted_whatever_its_status():
    code, msg = delete_block(status="DRAFT", approved=True, role="LAB_ADMIN")
    assert code == 409 and "permanent" in msg


def test_other_testers_cannot_delete_but_lab_admin_can():
    code, _ = delete_block(role="TESTER", actor="other", tester="u1")
    assert code == 403
    assert delete_block(role="LAB_ADMIN", actor="other", tester="u1") is None
    code, _ = delete_block(role="REVIEWER", actor="other", tester="u1")
    assert code == 403


def test_permission_is_checked_before_status_disclosure():
    # A non-owner gets 403 even for a session that would be 409.
    code, _ = delete_block(status="APPROVED", role="TESTER", actor="x", tester="u1")
    assert code == 403


# ---- instruments ------------------------------------------------------------

def instrument(**kw):
    base = dict(accuracy_class="III", max_capacity=30.0, min_capacity=0.2,
                verification_scale_interval=0.01, scale_interval=0.01,
                number_of_intervals=3000, unit="kg", manufacturer="ACME")
    base.update(kw)
    return SimpleNamespace(**base)


def test_unchanged_values_echoed_by_the_edit_form_are_not_changes():
    update = {"accuracy_class": "III", "max_capacity": 30.0, "unit": "kg", "manufacturer": "New Co"}
    assert changed_locked_fields(instrument(), update) == []


def test_changed_metrological_fields_are_detected():
    update = {"accuracy_class": "II", "max_capacity": 30.0, "scale_interval": 0.1, "manufacturer": "x"}
    assert changed_locked_fields(instrument(), update) == ["accuracy_class", "scale_interval"]


def test_locked_fields_block_only_when_sessions_are_past_draft():
    assert instrument_edit_block_reason(["accuracy_class"], 0) is None
    assert instrument_edit_block_reason([], 5) is None
    msg = instrument_edit_block_reason(["accuracy_class", "unit"], 2)
    assert "accuracy_class, unit" in msg and "2 test session" in msg


def test_instrument_in_use_cannot_be_deleted():
    assert instrument_delete_block_reason(0) is None
    assert "INACTIVE" in instrument_delete_block_reason(1)


def test_instrument_status_values():
    assert normalize_instrument_status(None) is None
    assert normalize_instrument_status(" inactive ") == "INACTIVE"
    assert normalize_instrument_status("ACTIVE") == "ACTIVE"
    with pytest.raises(ValueError):
        normalize_instrument_status("BROKEN")


# ---- equipment --------------------------------------------------------------

def test_equipment_used_in_tests_cannot_be_deleted():
    assert equipment_delete_block_reason(0) is None
    assert "traceability" in equipment_delete_block_reason(4)


# ---- reports ----------------------------------------------------------------

def test_approved_reports_are_immutable_others_are_not():
    assert report_change_block_reason("GENERATED", "deleted") is None
    assert report_change_block_reason("OUTDATED", "edited") is None
    assert report_change_block_reason(None, "edited") is None
    assert "cannot be deleted" in report_change_block_reason("APPROVED", "deleted")
    assert "cannot be edited" in report_change_block_reason("approved", "edited")
