# backend/app/services/chat_service.py
"""
Business rules for TeamDesk chat. Everything here is synchronous and takes a
SQLAlchemy session; the REST routes and the Socket.IO handlers both call it,
so a message is validated and stored the same way whichever door it came in by.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from backend.app.models.chat import ChatConversation, ChatMessage
from backend.app.models.laboratory import Laboratory
from backend.app.models.user import User

MAX_MESSAGE_LENGTH = 2000
PAGE_SIZE = 50
SEARCH_LIMIT = 20


class ChatError(Exception):
    """A chat rule was broken. `status` maps to the HTTP status code."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def chat_scope() -> str:
    """'all' (default): anyone can message anyone. 'lab': own laboratory only."""
    return "lab" if os.getenv("CHAT_SCOPE", "all").strip().lower() == "lab" else "all"


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:  # SQLite hands back naive datetimes
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def full_name(user: User) -> str:
    name = " ".join(p for p in (user.first_name, user.last_name) if p).strip()
    return name or user.email


def serialize_user(user: User, lab_name: str | None = None) -> dict:
    return {
        "user_id": str(user.user_id),
        "name": full_name(user),
        "email": user.email,
        "role": user.role,
        "designation": user.designation,
        "laboratory_id": str(user.laboratory_id),
        "laboratory_name": lab_name,
    }


def serialize_message(message: ChatMessage) -> dict:
    return {
        "message_id": str(message.message_id),
        "conversation_id": str(message.conversation_id),
        "sender_id": str(message.sender_id),
        "body": message.body,
        "created_at": iso(message.created_at),
        "read_at": iso(message.read_at),
    }


def _lab_name(db: Session, laboratory_id) -> str | None:
    lab = db.query(Laboratory).filter(Laboratory.laboratory_id == laboratory_id).first()
    return lab.name if lab else None


def _pair(a: UUID, b: UUID) -> tuple[UUID, UUID]:
    return (a, b) if str(a) < str(b) else (b, a)


def other_participant_id(conversation: ChatConversation, me: UUID) -> UUID:
    return (
        conversation.user_two_id
        if conversation.user_one_id == me
        else conversation.user_one_id
    )


def _can_reach(me: User, other: User) -> bool:
    return chat_scope() == "all" or me.laboratory_id == other.laboratory_id


# --------------------------------------------------------------------------
# people
# --------------------------------------------------------------------------
def search_users(db: Session, me: User, query: str) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []

    pattern = f"%{query.lower()}%"
    full = func.lower(
        func.coalesce(User.first_name, "") + " " + func.coalesce(User.last_name, "")
    )

    q = (
        db.query(User, Laboratory.name)
        .outerjoin(Laboratory, Laboratory.laboratory_id == User.laboratory_id)
        .filter(User.user_id != me.user_id, User.status == "ACTIVE")
        .filter(
            or_(
                full.like(pattern),
                func.lower(User.email).like(pattern),
                func.lower(func.coalesce(User.employee_id, "")).like(pattern),
            )
        )
    )

    if chat_scope() == "lab":
        q = q.filter(User.laboratory_id == me.laboratory_id)

    rows = q.order_by(User.first_name, User.last_name).limit(SEARCH_LIMIT).all()
    return [serialize_user(u, lab) for u, lab in rows]


# --------------------------------------------------------------------------
# conversations
# --------------------------------------------------------------------------
def get_or_create_conversation(db: Session, me: User, other_id: UUID) -> ChatConversation:
    if other_id == me.user_id:
        raise ChatError("You cannot start a conversation with yourself")

    other = db.query(User).filter(User.user_id == other_id).first()

    if not other or other.status != "ACTIVE" or not _can_reach(me, other):
        raise ChatError("User not found", 404)

    one, two = _pair(me.user_id, other_id)
    conversation = (
        db.query(ChatConversation)
        .filter(ChatConversation.user_one_id == one, ChatConversation.user_two_id == two)
        .first()
    )

    if conversation:
        return conversation

    conversation = ChatConversation(user_one_id=one, user_two_id=two)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation_for_user(db: Session, conversation_id: UUID, me: UUID) -> ChatConversation:
    conversation = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.conversation_id == conversation_id,
            or_(ChatConversation.user_one_id == me, ChatConversation.user_two_id == me),
        )
        .first()
    )
    if not conversation:
        raise ChatError("Conversation not found", 404)
    return conversation


def _unread_counts(db: Session, me: UUID, conversation_ids: list[UUID]) -> dict:
    if not conversation_ids:
        return {}
    rows = (
        db.query(ChatMessage.conversation_id, func.count(ChatMessage.message_id))
        .filter(
            ChatMessage.conversation_id.in_(conversation_ids),
            ChatMessage.sender_id != me,
            ChatMessage.read_at.is_(None),
        )
        .group_by(ChatMessage.conversation_id)
        .all()
    )
    return {cid: n for cid, n in rows}


