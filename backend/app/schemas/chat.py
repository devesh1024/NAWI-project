from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    user_id: UUID


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
