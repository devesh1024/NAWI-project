"""
Chat test bootstrap. Always uses a throw-away database (never backend/.env's).
Set TEST_DATABASE_URL to run against PostgreSQL instead of SQLite.
"""
import os
import queue
import socket
import tempfile
import threading
import time

_db_file = os.path.join(tempfile.mkdtemp(prefix="nawi-chat-tests-"), "test.db")
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", f"sqlite:///{_db_file}")
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ.pop("CHAT_SCOPE", None)

import pytest  # noqa: E402
import socketio  # noqa: E402
import uvicorn  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.app.models  # noqa: E402,F401
from backend.app.database.connection import Base, SessionLocal, engine  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


class Person:
    def __init__(self, client, email, user_id, token, role):
        self.client, self.email, self.user_id, self.token, self.role = client, email, user_id, token, role

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}


def register_lab(client, n, name="Ada", last=None):
    email = f"admin{n}@lab{n}.com"
    r = client.post("/api/auth/register", json=dict(
        laboratory_code=f"LAB{n}", laboratory_name=f"Lab {n}", first_name=name,
        email=email, password="password123"))
    assert r.status_code == 200, r.text
    return login(client, email)


def login(client, email):
    r = client.post("/api/auth/login", json=dict(email=email, password="password123"))
    assert r.status_code == 200, r.text
    d = r.json()
    return Person(client, email, d["user_id"], d["access_token"], d["role"])


def add_user(admin, email, first, role="TESTER", last=None):
    r = admin.client.post("/api/users", headers=admin.headers, json=dict(
        first_name=first, last_name=last, email=email, password="password123", role=role))
    assert r.status_code == 201, r.text
    return login(admin.client, email)


@pytest.fixture
def people(client):
    """Admin of lab 1 (Ada), tester in lab 1 (Tara), reviewer in lab 1 (Rey), admin of lab 2 (Bo)."""
    ada = register_lab(client, 1, "Ada")
    tara = add_user(ada, "tara@lab1.com", "Tara", "TESTER", "Singh")
    rey = add_user(ada, "rey@lab1.com", "Rey", "REVIEWER", "Das")
    bo = register_lab(client, 2, "Bo")
    return dict(ada=ada, tara=tara, rey=rey, bo=bo)


# ------------------------------------------------------------------ live server
@pytest.fixture(scope="session")
def live_server():
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


class Peer:
    """A Socket.IO client that records every event it receives."""

    def __init__(self, url, person, transports=("websocket",)):
        self.events = queue.Queue()
        self.sio = socketio.Client(reconnection=False)
        for name in ("message:new", "message:read", "typing", "presence", "auth:expired"):
            self.sio.on(name, self._recorder(name))
        self.sio.connect(url, auth={"token": person.token}, transports=list(transports), wait_timeout=5)

    def _recorder(self, name):
        return lambda data=None: self.events.put((name, data))

    def emit(self, event, data):
        return self.sio.call(event, data, timeout=5)

    def wait(self, name, timeout=3):
        end = time.time() + timeout
        while time.time() < end:
            try:
                got, data = self.events.get(timeout=0.2)
            except queue.Empty:
                continue
            if got == name:
                return data
        raise AssertionError(f"no '{name}' event within {timeout}s")

    def silent(self, name, timeout=0.6):
        end = time.time() + timeout
        while time.time() < end:
            try:
                got, _ = self.events.get(timeout=0.1)
            except queue.Empty:
                continue
            if got == name:
                return False
        return True

    def close(self):
        if self.sio.connected:
            self.sio.disconnect()


@pytest.fixture
def peers(live_server):
    made = []

    def make(person, **kw):
        p = Peer(live_server, person, **kw)
        made.append(p)
        return p

    yield make
    for p in made:
        p.close()
