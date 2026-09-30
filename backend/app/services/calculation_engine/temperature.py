from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

from .common_error import calculate_common_error
from .context import EvaluationContext, InstrumentContext, RuleSet
from .mpe import resolve_mpe
from .result_builder import CalculationResult, build_fail_result, build_pass_result
from .validators import (
    validate_load,
    validate_positive_e,
    validate_sequence_not_empty,
)


STATIC_TEMPERATURES = (
    Decimal("20"),
    Decimal("40"),
    Decimal("-10"),
    Decimal("5"),
    Decimal("20"),
)

NO_LOAD_TEMPERATURES = (
    Decimal("20"),
    Decimal("40"),
    Decimal("-10"),
)


@dataclass(frozen=True)
class TemperatureObservationResult:
    temperature: Decimal
    direction: str
    indicated_value: Decimal
    additional_load: Decimal
    zero_error: Decimal
    conventional_true_value: Decimal
    error: Decimal
    corrected_error: Decimal
    mpe: Decimal
    passed: bool


def _validate_temperature(
    temperature: Decimal,
    *,
    expected: Decimal,
) -> None:
    if not isinstance(temperature, Decimal):
        raise TypeError("temperature must be a Decimal")

    if temperature != expected:
        raise ValueError(
            f"Expected temperature {expected} °C, got {temperature} °C"
        )


def _calculate_temperature_observation(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    temperature: Decimal,
    direction: str,
    indicated_value: Decimal,
    additional_load: Decimal,
    reference_load: Decimal,
    zero_error: Decimal,
) -> TemperatureObservationResult:
    result = calculate_common_error(
        indicated_value=indicated_value,
        e=instrument.e,
        additional_load=additional_load,
        reference_load=reference_load,
        zero_error=zero_error,
    )

    mpe_result = resolve_mpe(
        rules=rules.mpe_rules,
        basis=evaluation.mpe_basis,
        accuracy_class=instrument.accuracy_class,
        load=reference_load,
        e=instrument.e,
    )

    passed = abs(result.corrected_error) <= mpe_result.value

    return TemperatureObservationResult(
        temperature=temperature,
        direction=direction,
        indicated_value=indicated_value,
        additional_load=additional_load,
        zero_error=zero_error,
        conventional_true_value=result.conventional_true_value,
        error=result.error,
        corrected_error=result.corrected_error,
        mpe=mpe_result.value,
        passed=passed,
    )


