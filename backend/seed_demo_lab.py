"""
Create a ready-to-explore demo laboratory: one person per role, some
instruments and reference weights, and sessions at every stage of the
workflow, so every role's dashboard has something real on it.

Everything is created through the application's own API, so the demo data
obeys exactly the same rules as real data (including maker-checker).

    python -m backend.seed_demo_lab

Safe to run twice: it stops if the demo laboratory already exists.
All demo accounts use the password  demo1234  (see frontend/src/lib/devAuth.js).
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.app.main import app

PASSWORD = "demo1234"
HEAD_EMAIL = "demo@nawitest.com"

STAFF = [
    # role,                  email,                      first,    last,      designation
    ("TECHNICAL_MANAGER",    "tm@nawitest.com",         "Tanvi",  "Mehta",   "Technical Manager"),
    ("QUALITY_MANAGER",      "quality@nawitest.com",    "Qasim",  "Khan",    "Quality Manager"),
    ("REVIEWER",             "reviewer@nawitest.com",   "Ravi",   "Verma",   "Assistant Director (Review)"),
    ("APPROVER",             "signatory@nawitest.com",  "Sunita", "Rao",     "Deputy Director (Authorised Signatory)"),
    ("TESTER",               "tester@nawitest.com",     "Tara",   "Singh",   "Senior Tester / Evaluator"),
    ("ASSISTANT",            "assistant@nawitest.com",  "Arjun",  "Patel",   "Lab Technician"),
    ("RECORDS_OFFICER",      "records@nawitest.com",    "Rekha",  "Iyer",    "Receiving & Records Officer"),
    ("STANDARDS_CUSTODIAN",  "custodian@nawitest.com",  "Chetan", "Nair",    "Standards Custodian"),
    ("AUDITOR",              "auditor@nawitest.com",    "Asha",   "Bose",    "NABL Assessor"),
]

PASS = {"measurements": [{"load": 10, "indication": 10.0, "additional_load": 0, "zero_error": 0}]}
FAIL = {"measurements": [{"load": 10, "indication": 10.5, "additional_load": 0, "zero_error": 0}]}


class Actor:
    def __init__(self, client, email):
        r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        r.raise_for_status()
        self.client, self.h = client, {"Authorization": f"Bearer {r.json()['access_token']}"}

    def _ok(self, r, what):
        if r.status_code >= 400:
            raise SystemExit(f"Seeding failed at: {what}\n  {r.status_code} {r.text}")
        if "json" not in r.headers.get("content-type", ""):
            return r.content          # e.g. a generated report file
        return r.json()

    def get(self, url): return self.client.get(url, headers=self.h)
    def post(self, url, body=None, what=""): return self._ok(self.client.post(url, headers=self.h, json=body), what or url)
    def patch(self, url, body=None, what=""): return self._ok(self.client.patch(url, headers=self.h, json=body), what or url)


def main() -> None:
    client = TestClient(app)

    if client.post("/api/auth/login", json={"email": HEAD_EMAIL, "password": PASSWORD}).status_code == 200:
        print("The demo laboratory already exists. Nothing to do.")
        return

    r = client.post("/api/auth/register", json={
        "laboratory_code": "RRSL-DEMO", "laboratory_name": "Regional Reference Standards Laboratory (Demo)",
        "first_name": "Harish", "last_name": "Deshmukh", "email": HEAD_EMAIL, "password": PASSWORD,
        "city": "Indore", "state": "Madhya Pradesh", "country": "India",
    })
    if r.status_code >= 400:
        raise SystemExit(f"Could not register the demo laboratory: {r.status_code} {r.text}")

    head = Actor(client, HEAD_EMAIL)

    for role, email, first, last, designation in STAFF:
        head.post("/api/users", {"first_name": first, "last_name": last, "email": email,
                                 "password": PASSWORD, "role": role, "designation": designation},
                  f"create {role}")

    who = {role: Actor(client, email) for role, email, *_ in STAFF}

    # ---- reference data (Lab Head / Technical Manager own the methods) ----
    std = head.post("/api/standards", {"standard_code": "OIML R 76-1", "title":
                    "Non-automatic weighing instruments", "version": "2006", "edition_year": 2006}, "standard")
    td = head.post("/api/test-definitions", {"standard_id": std["standard_id"], "test_code": "WP",
                   "test_name": "Weighing performance", "calculation_type": "weighing_error",
                   "is_mandatory": True}, "test definition")

    # ---- instruments received by Records ----
    def instrument(code, maker, model, cls="III", cap=30):
        return who["RECORDS_OFFICER"].post("/api/instruments", {
            "instrument_code": code, "manufacturer": maker, "model": model, "accuracy_class": cls,
            "max_capacity": cap, "min_capacity": 0.2, "verification_scale_interval": 0.01,
            "scale_interval": 0.01, "unit": "kg", "instrument_type": "Platform scale"}, f"instrument {code}")

    inst = [instrument("NAWI-001", "Essae", "DS-415"),
            instrument("NAWI-002", "Mettler Toledo", "IND560"),
            instrument("NAWI-003", "Avery Berkel", "L223"),
            instrument("NAWI-004", "Sartorius", "Combics 1"),
            instrument("NAWI-005", "Libra", "PS-30")]          # 004 and 005: received, not yet tested

    # ---- reference weights kept by the Standards Custodian ----
    today = date.today()
    for name, code, due in (("Reference weight set 1 kg-20 kg (M1)", "REF-W-01", today + timedelta(days=210)),
                            ("Reference weight 50 kg (F1)", "REF-W-02", today + timedelta(days=12)),
                            ("Reference weight 500 g (E2)", "REF-W-03", today - timedelta(days=9))):
        who["STANDARDS_CUSTODIAN"].post("/api/test-equipment", {
            "equipment_name": name, "equipment_code": code, "equipment_type": "Reference weight",
            "calibration_due_date": f"{due.isoformat()}T00:00:00",
            "calibration_status": "OVERDUE" if due < today else "VALID"}, f"equipment {code}")

    # ---- sessions at every stage ----
    tester, assistant = who["TESTER"], who["ASSISTANT"]
    reviewer, signatory = who["REVIEWER"], who["APPROVER"]

    def session(instrument_row, number, inputs, assistant_reading=True):
        sid = tester.post("/api/test-sessions", {"instrument_id": instrument_row["instrument_id"],
                          "standard_id": std["standard_id"], "session_number": number}, f"session {number}")["test_session_id"]
        stid = tester.post(f"/api/test-sessions/{sid}/tests", {"test_definition_id": td["test_definition_id"]},
                           "add test")["session_test_id"]
        if assistant_reading:
            assistant.post(f"/api/test-sessions/{stid}/observations", {
                "parameter_name": "Applied load", "parameter_code": "load", "value_numeric": 10, "unit": "kg"}, "reading")
        if inputs is not None:
            tester.post(f"/api/test-sessions/{stid}/calculation-result", {"inputs": inputs}, "calculate")
        tester.patch(f"/api/test-sessions/{sid}/status", {"status": "IN PROGRESS"}, "start")
        return sid

    def submit(sid):
        tester.post(f"/api/test-sessions/{sid}/generate-report", None, "draft report")
        tester.patch(f"/api/test-sessions/{sid}/status", {"status": "SUBMITTED"}, "submit")

    # 1. approved (the whole pipeline)
    a = session(inst[0], "TS-DEMO-001", PASS); submit(a)
    reviewer.patch(f"/api/test-sessions/{a}/status", {"status": "UNDER REVIEW"}, "review")
    reviewer.patch(f"/api/test-sessions/{a}/submit-for-approval", None, "forward")
    signatory.patch(f"/api/test-sessions/{a}/approve-report", None, "approve")

    # 2. forwarded, waiting for a signature
    b = session(inst[1], "TS-DEMO-002", PASS); submit(b)
    reviewer.patch(f"/api/test-sessions/{b}/status", {"status": "UNDER REVIEW"}, "review")
    reviewer.patch(f"/api/test-sessions/{b}/submit-for-approval", None, "forward")

    # 3. submitted, waiting for a reviewer (a failing result)
    c = session(inst[2], "TS-DEMO-003", FAIL); submit(c)

    # 4. still being tested
    session(inst[2], "TS-DEMO-004", None)

    # 5. returned for correction
    d = session(inst[1], "TS-DEMO-005", PASS); submit(d)
    reviewer.patch(f"/api/test-sessions/{d}/status", {"status": "UNDER REVIEW"}, "review")
    reviewer.patch(f"/api/test-sessions/{d}/status",
                   {"status": "REJECTED", "reason": "Ambient temperature was not recorded."}, "return")

    print("Demo laboratory created. Sign in with any of these (password: demo1234):\n")
    print(f"  {'Lab Head / In-charge':<34} {HEAD_EMAIL}")
    for role, email, first, last, designation in STAFF:
        print(f"  {designation:<34} {email}")


if __name__ == "__main__":
    main()