def _last_messages(db: Session, conversation_ids: list[UUID]) -> dict:
    if not conversation_ids:
        return {}
    newest = (
        db.query(
            ChatMessage.conversation_id.label("cid"),
            func.max(ChatMessage.created_at).label("newest"),
        )
        .filter(ChatMessage.conversation_id.in_(conversation_ids))
        .group_by(ChatMessage.conversation_id)
        .subquery()
    )
    rows = (
        db.query(ChatMessage)
        .join(
            newest,
            and_(
                ChatMessage.conversation_id == newest.c.cid,
                ChatMessage.created_at == newest.c.newest,
            ),
        )
        .all()
    )
    return {m.conversation_id: m for m in rows}


def summarize_conversations(
    db: Session, me: UUID, conversations: list[ChatConversation]
) -> list[dict]:
    """Conversation list rows from `me`'s point of view, newest activity first."""

    if not conversations:
        return []

    ids = [c.conversation_id for c in conversations]
    other_ids = {other_participant_id(c, me) for c in conversations}

    people = {
        u.user_id: (u, lab)
        for u, lab in db.query(User, Laboratory.name)
        .outerjoin(Laboratory, Laboratory.laboratory_id == User.laboratory_id)
        .filter(User.user_id.in_(other_ids))
        .all()
    }
    unread = _unread_counts(db, me, ids)
    last = _last_messages(db, ids)

    out = []
    for c in conversations:
        other_id = other_participant_id(c, me)
        if other_id not in people:
            continue
        user, lab = people[other_id]
        message = last.get(c.conversation_id)
        out.append(
            {
                "conversation_id": str(c.conversation_id),
                "other_user": serialize_user(user, lab),
                "last_message": serialize_message(message) if message else None,
                "last_message_at": iso(c.last_message_at or c.created_at),
                "unread_count": unread.get(c.conversation_id, 0),
            }
        )

    out.sort(key=lambda r: r["last_message_at"] or "", reverse=True)
    return out


def list_conversations(db: Session, me: User) -> list[dict]:
    conversations = (
        db.query(ChatConversation)
        .filter(
            or_(
                ChatConversation.user_one_id == me.user_id,
                ChatConversation.user_two_id == me.user_id,
            )
        )
        .all()
    )
    return summarize_conversations(db, me.user_id, conversations)


def conversation_summary(db: Session, conversation: ChatConversation, viewer: UUID) -> dict:
    return summarize_conversations(db, viewer, [conversation])[0]


# --------------------------------------------------------------------------
# messages
# --------------------------------------------------------------------------
def list_messages(
    db: Session, conversation: ChatConversation, before: datetime | None, limit: int
) -> dict:
    limit = max(1, min(limit or PAGE_SIZE, 100))
    q = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation.conversation_id
    )
    if before is not None:
        q = q.filter(ChatMessage.created_at < before)

    rows = q.order_by(ChatMessage.created_at.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = list(reversed(rows[:limit]))  # oldest -> newest

    return {"messages": [serialize_message(m) for m in rows], "has_more": has_more}


def clean_body(body: str | None) -> str:
    text = (body or "").strip()
    if not text:
        raise ChatError("Message cannot be empty", 422)
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ChatError(f"Message is too long (maximum {MAX_MESSAGE_LENGTH} characters)", 422)
    return text


def send_message(
    db: Session, conversation: ChatConversation, sender: User, body: str
) -> ChatMessage:
    text = clean_body(body)

    other = db.query(User).filter(
        User.user_id == other_participant_id(conversation, sender.user_id)
    ).first()

    if not other or other.status != "ACTIVE":
        raise ChatError("This user is no longer active and cannot receive messages", 409)

    now = datetime.now(timezone.utc)
    message = ChatMessage(
        conversation_id=conversation.conversation_id,
        sender_id=sender.user_id,
        body=text,
        created_at=now,
    )
    conversation.last_message_at = now
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def mark_read(db: Session, conversation: ChatConversation, me: UUID) -> list[str]:
    """Mark everything the other person sent as read. Returns the message ids."""

    unread = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation.conversation_id,
            ChatMessage.sender_id != me,
            ChatMessage.read_at.is_(None),
        )
        .all()
    )
    if not unread:
        return []

    now = datetime.now(timezone.utc)
    for m in unread:
        m.read_at = now
    db.commit()
    return [str(m.message_id) for m in unread]


# --------------------------------------------------------------------------
# notifications (unread messages, grouped by conversation)
# --------------------------------------------------------------------------
def notifications(db: Session, me: User) -> dict:
    rows = [c for c in list_conversations(db, me) if c["unread_count"] > 0]
    return {
        "unread_total": sum(c["unread_count"] for c in rows),
        "items": rows,
    }
