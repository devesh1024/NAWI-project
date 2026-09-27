from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class TestSessionCreate(BaseModel):
    instrument_id: UUID
    standard_id: UUID
    session_number: Optional[str] = None
    application_number: Optional[str] = None
    test_type: Optional[str] = None
    remarks: Optional[str] = None


class TestSessionResponse(BaseModel):
    test_session_id: UUID
    laboratory_id: UUID
    instrument_id: UUID
    tester_id: UUID
    reviewer_id: Optional[UUID] = None
    standard_id: UUID
    session_number: Optional[str] = None
    application_number: Optional[str] = None
    test_type: Optional[str] = None
    status: str
    overall_result: Optional[str] = None
    remarks: Optional[str] = None

    class Config:
        from_attributes = True