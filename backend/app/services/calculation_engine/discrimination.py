from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .context import EvaluationContext, InstrumentContext, RuleSet
from .result_builder import (
    CalculationResult,
    build_fail_result,
    build_pass_result,
)
from .validators import validate_sequence_not_empty


def calculate_discrimination(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the discrimination test for digital indication.

    OIML R 76-1:2006:
        §3.8
        A.4.8
        A.4.8.2

    The test is performed at:
        - Min
        - 1/2 Max
        - Max

    For each load:
        1. Initial indication = I
        2. Remove additional weights until indication = I - d
        3. Replace one additional weight
        4. Add 1.4d
        5. Required final indication = I + d
    """

    loads = inputs.get("loads")

    if loads is None:
        raise ValueError("loads are required")

    validate_sequence_not_empty(
        loads,
        field_name="loads",
    )

    if len(loads) != 3:
        raise ValueError(
            "discrimination test requires exactly 3 load points"
        )

    expected_loads = [
        ("MIN", instrument.min_capacity),
        ("HALF_MAX", instrument.max_capacity / Decimal("2")),
        ("MAX", instrument.max_capacity),
    ]

    d = instrument.d
    one_tenth_d = d / Decimal("10")
    one_point_four_d = d * Decimal("1.4")

    calculations: list[dict[str, Any]] = []
    failed_loads = 0

    for index, (load_input, expected) in enumerate(
        zip(loads, expected_loads),
        start=1,
    ):
        load_label, expected_load = expected

        load = load_input.get("load")
        initial_indication = load_input.get("initial_indication")
        decreased_indication = load_input.get(
            "decreased_indication"
        )
        increased_indication = load_input.get(
            "increased_indication"
        )

        if load is None:
            raise ValueError(
                f"load {index}: load is required"
            )

        if initial_indication is None:
            raise ValueError(
                f"load {index}: initial_indication is required"
            )

        if decreased_indication is None:
            raise ValueError(
                f"load {index}: decreased_indication is required"
            )

        if increased_indication is None:
            raise ValueError(
                f"load {index}: increased_indication is required"
            )

        if load != expected_load:
            raise ValueError(
                f"load {index}: expected {load_label} load "
                f"of {expected_load} kg"
            )

        expected_decreased = (
            initial_indication - d
        )

        expected_increased = (
            initial_indication + d
        )

        decrease_pass = (
            decreased_indication
            == expected_decreased
        )

        increase_pass = (
            increased_indication
            == expected_increased
        )

        load_pass = (
            decrease_pass
            and increase_pass
        )

        if not load_pass:
            failed_loads += 1

        calculations.append(
            {
                "load_label": load_label,
                "load": load,
                "initial_indication": initial_indication,
                "decreased_indication": decreased_indication,
                "expected_decreased_indication": (
                    expected_decreased
                ),
                "increased_indication": increased_indication,
                "expected_increased_indication": (
                    expected_increased
                ),
                "d": d,
                "one_tenth_d": one_tenth_d,
                "one_point_four_d": one_point_four_d,
                "decrease_pass": decrease_pass,
                "increase_pass": increase_pass,
                "load_pass": load_pass,
            }
        )

    overall_pass = failed_loads == 0

    result_details = {
        "calculations": calculations,
        "load_count": len(calculations),
        "failed_loads": failed_loads,
        "d": d,
        "one_tenth_d": one_tenth_d,
        "one_point_four_d": one_point_four_d,
        "acceptance_rule": (
            "INDICATION_TRANSITIONS_BY_ONE_SCALE_INTERVAL"
        ),
    }

    if overall_pass:
        return build_pass_result(
            test_code="DIS",
            unit="kg",
            clause_reference="§3.8, A.4.8.2",
            message=(
                "The instrument demonstrates the required "
                "discrimination at Min, 1/2 Max and Max."
            ),
            details=result_details,
        )

    return build_fail_result(
        test_code="DIS",
        unit="kg",
        clause_reference="§3.8, A.4.8.2",
        message=(
            "The instrument does not demonstrate the required "
            "discrimination at one or more test loads."
        ),
        details=result_details,
    )