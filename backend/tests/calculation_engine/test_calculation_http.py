from types import SimpleNamespace
from uuid import uuid4

# The route now requires the session's own tester (roles follow ISO 17025).
TESTER_ID = uuid4()

from fastapi.testclient import TestClient

from backend.app.database.connection import get_db
from backend.app.main import app
from backend.app.models.instrument import Instrument
from backend.app.models.test_calculation import TestCalculation
from backend.app.models.test_definition import TestDefinition
from backend.app.models.test_result import TestResult
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
from backend.app.utils.dependencies import get_current_user


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeDB:
    def __init__(self, objects):
        self.objects = objects
        self.added = []
        self.committed = False

    def query(self, model):
        return FakeQuery(self.objects.get(model))

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def refresh(self, obj):
        pass


def make_instrument(instrument_id, laboratory_id):
    return SimpleNamespace(
        instrument_id=instrument_id,
        laboratory_id=laboratory_id,
        instrument_code="NAWI-001",
        accuracy_class="III",
        max_capacity=30.0,
        min_capacity=0.2,
        verification_scale_interval=0.01,
        scale_interval=0.01,
        instrument_type="ELECTRONIC",
        indication_type="DIGITAL",
        tare_type="SEMI_AUTOMATIC_SUBTRACTIVE",
        power_supply="AC",
    )


def make_session(session_id, laboratory_id, instrument_id):
    return SimpleNamespace(
        test_session_id=session_id,
        laboratory_id=laboratory_id,
        instrument_id=instrument_id,
        tester_id=TESTER_ID,
        status="IN PROGRESS",
    )


def make_session_test(
    session_test_id,
    session_id,
    test_definition_id,
):
    return SimpleNamespace(
        session_test_id=session_test_id,
        test_session_id=session_id,
        test_definition_id=test_definition_id,
        result=None,
        status="PENDING",
    )


def make_test_definition(test_definition_id):
    return SimpleNamespace(
        test_definition_id=test_definition_id,
        test_code="WP",
        test_name="Weighing Performance",
        calculation_type="WEIGHING_PERFORMANCE",
        active=True,
    )


def make_user(laboratory_id):
    return SimpleNamespace(
        user_id=TESTER_ID,
        role="TESTER",
        authorization_scope=None,
        laboratory_id=laboratory_id,
    )


def test_http_calculation_endpoint_executes_successfully():
    laboratory_id = uuid4()
    instrument_id = uuid4()
    session_id = uuid4()
    session_test_id = uuid4()
    test_definition_id = uuid4()

    instrument = make_instrument(
        instrument_id=instrument_id,
        laboratory_id=laboratory_id,
    )

    session = make_session(
        session_id=session_id,
        laboratory_id=laboratory_id,
        instrument_id=instrument_id,
    )

    session_test = make_session_test(
        session_test_id=session_test_id,
        session_id=session_id,
        test_definition_id=test_definition_id,
    )

    test_definition = make_test_definition(
        test_definition_id=test_definition_id,
    )

    current_user = make_user(
        laboratory_id=laboratory_id,
    )

    fake_db = FakeDB(
        {
            TestSessionTest: session_test,
            TestSession: session,
            Instrument: instrument,
            TestDefinition: test_definition,
        }
    )

    def override_get_db():
        return fake_db

    def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)

    try:
        response = client.post(
            f"/api/test-sessions/{session_test_id}/calculation-result",
            json={
                "inputs": {
                    "measurements": [
                        {
                            "load": 10,
                            "indication": 10,
                            "additional_load": 0,
                            "zero_error": 0,
                        }
                    ]
                }
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, (
        f"Expected HTTP 201, got {response.status_code}: "
        f"{response.text}"
    )

    body = response.json()

    assert body["message"] == (
        "Calculation executed and result saved successfully"
    )

    assert body["test"]["test_code"] == "WP"
    assert body["test"]["test_name"] == "Weighing Performance"

    assert body["result"]["status"] == "PASS"
    assert body["result"]["pass_fail"] == "PASS"

    assert fake_db.committed is True
    assert session_test.status == "COMPLETED"
    assert session_test.result == "PASS"

    assert len(fake_db.added) == 2

    assert any(
        isinstance(obj, TestCalculation)
        for obj in fake_db.added
    )

    assert any(
        isinstance(obj, TestResult)
        for obj in fake_db.added
    )
