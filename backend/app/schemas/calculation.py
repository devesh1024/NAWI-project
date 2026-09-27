from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any


class CalculationResultCreate(BaseModel):
    calculation_type: Optional[str] = None
    input_values: Optional[dict[str, Any]] = None
    formula: Optional[str] = None
    calculated_value: Optional[float] = None
    unit: Optional[str] = None
    calculation_version: Optional[str] = None

    measured_value: Optional[float] = None
    mpe_value: Optional[float] = None
    error_value: Optional[float] = None
    corrected_error: Optional[float] = None
    acceptance_condition: Optional[str] = None
    pass_fail: Optional[str] = None
    result_summary: Optional[str] = None


class CalculationResponse(BaseModel):
    calculation_id: UUID
    session_test_id: UUID
    calculation_type: Optional[str] = None
    calculated_value: Optional[float] = None
    unit: Optional[str] = None
    calculation_version: Optional[str] = None

    class Config:
        from_attributes = True


class ResultResponse(BaseModel):
    result_id: UUID
    session_test_id: UUID
    measured_value: Optional[float] = None
    mpe_value: Optional[float] = None
    error_value: Optional[float] = None
    corrected_error: Optional[float] = None
    acceptance_condition: Optional[str] = None
    pass_fail: Optional[str] = None
    result_summary: Optional[str] = None
    calculation_version: Optional[str] = None

    class Config:
        from_attributes = True