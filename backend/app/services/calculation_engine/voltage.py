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


LOWER_VOLTAGE_FACTOR = Decimal("0.85")
UPPER_VOLTAGE_FACTOR = Decimal("1.10")
TEST_LOAD_IN_E = Decimal("10")


def calculate_voltage(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
    inputs: Mapping[str, Any],
) -> CalculationResult:
    """
    Calculate the voltage-variation test.

    OIML R 76-1:
        §3.9.3
        A.5.4
        A.5.4.1

    For the prototype:
        - AC mains supply
        - nominal voltage = 230 V
        - voltage range = 0.85 Unom to 1.10 Unom
        - test load = 10e

    Each observation is evaluated using:

        P  = I + 1/2 e - ΔL
        E  = P - L
        Ec = E - E0

    Acceptance:

        |Ec| <= MPE
    """

    if instrument.power_supply != "AC":
        raise ValueError(
            "VOLT calculation currently supports AC power supply only"
        )

    nominal_voltage = instrument.nominal_voltage

    if nominal_voltage <= Decimal("0"):
        raise ValueError(
            "nominal_voltage must be greater than zero"
        )

    expected_test_load = instrument.e * TEST_LOAD_IN_E

    test_load = inputs.get("load")

    if test_load is None:
        raise ValueError("load is required")

    if test_load != expected_test_load:
        raise ValueError(
            f"voltage test load must be exactly "
            f"{expected_test_load} kg (10e)"
        )

    lower_voltage = nominal_voltage * LOWER_VOLTAGE_FACTOR
    upper_voltage = nominal_voltage * UPPER_VOLTAGE_FACTOR

    observations = inputs.get("observations")

    if observations is None:
        raise ValueError("observations are required")

    validate_sequence_not_empty(
        observations,
        field_name="observations",
    )

    calculations: list[dict[str, Any]] = []
    failed_measurements = 0

    for index, observation in enumerate(observations, start=1):
        voltage = observation.get("voltage")
        indication = observation.get("indication")
        additional_load = observation.get("additional_load")
        zero_error = observation.get("zero_error")

        if voltage is None:
            raise ValueError(
                f"observation {index}: voltage is required"
            )

        if indication is None:
            raise ValueError(
                f"observation {index}: indication is required"
            )

        if additional_load is None:
            raise ValueError(
                f"observation {index}: additional_load is required"
            )

        if zero_error is None:
            raise ValueError(
                f"observation {index}: zero_error is required"
            )

        if voltage < lower_voltage or voltage > upper_voltage:
            raise ValueError(
                f"observation {index}: voltage is outside "
                f"the permitted range "
                f"{lower_voltage} V to {upper_voltage} V"
            )

        common_error = calculate_common_error(
            indicated_value=indication,
            e=instrument.e,
            additional_load=additional_load,
            reference_load=test_load,
            zero_error=zero_error,
        )

        mpe = resolve_mpe(
            accuracy_class=instrument.accuracy_class,
            load=test_load,
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
                "voltage": voltage,
                "load": test_load,
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
        "nominal_voltage": nominal_voltage,
        "lower_voltage": lower_voltage,
        "upper_voltage": upper_voltage,
        "test_load": test_load,
        "test_load_in_e": TEST_LOAD_IN_E,
        "observations": calculations,
        "measurement_count": len(calculations),
        "failed_measurements": failed_measurements,
        "voltage_range_rule": "0.85_Unom_TO_1.10_Unom",
        "acceptance_rule": "ABS_EC_LE_MPE",
    }

    if failed_measurements == 0:
        return build_pass_result(
            test_code="VOLT",
            unit="kg",
            clause_reference="§3.9.3, A.5.4, A.5.4.1",
            message=(
                "All voltage-variation measurements satisfy "
                "the applicable MPE."
            ),
            details=result_details,
        )

    return build_fail_result(
        test_code="VOLT",
        unit="kg",
        clause_reference="§3.9.3, A.5.4, A.5.4.1",
        message=(
            "One or more voltage-variation measurements exceed "
            "the applicable MPE."
        ),
        details=result_details,
    )