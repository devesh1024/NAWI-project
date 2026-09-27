from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class ObservationCreate(BaseModel):
    parameter_name: str
    parameter_code: Optional[str] = None
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    sequence_no: Optional[int] = None
    source: Optional[str] = "MANUAL"
    remarks: Optional[str] = None


class ObservationResponse(BaseModel):
    observation_id: UUID
    session_test_id: UUID
    parameter_name: str
    parameter_code: Optional[str] = None
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    sequence_no: Optional[int] = None
    source: Optional[str] = None
    remarks: Optional[str] = None

    class Config:
        from_attributes = True