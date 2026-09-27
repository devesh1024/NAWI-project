from pydantic import BaseModel
from typing import Any
from uuid import UUID


class InstrumentCreate(BaseModel):
    instrument_code: str

    manufacturer: str | None = None
    model: str | None = None
    type_designation: str | None = None
    serial_number: str | None = None

    instrument_type: str | None = None
    category: str | None = None
    accuracy_class: str | None = None

    max_capacity: float | None = None
    min_capacity: float | None = None
    verification_scale_interval: float | None = None
    scale_interval: float | None = None
    number_of_intervals: int | None = None

    unit: str | None = None

    tare_type: str | None = None
    zero_setting_type: str | None = None
    indication_type: str | None = None

    load_cell_info: str | None = None
    software_firmware: str | None = None
    power_supply: str | None = None

    interfaces: dict[str, Any] | None = None

    temperature_min: float | None = None
    temperature_max: float | None = None

    status: str | None = None


class InstrumentUpdate(BaseModel):
    manufacturer: str | None = None
    model: str | None = None
    type_designation: str | None = None
    serial_number: str | None = None

    instrument_type: str | None = None
    category: str | None = None
    accuracy_class: str | None = None

    max_capacity: float | None = None
    min_capacity: float | None = None
    verification_scale_interval: float | None = None
    scale_interval: float | None = None
    number_of_intervals: int | None = None

    unit: str | None = None

    tare_type: str | None = None
    zero_setting_type: str | None = None
    indication_type: str | None = None

    load_cell_info: str | None = None
    software_firmware: str | None = None
    power_supply: str | None = None

    interfaces: dict[str, Any] | None = None

    temperature_min: float | None = None
    temperature_max: float | None = None

    status: str | None = None


class InstrumentResponse(BaseModel):
    instrument_id: UUID
    laboratory_id: UUID
    instrument_code: str

    manufacturer: str | None = None
    model: str | None = None
    type_designation: str | None = None
    serial_number: str | None = None

    instrument_type: str | None = None
    category: str | None = None
    accuracy_class: str | None = None

    max_capacity: float | None = None
    min_capacity: float | None = None
    verification_scale_interval: float | None = None
    scale_interval: float | None = None
    number_of_intervals: int | None = None

    unit: str | None = None

    tare_type: str | None = None
    zero_setting_type: str | None = None
    indication_type: str | None = None

    load_cell_info: str | None = None
    software_firmware: str | None = None
    power_supply: str | None = None

    interfaces: dict[str, Any] | None = None

    temperature_min: float | None = None
    temperature_max: float | None = None

    status: str | None = None

    class Config:
        from_attributes = True