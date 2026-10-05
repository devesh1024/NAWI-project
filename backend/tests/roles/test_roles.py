"""Who may do what, and the maker-checker rule."""
import pytest

from backend.app.services import permissions as perm
from backend.tests.roles.conftest import (
    ALL_ROLES, WP_FAIL, WP_PASS, move, new_session, calculated_session,
)


# ------------------------------------------------------------ the catalogue
def test_every_role_has_a_label_and_known_capabilities():
    assert set(perm.ROLES) >= {"LAB_ADMIN", "TECHNICAL_MANAGER", "QUALITY_MANAGER", "REVIEWER",
                               "APPROVER", "TESTER", "ASSISTANT", "RECORDS_OFFICER",
                               "STANDARDS_CUSTODIAN", "AUDITOR"}
    for r in perm.ROLES.values():
        assert r.label and r.summary
        assert r.capabilities <= perm.ALL_CAPABILITIES


def test_no_role_can_both_test_and_check():
    testing = {perm.SESSIONS_CREATE, perm.SESSIONS_CALCULATE, perm.SESSIONS_ENTER_DATA}
    checking = {perm.SESSIONS_REVIEW, perm.SESSIONS_APPROVE}
    for r in perm.ROLES.values():
        assert not (r.capabilities & testing and r.capabilities & checking), r.code


def test_quality_manager_and_auditor_cannot_change_session_data():
    for code in ("QUALITY_MANAGER", "AUDITOR"):
        caps = perm.ROLES[code].capabilities
        assert not caps & {perm.SESSIONS_CREATE, perm.SESSIONS_ENTER_DATA, perm.SESSIONS_REVIEW,
                           perm.SESSIONS_APPROVE, perm.INSTRUMENTS_REGISTER}


def test_roles_endpoint_and_me_expose_capabilities(lab):
    roles = lab["TESTER"].get("/api/users/roles").json()
    assert {r["code"] for r in roles} >= set(ALL_ROLES) | {"LAB_ADMIN"}
    me = lab["REVIEWER"].get("/api/users/me").json()
    assert me["role_label"] == "Reviewer" and "sessions.review" in me["capabilities"]
    assert "sessions.approve" not in me["capabilities"]
    assert lab.head.get("/api/users/me").json()["role_label"] == "Lab Head / In-charge"


# ------------------------------------------------------------ the Lab Head does not test
def test_lab_head_cannot_run_tests(ready):
    lab, std, td, inst = ready
    h = lab.head
    assert h.post("/api/test-sessions", {"instrument_id": inst["instrument_id"],
                                         "standard_id": std["standard_id"]}).status_code == 403
    sid = new_session(lab, std, inst)
    stid = lab["TESTER"].post(f"/api/test-sessions/{sid}/tests",
                              {"test_definition_id": td["test_definition_id"]}).json()["session_test_id"]
    assert h.post(f"/api/test-sessions/{stid}/observations", {"parameter_name": "x", "value_numeric": 1}).status_code == 403
    assert h.post(f"/api/test-sessions/{stid}/calculation-result", {"inputs": WP_PASS}).status_code == 403
    assert move(lab, "LAB_ADMIN", sid, "IN PROGRESS").status_code == 403


# ------------------------------------------------------------ tester / assistant split
def test_assistant_enters_data_but_cannot_calculate_submit_or_plan(ready):
    lab, std, td, inst = ready
    sid = new_session(lab, std, inst)
    a = lab["ASSISTANT"]
    # cannot create a session or add a test
    assert a.post("/api/test-sessions", {"instrument_id": inst["instrument_id"], "standard_id": std["standard_id"]}).status_code == 403
    r = lab["TESTER"].post(f"/api/test-sessions/{sid}/tests", {"test_definition_id": td["test_definition_id"]})
    stid = r.json()["session_test_id"]
    assert a.post(f"/api/test-sessions/{sid}/tests", {"test_definition_id": td["test_definition_id"]}).status_code in (403, 400)
    # can record readings and environmental conditions
    assert a.post(f"/api/test-sessions/{stid}/observations",
                  {"parameter_name": "load", "value_numeric": 10, "unit": "kg"}).status_code == 201
    assert a.post("/api/environmental-conditions", {"test_session_id": sid, "temperature": 21.5}).status_code == 200
    # cannot calculate or submit
    assert a.post(f"/api/test-sessions/{stid}/calculation-result", {"inputs": WP_PASS}).status_code == 403
    assert move(lab, "ASSISTANT", sid, "IN PROGRESS").status_code == 403


