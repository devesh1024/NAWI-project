from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.user import User
from backend.app.realtime.socketio_server import publish_message, publish_read
from backend.app.schemas.chat import ConversationCreate, MessageCreate
from backend.app.services import chat_service as chat
from backend.app.utils.dependencies import get_current_user


router = APIRouter(prefix="/api/chat", tags=["TeamDesk Chat"])


def _http(exc: chat.ChatError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/users")
def search_people(
    q: str = Query("", max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search active users by name, email or employee id (own account excluded)."""
    return chat.search_users(db, current_user, q)


@router.get("/conversations")
def my_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return chat.list_conversations(db, current_user)


@router.post("/conversations", status_code=status.HTTP_200_OK)
def open_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start (or reopen) the one-to-one conversation with another user."""
    try:
        conversation = chat.get_or_create_conversation(db, current_user, data.user_id)
    except chat.ChatError as exc:
        raise _http(exc)
    return chat.conversation_summary(db, conversation, current_user.user_id)


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(
    conversation_id: UUID,
    before: datetime | None = None,
    limit: int = Query(chat.PAGE_SIZE, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        conversation = chat.get_conversation_for_user(db, conversation_id, current_user.user_id)
    except chat.ChatError as exc:
        raise _http(exc)
    return chat.list_messages(db, conversation, before, limit)


@router.post("/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
async def post_message(
    conversation_id: UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """HTTP fallback for sending (the app normally sends over the socket)."""

    def store():
        conversation = chat.get_conversation_for_user(db, conversation_id, current_user.user_id)
        return chat.send_message(db, conversation, current_user, data.body)

    try:
        message = await run_in_threadpool(store)
    except chat.ChatError as exc:
        raise _http(exc)

    await publish_message(message.message_id, str(current_user.user_id))
    return chat.serialize_message(message)


@router.post("/conversations/{conversation_id}/read")
async def read_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def mark():
        conversation = chat.get_conversation_for_user(db, conversation_id, current_user.user_id)
        ids = chat.mark_read(db, conversation, current_user.user_id)
        return ids, str(chat.other_participant_id(conversation, current_user.user_id))

    try:
        ids, other_id = await run_in_threadpool(mark)
    except chat.ChatError as exc:
        raise _http(exc)

    await publish_read(str(conversation_id), str(current_user.user_id), other_id, ids)
    return {"message_ids": ids}


@router.get("/notifications")
def my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unread messages grouped by conversation, for the notification bell."""
    return chat.notifications(db, current_user)
