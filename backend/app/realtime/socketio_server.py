# backend/app/realtime/socketio_server.py
"""
Socket.IO server for TeamDesk.

Every connection must present a valid login JWT in the handshake
(`auth: { token }`). The server joins the socket to a private room named
`user:<user_id>`; all pushes are addressed to those rooms, so a user's
other tabs/devices stay in sync and nobody can listen in on someone else.

Client -> server            Server -> client
------------------------    ------------------------------------------------
message:send  (ack)         message:new   {message, conversation, client_id?}
message:read  (ack)         message:read  {conversation_id, reader_id, message_ids}
typing                      typing        {conversation_id, user_id, is_typing}
presence:query (ack)        presence      {user_id, online}

State (presence, rate limits) is held in memory, so run ONE server process.
To scale out, give AsyncServer a Redis `client_manager`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any, Callable
from uuid import UUID

import socketio
from jose import JWTError, jwt

from backend.app.database.connection import SessionLocal
from backend.app.models.user import User
from backend.app.services import chat_service as chat
from backend.app.utils.security import ALGORITHM, SECRET_KEY

# CORS is handled once, by the FastAPI CORSMiddleware that wraps this app
# (see main.py). `[]` stops Socket.IO adding a second, duplicate header.
# Authentication is the JWT in the handshake, not cookies, so a cross-site page
# cannot open a usable socket on a visitor's behalf.
logger = logging.getLogger("uvicorn.error")

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[])

SEND_LIMIT = 20        # messages ...
SEND_WINDOW = 10.0     # ... per this many seconds, per connection

_online: dict[str, set[str]] = defaultdict(set)      # user_id -> {sid}
_send_times: dict[str, deque] = defaultdict(deque)   # sid -> timestamps


def user_room(user_id: str | UUID) -> str:
    return f"user:{user_id}"


async def _db(fn: Callable[[Any], Any]):
    """Run blocking DB work on a worker thread with its own session."""

    def runner():
        with SessionLocal() as db:
            return fn(db)

    return await asyncio.to_thread(runner)


def _decode(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        UUID(str(payload.get("user_id")))
        return payload
    except (JWTError, ValueError, TypeError):
        return None


async def _session(sid: str) -> dict | None:
    """The authenticated session for a socket, or None if it has expired."""
    data = await sio.get_session(sid)
    if not data or data.get("exp", 0) <= time.time():
        await sio.emit("auth:expired", room=sid)
        await sio.disconnect(sid)
        return None
    return data


def _partner_ids(db, user_id: UUID) -> list[str]:
    ids = set()
    for c in chat.list_conversations(db, _Ref(user_id)):
        ids.add(c["other_user"]["user_id"])
    return list(ids)


class _Ref:
    """Minimal stand-in for a User when only the id is needed."""

    def __init__(self, user_id: UUID):
        self.user_id = user_id


async def _announce_presence(user_id: str, online: bool) -> None:
    """Tell the user's chat partners they came online/went offline (best effort)."""
    try:
        partners = await _db(lambda db: _partner_ids(db, UUID(user_id)))
        for partner in partners:
            await sio.emit(
                "presence", {"user_id": user_id, "online": online}, room=user_room(partner)
            )
    except Exception:  # presence is cosmetic; never let it break a connection
        logger.exception("presence announcement failed for %s", user_id)


# ---------------------------------------------------------------- connection
@sio.event
async def connect(sid, environ, auth):
    token = auth.get("token") if isinstance(auth, dict) else None
    payload = _decode(token)

    if not payload:
        raise socketio.exceptions.ConnectionRefusedError("unauthorized")

    user = await _db(
        lambda db: (
            lambda u: None if u is None else {"status": u.status}
        )(db.query(User).filter(User.user_id == UUID(payload["user_id"])).first())
    )

    if not user or user["status"] != "ACTIVE":
        raise socketio.exceptions.ConnectionRefusedError("unauthorized")

    user_id = payload["user_id"]
    await sio.save_session(sid, {"user_id": user_id, "exp": payload.get("exp", 0)})
    await sio.enter_room(sid, user_room(user_id))

    first_connection = not _online[user_id]
    _online[user_id].add(sid)

    if first_connection:
        await _announce_presence(user_id, True)


@sio.event
async def disconnect(sid):
    _send_times.pop(sid, None)

    for user_id, sids in list(_online.items()):
        if sid in sids:
            sids.discard(sid)
            if not sids:
                _online.pop(user_id, None)
                await _announce_presence(user_id, False)
            break


