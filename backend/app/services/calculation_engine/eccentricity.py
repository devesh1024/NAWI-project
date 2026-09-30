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


def calculate_eccentricity(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the eccentricity test for the prototype instrument.

    OIML R 76-1:
        §3.6.2
        A.4.7
        A.4.7.1

    Prototype scope:
        - Fixed instrument
        - Conventional platform
        - Four support points
        - Four quarter-segment load positions
        - Class III
        - Single range
        - Subtractive tare

    For the prototype configuration, the eccentricity test load is:

        Test load = Max / 3

    For each position:

        P  = I + 1/2 e - ΔL
        E  = P - L
        Ec = E - E0

    Acceptance:

        |Ec| <= MPE
    """

    measurements = inputs.get("measurements")

    if measurements is None:
        raise ValueError("measurements are required")

    validate_sequence_not_empty(
        measurements,
        field_name="measurements",
    )

    # A.4.7.1:
    # For a load receptor with not more than four support points,
    # the four quarter segments are loaded in turn.
    expected_position_count = 4

    if len(measurements) != expected_position_count:
        raise ValueError(
            "eccentricity test requires exactly 4 measurements "
            "for the prototype four-support platform"
        )

    # §3.6.2.1:
    # For this prototype's subtractive-tare configuration,
    # the applicable eccentricity test load is Max / 3.
    expected_test_load = (
        instrument.max_capacity / Decimal("3")
    )

    calculations: list[dict[str, Any]] = []
    failed_positions = 0

    for index, measurement in enumerate(measurements, start=1):
        position = measurement.get("position")
        load = measurement.get("load")
        indication = measurement.get("indication")
        additional_load = measurement.get("additional_load")
        zero_error = measurement.get("zero_error")

        if position is None:
            raise ValueError(
                f"measurement {index}: position is required"
            )

        if load is None:
            raise ValueError(
                f"measurement {index}: load is required"
            )

        if indication is None:
            raise ValueError(
                f"measurement {index}: indication is required"
            )

        if additional_load is None:
            raise ValueError(
                f"measurement {index}: additional_load is required"
            )

        if zero_error is None:
            raise ValueError(
                f"measurement {index}: zero_error is required"
            )

        if load != expected_test_load:
            raise ValueError(
                f"measurement {index}: load must be "
                f"{expected_test_load} kg for the prototype "
                f"eccentricity test"
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

        passes = (
            abs(common_error.corrected_error)
            <= mpe.value
        )

        if not passes:
            failed_positions += 1

        calculations.append(
            {
                "position": position,
                "sequence_no": index,
                "load": load,
                "indication": indication,
                "additional_load": additional_load,
                "zero_error": zero_error,
                "conventional_true_value": (
                    common_error.conventional_true_value
                ),
                "error": common_error.error,
                "corrected_error": (
                    common_error.corrected_error
                ),
                "mpe": mpe.value,
                "mpe_multiplier": mpe.multiplier,
                "mpe_rule_id": mpe.rule_id,
                "pass": passes,
            }
        )

    overall_pass = failed_positions == 0

    result_details = {
        "calculations": calculations,
        "measurement_count": len(calculations),
        "failed_positions": failed_positions,
        "expected_test_load": expected_test_load,
        "position_count": expected_position_count,
        "acceptance_rule": "ABS_EC_LE_MPE",
    }

    if overall_pass:
        return build_pass_result(
            test_code="ECC_WEIGHT",
            unit="kg",
            clause_reference="§3.6.2, A.4.7, A.4.7.1",
            message=(
                "All four eccentric loading positions "
                "satisfy the applicable MPE."
            ),
            details=result_details,
        )

    return build_fail_result(
        test_code="ECC_WEIGHT",
        unit="kg",
        clause_reference="§3.6.2, A.4.7, A.4.7.1",
        message=(
            "One or more eccentric loading positions "
            "exceed the applicable MPE."
        ),
        details=result_details,
    )