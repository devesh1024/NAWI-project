from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.database.connection import get_db
from backend.app.main import app
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
        self.committed = False

    def query(self, model):
        return FakeQuery(self.objects.get(model))

    def add(self, obj):
        pass

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        pass

    def rollback(self):
        pass


def make_user(laboratory_id, user_id=None):
    return SimpleNamespace(
        user_id=user_id or uuid4(),
        laboratory_id=laboratory_id,
        role="TESTER",
        status="ACTIVE",
    )


def make_session(laboratory_id, tester_id):
    return SimpleNamespace(
        test_session_id=uuid4(),
        laboratory_id=laboratory_id,
        instrument_id=uuid4(),
        tester_id=tester_id,
        reviewer_id=None,
        standard_id=uuid4(),
        session_number="SESSION-001",
        application_number="APP-001",
        test_type="TYPE_EVALUATION",
        status="DRAFT",
        overall_result=None,
        remarks=None,
    )


def make_test(
    session_id,
    applicability_status="APPLICABLE",
    result=None,
    status="PENDING",
):
    return SimpleNamespace(
        session_test_id=uuid4(),
        test_session_id=session_id,
        test_definition_id=uuid4(),
        applicability_status=applicability_status,
        na_reason=None,
        status=status,
        result=result,
    )


def submit_session(session, tests):
    """
    Execute the session submission workflow using a fake DB.

    Tester workflow:
        DRAFT -> IN PROGRESS -> SUBMITTED
    """

    current_user = make_user(
        laboratory_id=session.laboratory_id,
        user_id=session.tester_id,
    )

    fake_db = FakeDB(
        {
            TestSession: session,
            TestSessionTest: tests,
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
        # Step 1: DRAFT -> IN PROGRESS
        response = client.patch(
            f"/api/test-sessions/"
            f"{session.test_session_id}/status",
            json={
                "status": "IN PROGRESS",
            },
        )

        assert response.status_code == 200
        assert session.status == "IN PROGRESS"

        # Step 2: IN PROGRESS -> SUBMITTED
        response = client.patch(
            f"/api/test-sessions/"
            f"{session.test_session_id}/status",
            json={
                "status": "SUBMITTED",
            },
        )

        return response, fake_db

    finally:
        app.dependency_overrides.clear()


def test_submit_session_with_all_tests_passed():
    laboratory_id = uuid4()
    tester_id = uuid4()

    session = make_session(
        laboratory_id=laboratory_id,
        tester_id=tester_id,
    )

    tests = [
        make_test(
            session.test_session_id,
            result="PASS",
            status="COMPLETED",
        ),
        make_test(
            session.test_session_id,
            result="PASS",
            status="COMPLETED",
        ),
    ]

    response, fake_db = submit_session(
        session,
        tests,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "SUBMITTED"
    assert body["overall_result"] == "PASS"

    assert session.status == "SUBMITTED"
    assert session.overall_result == "PASS"
    assert fake_db.committed is True


def test_submit_session_with_any_failed_test():
    laboratory_id = uuid4()
    tester_id = uuid4()

    session = make_session(
        laboratory_id=laboratory_id,
        tester_id=tester_id,
    )

    tests = [
        make_test(
            session.test_session_id,
            result="PASS",
            status="COMPLETED",
        ),
        make_test(
            session.test_session_id,
            result="FAIL",
            status="COMPLETED",
        ),
    ]

    response, fake_db = submit_session(
        session,
        tests,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "SUBMITTED"
    assert body["overall_result"] == "FAIL"

    assert session.status == "SUBMITTED"
    assert session.overall_result == "FAIL"
    assert fake_db.committed is True


def test_submit_session_with_incomplete_applicable_test():
    laboratory_id = uuid4()
    tester_id = uuid4()

    session = make_session(
        laboratory_id=laboratory_id,
        tester_id=tester_id,
    )

    tests = [
        make_test(
            session.test_session_id,
            result="PASS",
            status="COMPLETED",
        ),
        make_test(
            session.test_session_id,
            result=None,
            status="PENDING",
        ),
    ]

    response, fake_db = submit_session(
        session,
        tests,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "SUBMITTED"
    assert body["overall_result"] is None

    assert session.status == "SUBMITTED"
    assert session.overall_result is None
    assert fake_db.committed is True


def test_submit_session_with_only_not_applicable_tests():
    laboratory_id = uuid4()
    tester_id = uuid4()

    session = make_session(
        laboratory_id=laboratory_id,
        tester_id=tester_id,
    )

    tests = [
        make_test(
            session.test_session_id,
            applicability_status="NOT_APPLICABLE",
            result=None,
            status="PENDING",
        ),
        make_test(
            session.test_session_id,
            applicability_status="NOT_APPLICABLE",
            result=None,
            status="PENDING",
        ),
    ]

    response, fake_db = submit_session(
        session,
        tests,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "SUBMITTED"
    assert body["overall_result"] is None

    assert session.status == "SUBMITTED"
    assert session.overall_result is None
    assert fake_db.committed is True