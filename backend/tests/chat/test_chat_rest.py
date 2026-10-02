import pytest

from backend.app.database.connection import SessionLocal
from backend.app.models.user import User
from backend.tests.chat.conftest import login


def open_chat(a, b):
    r = a.client.post("/api/chat/conversations", headers=a.headers, json={"user_id": b.user_id})
    assert r.status_code == 200, r.text
    return r.json()


def send(a, cid, body):
    return a.client.post(f"/api/chat/conversations/{cid}/messages", headers=a.headers, json={"body": body})


# ------------------------------------------------------------------ people search
def test_endpoints_require_login(client):
    for path in ("/api/chat/users?q=a", "/api/chat/conversations", "/api/chat/notifications"):
        assert client.get(path).status_code in (401, 403)


def test_search_finds_users_across_labs_and_excludes_self(people, client):
    ada = people["ada"]
    r = client.get("/api/chat/users", params={"q": "tara"}, headers=ada.headers).json()
    assert [u["name"] for u in r] == ["Tara Singh"] and r[0]["role"] == "TESTER"
    assert r[0]["laboratory_name"] == "Lab 1"

    r = client.get("/api/chat/users", params={"q": "bo"}, headers=ada.headers).json()   # other lab
    assert any(u["name"] == "Bo" and u["laboratory_name"] == "Lab 2" for u in r)

    names = [u["name"] for u in client.get("/api/chat/users", params={"q": "@lab"}, headers=ada.headers).json()]
    assert "Ada" not in names and {"Tara Singh", "Rey Das", "Bo"} <= set(names)

    assert client.get("/api/chat/users", params={"q": ""}, headers=ada.headers).json() == []
    assert client.get("/api/chat/users", params={"q": "Singh"}, headers=ada.headers).json()[0]["name"] == "Tara Singh"
    assert "password_hash" not in str(r)


def test_search_hides_inactive_users(people, client):
    with SessionLocal() as db:
        db.query(User).filter(User.email == "rey@lab1.com").update({"status": "INACTIVE"})
        db.commit()
    assert client.get("/api/chat/users", params={"q": "rey"}, headers=people["ada"].headers).json() == []


def test_lab_scope_setting_restricts_to_own_lab(people, client, monkeypatch):
    monkeypatch.setenv("CHAT_SCOPE", "lab")
    ada = people["ada"]
    names = [u["name"] for u in client.get("/api/chat/users", params={"q": "@lab"}, headers=ada.headers).json()]
    assert "Bo" not in names and "Tara Singh" in names
    r = client.post("/api/chat/conversations", headers=ada.headers, json={"user_id": people["bo"].user_id})
    assert r.status_code == 404


# ------------------------------------------------------------------ conversations
def test_conversation_is_shared_and_idempotent(people):
    ada, tara = people["ada"], people["tara"]
    a = open_chat(ada, tara)
    assert open_chat(ada, tara)["conversation_id"] == a["conversation_id"]
    b = open_chat(tara, ada)                                  # started from the other side
    assert b["conversation_id"] == a["conversation_id"]
    assert b["other_user"]["name"] == "Ada" and a["other_user"]["name"] == "Tara Singh"


def test_cannot_chat_with_self_or_unknown_user(people):
    ada = people["ada"]
    assert ada.client.post("/api/chat/conversations", headers=ada.headers, json={"user_id": ada.user_id}).status_code == 400
    r = ada.client.post("/api/chat/conversations", headers=ada.headers,
                        json={"user_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404


def test_cross_lab_conversation_works_by_default(people):
    assert open_chat(people["ada"], people["bo"])["other_user"]["laboratory_name"] == "Lab 2"


# ------------------------------------------------------------------ messages
def test_send_list_unread_and_read(people):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]

    assert send(ada, cid, "  Hello Tara  ").status_code == 201
    assert send(ada, cid, "Report ready?").status_code == 201

    msgs = tara.client.get(f"/api/chat/conversations/{cid}/messages", headers=tara.headers).json()
    assert [m["body"] for m in msgs["messages"]] == ["Hello Tara", "Report ready?"]   # trimmed, in order
    assert msgs["has_more"] is False and all(m["read_at"] is None for m in msgs["messages"])

    row = tara.client.get("/api/chat/conversations", headers=tara.headers).json()[0]
    assert row["unread_count"] == 2 and row["last_message"]["body"] == "Report ready?"
    sender_row = ada.client.get("/api/chat/conversations", headers=ada.headers).json()[0]
    assert sender_row["unread_count"] == 0                                     # own messages never unread

    note = tara.client.get("/api/chat/notifications", headers=tara.headers).json()
    assert note["unread_total"] == 2 and note["items"][0]["other_user"]["name"] == "Ada"

    r = tara.client.post(f"/api/chat/conversations/{cid}/read", headers=tara.headers).json()
    assert len(r["message_ids"]) == 2
    assert tara.client.get("/api/chat/notifications", headers=tara.headers).json()["unread_total"] == 0
    msgs = ada.client.get(f"/api/chat/conversations/{cid}/messages", headers=ada.headers).json()
    assert all(m["read_at"] for m in msgs["messages"])


def test_message_validation(people):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    assert send(ada, cid, "   ").status_code == 422
    assert send(ada, cid, "x" * 2001).status_code == 422
    assert send(ada, cid, "x" * 2000).status_code == 201


def test_pagination(people):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    for i in range(1, 8):
        send(ada, cid, f"m{i}")
    page = ada.client.get(f"/api/chat/conversations/{cid}/messages", params={"limit": 3}, headers=ada.headers).json()
    assert [m["body"] for m in page["messages"]] == ["m5", "m6", "m7"] and page["has_more"] is True
    older = ada.client.get(f"/api/chat/conversations/{cid}/messages",
                           params={"limit": 3, "before": page["messages"][0]["created_at"]}, headers=ada.headers).json()
    assert [m["body"] for m in older["messages"]] == ["m2", "m3", "m4"] and older["has_more"] is True


def test_outsiders_cannot_read_or_write(people):
    ada, tara, rey = people["ada"], people["tara"], people["rey"]
    cid = open_chat(ada, tara)["conversation_id"]
    send(ada, cid, "private")
    assert rey.client.get(f"/api/chat/conversations/{cid}/messages", headers=rey.headers).status_code == 404
    assert send(rey, cid, "hi").status_code == 404
    assert rey.client.post(f"/api/chat/conversations/{cid}/read", headers=rey.headers).status_code == 404
    assert rey.client.get("/api/chat/conversations", headers=rey.headers).json() == []


def test_cannot_message_deactivated_user(people):
    ada, tara = people["ada"], people["tara"]
    cid = open_chat(ada, tara)["conversation_id"]
    with SessionLocal() as db:
        db.query(User).filter(User.email == "tara@lab1.com").update({"status": "INACTIVE"})
        db.commit()
    assert send(ada, cid, "hello?").status_code == 409


def test_conversation_list_sorted_by_latest_activity(people):
    ada = people["ada"]
    c1 = open_chat(ada, people["tara"])["conversation_id"]
    c2 = open_chat(ada, people["rey"])["conversation_id"]
    send(ada, c1, "first"); send(ada, c2, "second")
    assert [r["conversation_id"] for r in ada.client.get("/api/chat/conversations", headers=ada.headers).json()] == [c2, c1]
    send(ada, c1, "bump")
    assert ada.client.get("/api/chat/conversations", headers=ada.headers).json()[0]["conversation_id"] == c1
