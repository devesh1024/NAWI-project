# backend/app/services/calculation_engine/result_builder.py

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping


@dataclass(frozen=True)
class CalculationResult:
    """
    Standard result returned by a calculation-engine test.
    """

    test_code: str
    status: str

    measured_value: Decimal | None = None
    limit: Decimal | None = None
    error: Decimal | None = None

    unit: str | None = None

    rule_id: str | None = None
    clause_reference: str | None = None

    message: str | None = None

    details: Mapping[str, Any] = field(default_factory=dict)


VALID_STATUSES = {
    "PASS",
    "FAIL",
    "N/A",
}


def build_result(
    *,
    test_code: str,
    status: str,
    measured_value: Decimal | None = None,
    limit: Decimal | None = None,
    error: Decimal | None = None,
    unit: str | None = None,
    rule_id: str | None = None,
    clause_reference: str | None = None,
    message: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> CalculationResult:
    """
    Build a standardized calculation result.
    """

    if not test_code:
        raise ValueError("test_code is required")

    normalized_status = status.strip().upper()

    if normalized_status not in VALID_STATUSES:
        raise ValueError(
            f"Unsupported result status: {normalized_status}"
        )

    return CalculationResult(
        test_code=test_code,
        status=normalized_status,
        measured_value=measured_value,
        limit=limit,
        error=error,
        unit=unit,
        rule_id=rule_id,
        clause_reference=clause_reference,
        message=message,
        details=details or {},
    )


def build_pass_result(
    *,
    test_code: str,
    measured_value: Decimal | None = None,
    limit: Decimal | None = None,
    error: Decimal | None = None,
    unit: str | None = None,
    rule_id: str | None = None,
    clause_reference: str | None = None,
    message: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> CalculationResult:
    """
    Convenience builder for a PASS result.
    """

    return build_result(
        test_code=test_code,
        status="PASS",
        measured_value=measured_value,
        limit=limit,
        error=error,
        unit=unit,
        rule_id=rule_id,
        clause_reference=clause_reference,
        message=message,
        details=details,
    )


def build_fail_result(
    *,
    test_code: str,
    measured_value: Decimal | None = None,
    limit: Decimal | None = None,
    error: Decimal | None = None,
    unit: str | None = None,
    rule_id: str | None = None,
    clause_reference: str | None = None,
    message: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> CalculationResult:
    """
    Convenience builder for a FAIL result.
    """

    return build_result(
        test_code=test_code,
        status="FAIL",
        measured_value=measured_value,
        limit=limit,
        error=error,
        unit=unit,
        rule_id=rule_id,
        clause_reference=clause_reference,
        message=message,
        details=details,
    )


def build_na_result(
    *,
    test_code: str,
    message: str | None = None,
    rule_id: str | None = None,
    clause_reference: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> CalculationResult:
    """
    Convenience builder for a not-applicable result.
    """

    return build_result(
        test_code=test_code,
        status="N/A",
        rule_id=rule_id,
        clause_reference=clause_reference,
        message=message,
        details=details,
    )