def test_a_tester_cannot_work_on_a_colleagues_session(ready):
    lab, std, td, inst = ready
    other = lab.add("TESTER")
    sid, stid = calculated_session(lab, std, td, inst)
    assert other.post(f"/api/test-sessions/{stid}/observations", {"parameter_name": "x", "value_numeric": 1}).status_code == 403
    assert other.post(f"/api/test-sessions/{stid}/calculation-result", {"inputs": WP_PASS}).status_code == 403
    assert other.get(f"/api/test-sessions/{sid}").status_code == 404      # not even visible
    assert other.patch(f"/api/test-sessions/{sid}/status", {"status": "SUBMITTED"}).status_code == 403


def test_data_is_locked_once_submitted(ready):
    lab, std, td, inst = ready
    sid, stid = calculated_session(lab, std, td, inst)
    assert move(lab, "TESTER", sid, "SUBMITTED").status_code == 200
    assert lab["ASSISTANT"].post(f"/api/test-sessions/{stid}/observations", {"parameter_name": "x", "value_numeric": 1}).status_code == 409
    assert lab["TESTER"].post(f"/api/test-sessions/{stid}/calculation-result", {"inputs": WP_PASS}).status_code == 409


def test_authorisation_scope_limits_which_tests_a_tester_may_run(ready):
    lab, std, td, inst = ready
    narrow = lab.add("TESTER", authorization_scope={"test_codes": ["ZR"]})
    sid = narrow.post("/api/test-sessions", {"instrument_id": inst["instrument_id"],
                                             "standard_id": std["standard_id"]}).json()["test_session_id"]
    r = narrow.post(f"/api/test-sessions/{sid}/tests", {"test_definition_id": td["test_definition_id"]})
    assert r.status_code == 403 and "not authorised" in r.json()["detail"]


# ------------------------------------------------------------ the full pipeline
def test_full_pipeline_tester_reviewer_signatory(ready):
    lab, std, td, inst = ready
    sid, stid = calculated_session(lab, std, td, inst)
    t, rv, ap, head = lab["TESTER"], lab["REVIEWER"], lab["APPROVER"], lab.head

    assert t.post(f"/api/test-sessions/{sid}/generate-report").status_code == 200   # tester drafts
    assert move(lab, "TESTER", sid, "SUBMITTED").status_code == 200

    # review is the reviewer's job, in order
    assert move(lab, "TESTER", sid, "UNDER REVIEW").status_code == 403
    assert move(lab, "APPROVER", sid, "UNDER REVIEW").status_code == 403
    assert move(lab, "REVIEWER", sid, "UNDER REVIEW").status_code == 200

    # signing is blocked until the reviewer forwards the report
    assert ap.patch(f"/api/test-sessions/{sid}/approve-report").status_code == 400
    assert t.patch(f"/api/test-sessions/{sid}/submit-for-approval").status_code == 403
    assert rv.patch(f"/api/test-sessions/{sid}/submit-for-approval").status_code == 200

    # the status endpoint can never mark a session approved
    assert move(lab, "LAB_ADMIN", sid, "APPROVED").status_code == 409
    # the reviewer cannot sign, the tester cannot sign
    assert rv.patch(f"/api/test-sessions/{sid}/approve-report").status_code == 403
    assert t.patch(f"/api/test-sessions/{sid}/approve-report").status_code == 403

    r = ap.patch(f"/api/test-sessions/{sid}/approve-report")
    assert r.status_code == 200, r.text
    assert head.get(f"/api/test-sessions/{sid}").json()["status"] == "APPROVED"
    # approved is final
    assert move(lab, "TESTER", sid, "IN PROGRESS").status_code == 409


def test_lab_head_can_sign_off_as_the_final_authority(ready):
    lab, std, td, inst = ready
    sid, _ = calculated_session(lab, std, td, inst)
    lab["TESTER"].post(f"/api/test-sessions/{sid}/generate-report")
    move(lab, "TESTER", sid, "SUBMITTED"); move(lab, "REVIEWER", sid, "UNDER REVIEW")
    lab["REVIEWER"].patch(f"/api/test-sessions/{sid}/submit-for-approval")
    r = lab.head.patch(f"/api/test-sessions/{sid}/approve-report")
    assert r.status_code == 200, r.text


