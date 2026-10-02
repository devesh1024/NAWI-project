import time

import pytest
import requests
import socketio

from backend.tests.chat.conftest import Peer
from backend.tests.chat.test_chat_rest import open_chat


def test_unauthenticated_socket_is_refused(live_server):
    for auth in (None, {}, {"token": "garbage"}):
        c = socketio.Client(reconnection=False)
        with pytest.raises(socketio.exceptions.ConnectionError):
            c.connect(live_server, auth=auth, transports=["websocket"], wait_timeout=3)


def test_deactivated_user_cannot_connect(people, live_server):
    from backend.app.database.connection import SessionLocal
    from backend.app.models.user import User
    with SessionLocal() as db:
        db.query(User).filter(User.email == "tara@lab1.com").update({"status": "INACTIVE"})
        db.commit()
    c = socketio.Client(reconnection=False)
    with pytest.raises(socketio.exceptions.ConnectionError):
        c.connect(live_server, auth={"token": people["tara"].token}, transports=["websocket"], wait_timeout=3)


def test_message_reaches_both_ends_in_real_time(people, peers):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    p_ada, p_tara = peers(ada), peers(tara)

    t0 = time.time()
    ack = p_ada.emit("message:send", {"conversation_id": cid, "body": "Hello Tara", "client_id": "c-1"})
    assert ack["ok"] and ack["message"]["body"] == "Hello Tara" and ack["client_id"] == "c-1"

    got = p_tara.wait("message:new")                                  # recipient, pushed
    assert time.time() - t0 < 2
    assert got["message"]["body"] == "Hello Tara" and got["message"]["sender_id"] == ada.user_id
    assert got["conversation"]["other_user"]["name"] == "Ada" and got["conversation"]["unread_count"] == 1
    assert "client_id" not in got                                      # only the sender sees its own client_id

    echo = p_ada.wait("message:new")                                   # sender's room also updated (other tabs)
    assert echo["client_id"] == "c-1" and echo["conversation"]["unread_count"] == 0

    # reply the other way
    p_tara.emit("message:send", {"conversation_id": cid, "body": "Hi Ada!", "client_id": "c-2"})
    assert p_ada.wait("message:new")["message"]["body"] == "Hi Ada!"

    # persisted, and visible through REST
    msgs = ada.client.get(f"/api/chat/conversations/{cid}/messages", headers=ada.headers).json()["messages"]
    assert [m["body"] for m in msgs] == ["Hello Tara", "Hi Ada!"]


def test_first_message_creates_unknown_conversation_on_recipient_side(people, peers):
    ada, tara = people["ada"], people["tara"]
    p_tara = peers(tara)
    cid = open_chat(ada, tara)["conversation_id"]            # Tara has not fetched anything yet
    peers(ada).emit("message:send", {"conversation_id": cid, "body": "ping"})
    got = p_tara.wait("message:new")
    assert got["conversation"]["conversation_id"] == cid and got["conversation"]["other_user"]["user_id"] == ada.user_id


def test_read_receipts(people, peers):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    p_ada, p_tara = peers(ada), peers(tara)
    ack = p_ada.emit("message:send", {"conversation_id": cid, "body": "read me"})
    p_tara.wait("message:new")

    res = p_tara.emit("message:read", {"conversation_id": cid})
    assert res["ok"] and res["message_ids"] == [ack["message"]["message_id"]]
    receipt = p_ada.wait("message:read")
    assert receipt["conversation_id"] == cid and receipt["reader_id"] == tara.user_id
    assert receipt["message_ids"] == [ack["message"]["message_id"]]

    assert p_tara.emit("message:read", {"conversation_id": cid})["message_ids"] == []   # idempotent
    assert p_ada.silent("message:read")