def calculate_static_temperatures(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    TEMP_STATIC

    OIML R76-1:2006:
        §3.9.2.1
        §3.9.2.2
        A.5.3.1

    Prototype sequence for the fixed Class III instrument:

        20 °C  -> reference temperature
        40 °C  -> specified high temperature
        -10 °C -> specified low temperature
        5 °C   -> required because low temperature <= 0 °C
        20 °C  -> reference temperature again

    At every temperature, both loading and unloading observations
    are evaluated against the applicable MPE.

    Required input:

        {
            "load": Decimal(...),
            "observations": [
                {
                    "temperature": Decimal("20"),
                    "loading": {
                        "indicated_value": Decimal(...),
                        "additional_load": Decimal(...),
                        "zero_error": Decimal(...),
                    },
                    "unloading": {
                        "indicated_value": Decimal(...),
                        "additional_load": Decimal(...),
                        "zero_error": Decimal(...),
                    },
                },
                ...
            ],
        }
    """

    validate_positive_e(instrument.e)

    if instrument.accuracy_class != "III":
        raise ValueError(
            "TEMP_STATIC is configured for the prototype Class III instrument"
        )

    load = inputs.get("load")
    if not isinstance(load, Decimal):
        raise TypeError("load must be a Decimal")

    validate_load(load)

    if load < instrument.min_capacity or load > instrument.max_capacity:
        raise ValueError("load is outside the instrument capacity range")

    observations = inputs.get("observations")
    validate_sequence_not_empty(
        observations or [],
        field_name="observations",
    )

    if len(observations) != len(STATIC_TEMPERATURES):
        raise ValueError(
            "TEMP_STATIC requires exactly 5 temperature observations"
        )

    results: list[TemperatureObservationResult] = []

    for index, (observation, expected_temperature) in enumerate(
        zip(observations, STATIC_TEMPERATURES)
    ):
        if not isinstance(observation, Mapping):
            raise TypeError(
                f"observation[{index}] must be a mapping"
            )

        temperature = observation.get("temperature")

        _validate_temperature(
            temperature,
            expected=expected_temperature,
        )

        for direction in ("loading", "unloading"):
            measurement = observation.get(direction)

            if not isinstance(measurement, Mapping):
                raise ValueError(
                    f"observation[{index}]['{direction}'] is required"
                )

            indicated_value = measurement.get("indicated_value")
            additional_load = measurement.get("additional_load", Decimal("0"))
            zero_error = measurement.get("zero_error", Decimal("0"))

            if not isinstance(indicated_value, Decimal):
                raise TypeError(
                    f"observation[{index}]['{direction}']['indicated_value'] "
                    "must be a Decimal"
                )

            if not isinstance(additional_load, Decimal):
                raise TypeError(
                    f"observation[{index}]['{direction}']['additional_load'] "
                    "must be a Decimal"
                )

            if not isinstance(zero_error, Decimal):
                raise TypeError(
                    f"observation[{index}]['{direction}']['zero_error'] "
                    "must be a Decimal"
                )

            calculated = _calculate_temperature_observation(
                instrument=instrument,
                evaluation=evaluation,
                rules=rules,
                temperature=temperature,
                direction=direction,
                indicated_value=indicated_value,
                additional_load=additional_load,
                reference_load=load,
                zero_error=zero_error,
            )

            results.append(calculated)

    failed = [result for result in results if not result.passed]

    details = {
        "test": "Static Temperatures",
        "clause_reference": "§3.9.2.1, §3.9.2.2, A.5.3.1",
        "temperatures": [str(value) for value in STATIC_TEMPERATURES],
        "load": str(load),
        "observations": [
            {
                "temperature": str(result.temperature),
                "direction": result.direction,
                "indicated_value": str(result.indicated_value),
                "additional_load": str(result.additional_load),
                "zero_error": str(result.zero_error),
                "conventional_true_value": str(
                    result.conventional_true_value
                ),
                "error": str(result.error),
                "corrected_error": str(result.corrected_error),
                "mpe": str(result.mpe),
                "passed": result.passed,
            }
            for result in results
        ],
        "failed_observations": len(failed),
    }

    if failed:
        return build_fail_result(
            test_code="TEMP_STATIC",
            measured_value=max(
                abs(result.corrected_error)
                for result in results
            ),
            limit=max(result.mpe for result in results),
            unit="kg",
            clause_reference="§3.9.2.1, §3.9.2.2, A.5.3.1",
            message=(
                f"{len(failed)} temperature observation(s) exceeded "
                "the applicable MPE."
            ),
            details=details,
        )

    return build_pass_result(
        test_code="TEMP_STATIC",
        measured_value=max(
            abs(result.corrected_error)
            for result in results
        ),
        limit=max(result.mpe for result in results),
        unit="kg",
        clause_reference="§3.9.2.1, §3.9.2.2, A.5.3.1",
        message="Static temperature test passed.",
        details=details,
    )


def calculate_temperature_no_load(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    TEMP_NO_LOAD

    OIML R76-1:2006:
        §3.9.2.3
        A.5.3.2

    For Class III, the zero indication may change by no more than
    one verification scale interval (e) for a 5 °C temperature
    difference.

    Prototype sequence:

        20 °C -> 40 °C -> -10 °C

    No preloading is permitted.

    Required input:

        {
            "observations": [
                {
                    "temperature": Decimal("20"),
                    "zero_error": Decimal(...),
                },
                {
                    "temperature": Decimal("40"),
                    "zero_error": Decimal(...),
                },
                {
                    "temperature": Decimal("-10"),
                    "zero_error": Decimal(...),
                },
            ]
        }
    """

    validate_positive_e(instrument.e)

    if instrument.accuracy_class != "III":
        raise ValueError(
            "TEMP_NO_LOAD is configured for the prototype Class III instrument"
        )

    observations = inputs.get("observations")
    validate_sequence_not_empty(
        observations or [],
        field_name="observations",
    )

    if len(observations) != len(NO_LOAD_TEMPERATURES):
        raise ValueError(
            "TEMP_NO_LOAD requires exactly 3 temperature observations"
        )

    zero_results: list[dict[str, Decimal | bool]] = []

    for index, (observation, expected_temperature) in enumerate(
        zip(observations, NO_LOAD_TEMPERATURES)
    ):
        if not isinstance(observation, Mapping):
            raise TypeError(
                f"observation[{index}] must be a mapping"
            )

        temperature = observation.get("temperature")
        _validate_temperature(
            temperature,
            expected=expected_temperature,
        )

        zero_error = observation.get("zero_error")

        if not isinstance(zero_error, Decimal):
            raise TypeError(
                f"observation[{index}]['zero_error'] must be a Decimal"
            )

        zero_results.append(
            {
                "temperature": temperature,
                "zero_error": zero_error,
            }
        )

    # For classes other than I, the limit is 1e per 5 °C.
    limit_per_5_c = instrument.e

    consecutive_results: list[dict[str, Any]] = []

    for first, second in zip(
        zero_results,
        zero_results[1:],
    ):
        first_temperature = first["temperature"]
        second_temperature = second["temperature"]

        first_zero = first["zero_error"]
        second_zero = second["zero_error"]

        temperature_difference = abs(
            second_temperature - first_temperature
        )

        zero_change = abs(second_zero - first_zero)

        # Normalize the observed zero change to a 5 °C interval.
        normalized_change = (
            zero_change
            * Decimal("5")
            / temperature_difference
        )

        passed = normalized_change <= limit_per_5_c

        consecutive_results.append(
            {
                "from_temperature": first_temperature,
                "to_temperature": second_temperature,
                "temperature_difference": temperature_difference,
                "zero_change": zero_change,
                "normalized_change_per_5_c": normalized_change,
                "limit_per_5_c": limit_per_5_c,
                "passed": passed,
            }
        )

    failed = [
        result
        for result in consecutive_results
        if not result["passed"]
    ]

    details = {
        "test": "Temperature Effect on No-Load Indication",
        "clause_reference": "§3.9.2.3, A.5.3.2",
        "temperatures": [str(value) for value in NO_LOAD_TEMPERATURES],
        "zero_indications": [
            {
                "temperature": str(item["temperature"]),
                "zero_error": str(item["zero_error"]),
            }
            for item in zero_results
        ],
        "limit_per_5_c": str(limit_per_5_c),
        "consecutive_temperature_changes": [
            {
                "from_temperature": str(result["from_temperature"]),
                "to_temperature": str(result["to_temperature"]),
                "temperature_difference": str(
                    result["temperature_difference"]
                ),
                "zero_change": str(result["zero_change"]),
                "normalized_change_per_5_c": str(
                    result["normalized_change_per_5_c"]
                ),
                "limit_per_5_c": str(result["limit_per_5_c"]),
                "passed": result["passed"],
            }
            for result in consecutive_results
        ],
        "failed_intervals": len(failed),
    }

    max_measured_change = max(
        result["normalized_change_per_5_c"]
        for result in consecutive_results
    )

    if failed:
        return build_fail_result(
            test_code="TEMP_NO_LOAD",
            measured_value=max_measured_change,
            limit=limit_per_5_c,
            unit="kg",
            clause_reference="§3.9.2.3, A.5.3.2",
            message=(
                f"{len(failed)} temperature interval(s) exceeded "
                "the allowable zero-indication change."
            ),
            details=details,
        )

    return build_pass_result(
        test_code="TEMP_NO_LOAD",
        measured_value=max_measured_change,
        limit=limit_per_5_c,
        unit="kg",
        clause_reference="§3.9.2.3, A.5.3.2",
        message="Temperature effect on no-load indication passed.",
        details=details,
    )