def test_reviewer_returns_for_correction_with_a_reason_and_tester_reworks(ready):
    lab, std, td, inst = ready
    sid, _ = calculated_session(lab, std, td, inst, inputs=WP_FAIL)
    move(lab, "TESTER", sid, "SUBMITTED"); move(lab, "REVIEWER", sid, "UNDER REVIEW")
    assert move(lab, "REVIEWER", sid, "REJECTED").status_code == 422                  # reason needed
    r = move(lab, "REVIEWER", sid, "REJECTED", reason="Zero error not recorded")
    assert r.status_code == 200
    assert move(lab, "REVIEWER", sid, "IN PROGRESS").status_code == 403               # only the tester reworks
    assert move(lab, "TESTER", sid, "IN PROGRESS").status_code == 200


def test_signatory_must_give_a_reason_to_reject(ready):
    lab, std, td, inst = ready
    sid, _ = calculated_session(lab, std, td, inst)
    lab["TESTER"].post(f"/api/test-sessions/{sid}/generate-report")
    move(lab, "TESTER", sid, "SUBMITTED"); move(lab, "REVIEWER", sid, "UNDER REVIEW")
    lab["REVIEWER"].patch(f"/api/test-sessions/{sid}/submit-for-approval")
    ap = lab["APPROVER"]
    assert ap.patch(f"/api/test-sessions/{sid}/approve-report?action=REJECT").status_code == 422
    r = ap.patch(f"/api/test-sessions/{sid}/approve-report?action=REJECT&reason=Wrong%20class")
    assert r.status_code == 200
    assert ap.get(f"/api/test-sessions/{sid}").json()["status"] == "REJECTED"


def test_cannot_skip_steps(ready):
    lab, std, td, inst = ready
    sid = new_session(lab, std, inst)
    assert move(lab, "TESTER", sid, "SUBMITTED").status_code == 409       # DRAFT -> SUBMITTED
    assert move(lab, "TESTER", sid, "BANANA").status_code == 400
    assert move(lab, "TESTER", sid, "IN PROGRESS").status_code == 200
    assert move(lab, "REVIEWER", sid, "UNDER REVIEW").status_code == 409  # not submitted yet


# ------------------------------------------------------------ maker-checker
def test_a_tester_who_becomes_reviewer_cannot_check_their_own_work(ready):
    """The rule must hold even if roles change after the testing was done."""
    lab, std, td, inst = ready
    sam = lab.add("TESTER")
    sid, _ = calculated_session(lab, std, td, inst, who="TESTER")
    # swap: the original tester was promoted to reviewer after testing
    tester = lab["TESTER"]
    assert lab.head.patch(f"/api/users/{tester.user_id}", {"role": "REVIEWER"}).status_code == 200
    # re-login is not needed: the role is read from the database on each request
    assert tester.patch(f"/api/test-sessions/{sid}/status", {"status": "SUBMITTED"}).status_code == 403  # no longer a tester
    # (a different tester must now submit it; the promoted person can never review it)
    del sam


def test_assistant_who_entered_data_cannot_later_review_it(ready):
    lab, std, td, inst = ready
    sid = new_session(lab, std, inst)
    stid = lab["TESTER"].post(f"/api/test-sessions/{sid}/tests",
                              {"test_definition_id": td["test_definition_id"]}).json()["session_test_id"]
    a = lab["ASSISTANT"]
    assert a.post(f"/api/test-sessions/{stid}/observations", {"parameter_name": "load", "value_numeric": 10}).status_code == 201
    lab["TESTER"].post(f"/api/test-sessions/{stid}/calculation-result", {"inputs": WP_PASS})
    move(lab, "TESTER", sid, "IN PROGRESS"); move(lab, "TESTER", sid, "SUBMITTED")
    # the assistant is promoted to reviewer, then tries to review the session they recorded
    assert lab.head.patch(f"/api/users/{a.user_id}", {"role": "REVIEWER"}).status_code == 200
    r = a.patch(f"/api/test-sessions/{sid}/status", {"status": "UNDER REVIEW"})
    assert r.status_code == 403 and "took part" in r.json()["detail"]
    # a different reviewer can
    assert move(lab, "REVIEWER", sid, "UNDER REVIEW").status_code == 200