# ------------------------------------------------------------------ messages
def _build_payloads(db, message_id: UUID) -> dict:
    """Per-viewer payloads, because 'the other person' differs for each side."""
    from backend.app.models.chat import ChatConversation, ChatMessage

    message = db.query(ChatMessage).filter(ChatMessage.message_id == message_id).first()
    conversation = (
        db.query(ChatConversation)
        .filter(ChatConversation.conversation_id == message.conversation_id)
        .first()
    )
    body = chat.serialize_message(message)
    return {
        str(viewer): {
            "message": body,
            "conversation": chat.conversation_summary(db, conversation, viewer),
        }
        for viewer in (conversation.user_one_id, conversation.user_two_id)
    }


async def publish_message(message_id: UUID, sender_id: str, client_id: str | None = None):
    """Push a stored message to both participants (used by sockets and REST)."""
    payloads = await _db(lambda db: _build_payloads(db, message_id))

    for viewer, payload in payloads.items():
        event = dict(payload)
        if viewer == str(sender_id) and client_id:
            event["client_id"] = client_id
        await sio.emit("message:new", event, room=user_room(viewer))


async def publish_read(conversation_id: str, reader_id: str, other_id: str, message_ids: list[str]):
    if not message_ids:
        return
    await sio.emit(
        "message:read",
        {
            "conversation_id": conversation_id,
            "reader_id": reader_id,
            "message_ids": message_ids,
        },
        room=user_room(other_id),
    )


def _too_fast(sid: str) -> bool:
    now = time.monotonic()
    times = _send_times[sid]
    while times and now - times[0] > SEND_WINDOW:
        times.popleft()
    if len(times) >= SEND_LIMIT:
        return True
    times.append(now)
    return False


@sio.on("message:send")
async def on_message_send(sid, data=None):
    session = await _session(sid)
    if not session:
        return {"ok": False, "error": "Session expired. Please sign in again."}

    if not isinstance(data, dict):
        return {"ok": False, "error": "Invalid request"}

    if _too_fast(sid):
        return {"ok": False, "error": "You are sending messages too quickly. Please slow down."}

    user_id = UUID(session["user_id"])

    def store(db):
        me = db.query(User).filter(User.user_id == user_id).first()
        if not me or me.status != "ACTIVE":
            raise chat.ChatError("Account is not active", 403)
        conversation = chat.get_conversation_for_user(
            db, UUID(str(data.get("conversation_id"))), user_id
        )
        message = chat.send_message(db, conversation, me, data.get("body"))
        return message.message_id, str(message.conversation_id)

    try:
        message_id, _ = await _db(store)
    except chat.ChatError as exc:
        return {"ok": False, "error": exc.message}
    except (ValueError, TypeError):
        return {"ok": False, "error": "Invalid conversation"}

    client_id = data.get("client_id") if isinstance(data.get("client_id"), str) else None
    await publish_message(message_id, session["user_id"], client_id)

    stored = await _db(lambda db: chat.serialize_message(_fetch_message(db, message_id)))
    return {"ok": True, "message": stored, "client_id": client_id}


def _fetch_message(db, message_id):
    from backend.app.models.chat import ChatMessage

    return db.query(ChatMessage).filter(ChatMessage.message_id == message_id).first()


@sio.on("message:read")
async def on_message_read(sid, data=None):
    session = await _session(sid)
    if not session or not isinstance(data, dict):
        return {"ok": False}

    user_id = UUID(session["user_id"])

    def mark(db):
        conversation = chat.get_conversation_for_user(
            db, UUID(str(data.get("conversation_id"))), user_id
        )
        ids = chat.mark_read(db, conversation, user_id)
        return ids, str(chat.other_participant_id(conversation, user_id)), str(
            conversation.conversation_id
        )

    try:
        ids, other_id, conversation_id = await _db(mark)
    except (chat.ChatError, ValueError, TypeError):
        return {"ok": False}

    await publish_read(conversation_id, session["user_id"], other_id, ids)
    return {"ok": True, "message_ids": ids}


@sio.on("typing")
async def on_typing(sid, data=None):
    session = await _session(sid)
    if not session or not isinstance(data, dict):
        return

    user_id = UUID(session["user_id"])

    def other(db):
        conversation = chat.get_conversation_for_user(
            db, UUID(str(data.get("conversation_id"))), user_id
        )
        return str(chat.other_participant_id(conversation, user_id)), str(
            conversation.conversation_id
        )

    try:
        other_id, conversation_id = await _db(other)
    except (chat.ChatError, ValueError, TypeError):
        return

    await sio.emit(
        "typing",
        {
            "conversation_id": conversation_id,
            "user_id": session["user_id"],
            "is_typing": bool(data.get("is_typing")),
        },
        room=user_room(other_id),
    )


@sio.on("presence:query")
async def on_presence_query(sid, data=None):
    session = await _session(sid)
    if not session:
        return {"online": []}

    ids = data.get("user_ids", []) if isinstance(data, dict) else []
    return {"online": [u for u in ids if isinstance(u, str) and u in _online][:200]}
