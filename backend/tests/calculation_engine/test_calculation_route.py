from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

# The route now requires the session's own tester (roles follow ISO 17025).
TESTER_ID = uuid4()

from backend.app.api.test_sessions.calculation_routes import (
    calculate_and_save_result,
)
from backend.app.models.instrument import Instrument
from backend.app.models.test_calculation import TestCalculation
from backend.app.models.test_definition import TestDefinition
from backend.app.models.test_result import TestResult
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.user import User
from backend.app.schemas.calculation import CalculationResultCreate


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


def make_session_test(session_test_id, session_id, test_definition_id):
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


def test_calculation_route_executes_engine_and_saves_result():
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

    db = FakeDB(
        {
            TestSessionTest: session_test,
            TestSession: session,
            Instrument: instrument,
            TestDefinition: test_definition,
        }
    )

    data = CalculationResultCreate(
        inputs={
            "measurements": [
                {
                    "load": Decimal("10"),
                    "indication": Decimal("10"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                }
            ]
        }
    )

    response = calculate_and_save_result(
        session_test_id=session_test_id,
        data=data,
        current_user=current_user,
        db=db,
    )

    assert db.committed is True

    assert session_test.status == "COMPLETED"
    assert session_test.result == "PASS"

    assert len(db.added) == 2

    calculation = next(
        obj
        for obj in db.added
        if isinstance(obj, TestCalculation)
    )

    result = next(
        obj
        for obj in db.added
        if isinstance(obj, TestResult)
    )

    assert calculation.session_test_id == session_test_id
    assert calculation.calculation_type == "WEIGHING_PERFORMANCE"
    assert calculation.calculation_version == "1.0.0"

    assert result.session_test_id == session_test_id
    assert result.pass_fail == "PASS"
    assert result.calculation_version == "1.0.0"

    assert response["test"]["test_code"] == "WP"
    assert response["test"]["test_name"] == "Weighing Performance"

    assert response["result"]["status"] == "PASS"
    assert response["result"]["pass_fail"] == "PASS"


def test_calculation_route_rejects_missing_session_test():
    laboratory_id = uuid4()
    session_test_id = uuid4()

    current_user = make_user(
        laboratory_id=laboratory_id,
    )

    db = FakeDB(
        {
            TestSessionTest: None,
            TestSession: None,
            Instrument: None,
            TestDefinition: None,
        }
    )

    data = CalculationResultCreate(
        inputs={}
    )

    try:
        calculate_and_save_result(
            session_test_id=session_test_id,
            data=data,
            current_user=current_user,
            db=db,
        )
    except Exception as exc:
        assert exc.status_code == 404
        assert exc.detail == "Session test not found"
    else:
        raise AssertionError(
            "Expected HTTPException for missing session test"
        )