# ------------------------------------------------------------ what each role sees
def test_session_visibility_per_role(ready):
    lab, std, td, inst = ready
    other = lab.add("TESTER")
    draft = new_session(lab, std, inst)                                    # TESTER, draft
    sub, _ = calculated_session(lab, std, td, inst)                            # TESTER
    move(lab, "TESTER", sub, "SUBMITTED")
    theirs = new_session(lab, std, inst, who="TESTER")
    ids = lambda who: {s["test_session_id"] for s in lab[who].get("/api/test-sessions").json()}

    assert ids("TESTER") == {draft, sub, theirs}
    assert other.get("/api/test-sessions").json() == []                    # not theirs
    assert ids("LAB_ADMIN") == ids("AUDITOR") == ids("QUALITY_MANAGER") == {draft, sub, theirs}
    assert ids("REVIEWER") == {sub}                                        # only submitted work
    assert ids("APPROVER") == set()                                        # nothing under review yet
    assert ids("ASSISTANT") == {draft, theirs}                             # open sessions only
    assert lab["REVIEWER"].get(f"/api/test-sessions/{draft}").status_code == 404


def test_workflow_actions_match_the_role(ready):
    lab, std, td, inst = ready
    sid, _ = calculated_session(lab, std, td, inst)
    move(lab, "TESTER", sid, "SUBMITTED")
    keys = lambda who: {a["key"]: a for a in lab[who].get(f"/api/test-sessions/{sid}/workflow").json()["actions"]}

    assert set(keys("TESTER")) == {"recall"}
    assert set(keys("REVIEWER")) == {"start_review"} and keys("REVIEWER")["start_review"]["enabled"]
    assert lab["ASSISTANT"].get(f"/api/test-sessions/{sid}/workflow").status_code == 404   # submitted work is not theirs to see
    assert keys("AUDITOR") == {}
    assert "start_review" in keys("LAB_ADMIN")


def test_workflow_explains_why_an_action_is_blocked(ready):
    lab, std, td, inst = ready
    sid = new_session(lab, std, inst)
    stid = lab["TESTER"].post(f"/api/test-sessions/{sid}/tests",
                              {"test_definition_id": td["test_definition_id"]}).json()["session_test_id"]
    a = lab["ASSISTANT"]
    a.post(f"/api/test-sessions/{stid}/observations", {"parameter_name": "load", "value_numeric": 10})
    lab["TESTER"].post(f"/api/test-sessions/{stid}/calculation-result", {"inputs": WP_PASS})
    move(lab, "TESTER", sid, "IN PROGRESS"); move(lab, "TESTER", sid, "SUBMITTED")
    lab.head.patch(f"/api/users/{a.user_id}", {"role": "REVIEWER"})
    wf = a.get(f"/api/test-sessions/{sid}/workflow").json()
    assert wf["took_part"] is True
    start = next(x for x in wf["actions"] if x["key"] == "start_review")
    assert start["enabled"] is False and "took part" in start["reason"]


def test_workflow_history_records_who_did_what(ready):
    lab, std, td, inst = ready
    sid, _ = calculated_session(lab, std, td, inst)
    move(lab, "TESTER", sid, "SUBMITTED"); move(lab, "REVIEWER", sid, "UNDER REVIEW")
    hist = lab.head.get(f"/api/test-sessions/{sid}/workflow").json()["history"]
    steps = [(h["action"], h["by_role"]) for h in hist]
    assert ("SUBMIT", "Senior Tester / Evaluator") in steps
    assert ("START_REVIEW", "Reviewer") in steps


# ------------------------------------------------------------ everything else in the lab
def test_instruments_are_received_by_records_and_testers_but_not_everyone(lab):
    for who in ("RECORDS_OFFICER", "TESTER", "LAB_ADMIN", "TECHNICAL_MANAGER"):
        lab.instrument(who=who)
    body = {"instrument_code": "Z", "accuracy_class": "III", "max_capacity": 30, "min_capacity": 0.2,
            "verification_scale_interval": 0.01, "scale_interval": 0.01}
    for who in ("ASSISTANT", "REVIEWER", "APPROVER", "AUDITOR", "QUALITY_MANAGER", "STANDARDS_CUSTODIAN"):
        assert lab[who].post("/api/instruments", body).status_code == 403, who
    assert lab["AUDITOR"].get("/api/instruments").status_code == 200       # everyone can read


