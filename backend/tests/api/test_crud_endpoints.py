# backend/tests/api/test_crud_endpoints.py
#
# End-to-end tests for update/delete on instruments, test sessions, reports and
# equipment, against an in-memory SQLite database.
#
# SAFETY: DATABASE_URL is forced to SQLite *before* the app is imported, because
# backend/.env may point at a real database and connection.py loads it.
#
# Run:  python -m pytest backend/tests/api -q      (needs fastapi, httpx, sqlalchemy)

import os

os.environ["DATABASE_URL"] = "sqlite://"   # must precede any backend.app import

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401  (registers every table on Base)
from backend.app.database.connection import Base, get_db
from backend.app.main import app
from backend.app.models.report import Report


@pytest.fixture()
def env():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, TestingSession
    app.dependency_overrides.clear()
    engine.dispose()


def make_lab(client, n):
    """Register a lab (its admin is a LAB_ADMIN) and return auth headers."""
    email = f"admin{n}@example.com"
    r = client.post("/api/auth/register", json={
        "laboratory_code": f"LAB{n}", "laboratory_name": f"Lab {n}",
        "first_name": "Ada", "email": email, "password": "Passw0rd!x",
    })
    assert r.status_code in (200, 201), r.text
    r = client.post("/api/auth/login", json={"email": email, "password": "Passw0rd!x"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_instrument(client, h, code="I-1", **extra):
    body = {"instrument_code": code, "manufacturer": "ACME", "model": "X1",
            "accuracy_class": "III", "max_capacity": 30, "min_capacity": 0.2,
            "verification_scale_interval": 0.01, "scale_interval": 0.01}
    body.update(extra)
    r = client.post("/api/instruments", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def make_standard(client, h):
    r = client.post("/api/standards", json={"standard_code": "OIML R76", "title": "NAWI"}, headers=h)
    assert r.status_code in (200, 201), r.text
    return r.json()


def make_session(client, h, instrument, standard, number="S-1"):
    r = client.post("/api/test-sessions", headers=h, json={
        "instrument_id": instrument["instrument_id"],
        "standard_id": standard["standard_id"], "session_number": number})
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- instruments

def test_instrument_update_and_delete(env):
    client, _ = env
    h = make_lab(client, 1)
    inst = make_instrument(client, h)
    url = f"/api/instruments/{inst['instrument_id']}"

    r = client.put(url, json={"manufacturer": "New Co"}, headers=h)
    assert r.status_code == 200 and r.json()["manufacturer"] == "New Co"

    assert client.put(url, json={"status": "BROKEN"}, headers=h).status_code == 422
    assert client.put(url, json={"status": "inactive"}, headers=h).json()["status"] == "INACTIVE"

    assert client.delete(url, headers=h).status_code == 200
    assert client.get(url, headers=h).status_code == 404


def test_instrument_with_sessions_cannot_be_deleted(env):
    client, _ = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    make_session(client, h, inst, std)

    r = client.delete(f"/api/instruments/{inst['instrument_id']}", headers=h)
    assert r.status_code == 409 and "INACTIVE" in r.json()["detail"]


def test_inactive_instrument_cannot_start_new_sessions(env):
    client, _ = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    client.put(f"/api/instruments/{inst['instrument_id']}", json={"status": "INACTIVE"}, headers=h)

    r = client.post("/api/test-sessions", headers=h, json={
        "instrument_id": inst["instrument_id"], "standard_id": std["standard_id"]})
    assert r.status_code == 409


def test_metrological_fields_lock_once_a_session_is_past_draft(env):
    client, _ = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    session = make_session(client, h, inst, std)
    url = f"/api/instruments/{inst['instrument_id']}"

    # Still DRAFT: changing the class is allowed.
    assert client.put(url, json={"accuracy_class": "II"}, headers=h).status_code == 200

    client.patch(f"/api/test-sessions/{session['test_session_id']}/status",
                 json={"status": "IN PROGRESS"}, headers=h)

    r = client.put(url, json={"accuracy_class": "I"}, headers=h)
    assert r.status_code == 409 and "accuracy_class" in r.json()["detail"]

    # The edit form echoes unchanged values back; that must still work.
    r = client.put(url, json={"accuracy_class": "II", "max_capacity": 30, "manufacturer": "Renamed"}, headers=h)
    assert r.status_code == 200


def test_other_labs_cannot_touch_an_instrument(env):
    client, _ = env
    h1, h2 = make_lab(client, 1), make_lab(client, 2)
    inst = make_instrument(client, h1)
    url = f"/api/instruments/{inst['instrument_id']}"
    assert client.put(url, json={"manufacturer": "hacked"}, headers=h2).status_code == 404
    assert client.delete(url, headers=h2).status_code == 404


# ------------------------------------------------------------------- sessions

def test_session_update_then_delete(env):
    client, _ = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    session = make_session(client, h, inst, std)
    url = f"/api/test-sessions/{session['test_session_id']}"

    r = client.put(url, json={"session_number": "S-99", "remarks": "recheck"}, headers=h)
    assert r.status_code == 200
    assert r.json()["session_number"] == "S-99" and r.json()["remarks"] == "recheck"

    # Explicitly clearing a text field works; a null link means "keep".
    r = client.put(url, json={"remarks": None, "instrument_id": None}, headers=h)
    assert r.json()["remarks"] is None and r.json()["instrument_id"] == inst["instrument_id"]

    assert client.delete(url, headers=h).status_code == 200
    assert client.get(url, headers=h).status_code == 404


def test_submitted_session_is_frozen(env):
    client, _ = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    session = make_session(client, h, inst, std)
    url = f"/api/test-sessions/{session['test_session_id']}"
    client.patch(f"{url}/status", json={"status": "SUBMITTED"}, headers=h)

    assert client.put(url, json={"remarks": "x"}, headers=h).status_code == 409
    assert client.delete(url, headers=h).status_code == 409


def test_changing_to_an_unknown_standard_is_404(env):
    client, _ = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    session = make_session(client, h, inst, std)
    url = f"/api/test-sessions/{session['test_session_id']}"

    r = client.put(url, json={"standard_id": str(uuid.uuid4())}, headers=h)
    assert r.status_code == 404  # standard does not exist


def test_deleting_a_session_removes_its_report_and_children(env):
    client, Db = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    session = make_session(client, h, inst, std)
    sid = uuid.UUID(session["test_session_id"])

    with Db() as db:
        db.add(Report(test_session_id=sid, report_number="R-1", report_status="GENERATED"))
        db.commit()

    assert client.delete(f"/api/test-sessions/{sid}", headers=h).status_code == 200
    with Db() as db:
        assert db.query(Report).filter(Report.test_session_id == sid).count() == 0


def test_session_with_approved_report_cannot_be_deleted(env):
    client, Db = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    session = make_session(client, h, inst, std)
    sid = uuid.UUID(session["test_session_id"])
    with Db() as db:
        db.add(Report(test_session_id=sid, report_number="R-1", report_status="APPROVED"))
        db.commit()

    r = client.delete(f"/api/test-sessions/{sid}", headers=h)
    assert r.status_code == 409 and "permanent" in r.json()["detail"]


# -------------------------------------------------------------------- reports

def seed_report(Db, session, status="GENERATED"):
    with Db() as db:
        report = Report(test_session_id=uuid.UUID(session["test_session_id"]),
                        report_number="R-1", report_status=status, overall_result="PASS")
        db.add(report)
        db.commit()
        return str(report.report_id)


def test_report_list_edit_and_delete(env):
    client, Db = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    session = make_session(client, h, inst, std)
    rid = seed_report(Db, session)

    listed = client.get("/api/reports", headers=h).json()
    assert [r["report_id"] for r in listed] == [rid] and listed[0]["session_number"] == "S-1"

    r = client.put(f"/api/reports/{rid}", json={"remarks": "checked"}, headers=h)
    assert r.status_code == 200 and r.json()["remarks"] == "checked"

    # Only remarks are editable; anything else is rejected, not ignored.
    assert client.put(f"/api/reports/{rid}", json={"report_status": "APPROVED"}, headers=h).status_code == 422

    assert client.delete(f"/api/reports/{rid}", headers=h).status_code == 200
    assert client.get("/api/reports", headers=h).json() == []


def test_approved_report_is_immutable(env):
    client, Db = env
    h = make_lab(client, 1)
    inst, std = make_instrument(client, h), make_standard(client, h)
    rid = seed_report(Db, make_session(client, h, inst, std), status="APPROVED")

    assert client.put(f"/api/reports/{rid}", json={"remarks": "x"}, headers=h).status_code == 409
    assert client.delete(f"/api/reports/{rid}", headers=h).status_code == 409


def test_reports_are_isolated_between_labs(env):
    client, Db = env
    h1, h2 = make_lab(client, 1), make_lab(client, 2)
    inst, std = make_instrument(client, h1), make_standard(client, h1)
    rid = seed_report(Db, make_session(client, h1, inst, std))

    assert client.get("/api/reports", headers=h2).json() == []
    assert client.delete(f"/api/reports/{rid}", headers=h2).status_code == 404


# ------------------------------------------------------------------ equipment

def test_equipment_update_and_delete(env):
    client, _ = env
    h = make_lab(client, 1)
    r = client.post("/api/test-equipment", json={"equipment_name": "Weight 10kg"}, headers=h)
    assert r.status_code in (200, 201), r.text
    url = f"/api/test-equipment/{r.json()['equipment_id']}"

    r = client.put(url, json={"equipment_name": "Weight 10kg E2", "calibration_status": "VALID"}, headers=h)
    assert r.status_code == 200 and r.json()["equipment_name"] == "Weight 10kg E2"

    assert client.put(url, json={"equipment_name": None}, headers=h).status_code == 422

    assert client.delete(url, headers=h).status_code == 200
