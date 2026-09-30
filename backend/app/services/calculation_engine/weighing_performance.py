# backend/app/services/calculation_engine/weighing_performance.py

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .common_error import calculate_common_error
from .context import EvaluationContext, InstrumentContext, RuleSet
from .mpe import resolve_mpe
from .result_builder import CalculationResult, build_fail_result, build_pass_result
from .validators import validate_sequence_not_empty


def calculate_weighing_performance(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the weighing-performance test.

    OIML R 76-1:
        §3.5
        §3.5.3
        A.4.4

    For each weighing observation:

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

    calculations: list[dict[str, Any]] = []
    failed_measurements = 0

    for index, measurement in enumerate(measurements, start=1):
        load = measurement.get("load")
        indication = measurement.get("indication")
        additional_load = measurement.get("additional_load")
        zero_error = measurement.get("zero_error")

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
                "sequence_no": index,
                "load": load,
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

    overall_pass = failed_measurements == 0

    result_details = {
        "calculations": calculations,
        "measurement_count": len(calculations),
        "failed_measurements": failed_measurements,
        "acceptance_rule": "ABS_EC_LE_MPE",
    }

    if overall_pass:
        return build_pass_result(
            test_code="WP",
            unit="kg",
            clause_reference="§3.5, §3.5.3, A.4.4",
            message="All weighing-performance measurements satisfy the applicable MPE.",
            details=result_details,
        )

    return build_fail_result(
        test_code="WP",
        unit="kg",
        clause_reference="§3.5, §3.5.3, A.4.4",
        message="One or more weighing-performance measurements exceed the applicable MPE.",
        details=result_details,
    )