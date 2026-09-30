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


def calculate_repeatability(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the repeatability test.

    OIML R 76-1:2006:
        §3.6
        §3.6.1
        A.4.10

    Prototype:
        - Class III
        - Max = 30 kg
        - e = 10 g
        - Max < 1000 kg
        - 10 weighings at approximately 50 % Max
        - 10 weighings close to 100 % Max

    Acceptance:
        1. Each individual weighing error must not exceed MPE.
        2. Difference between the repeated results must not exceed
           the absolute MPE for that load.
    """

    series = inputs.get("series")

    if series is None:
        raise ValueError("series are required")

    validate_sequence_not_empty(
        series,
        field_name="series",
    )

    if len(series) != 2:
        raise ValueError(
            "repeatability test requires exactly 2 series"
        )

    calculations: list[dict[str, Any]] = []
    failed_series = 0
    total_failed_measurements = 0

    expected_series = [
        {
            "series_id": "50_PERCENT_MAX",
            "expected_load": instrument.max_capacity / Decimal("2"),
        },
        {
            "series_id": "100_PERCENT_MAX",
            "expected_load": instrument.max_capacity,
        },
    ]

    for series_index, (series_input, expected) in enumerate(
        zip(series, expected_series),
        start=1,
    ):
        series_id = series_input.get("series_id")

        if series_id is None:
            raise ValueError(
                f"series {series_index}: series_id is required"
            )

        if series_id != expected["series_id"]:
            raise ValueError(
                f"series {series_index}: expected series_id "
                f"{expected['series_id']}"
            )

        measurements = series_input.get("measurements")

        if measurements is None:
            raise ValueError(
                f"series {series_index}: measurements are required"
            )

        validate_sequence_not_empty(
            measurements,
            field_name=f"series {series_index} measurements",
        )

        if len(measurements) != 10:
            raise ValueError(
                f"series {series_index}: exactly 10 weighings "
                f"are required for Max < 1000 kg"
            )

        expected_load = expected["expected_load"]

        series_results: list[dict[str, Any]] = []
        failed_measurements = 0

        for measurement_index, measurement in enumerate(
            measurements,
            start=1,
        ):
            load = measurement.get("load")
            indication = measurement.get("indication")
            additional_load = measurement.get("additional_load")

            if load is None:
                raise ValueError(
                    f"series {series_index}, measurement "
                    f"{measurement_index}: load is required"
                )

            if indication is None:
                raise ValueError(
                    f"series {series_index}, measurement "
                    f"{measurement_index}: indication is required"
                )

            if additional_load is None:
                raise ValueError(
                    f"series {series_index}, measurement "
                    f"{measurement_index}: additional_load is required"
                )

            if load != expected_load:
                raise ValueError(
                    f"series {series_index}, measurement "
                    f"{measurement_index}: load must be "
                    f"{expected_load} kg"
                )

            # A.4.10 states that when zero deviates between
            # weighings, the instrument is reset to zero without
            # determining the error at zero.
            #
            # Therefore repeatability does not use a measured
            # zero-error correction.
            zero_error = Decimal("0")

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

            individual_pass = (
                abs(common_error.corrected_error)
                <= mpe.value
            )

            if not individual_pass:
                failed_measurements += 1

            series_results.append(
                {
                    "sequence_no": measurement_index,
                    "load": load,
                    "indication": indication,
                    "additional_load": additional_load,
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
                    "individual_pass": individual_pass,
                }
            )

        # Repeatability is the difference between the
        # highest and lowest results.
        results = [
            item["conventional_true_value"]
            for item in series_results
        ]

        maximum_result = max(results)
        minimum_result = min(results)

        repeatability_difference = (
            maximum_result - minimum_result
        )

        series_mpe = resolve_mpe(
            accuracy_class=instrument.accuracy_class,
            load=expected_load,
            e=instrument.e,
            basis=evaluation.mpe_basis,
            rules=rules.mpe_rules,
        )

        repeatability_pass = (
            repeatability_difference
            <= abs(series_mpe.value)
        )

        series_pass = (
            failed_measurements == 0
            and repeatability_pass
        )

        if not series_pass:
            failed_series += 1

        total_failed_measurements += failed_measurements

        calculations.append(
            {
                "series_id": series_id,
                "expected_load": expected_load,
                "measurement_count": len(series_results),
                "measurements": series_results,
                "minimum_result": minimum_result,
                "maximum_result": maximum_result,
                "repeatability_difference": (
                    repeatability_difference
                ),
                "mpe": series_mpe.value,
                "mpe_multiplier": series_mpe.multiplier,
                "mpe_rule_id": series_mpe.rule_id,
                "individual_failed_measurements": (
                    failed_measurements
                ),
                "individual_measurements_pass": (
                    failed_measurements == 0
                ),
                "repeatability_pass": repeatability_pass,
                "series_pass": series_pass,
            }
        )

    overall_pass = failed_series == 0

    result_details = {
        "calculations": calculations,
        "series_count": len(calculations),
        "failed_series": failed_series,
        "total_failed_measurements": total_failed_measurements,
        "acceptance_rules": [
            "ABS_INDIVIDUAL_ERROR_LE_MPE",
            "REPEATABILITY_DIFFERENCE_LE_ABS_MPE",
        ],
    }

    if overall_pass:
        return build_pass_result(
            test_code="REP",
            unit="kg",
            clause_reference="§3.6, §3.6.1, A.4.10",
            message=(
                "Both repeatability series satisfy the "
                "individual-error and repeatability requirements."
            ),
            details=result_details,
        )

    return build_fail_result(
        test_code="REP",
        unit="kg",
        clause_reference="§3.6, §3.6.1, A.4.10",
        message=(
            "One or more repeatability requirements are not satisfied."
        ),
        details=result_details,
    )