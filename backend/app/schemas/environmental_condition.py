from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EnvironmentalConditionCreate(BaseModel):
    test_session_id: UUID
    temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    source: str | None = None
    remarks: str | None = None


class EnvironmentalConditionUpdate(BaseModel):
    temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    source: str | None = None
    remarks: str | None = None


class EnvironmentalConditionResponse(BaseModel):
    environment_id: UUID
    test_session_id: UUID
    temperature: float | None
    humidity: float | None
    pressure: float | None
    recorded_at: datetime
    recorded_by: UUID | None
    source: str | None
    remarks: str | None

    model_config = ConfigDict(from_attributes=True)