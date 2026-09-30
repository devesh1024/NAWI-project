from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .context import EvaluationContext, InstrumentContext, RuleSet
from .result_builder import (
    CalculationResult,
    build_fail_result,
    build_pass_result,
)
from .validators import validate_non_negative_decimal


def calculate_zero_return(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the zero return test.

    OIML R 76-1:2006:
        §3.9.4.2
        A.4.11.2

    Procedure:
        - Determine zero indication before loading.
        - Apply a load close to Max for 30 minutes.
        - Remove the load.
        - Take the zero indication after stabilization.
        - Determine the deviation between the two zero indications.

    Acceptance:
        Zero-return deviation <= 0.5 e

    Prototype:
        e = 0.010 kg
        Limit = 0.005 kg
    """

    load = inputs.get("load")
    zero_before = inputs.get("zero_before")
    zero_after = inputs.get("zero_after")
    automatic_zero_tracking_disabled = inputs.get(
        "automatic_zero_tracking_disabled"
    )

    if load is None:
        raise ValueError("load is required")

    if zero_before is None:
        raise ValueError("zero_before is required")

    if zero_after is None:
        raise ValueError("zero_after is required")

    if automatic_zero_tracking_disabled is None:
        raise ValueError(
            "automatic_zero_tracking_disabled is required"
        )

    if not automatic_zero_tracking_disabled:
        raise ValueError(
            "automatic zero-setting or zero-tracking must "
            "be disabled during the zero return test"
        )

    validate_non_negative_decimal(
        load,
        field_name="load",
    )

    validate_non_negative_decimal(
        zero_before,
        field_name="zero_before",
    )

    validate_non_negative_decimal(
        zero_after,
        field_name="zero_after",
    )

    if load > instrument.max_capacity:
        raise ValueError(
            "load cannot exceed instrument maximum capacity"
        )

    # A.4.11.2 specifies a load close to Max for half an hour.
    # The actual load is retained in the result for traceability;
    # the zero-return acceptance criterion itself is independent
    # of the exact load value.
    load_duration_minutes = Decimal("30")

    zero_deviation = abs(
        zero_after - zero_before
    )

    limit = instrument.e / Decimal("2")

    passes = zero_deviation <= limit

    result_details = {
        "load": load,
        "load_duration_minutes": load_duration_minutes,
        "zero_before": zero_before,
        "zero_after": zero_after,
        "zero_deviation": zero_deviation,
        "limit": limit,
        "limit_multiplier_e": Decimal("0.5"),
        "automatic_zero_tracking_disabled": (
            automatic_zero_tracking_disabled
        ),
        "acceptance_rule": "ZERO_DEVIATION_LE_0.5E",
    }

    if passes:
        return build_pass_result(
            test_code="ZR",
            unit="kg",
            measured_value=zero_deviation,
            limit=limit,
            clause_reference="§3.9.4.2, A.4.11.2",
            message=(
                "The zero-return deviation does not exceed 0.5 e."
            ),
            details=result_details,
        )

    return build_fail_result(
        test_code="ZR",
        unit="kg",
        measured_value=zero_deviation,
        limit=limit,
        clause_reference="§3.9.4.2, A.4.11.2",
        message=(
            "The zero-return deviation exceeds 0.5 e."
        ),
        details=result_details,
    )