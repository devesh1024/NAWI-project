from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .context import EvaluationContext, InstrumentContext, RuleSet
from .mpe import resolve_mpe
from .result_builder import (
    CalculationResult,
    build_fail_result,
    build_pass_result,
)
from .validators import validate_sequence_not_empty


def calculate_creep(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the creep test.

    OIML R 76-1:2006:
        §3.9.4.1
        A.4.11.1

    Required readings:
        0 min, 5 min, 15 min, 30 min,
        1 h, 2 h, 3 h, 4 h

    The test may terminate at 30 minutes if:
        ΔP(30 min) <= 0.5 e
        AND
        |P(30 min) - P(15 min)| <= 0.2 e

    Otherwise the test continues to 4 hours and:
        |ΔP| <= absolute MPE
        throughout the 4-hour period.

    P = I + 1/2 e - ΔL
    ΔP = P(t) - P(0)
    """

    readings = inputs.get("readings")

    if readings is None:
        raise ValueError("readings are required")

    validate_sequence_not_empty(
        readings,
        field_name="readings",
    )

    expected_times = [
        Decimal("0"),
        Decimal("5"),
        Decimal("15"),
        Decimal("30"),
        Decimal("60"),
        Decimal("120"),
        Decimal("180"),
        Decimal("240"),
    ]

    if len(readings) not in (4, 8):
        raise ValueError(
            "creep test requires either the first 4 readings "
            "(early termination at 30 minutes) or all 8 readings "
            "(full 4-hour test)"
        )

    temperatures = inputs.get("temperatures")

    if temperatures is None:
        raise ValueError("temperatures are required")

    if len(temperatures) != len(readings):
        raise ValueError(
            "temperatures must contain one value for each reading"
        )

    load = inputs.get("load")

    if load is None:
        raise ValueError("load is required")

    if load > instrument.max_capacity:
        raise ValueError(
            "load cannot exceed instrument maximum capacity"
        )

    if load <= Decimal("0"):
        raise ValueError("load must be greater than zero")

    temperature_values = list(temperatures)

    temperature_range = (
        max(temperature_values)
        - min(temperature_values)
    )

    if temperature_range > Decimal("2"):
        raise ValueError(
            "temperature variation during creep test "
            "must not exceed 2 °C"
        )

    mpe = resolve_mpe(
        accuracy_class=instrument.accuracy_class,
        load=load,
        e=instrument.e,
        basis=evaluation.mpe_basis,
        rules=rules.mpe_rules,
    )

    calculations: list[dict[str, Any]] = []

    initial_p: Decimal | None = None

    for index, reading in enumerate(readings):
        time_minutes = reading.get("time_minutes")
        indication = reading.get("indication")
        additional_load = reading.get("additional_load")

        if time_minutes is None:
            raise ValueError(
                f"reading {index + 1}: time_minutes is required"
            )

        if indication is None:
            raise ValueError(
                f"reading {index + 1}: indication is required"
            )

        if additional_load is None:
            raise ValueError(
                f"reading {index + 1}: additional_load is required"
            )

        expected_time = expected_times[index]

        if time_minutes != expected_time:
            raise ValueError(
                f"reading {index + 1}: expected time "
                f"{expected_time} minutes"
            )

        p = (
            indication
            + (instrument.e / Decimal("2"))
            - additional_load
        )

        if initial_p is None:
            initial_p = p

        delta_p = p - initial_p

        calculations.append(
            {
                "time_minutes": time_minutes,
                "indication": indication,
                "additional_load": additional_load,
                "p": p,
                "delta_p": delta_p,
                "temperature": temperature_values[index],
            }
        )

    assert initial_p is not None

    # First 30-minute condition.
    p_15 = calculations[2]["p"]
    p_30 = calculations[3]["p"]

    delta_p_30 = abs(
        calculations[3]["delta_p"]
    )

    delta_p_15_to_30 = abs(
        p_30 - p_15
    )

    early_condition_a = (
        delta_p_30 <= instrument.e / Decimal("2")
        and
        delta_p_15_to_30
        <= instrument.e * Decimal("0.2")
    )

    # If only the first four readings are supplied, the caller
    # is declaring that the test terminated at 30 minutes.
    if len(readings) == 4:
        if not early_condition_a:
            return build_fail_result(
                test_code="CRP",
                unit="kg",
                measured_value=delta_p_30,
                limit=instrument.e / Decimal("2"),
                clause_reference="§3.9.4.1, A.4.11.1",
                message=(
                    "The 30-minute creep termination conditions "
                    "are not satisfied."
                ),
                details={
                    "load": load,
                    "duration_minutes": 30,
                    "calculations": calculations,
                    "delta_p_30": delta_p_30,
                    "delta_p_15_to_30": delta_p_15_to_30,
                    "early_limit_0_5e": (
                        instrument.e / Decimal("2")
                    ),
                    "early_limit_0_2e": (
                        instrument.e * Decimal("0.2")
                    ),
                    "early_condition_pass": False,
                    "temperature_range": temperature_range,
                    "mpe": mpe.value,
                    "termination": "30_MINUTES",
                },
            )

        return build_pass_result(
            test_code="CRP",
            unit="kg",
            measured_value=delta_p_30,
            limit=instrument.e / Decimal("2"),
            clause_reference="§3.9.4.1, A.4.11.1",
            message=(
                "The creep test satisfies both 30-minute "
                "early-termination conditions."
            ),
            details={
                "load": load,
                "duration_minutes": 30,
                "calculations": calculations,
                "delta_p_30": delta_p_30,
                "delta_p_15_to_30": delta_p_15_to_30,
                "early_limit_0_5e": (
                    instrument.e / Decimal("2")
                ),
                "early_limit_0_2e": (
                    instrument.e * Decimal("0.2")
                ),
                "early_condition_pass": True,
                "temperature_range": temperature_range,
                "mpe": mpe.value,
                "termination": "30_MINUTES",
            },
        )

    # Full 4-hour test.
    max_absolute_delta_p = max(
        abs(item["delta_p"])
        for item in calculations
    )

    full_test_pass = (
        max_absolute_delta_p <= abs(mpe.value)
    )

    if full_test_pass:
        return build_pass_result(
            test_code="CRP",
            unit="kg",
            measured_value=max_absolute_delta_p,
            limit=abs(mpe.value),
            clause_reference="§3.9.4.1, A.4.11.1",
            message=(
                "The creep variation remains within the "
                "applicable MPE throughout the 4-hour test."
            ),
            details={
                "load": load,
                "duration_minutes": 240,
                "calculations": calculations,
                "delta_p_30": delta_p_30,
                "delta_p_15_to_30": delta_p_15_to_30,
                "early_condition_pass": early_condition_a,
                "max_absolute_delta_p": max_absolute_delta_p,
                "mpe": mpe.value,
                "mpe_rule_id": mpe.rule_id,
                "temperature_range": temperature_range,
                "termination": "4_HOURS",
            },
        )

    return build_fail_result(
        test_code="CRP",
        unit="kg",
        measured_value=max_absolute_delta_p,
        limit=abs(mpe.value),
        clause_reference="§3.9.4.1, A.4.11.1",
        message=(
            "The creep variation exceeds the applicable "
            "MPE during the 4-hour test."
        ),
        details={
            "load": load,
            "duration_minutes": 240,
            "calculations": calculations,
            "delta_p_30": delta_p_30,
            "delta_p_15_to_30": delta_p_15_to_30,
            "early_condition_pass": early_condition_a,
            "max_absolute_delta_p": max_absolute_delta_p,
            "mpe": mpe.value,
            "mpe_rule_id": mpe.rule_id,
            "temperature_range": temperature_range,
            "termination": "4_HOURS",
        },
    )