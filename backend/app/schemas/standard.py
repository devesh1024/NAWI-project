from uuid import UUID
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StandardResponse(BaseModel):
    standard_id: UUID
    standard_code: str
    title: str
    version: str | None = None
    edition_year: int | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    source_document: str | None = None
    source_url: str | None = None
    status: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StandardCreate(BaseModel):
    standard_code: str
    title: str
    version: str | None = None
    edition_year: int | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    source_document: str | None = None
    source_url: str | None = None
    status: str | None = "ACTIVE"


class StandardUpdate(BaseModel):
    standard_code: str | None = None
    title: str | None = None
    version: str | None = None
    edition_year: int | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    source_document: str | None = None
    source_url: str | None = None
    status: str | None = None