def test_typing_indicator_is_relayed_to_the_other_person_only(people, peers):
    ada, tara, rey = people["ada"], people["tara"], people["rey"]
    cid = open_chat(ada, tara)["conversation_id"]
    p_ada, p_tara, p_rey = peers(ada), peers(tara), peers(rey)
    p_ada.sio.emit("typing", {"conversation_id": cid, "is_typing": True})
    ev = p_tara.wait("typing")
    assert ev == {"conversation_id": cid, "user_id": ada.user_id, "is_typing": True}
    assert p_rey.silent("typing") and p_ada.silent("typing")


def test_outsider_cannot_send_or_spy(people, peers):
    ada, tara, rey = people["ada"], people["tara"], people["rey"]
    cid = open_chat(ada, tara)["conversation_id"]
    p_ada, p_tara, p_rey = peers(ada), peers(tara), peers(rey)

    res = p_rey.emit("message:send", {"conversation_id": cid, "body": "intruder"})
    assert res["ok"] is False
    p_ada.emit("message:send", {"conversation_id": cid, "body": "secret"})
    p_tara.wait("message:new")
    assert p_rey.silent("message:new")
    assert p_rey.emit("message:read", {"conversation_id": cid})["ok"] is False


def test_bad_payloads_are_rejected_not_crashed(people, peers):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    p = peers(ada)
    for bad in (None, "x", {}, {"conversation_id": "nope", "body": "x"},
                {"conversation_id": cid, "body": ""}, {"conversation_id": cid, "body": "x" * 5000}):
        assert p.emit("message:send", bad)["ok"] is False
    assert p.emit("message:send", {"conversation_id": cid, "body": "still alive"})["ok"] is True


def test_rate_limit(people, peers):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    p = peers(ada)
    results = [p.emit("message:send", {"conversation_id": cid, "body": f"m{i}"})["ok"] for i in range(25)]
    assert results[:20] == [True] * 20 and results[20:] == [False] * 5


def test_presence(people, peers):
    ada, tara = people["ada"], people["tara"]
    open_chat(ada, tara)
    p_ada = peers(ada)
    p_tara = peers(tara)
    assert p_ada.wait("presence") == {"user_id": tara.user_id, "online": True}
    assert p_ada.emit("presence:query", {"user_ids": [tara.user_id, "zzz"]}) == {"online": [tara.user_id]}
    p_tara.close()
    assert p_ada.wait("presence") == {"user_id": tara.user_id, "online": False}


def test_rest_send_is_also_pushed_live(people, peers):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    p_tara = peers(tara)
    r = ada.client.post(f"/api/chat/conversations/{cid}/messages", headers=ada.headers, json={"body": "via http"})
    assert r.status_code == 201
    # TestClient runs the app in a different loop than the live server, so push through the live HTTP API
    # is covered below; here we only assert the message is stored.
    assert ada.client.get(f"/api/chat/conversations/{cid}/messages", headers=ada.headers).json()["messages"][0]["body"] == "via http"


def test_live_http_send_and_read_push_over_socket(people, peers, live_server):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    p_ada, p_tara = peers(ada), peers(tara)
    r = requests.post(f"{live_server}/api/chat/conversations/{cid}/messages", headers=ada.headers, json={"body": "via http"})
    assert r.status_code == 201
    assert p_tara.wait("message:new")["message"]["body"] == "via http"
    r = requests.post(f"{live_server}/api/chat/conversations/{cid}/read", headers=tara.headers)
    assert r.status_code == 200
    assert p_ada.wait("message:read")["message_ids"] == [r.json()["message_ids"][0]]


def test_long_polling_fallback_works(people, peers):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    p_ada, p_tara = peers(ada, transports=("polling",)), peers(tara, transports=("polling",))
    p_ada.emit("message:send", {"conversation_id": cid, "body": "over polling"})
    assert p_tara.wait("message:new", timeout=5)["message"]["body"] == "over polling"


def test_cors_headers_not_duplicated(live_server):
    r = requests.get(f"{live_server}/socket.io/", params={"EIO": "4", "transport": "polling"},
                     headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"      # one value, not "a, a"
    evil = requests.get(f"{live_server}/socket.io/", params={"EIO": "4", "transport": "polling"},
                        headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers
