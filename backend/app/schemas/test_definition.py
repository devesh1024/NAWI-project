from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TestDefinitionResponse(BaseModel):
    test_definition_id: UUID
    standard_id: UUID

    test_code: str
    test_name: str
    category: str | None = None
    description: str | None = None
    reference_clause: str | None = None

    procedure: str | None = None
    required_inputs: dict | None = None
    calculation_type: str | None = None
    acceptance_rule: dict | None = None
    required_equipment: dict | None = None

    is_mandatory: bool
    active: bool

    model_config = ConfigDict(from_attributes=True)


class TestDefinitionCreate(BaseModel):
    standard_id: UUID

    test_code: str
    test_name: str
    category: str | None = None
    description: str | None = None
    reference_clause: str | None = None

    procedure: str | None = None
    required_inputs: dict | None = None
    calculation_type: str | None = None
    acceptance_rule: dict | None = None
    required_equipment: dict | None = None

    is_mandatory: bool = False
    active: bool = True


class TestDefinitionUpdate(BaseModel):
    test_code: str | None = None
    test_name: str | None = None
    category: str | None = None
    description: str | None = None
    reference_clause: str | None = None

    procedure: str | None = None
    required_inputs: dict | None = None
    calculation_type: str | None = None
    acceptance_rule: dict | None = None
    required_equipment: dict | None = None

    is_mandatory: bool | None = None
    active: bool | None = None