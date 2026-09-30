from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LaboratoryResponse(BaseModel):
    laboratory_id: UUID
    laboratory_code: str
    name: str
    registration_number: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    accreditation_fields: str | None = None
    status: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LaboratoryUpdate(BaseModel):
    name: str | None = None
    registration_number: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    accreditation_fields: str | None = None
    status: str | None = None