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


WARMUP_TIMES = (5, 15, 30)


def calculate_warmup(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the warm-up time test.

    OIML R 76-1:
        §5.3.5
        A.5.2

    Test procedure:
        - Instrument disconnected for at least 8 hours.
        - Switch on and wait until indication stabilizes.
        - Set zero and determine zero error.
        - Apply a load close to Max.
        - Repeat observations at 5, 15 and 30 minutes.
        - Correct every loaded measurement for the zero error
          determined at that same time.

    Acceptance:
        Every corrected error must be within the applicable MPE.
    """

    power_off_hours = inputs.get("power_off_hours")

    if power_off_hours is None:
        raise ValueError("power_off_hours is required")

    if power_off_hours < Decimal("8"):
        raise ValueError(
            "power_off_hours must be at least 8 hours"
        )

    load = inputs.get("load")

    if load is None:
        raise ValueError("load is required")

    if load <= Decimal("0"):
        raise ValueError("load must be greater than zero")

    if load > instrument.max_capacity:
        raise ValueError("load cannot exceed maximum capacity")

    observations = inputs.get("observations")

    if observations is None:
        raise ValueError("observations are required")

    validate_sequence_not_empty(
        observations,
        field_name="observations",
    )

    observations_by_time: dict[int, Mapping[str, Any]] = {}

    for observation in observations:
        elapsed_minutes = observation.get("elapsed_minutes")

        if elapsed_minutes is None:
            raise ValueError(
                "elapsed_minutes is required"
            )

        if elapsed_minutes in observations_by_time:
            raise ValueError(
                f"Duplicate warm-up observation at "
                f"{elapsed_minutes} minutes"
            )

        observations_by_time[elapsed_minutes] = observation

    for minute in WARMUP_TIMES:
        if minute not in observations_by_time:
            raise ValueError(
                f"Observation at {minute} minutes is required"
            )

    calculations: list[dict[str, Any]] = []
    failed_measurements = 0

    for minute in WARMUP_TIMES:
        observation = observations_by_time[minute]

        indication = observation.get("indication")
        zero_error = observation.get("zero_error")
        additional_load = observation.get("additional_load")

        if indication is None:
            raise ValueError(
                f"indication is required at {minute} minutes"
            )

        if zero_error is None:
            raise ValueError(
                f"zero_error is required at {minute} minutes"
            )

        if additional_load is None:
            raise ValueError(
                f"additional_load is required at {minute} minutes"
            )

        common_error = calculate_common_error(
            indicated_value=indication,
            e=instrument.e,
            additional_load=additional_load,
            reference_load=load,
            zero_error=zero_error,
        )

        mpe = resolve_mpe(
            accuracy_class=instrument.accuracy_class,
            load=load,
            e=instrument.e,
            basis=evaluation.mpe_basis,
            rules=rules.mpe_rules,
        )

        passes = abs(common_error.corrected_error) <= mpe.value

        if not passes:
            failed_measurements += 1

        calculations.append(
            {
                "elapsed_minutes": minute,
                "load": load,
                "indication": indication,
                "additional_load": additional_load,
                "zero_error": zero_error,
                "conventional_true_value": (
                    common_error.conventional_true_value
                ),
                "error": common_error.error,
                "corrected_error": common_error.corrected_error,
                "mpe": mpe.value,
                "mpe_multiplier": mpe.multiplier,
                "mpe_rule_id": mpe.rule_id,
                "pass": passes,
            }
        )

    result_details = {
        "power_off_hours": power_off_hours,
        "test_load": load,
        "observations": calculations,
        "measurement_count": len(calculations),
        "failed_measurements": failed_measurements,
        "required_times_minutes": list(WARMUP_TIMES),
        "acceptance_rule": "ABS_EC_LE_MPE",
    }

    if failed_measurements == 0:
        return build_pass_result(
            test_code="WARMUP",
            unit="kg",
            clause_reference="§5.3.5, A.5.2",
            message=(
                "All warm-up measurements satisfy the applicable MPE."
            ),
            details=result_details,
        )

    return build_fail_result(
        test_code="WARMUP",
        unit="kg",
        clause_reference="§5.3.5, A.5.2",
        message=(
            "One or more warm-up measurements exceed "
            "the applicable MPE."
        ),
        details=result_details,
    )