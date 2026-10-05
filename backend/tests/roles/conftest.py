"""
Fixtures for the role tests. A throw-away in-memory SQLite database is used
(the app is pointed at it before import), so backend/.env is never touched.
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("JWT_SECRET_KEY", "role-tests-secret")

import itertools  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import backend.app.models  # noqa: E402,F401
from backend.app.utils.security import pwd_context  # noqa: E402

pwd_context.update(bcrypt__rounds=4)   # tests only: hash quickly
from backend.app.database.connection import Base, get_db  # noqa: E402
from backend.app.main import app  # noqa: E402

PASSWORD = "Passw0rd!x"
_n = itertools.count(1)

ALL_ROLES = (
    "TECHNICAL_MANAGER", "QUALITY_MANAGER", "REVIEWER", "APPROVER", "TESTER",
    "ASSISTANT", "RECORDS_OFFICER", "STANDARDS_CUSTODIAN", "AUDITOR",
)

# a passing weighing-performance reading, and one that fails
# (10.01 on 10 kg would fail: OIML adds the 0.5 e rounding correction)
WP_PASS = {"measurements": [{"load": 10, "indication": 10.0, "additional_load": 0, "zero_error": 0}]}
WP_FAIL = {"measurements": [{"load": 10, "indication": 10.5, "additional_load": 0, "zero_error": 0}]}


class Person:
    def __init__(self, client, email, role):
        self.client, self.email, self.role = client, email, role
        r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        self.user_id = r.json()["user_id"]
        self.h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # tiny request helpers so tests read like sentences
    def get(self, url, **kw): return self.client.get(url, headers=self.h, **kw)
    def post(self, url, json=None, **kw): return self.client.post(url, headers=self.h, json=json, **kw)
    def put(self, url, json=None, **kw): return self.client.put(url, headers=self.h, json=json, **kw)
    def patch(self, url, json=None, **kw): return self.client.patch(url, headers=self.h, json=json, **kw)
    def delete(self, url, **kw): return self.client.delete(url, headers=self.h, **kw)


class Lab:
    """A laboratory with its Lab Head and one staff member per role."""

    def __init__(self, client):
        self.client = client
        n = next(_n)
        email = f"head{n}@lab{n}.example.com"
        r = client.post("/api/auth/register", json={
            "laboratory_code": f"LAB{n}", "laboratory_name": f"Lab {n}",
            "first_name": "Hema", "last_name": "Head", "email": email, "password": PASSWORD})
        assert r.status_code in (200, 201), r.text
        self.head = Person(client, email, "LAB_ADMIN")
        self.staff = {}
        for role in ALL_ROLES:
            self.add(role)

    def add(self, role, **extra):
        n = next(_n)
        email = f"{role.lower()}{n}@x.example.com"
        body = {"first_name": role.title().replace("_", " "), "email": email,
                "password": PASSWORD, "role": role}
        body.update(extra)
        r = self.head.post("/api/users", body)
        assert r.status_code == 201, r.text
        p = Person(self.client, email, role)
        self.staff.setdefault(role, p)
        return p

    def __getitem__(self, role):
        return self.head if role == "LAB_ADMIN" else self.staff[role]

    # ---- reference data the Lab Head sets up -------------------------------
    def standard_and_test(self, code="WP"):
        r = self.head.post("/api/standards", {"standard_code": "OIML R76", "title": "NAWI"})
        assert r.status_code in (200, 201), r.text
        std = r.json()
        r = self.head.post("/api/test-definitions", {
            "standard_id": std["standard_id"], "test_code": code,
            "test_name": "Weighing Performance", "calculation_type": "weighing_error",
            "is_mandatory": True})
        assert r.status_code in (200, 201), r.text
        return std, r.json()

    def instrument(self, who="RECORDS_OFFICER", **extra):
        body = {"instrument_code": f"I-{next(_n)}", "manufacturer": "ACME", "model": "X1",
                "accuracy_class": "III", "max_capacity": 30, "min_capacity": 0.2,
                "verification_scale_interval": 0.01, "scale_interval": 0.01, "unit": "kg"}
        body.update(extra)
        r = self[who].post("/api/instruments", body)
        assert r.status_code == 201, r.text
        return r.json()


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Maker = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override():
        db = Maker()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app), Maker
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture()
def lab(env):
    return Lab(env[0])


@pytest.fixture()
def ready(lab):
    """A lab with a standard, a WP test definition and an instrument on record."""
    std, td = lab.standard_and_test()
    inst = lab.instrument()
    return lab, std, td, inst


def new_session(lab, std, inst, who="TESTER", number=None):
    r = lab[who].post("/api/test-sessions", {
        "instrument_id": inst["instrument_id"], "standard_id": std["standard_id"],
        "session_number": number or f"S-{next(_n)}"})
    assert r.status_code == 201, r.text
    return r.json()["test_session_id"]


def calculated_session(lab, std, td, inst, inputs=WP_PASS, who="TESTER"):
    """Tester plans WP, calculates, and returns (session_id, session_test_id)."""
    sid = new_session(lab, std, inst, who)
    r = lab[who].post(f"/api/test-sessions/{sid}/tests", {"test_definition_id": td["test_definition_id"]})
    assert r.status_code == 201, r.text
    stid = r.json()["session_test_id"]
    r = lab[who].post(f"/api/test-sessions/{stid}/calculation-result", {"inputs": inputs})
    assert r.status_code == 201, r.text
    # "Start testing": DRAFT -> IN PROGRESS, as the tester does in the app
    r = lab[who].patch(f"/api/test-sessions/{sid}/status", {"status": "IN PROGRESS"})
    assert r.status_code == 200, r.text
    return sid, stid


def move(lab, who, sid, status, **extra):
    return lab[who].patch(f"/api/test-sessions/{sid}/status", {"status": status, **extra})
