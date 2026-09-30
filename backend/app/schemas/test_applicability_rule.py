from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TestApplicabilityRuleResponse(BaseModel):
    applicability_rule_id: UUID
    test_definition_id: UUID

    instrument_condition: dict | None = None
    applicable: bool
    reason: str | None = None
    priority: int | None = None
    standard_clause: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TestApplicabilityRuleCreate(BaseModel):
    test_definition_id: UUID

    instrument_condition: dict | None = None
    applicable: bool
    reason: str | None = None
    priority: int | None = None
    standard_clause: str | None = None


class TestApplicabilityRuleUpdate(BaseModel):
    instrument_condition: dict | None = None
    applicable: bool | None = None
    reason: str | None = None
    priority: int | None = None
    standard_clause: str | None = None