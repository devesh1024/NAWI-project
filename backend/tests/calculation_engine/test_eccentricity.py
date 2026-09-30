from decimal import Decimal

import pytest

from app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from app.services.calculation_engine.eccentricity import (
    calculate_eccentricity,
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


def test_eccentricity_passes(
    instrument,
    evaluation,
    rules,
):
    result = calculate_eccentricity(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "measurements": [
                {
                    "position": "Q1",
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.005"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                {
                    "position": "Q2",
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.000"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                {
                    "position": "Q3",
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.003"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                {
                    "position": "Q4",
                    "load": Decimal("10.000"),
                    "indication": Decimal("9.995"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
            ]
        },
    )

    assert result.status == "PASS"
    assert result.test_code == "ECC_WEIGHT"

    assert result.details["measurement_count"] == 4
    assert result.details["failed_positions"] == 0
    assert result.details["expected_test_load"] == Decimal("10")

    calculations = result.details["calculations"]

    assert calculations[0]["position"] == "Q1"
    assert calculations[0]["corrected_error"] == Decimal("0.010")
    assert calculations[0]["mpe"] == Decimal("0.010")
    assert calculations[0]["pass"] is True

    assert calculations[1]["position"] == "Q2"
    assert calculations[1]["corrected_error"] == Decimal("0.005")
    assert calculations[1]["pass"] is True

    assert calculations[2]["position"] == "Q3"
    assert calculations[2]["corrected_error"] == Decimal("0.008")
    assert calculations[2]["pass"] is True

    assert calculations[3]["position"] == "Q4"
    assert calculations[3]["corrected_error"] == Decimal("0.000")
    assert calculations[3]["pass"] is True


def test_eccentricity_fails_when_one_position_exceeds_mpe(
    instrument,
    evaluation,
    rules,
):
    result = calculate_eccentricity(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "measurements": [
                {
                    "position": "Q1",
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.000"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                {
                    "position": "Q2",
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.000"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                {
                    "position": "Q3",
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.020"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                {
                    "position": "Q4",
                    "load": Decimal("10.000"),
                    "indication": Decimal("10.000"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
            ]
        },
    )

    assert result.status == "FAIL"

    assert result.details["measurement_count"] == 4
    assert result.details["failed_positions"] == 1

    calculation = result.details["calculations"][2]

    assert calculation["position"] == "Q3"
    assert calculation["corrected_error"] == Decimal("0.025")
    assert calculation["mpe"] == Decimal("0.010")
    assert calculation["pass"] is False


def test_eccentricity_requires_exactly_four_positions(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="requires exactly 4 measurements",
    ):
        calculate_eccentricity(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "measurements": [
                    {
                        "position": "Q1",
                        "load": Decimal("10.000"),
                        "indication": Decimal("10.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    }
                ]
            },
        )


def test_eccentricity_requires_measurements(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="measurements are required",
    ):
        calculate_eccentricity(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={},
        )


def test_eccentricity_rejects_wrong_test_load(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="load must be 10",
    ):
        calculate_eccentricity(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "measurements": [
                    {
                        "position": "Q1",
                        "load": Decimal("5.000"),
                        "indication": Decimal("5.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "position": "Q2",
                        "load": Decimal("10.000"),
                        "indication": Decimal("10.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "position": "Q3",
                        "load": Decimal("10.000"),
                        "indication": Decimal("10.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "position": "Q4",
                        "load": Decimal("10.000"),
                        "indication": Decimal("10.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                ]
            },
        )


def test_eccentricity_requires_position(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="measurement 1: position is required",
    ):
        calculate_eccentricity(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "measurements": [
                    {
                        "load": Decimal("10.000"),
                        "indication": Decimal("10.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "position": "Q2",
                        "load": Decimal("10.000"),
                        "indication": Decimal("10.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "position": "Q3",
                        "load": Decimal("10.000"),
                        "indication": Decimal("10.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "position": "Q4",
                        "load": Decimal("10.000"),
                        "indication": Decimal("10.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                ]
            },
        )