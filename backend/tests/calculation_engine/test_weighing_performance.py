# backend/tests/calculation_engine/test_weighing_performance.py

from decimal import Decimal

import pytest

from app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from app.services.calculation_engine.weighing_performance import (
    calculate_weighing_performance,
)


@pytest.fixture
def instrument():
    return InstrumentContext(
        accuracy_class="III",
        max_capacity=Decimal("30"),
        min_capacity=Decimal("0.2"),
        e=Decimal("0.01"),
        d=Decimal("0.01"),
    )


@pytest.fixture
def evaluation():
    return EvaluationContext(
        mode="TYPE_EVALUATION",
        mpe_basis="initial_verification",
    )


@pytest.fixture
def rules():
    return RuleSet(
        ruleset_version="R76-1:2006",
        mpe_rules={
            "initial_verification": {
                "III": [
                    {
                        "rule_id": "MPE_III_001",
                        "min_e": 0,
                        "max_e": 500,
                        "mpe_multiplier_e": "0.5",
                    },
                    {
                        "rule_id": "MPE_III_002",
                        "min_e": 500,
                        "max_e": 2000,
                        "mpe_multiplier_e": "1.0",
                    },
                    {
                        "rule_id": "MPE_III_003",
                        "min_e": 2000,
                        "max_e": 10000,
                        "mpe_multiplier_e": "1.5",
                    },
                ]
            }
        },
    )


def test_weighing_performance_passes(
    instrument,
    evaluation,
    rules,
):
    result = calculate_weighing_performance(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "measurements": [
                {
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.005"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0.001"),
                }
            ]
        },
    )

    # P = 10.006 + 0.005 - 0
    #   = 10.011
    #
    # E = 10.011 - 10.000
    #   = 0.011
    #
    # Ec = 0.011 - 0.001
    #    = 0.010
    #
    # At 10 kg, Class III MPE = 0.010 kg.
    assert result.status == "PASS"
    assert result.test_code == "WP"

    calculation = result.details["calculations"][0]

    assert calculation["conventional_true_value"] == Decimal("10.010")
    assert calculation["error"] == Decimal("0.010")
    assert calculation["corrected_error"] == Decimal("0.009")
    assert calculation["mpe"] == Decimal("0.010")
    assert calculation["pass"] is True


def test_weighing_performance_fails_when_mpe_is_exceeded(
    instrument,
    evaluation,
    rules,
):
    result = calculate_weighing_performance(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "measurements": [
                {
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.012"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                }
            ]
        },
    )

    # Ec = 0.012 kg
    # MPE = 0.010 kg
    assert result.status == "FAIL"

    calculation = result.details["calculations"][0]

    assert calculation["corrected_error"] == Decimal("0.017")
    assert calculation["mpe"] == Decimal("0.010")
    assert calculation["pass"] is False


def test_multiple_measurements_all_must_pass(
    instrument,
    evaluation,
    rules,
):
    result = calculate_weighing_performance(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "measurements": [
                {
                    "load": Decimal("2.000"),
                    "indication": Decimal("2.000"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                {
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.005"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                {
                    "load": Decimal("25.000"),
                    "indication": Decimal("25.008"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
            ]
        },
    )

    assert result.status == "PASS"
    assert result.details["measurement_count"] == 3
    assert result.details["failed_measurements"] == 0


def test_one_failed_measurement_fails_overall_test(
    instrument,
    evaluation,
    rules,
):
    result = calculate_weighing_performance(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "measurements": [
                {
                    "load": Decimal("2.000"),
                    "indication": Decimal("2.000"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                {
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.020"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
            ]
        },
    )

    assert result.status == "FAIL"
    assert result.details["measurement_count"] == 2
    assert result.details["failed_measurements"] == 1


def test_empty_measurements_are_rejected(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="measurements cannot be empty",
    ):
        calculate_weighing_performance(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "measurements": []
            },
        )


def test_missing_measurements_are_rejected(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="measurements are required",
    ):
        calculate_weighing_performance(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={},
        )


def test_missing_measurement_field_is_rejected(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="measurement 1: indication is required",
    ):
        calculate_weighing_performance(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "measurements": [
                    {
                        "load": Decimal("10"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    }
                ]
            },
        )