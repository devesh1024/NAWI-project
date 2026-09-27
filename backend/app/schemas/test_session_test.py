from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class TestSessionTestCreate(BaseModel):
    test_definition_id: UUID
    applicability_status: Optional[str] = "APPLICABLE"
    na_reason: Optional[str] = None


class TestSessionTestResponse(BaseModel):
    session_test_id: UUID
    test_session_id: UUID
    test_definition_id: UUID
    applicability_status: Optional[str] = None
    na_reason: Optional[str] = None
    status: str
    result: Optional[str] = None

    class Config:
        from_attributes = True