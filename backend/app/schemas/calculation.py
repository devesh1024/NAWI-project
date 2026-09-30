from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CalculationResultCreate(BaseModel):
    """
    Input received from the client for running a calculation.

    The client supplies only the raw observations/inputs required
    by the selected calculation. The backend calculation engine is
    responsible for calculating MPE, error, corrected error,
    acceptance, and PASS/FAIL.
    """

    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw observations and inputs required by the calculation engine.",
    )


class CalculationResponse(BaseModel):
    calculation_id: UUID
    session_test_id: UUID
    calculation_type: str | None = None
    calculated_value: float | None = None
    unit: str | None = None
    calculation_version: str | None = None

    class Config:
        from_attributes = True


class ResultResponse(BaseModel):
    result_id: UUID
    session_test_id: UUID
    measured_value: float | None = None
    mpe_value: float | None = None
    error_value: float | None = None
    corrected_error: float | None = None
    acceptance_condition: str | None = None
    pass_fail: str | None = None
    result_summary: str | None = None
    calculation_version: str | None = None

    class Config:
        from_attributes = True