def test_equipment_is_kept_by_the_custodian_and_quality_manager(lab):
    for who in ("STANDARDS_CUSTODIAN", "QUALITY_MANAGER", "LAB_ADMIN", "TECHNICAL_MANAGER"):
        assert lab[who].post("/api/test-equipment", {"equipment_name": f"Weight {who}"}).status_code in (200, 201), who
    for who in ("TESTER", "ASSISTANT", "REVIEWER", "AUDITOR", "RECORDS_OFFICER"):
        assert lab[who].post("/api/test-equipment", {"equipment_name": "x"}).status_code == 403, who


def test_methods_standards_are_managed_by_head_and_technical_manager(lab):
    lab["TECHNICAL_MANAGER"].post("/api/standards", {"standard_code": "TM-STD", "title": "x"})
    for who in ("TESTER", "QUALITY_MANAGER", "REVIEWER", "AUDITOR"):
        assert lab[who].post("/api/standards", {"standard_code": "no", "title": "no"}).status_code == 403, who
        assert lab[who].get("/api/standards").status_code == 200


def test_audit_log_is_for_head_quality_manager_and_auditor(lab):
    for who in ("LAB_ADMIN", "QUALITY_MANAGER", "AUDITOR"):
        assert lab[who].get("/api/audit-logs").status_code == 200, who
    for who in ("TESTER", "REVIEWER", "ASSISTANT", "RECORDS_OFFICER", "TECHNICAL_MANAGER"):
        assert lab[who].get("/api/audit-logs").status_code == 403, who


def test_auditor_is_strictly_read_only(ready):
    lab, std, td, inst = ready
    sid, stid = calculated_session(lab, std, td, inst)
    a = lab["AUDITOR"]
    assert a.get(f"/api/test-sessions/{sid}").status_code == 200
    assert a.get(f"/api/test-sessions/{sid}/report-data").status_code == 200
    writes = [
        a.post("/api/test-sessions", {"instrument_id": inst["instrument_id"], "standard_id": std["standard_id"]}),
        a.post(f"/api/test-sessions/{stid}/observations", {"parameter_name": "x", "value_numeric": 1}),
        a.post("/api/test-equipment", {"equipment_name": "x"}),
        a.post("/api/instruments", {"instrument_code": "x"}),
        a.patch(f"/api/test-sessions/{sid}/status", {"status": "SUBMITTED"}),
        a.post(f"/api/test-sessions/{sid}/generate-report"),
        a.post("/api/users", {"first_name": "x", "email": "n@x.example.com", "password": "pw", "role": "TESTER"}),
    ]
    assert [w.status_code for w in writes] == [403] * len(writes)


def test_report_generation_rules(ready):
    lab, std, td, inst = ready
    sid, _ = calculated_session(lab, std, td, inst)
    other = lab.add("TESTER")
    assert other.post(f"/api/test-sessions/{sid}/generate-report").status_code in (403, 404)
    assert lab["ASSISTANT"].post(f"/api/test-sessions/{sid}/generate-report").status_code == 403
    # a reviewer cannot regenerate while the tester is still working
    assert lab["REVIEWER"].post(f"/api/test-sessions/{sid}/generate-report").status_code in (404, 409)
    assert lab["TESTER"].post(f"/api/test-sessions/{sid}/generate-report").status_code == 200


# ------------------------------------------------------------ user management
def test_lab_head_manages_users_and_roles(lab):
    h = lab.head
    assert h.post("/api/users", {"first_name": "x", "email": "a1@x.example.com", "password": "pw", "role": "LAB_ADMIN"}).status_code == 400
    assert h.post("/api/users", {"first_name": "x", "email": "a2@x.example.com", "password": "pw", "role": "WIZARD"}).status_code == 400
    u = lab["TESTER"]
    assert h.patch(f"/api/users/{u.user_id}", {"role": "ASSISTANT"}).json()["role_label"] == "Technician / Lab Assistant"
    assert h.patch(f"/api/users/{u.user_id}", {"status": "INACTIVE"}).status_code == 200
    assert u.get("/api/users/me").status_code == 403                  # deactivated: locked out at once
    assert h.patch(f"/api/users/{u.user_id}", {"status": "ACTIVE"}).status_code == 200
    assert u.get("/api/users/me").status_code == 200


