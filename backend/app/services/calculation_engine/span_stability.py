from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .common_error import calculate_common_error
from .context import EvaluationContext, InstrumentContext, RuleSet
from .mpe import resolve_mpe
from .result_builder import (
    CalculationResult,
    build_fail_result,
    build_pass_result,
)
from .validators import validate_sequence_not_empty


MIN_MEASUREMENTS = 8
MIN_POWER_DISCONNECTION_HOURS = Decimal("8")
INITIAL_REPEATS = 5


def _calculate_error(
    *,
    indication: Decimal,
    load: Decimal,
    e: Decimal,
    additional_load: Decimal,
    zero_error: Decimal,
) -> Decimal:
    result = calculate_common_error(
        indicated_value=indication,
        e=e,
        additional_load=additional_load,
        reference_load=load,
        zero_error=zero_error,
    )

    return result.corrected_error


def calculate_span_stability(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the span stability test.

    OIML R 76-1:
        §5.3.3
        §5.4.4
        B.4

    Prototype implementation:
        - Class III electronic instrument
        - test load near Max
        - minimum 8 measurements
        - first measurement consists of 5 repeated readings
        - subsequent measurements use one reading
        - two power disconnections of at least 8 hours
        - automatic zero tracking disabled
        - span adjustment enabled if applicable

    Acceptance:

        Every error near Max <= MPE

        max(error) - min(error)
            <= max(0.5e, 0.5*MPE)
    """

    if instrument.accuracy_class == "I":
        raise ValueError(
            "Span stability test is not applicable to class I instruments"
        )

    test_load = inputs.get("load")

    if test_load is None:
        raise ValueError("load is required")

    if test_load <= Decimal("0"):
        raise ValueError("load must be greater than zero")

    if test_load > instrument.max_capacity:
        raise ValueError(
            "load cannot exceed maximum capacity"
        )

    power_disconnections = inputs.get(
        "power_disconnections"
    )

    if power_disconnections is None:
        raise ValueError(
            "power_disconnections are required"
        )

    if len(power_disconnections) < 2:
        raise ValueError(
            "at least two power disconnections are required"
        )

    for index, duration in enumerate(
        power_disconnections[:2],
        start=1,
    ):
        if duration < MIN_POWER_DISCONNECTION_HOURS:
            raise ValueError(
                f"power disconnection {index} must be "
                f"at least 8 hours"
            )

    initial_readings = inputs.get("initial_readings")

    if initial_readings is None:
        raise ValueError(
            "initial_readings are required"
        )

    validate_sequence_not_empty(
        initial_readings,
        field_name="initial_readings",
    )

    if len(initial_readings) != INITIAL_REPEATS:
        raise ValueError(
            "initial_readings must contain exactly 5 readings"
        )

    measurements = inputs.get("measurements")

    if measurements is None:
        raise ValueError("measurements are required")

    validate_sequence_not_empty(
        measurements,
        field_name="measurements",
    )

    if len(measurements) < MIN_MEASUREMENTS:
        raise ValueError(
            "at least 8 span measurements are required"
        )

    mpe = resolve_mpe(
        accuracy_class=instrument.accuracy_class,
        load=test_load,
        e=instrument.e,
        basis=evaluation.mpe_basis,
        rules=rules.mpe_rules,
    )

    allowable_variation = max(
        instrument.e / Decimal("2"),
        mpe.value / Decimal("2"),
    )

    initial_errors: list[Decimal] = []

    for index, reading in enumerate(
        initial_readings,
        start=1,
    ):
        indication = reading.get("indication")
        additional_load = reading.get("additional_load")
        zero_error = reading.get("zero_error")

        if indication is None:
            raise ValueError(
                f"initial reading {index}: indication is required"
            )

        if additional_load is None:
            raise ValueError(
                f"initial reading {index}: "
                "additional_load is required"
            )

        if zero_error is None:
            raise ValueError(
                f"initial reading {index}: "
                "zero_error is required"
            )

        error = _calculate_error(
            indication=indication,
            load=test_load,
            e=instrument.e,
            additional_load=additional_load,
            zero_error=zero_error,
        )

        initial_errors.append(error)

    initial_average_error = (
        sum(initial_errors, Decimal("0"))
        / Decimal(len(initial_errors))
    )

    errors: list[dict[str, Any]] = [
        {
            "measurement_no": 1,
            "error": initial_average_error,
            "source": "AVERAGE_OF_5_INITIAL_READINGS",
        }
    ]

    for measurement_no, measurement in enumerate(
        measurements[1:],
        start=2,
    ):
        indication = measurement.get("indication")
        additional_load = measurement.get("additional_load")
        zero_error = measurement.get("zero_error")

        if indication is None:
            raise ValueError(
                f"measurement {measurement_no}: "
                "indication is required"
            )

        if additional_load is None:
            raise ValueError(
                f"measurement {measurement_no}: "
                "additional_load is required"
            )

        if zero_error is None:
            raise ValueError(
                f"measurement {measurement_no}: "
                "zero_error is required"
            )

        error = _calculate_error(
            indication=indication,
            load=test_load,
            e=instrument.e,
            additional_load=additional_load,
            zero_error=zero_error,
        )

        errors.append(
            {
                "measurement_no": measurement_no,
                "error": error,
                "source": "SINGLE_READING",
            }
        )

    error_values = [
        item["error"]
        for item in errors
    ]

    minimum_error = min(error_values)
    maximum_error = max(error_values)
    error_range = maximum_error - minimum_error

    individual_failures = [
        item
        for item in errors
        if abs(item["error"]) > mpe.value
    ]

    variation_passes = error_range <= allowable_variation
    individual_passes = len(individual_failures) == 0

    overall_pass = (
        individual_passes
        and variation_passes
    )

    result_details = {
        "test_load": test_load,
        "mpe": mpe.value,
        "mpe_rule_id": mpe.rule_id,
        "allowable_variation": allowable_variation,
        "minimum_error": minimum_error,
        "maximum_error": maximum_error,
        "error_range": error_range,
        "initial_readings": initial_errors,
        "initial_average_error": initial_average_error,
        "measurements": errors,
        "measurement_count": len(errors),
        "individual_mpe_failures": len(individual_failures),
        "individual_mpe_pass": individual_passes,
        "variation_pass": variation_passes,
        "power_disconnections": power_disconnections,
        "acceptance_rule": (
            "ERROR_ABS_LE_MPE_AND_ERROR_RANGE_LE_MAX_HALF_E_HALF_MPE"
        ),
    }

    if overall_pass:
        return build_pass_result(
            test_code="SPAN",
            unit="kg",
            clause_reference="§5.3.3, §5.4.4, B.4",
            message=(
                "Span stability measurements remain within "
                "the applicable MPE and allowable variation."
            ),
            details=result_details,
        )

    return build_fail_result(
        test_code="SPAN",
        unit="kg",
        clause_reference="§5.3.3, §5.4.4, B.4",
        message=(
            "Span stability measurements exceed the "
            "applicable MPE or allowable variation."
        ),
        details=result_details,
    )