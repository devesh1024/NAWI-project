from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MPERuleResponse(BaseModel):
    mpe_rule_id: UUID
    standard_id: UUID

    accuracy_class: str
    range_min_e: float | None = None
    range_max_e: float | None = None
    mpe_value_e: float | None = None
    mpe_unit_type: str | None = None
    condition: str | None = None
    test_type: str | None = None
    reference_clause: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MPERuleCreate(BaseModel):
    standard_id: UUID

    accuracy_class: str
    range_min_e: float | None = None
    range_max_e: float | None = None
    mpe_value_e: float | None = None
    mpe_unit_type: str | None = None
    condition: str | None = None
    test_type: str | None = None
    reference_clause: str | None = None


class MPERuleUpdate(BaseModel):
    accuracy_class: str | None = None
    range_min_e: float | None = None
    range_max_e: float | None = None
    mpe_value_e: float | None = None
    mpe_unit_type: str | None = None
    condition: str | None = None
    test_type: str | None = None
    reference_clause: str | None = None