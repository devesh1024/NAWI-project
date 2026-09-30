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
from .validators import (
    validate_non_negative_decimal,
    validate_positive_decimal,
    validate_sequence_not_empty,
)


def _validate_tare_value(
    *,
    tare_value: Decimal,
    maximum_tare: Decimal,
) -> None:
    validate_positive_decimal(
        maximum_tare,
        field_name="maximum_tare",
    )

    validate_non_negative_decimal(
        tare_value,
        field_name="tare_value",
    )

    if tare_value > maximum_tare:
        raise ValueError("tare_value cannot exceed maximum_tare")

    lower_limit = maximum_tare / Decimal("3")
    upper_limit = (maximum_tare * Decimal("2")) / Decimal("3")

    if tare_value < lower_limit or tare_value > upper_limit:
        raise ValueError(
            "For subtractive tare, tare_value must be between "
            "1/3 and 2/3 of maximum_tare"
        )


def _validate_measurements(
    *,
    measurements: Any,
    direction: str,
    instrument: InstrumentContext,
    tare_value: Decimal,
) -> None:
    if measurements is None:
        raise ValueError(f"{direction}_measurements are required")

    validate_sequence_not_empty(
        measurements,
        field_name=f"{direction}_measurements",
    )

    if len(measurements) < 5:
        raise ValueError(
            f"{direction}_measurements must contain at least 5 load steps"
        )

    maximum_possible_net_load = instrument.max_capacity - tare_value

    if maximum_possible_net_load < instrument.min_capacity:
        raise ValueError(
            "tare_value leaves no valid net weighing range"
        )

    for index, measurement in enumerate(measurements, start=1):
        load = measurement.get("load")
        indication = measurement.get("indication")
        additional_load = measurement.get("additional_load")
        zero_error = measurement.get("zero_error")

        if load is None:
            raise ValueError(
                f"{direction} measurement {index}: load is required"
            )

        if indication is None:
            raise ValueError(
                f"{direction} measurement {index}: indication is required"
            )

        if additional_load is None:
            raise ValueError(
                f"{direction} measurement {index}: additional_load is required"
            )

        if zero_error is None:
            raise ValueError(
                f"{direction} measurement {index}: zero_error is required"
            )

        if load < instrument.min_capacity:
            raise ValueError(
                f"{direction} measurement {index}: "
                "load is below instrument minimum capacity"
            )

        if load > maximum_possible_net_load:
            raise ValueError(
                f"{direction} measurement {index}: "
                "load exceeds maximum possible net load "
                "for the selected tare"
            )


def _calculate_direction(
    *,
    measurements: Any,
    direction: str,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
) -> tuple[list[dict[str, Any]], int]:
    calculations: list[dict[str, Any]] = []
    failed_measurements = 0

    for index, measurement in enumerate(measurements, start=1):
        load = measurement["load"]
        indication = measurement["indication"]
        additional_load = measurement["additional_load"]
        zero_error = measurement["zero_error"]

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
                "direction": direction,
                "sequence_no": index,
                "net_load": load,
                "indication": indication,
                "additional_load": additional_load,
                "conventional_true_value": (
                    common_error.conventional_true_value
                ),
                "error": common_error.error,
                "zero_error": common_error.zero_error,
                "corrected_error": common_error.corrected_error,
                "mpe": mpe.value,
                "mpe_multiplier": mpe.multiplier,
                "mpe_rule_id": mpe.rule_id,
                "pass": passes,
            }
        )

    return calculations, failed_measurements


def calculate_tare(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the tare weighing test.

    OIML R 76-1:
        §3.5.3.3
        A.4.6.1
        A.4.4.1

    Prototype scope:
        - subtractive tare
        - semi-automatic tare
        - single-range instrument
        - type evaluation

    A.4.6.1 requires:
        - different tare values in general
        - at least 5 load steps
        - load steps covering Min
        - MPE transition points where applicable
        - maximum possible net load
        - for subtractive tare, tare value between
          1/3 and 2/3 of maximum tare

    The prototype evaluates one selected tare value per test session.
    Loading and unloading measurements are both required.

    For each net weighing observation:

        P  = I + 1/2 e - ΔL
        E  = P - L
        Ec = E - E0

    Acceptance:

        |Ec| <= MPE
    """

    if instrument.tare_type != "SEMI_AUTOMATIC_SUBTRACTIVE":
        raise ValueError(
            "TARE calculation currently supports only "
            "semi-automatic subtractive tare"
        )

    tare_value = inputs.get("tare_value")
    maximum_tare = inputs.get("maximum_tare")

    if tare_value is None:
        raise ValueError("tare_value is required")

    if maximum_tare is None:
        raise ValueError("maximum_tare is required")

    _validate_tare_value(
        tare_value=tare_value,
        maximum_tare=maximum_tare,
    )

    loading_measurements = inputs.get("loading_measurements")
    unloading_measurements = inputs.get("unloading_measurements")

    _validate_measurements(
        measurements=loading_measurements,
        direction="loading",
        instrument=instrument,
        tare_value=tare_value,
    )

    _validate_measurements(
        measurements=unloading_measurements,
        direction="unloading",
        instrument=instrument,
        tare_value=tare_value,
    )

    loading_calculations, loading_failures = _calculate_direction(
        measurements=loading_measurements,
        direction="LOADING",
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
    )

    unloading_calculations, unloading_failures = _calculate_direction(
        measurements=unloading_measurements,
        direction="UNLOADING",
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
    )

    all_calculations = (
        loading_calculations + unloading_calculations
    )

    failed_measurements = loading_failures + unloading_failures

    maximum_possible_net_load = (
        instrument.max_capacity - tare_value
    )

    result_details = {
        "tare_value": tare_value,
        "maximum_tare": maximum_tare,
        "maximum_possible_net_load": maximum_possible_net_load,
        "loading_measurements": loading_calculations,
        "unloading_measurements": unloading_calculations,
        "all_measurements": all_calculations,
        "loading_count": len(loading_calculations),
        "unloading_count": len(unloading_calculations),
        "measurement_count": len(all_calculations),
        "failed_measurements": failed_measurements,
        "tare_range_rule": "1/3 <= tare_value/max_tare <= 2/3",
        "acceptance_rule": "ABS_EC_LE_MPE",
    }

    if failed_measurements == 0:
        return build_pass_result(
            test_code="TARE",
            unit="kg",
            clause_reference="§3.5.3.3, A.4.6.1",
            message=(
                "All net weighing measurements satisfy the applicable "
                "MPE with the selected subtractive tare."
            ),
            details=result_details,
        )

    return build_fail_result(
        test_code="TARE",
        unit="kg",
        clause_reference="§3.5.3.3, A.4.6.1",
        message=(
            "One or more net weighing measurements exceed the "
            "applicable MPE with the selected subtractive tare."
        ),
        details=result_details,
    )