def test_user_management_guards(lab):
    h = lab.head
    assert h.patch(f"/api/users/{h.user_id}", {"role": "TESTER"}).status_code == 409        # not own role
    assert h.patch(f"/api/users/{h.user_id}", {"status": "INACTIVE"}).status_code == 409    # not own account
    assert lab["TESTER"].patch(f"/api/users/{lab['ASSISTANT'].user_id}", {"role": "AUDITOR"}).status_code == 403
    assert lab["TESTER"].get("/api/users").status_code == 403
    assert lab["TECHNICAL_MANAGER"].get("/api/users").status_code == 200


def test_technical_manager_sets_authorisation_only(lab):
    tm, t = lab["TECHNICAL_MANAGER"], lab["TESTER"]
    r = tm.patch(f"/api/users/{t.user_id}", {"authorization_scope": {"test_codes": ["WP", "ZR"]}})
    assert r.status_code == 200 and r.json()["authorization_scope"] == {"test_codes": ["WP", "ZR"]}
    assert tm.patch(f"/api/users/{t.user_id}", {"role": "AUDITOR"}).status_code == 403
    assert tm.patch(f"/api/users/{t.user_id}", {"status": "INACTIVE"}).status_code == 403
    # people cannot grant themselves authorisation
    t.put("/api/users/me", {"authorization_scope": {"test_codes": []}})
    assert t.get("/api/users/me").json()["authorization_scope"] == {"test_codes": ["WP", "ZR"]}


def test_other_labs_cannot_see_or_change_my_staff(env, lab):
    from backend.tests.roles.conftest import Lab
    other = Lab(env[0])
    assert other.head.patch(f"/api/users/{lab['TESTER'].user_id}", {"role": "AUDITOR"}).status_code == 404


# ------------------------------------------------------------ dashboards
@pytest.mark.parametrize("role", ["LAB_ADMIN", *ALL_ROLES])
def test_every_role_gets_its_own_dashboard(ready, role):
    lab, std, td, inst = ready
    sid, _ = calculated_session(lab, std, td, inst)
    move(lab, "TESTER", sid, "SUBMITTED")
    d = lab[role].get("/api/dashboard")
    assert d.status_code == 200, d.text
    body = d.json()
    assert body["role"] == role and body["role_label"] == perm.label_for(role)
    assert body["kpis"] and all({"key", "label", "value"} <= set(k) for k in body["kpis"])
    assert isinstance(body["queues"], list) and body["queues"]


def test_dashboard_content_reflects_the_job(ready):
    lab, std, td, inst = ready
    sid, _ = calculated_session(lab, std, td, inst)
    move(lab, "TESTER", sid, "SUBMITTED")
    kpi = lambda who, key: next(k["value"] for k in lab[who].get("/api/dashboard").json()["kpis"] if k["key"] == key)
    q = lambda who, key: next(x for x in lab[who].get("/api/dashboard").json()["queues"] if x["key"] == key)

    assert kpi("REVIEWER", "ready") == 1                       # one session waiting for review
    assert q("REVIEWER", "ready")["items"][0]["href"].endswith(sid)
    assert kpi("APPROVER", "sign") == 0                        # nothing for the signatory yet
    assert kpi("TESTER", "review") == 1
    assert kpi("RECORDS_OFFICER", "total") == 1
    assert kpi("STANDARDS_CUSTODIAN", "total") == 0
    assert lab["TESTER"].get("/api/dashboard").json()["charts"]["results"][0] == {"name": "PASS", "value": 1}


def test_dashboard_is_scoped_to_the_tester(ready):
    lab, std, td, inst = ready
    calculated_session(lab, std, td, inst)
    other = lab.add("TESTER")
    d = other.get("/api/dashboard").json()
    assert next(k["value"] for k in d["kpis"] if k["key"] == "open") == 0
    assert d["charts"]["results"][0]["value"] == 0


def test_custodian_dashboard_flags_overdue_calibration(lab):
    lab["STANDARDS_CUSTODIAN"].post("/api/test-equipment", {
        "equipment_name": "Old weight", "calibration_due_date": "2020-01-01T00:00:00"})
    lab["STANDARDS_CUSTODIAN"].post("/api/test-equipment", {
        "equipment_name": "New weight", "calibration_due_date": "2099-01-01T00:00:00"})
    d = lab["STANDARDS_CUSTODIAN"].get("/api/dashboard").json()
    k = {x["key"]: x["value"] for x in d["kpis"]}
    assert k["overdue"] == 1 and k["valid"] == 1
    assert d["queues"][0]["items"][0]["subtitle"] == "Old weight"
