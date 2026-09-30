from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TestEquipmentCreate(BaseModel):
    equipment_code: str | None = None
    equipment_name: str
    model: str | None = None
    serial_number: str | None = None
    identification_number: str | None = None
    calibration_status: str | None = None
    calibration_date: datetime | None = None
    calibration_due_date: datetime | None = None
    remarks: str | None = None


class TestEquipmentUpdate(BaseModel):
    equipment_code: str | None = None
    equipment_name: str | None = None
    model: str | None = None
    serial_number: str | None = None
    identification_number: str | None = None
    calibration_status: str | None = None
    calibration_date: datetime | None = None
    calibration_due_date: datetime | None = None
    remarks: str | None = None


class TestEquipmentResponse(BaseModel):
    equipment_id: UUID
    laboratory_id: UUID
    equipment_code: str | None
    equipment_name: str
    model: str | None
    serial_number: str | None
    identification_number: str | None
    calibration_status: str | None
    calibration_date: datetime | None
    calibration_due_date: datetime | None
    remarks: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestEquipmentUsageCreate(BaseModel):
    session_test_id: UUID
    equipment_id: UUID
    used_from: datetime | None = None
    used_to: datetime | None = None
    remarks: str | None = None


class TestEquipmentUsageResponse(BaseModel):
    usage_id: UUID
    session_test_id: UUID
    equipment_id: UUID
    used_from: datetime | None
    used_to: datetime | None
    remarks: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)