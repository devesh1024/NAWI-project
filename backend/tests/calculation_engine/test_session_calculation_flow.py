from types import SimpleNamespace
from uuid import uuid4

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

    def all(self):
        if isinstance(self.result, list):
            return self.result
        return []


class FakeDB:
    def __init__(self, objects):
        self.objects = objects
        self.added = []
        self.committed = False

    def query(self, model):
        return FakeQuery(
            self.objects.get(model)
        )

    def add(self, obj):
        self.added.append(obj)

        # Simulate persistence of newly created objects.
        if isinstance(obj, TestSession):
            self.objects[TestSession] = obj

        elif isinstance(obj, TestSessionTest):
            self.objects[TestSessionTest] = obj

        elif isinstance(obj, TestCalculation):
            self.objects.setdefault(
                TestCalculation,
                []
            )
            self.objects[TestCalculation].append(obj)

        elif isinstance(obj, TestResult):
            self.objects.setdefault(
                TestResult,
                []
            )
            self.objects[TestResult].append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        """
        Simulate database-generated UUIDs.
        """

        if isinstance(obj, TestSession):
            if obj.test_session_id is None:
                obj.test_session_id = uuid4()

            self.objects[TestSession] = obj

        elif isinstance(obj, TestSessionTest):
            if obj.session_test_id is None:
                obj.session_test_id = uuid4()

            self.objects[TestSessionTest] = obj

        elif isinstance(obj, TestCalculation):
            if obj.calculation_id is None:
                obj.calculation_id = uuid4()

        elif isinstance(obj, TestResult):
            if obj.result_id is None:
                obj.result_id = uuid4()

    def rollback(self):
        pass


def make_user(laboratory_id):
    return SimpleNamespace(
        user_id=uuid4(),
        laboratory_id=laboratory_id,
        role="TESTER",
        status="ACTIVE",
    )


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


def make_test_definition(
    test_definition_id,
    standard_id,
):
    return SimpleNamespace(
        test_definition_id=test_definition_id,
        standard_id=standard_id,
        test_code="WP",
        test_name="Weighing Performance",
        calculation_type="WEIGHING_PERFORMANCE",
        active=True,
    )


def test_session_to_calculation_flow():
    laboratory_id = uuid4()
    tester_id = uuid4()
    instrument_id = uuid4()
    standard_id = uuid4()
    test_definition_id = uuid4()

    current_user = make_user(
        laboratory_id=laboratory_id,
    )

    current_user.user_id = tester_id

    instrument = make_instrument(
        instrument_id=instrument_id,
        laboratory_id=laboratory_id,
    )

    test_definition = make_test_definition(
        test_definition_id=test_definition_id,
        standard_id=standard_id,
    )

    fake_db = FakeDB(
        {
            Instrument: instrument,
            TestDefinition: test_definition,

            # Important:
            # TestSession and TestSessionTest are initially absent.
            TestSession: None,
            TestSessionTest: None,
        }
    )

    def override_get_db():
        return fake_db

    def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    client = TestClient(app)

    try:
        # ---------------------------------------------------------
        # 1. Create test session
        # ---------------------------------------------------------
        create_response = client.post(
            "/api/test-sessions",
            json={
                "instrument_id": str(instrument_id),
                "standard_id": str(standard_id),
                "session_number": "SESSION-001",
                "application_number": "APP-001",
                "test_type": "TYPE_EVALUATION",
                "remarks": "Integration test session",
            },
        )

        assert create_response.status_code == 201, (
            f"Expected session creation HTTP 201, "
            f"got {create_response.status_code}: "
            f"{create_response.text}"
        )

        created_session = create_response.json()

        assert created_session["test_session_id"] is not None
        assert created_session["laboratory_id"] == str(
            laboratory_id
        )
        assert created_session["instrument_id"] == str(
            instrument_id
        )
        assert created_session["standard_id"] == str(
            standard_id
        )
        assert created_session["status"] == "DRAFT"

        created_session_id = created_session[
            "test_session_id"
        ]

        # ---------------------------------------------------------
        # 2. Add WP test to the session
        # ---------------------------------------------------------
        add_test_response = client.post(
            f"/api/test-sessions/{created_session_id}/tests",
            json={
                "test_definition_id": str(test_definition_id),
                "applicability_status": "APPLICABLE",
            },
        )

        assert add_test_response.status_code == 201, (
            f"Expected test creation HTTP 201, "
            f"got {add_test_response.status_code}: "
            f"{add_test_response.text}"
        )

        added_test = add_test_response.json()

        assert added_test["test_definition_id"] == str(
            test_definition_id
        )
        assert added_test["status"] == "PENDING"
        assert added_test["applicability_status"] == "APPLICABLE"

        created_session_test_id = added_test[
            "session_test_id"
        ]

        # ---------------------------------------------------------
        # 3. Execute WP calculation
        # ---------------------------------------------------------
        calculation_response = client.post(
            f"/api/test-sessions/"
            f"{created_session_test_id}/calculation-result",
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

        assert calculation_response.status_code == 201, (
            f"Expected calculation HTTP 201, "
            f"got {calculation_response.status_code}: "
            f"{calculation_response.text}"
        )

        body = calculation_response.json()

        # ---------------------------------------------------------
        # 4. Verify calculation result
        # ---------------------------------------------------------
        assert body["test"]["test_code"] == "WP"
        assert body["test"]["test_name"] == (
            "Weighing Performance"
        )

        assert body["result"]["status"] == "PASS"
        assert body["result"]["pass_fail"] == "PASS"

        # ---------------------------------------------------------
        # 5. Verify session-test state
        # ---------------------------------------------------------
        created_session_test = fake_db.objects[
            TestSessionTest
        ]

        assert created_session_test.status == "COMPLETED"
        assert created_session_test.result == "PASS"

        # ---------------------------------------------------------
        # 6. Verify persistence
        # ---------------------------------------------------------
        assert fake_db.committed is True

        assert any(
            isinstance(obj, TestCalculation)
            for obj in fake_db.added
        )

        assert any(
            isinstance(obj, TestResult)
            for obj in fake_db.added
        )

    finally:
        app.dependency_overrides.clear()