from decimal import Decimal

import pytest

from app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from app.services.calculation_engine.creep import (
    calculate_creep,
)


@pytest.fixture
def instrument():
    return InstrumentContext(
        accuracy_class="III",
        max_capacity=Decimal("30"),
        min_capacity=Decimal("0.2"),
        e=Decimal("0.010"),
        d=Decimal("0.010"),
    )


@pytest.fixture
def evaluation():
    return EvaluationContext(
        mode="TYPE_EVALUATION",
        mpe_basis="INITIAL_VERIFICATION",
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


def make_readings(
    indications,
    times=None,
):
    if times is None:
        times = [0, 5, 15, 30]

    return [
        {
            "time_minutes": Decimal(str(time)),
            "indication": Decimal(str(indication)),
            "additional_load": Decimal("0"),
        }
        for time, indication in zip(times, indications)
    ]


def test_creep_passes_with_30_minute_termination(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "load": Decimal("30"),
        "readings": make_readings(
            [
                "30.000",
                "30.001",
                "30.002",
                "30.003",
            ]
        ),
        "temperatures": [
            Decimal("20"),
            Decimal("20"),
            Decimal("20.5"),
            Decimal("20.5"),
        ],
    }

    result = calculate_creep(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.test_code == "CRP"
    assert result.status == "PASS"

    assert result.details["termination"] == "30_MINUTES"
    assert result.details["delta_p_30"] == Decimal("0.003")
    assert result.details["delta_p_15_to_30"] == Decimal("0.001")


def test_creep_fails_30_minute_termination_condition(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "load": Decimal("30"),
        "readings": make_readings(
            [
                "30.000",
                "30.001",
                "30.003",
                "30.006",
            ]
        ),
        "temperatures": [
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
        ],
    }

    result = calculate_creep(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.status == "FAIL"
    assert result.details["termination"] == "30_MINUTES"


def test_creep_passes_full_four_hour_test(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "load": Decimal("30"),
        "readings": make_readings(
            [
                "30.000",
                "30.001",
                "30.002",
                "30.004",
                "30.005",
                "30.006",
                "30.007",
                "30.008",
            ],
            times=[0, 5, 15, 30, 60, 120, 180, 240],
        ),
        "temperatures": [
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
            Decimal("20.5"),
            Decimal("20.5"),
            Decimal("20.5"),
            Decimal("21"),
        ],
    }

    result = calculate_creep(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.status == "PASS"
    assert result.details["termination"] == "4_HOURS"
    assert result.details["max_absolute_delta_p"] == Decimal(
        "0.008"
    )


def test_creep_fails_full_four_hour_mpe_condition(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "load": Decimal("30"),
        "readings": make_readings(
            [
                "30.000",
                "30.002",
                "30.004",
                "30.006",
                "30.008",
                "30.012",
                "30.016",
                "30.020",
            ],
            times=[0, 5, 15, 30, 60, 120, 180, 240],
        ),
        "temperatures": [
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
        ],
    }

    result = calculate_creep(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.status == "FAIL"
    assert result.details["max_absolute_delta_p"] == Decimal(
        "0.020"
    )


def test_creep_rejects_temperature_variation_over_two_degrees(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "load": Decimal("30"),
        "readings": make_readings(
            [
                "30.000",
                "30.001",
                "30.002",
                "30.003",
            ]
        ),
        "temperatures": [
            Decimal("20"),
            Decimal("20"),
            Decimal("21"),
            Decimal("22.1"),
        ],
    }

    with pytest.raises(
        ValueError,
        match="temperature variation",
    ):
        calculate_creep(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_creep_requires_load(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "readings": make_readings(
            [
                "30.000",
                "30.001",
                "30.002",
                "30.003",
            ]
        ),
        "temperatures": [
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
            Decimal("20"),
        ],
    }

    with pytest.raises(
        ValueError,
        match="load is required",
    ):
        calculate_creep(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )