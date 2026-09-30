from decimal import Decimal

import pytest

from app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from app.services.calculation_engine.repeatability import (
    calculate_repeatability,
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


def make_measurements(
    *,
    load: str,
    indications: list[str],
):
    return [
        {
            "load": Decimal(load),
            "indication": Decimal(indication),
            "additional_load": Decimal("0"),
        }
        for indication in indications
    ]


def test_repeatability_passes(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "series": [
            {
                "series_id": "50_PERCENT_MAX",
                "measurements": make_measurements(
                    load="15",
                    indications=[
                        "15.000",
                        "15.005",
                        "15.000",
                        "14.995",
                        "15.005",
                        "15.000",
                        "15.005",
                        "15.000",
                        "14.995",
                        "15.000",
                    ],
                ),
            },
            {
                "series_id": "100_PERCENT_MAX",
                "measurements": make_measurements(
                    load="30",
                    indications=[
                        "30.000",
                        "30.005",
                        "30.000",
                        "29.995",
                        "30.005",
                        "30.000",
                        "30.005",
                        "30.000",
                        "29.995",
                        "30.000",
                    ],
                ),
            },
        ]
    }

    result = calculate_repeatability(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.test_code == "REP"
    assert result.status == "PASS"

    assert result.details["series_count"] == 2
    assert result.details["failed_series"] == 0


def test_repeatability_fails_when_spread_exceeds_mpe(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "series": [
            {
                "series_id": "50_PERCENT_MAX",
                "measurements": make_measurements(
                    load="15",
                    indications=[
                        "15.000",
                        "15.005",
                        "15.000",
                        "14.995",
                        "15.020",
                        "15.000",
                        "15.005",
                        "15.000",
                        "14.995",
                        "15.000",
                    ],
                ),
            },
            {
                "series_id": "100_PERCENT_MAX",
                "measurements": make_measurements(
                    load="30",
                    indications=[
                        "30.000",
                        "30.005",
                        "30.000",
                        "29.995",
                        "30.005",
                        "30.000",
                        "30.005",
                        "30.000",
                        "29.995",
                        "30.000",
                    ],
                ),
            },
        ]
    }

    result = calculate_repeatability(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.status == "FAIL"

    first_series = result.details["calculations"][0]

    assert (
        first_series["repeatability_difference"]
        > first_series["mpe"]
    )


def test_repeatability_fails_when_individual_error_exceeds_mpe(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "series": [
            {
                "series_id": "50_PERCENT_MAX",
                "measurements": make_measurements(
                    load="15",
                    indications=[
                        "15.000",
                        "15.005",
                        "15.000",
                        "14.995",
                        "15.020",
                        "15.000",
                        "15.005",
                        "15.000",
                        "14.995",
                        "15.000",
                    ],
                ),
            },
            {
                "series_id": "100_PERCENT_MAX",
                "measurements": make_measurements(
                    load="30",
                    indications=[
                        "30.000",
                        "30.005",
                        "30.000",
                        "29.995",
                        "30.005",
                        "30.000",
                        "30.005",
                        "30.000",
                        "29.995",
                        "30.000",
                    ],
                ),
            },
        ]
    }

    result = calculate_repeatability(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.status == "FAIL"

    first_series = result.details["calculations"][0]

    assert first_series["individual_failed_measurements"] == 1
    assert first_series["individual_measurements_pass"] is False


def test_repeatability_requires_two_series(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "series": [
            {
                "series_id": "50_PERCENT_MAX",
                "measurements": make_measurements(
                    load="15",
                    indications=["15.000"] * 10,
                ),
            }
        ]
    }

    with pytest.raises(ValueError, match="exactly 2 series"):
        calculate_repeatability(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_repeatability_requires_ten_weighings_per_series(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "series": [
            {
                "series_id": "50_PERCENT_MAX",
                "measurements": make_measurements(
                    load="15",
                    indications=["15.000"] * 9,
                ),
            },
            {
                "series_id": "100_PERCENT_MAX",
                "measurements": make_measurements(
                    load="30",
                    indications=["30.000"] * 10,
                ),
            },
        ]
    }

    with pytest.raises(
        ValueError,
        match="exactly 10 weighings",
    ):
        calculate_repeatability(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_repeatability_rejects_wrong_load(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "series": [
            {
                "series_id": "50_PERCENT_MAX",
                "measurements": make_measurements(
                    load="10",
                    indications=["10.000"] * 10,
                ),
            },
            {
                "series_id": "100_PERCENT_MAX",
                "measurements": make_measurements(
                    load="30",
                    indications=["30.000"] * 10,
                ),
            },
        ]
    }

    with pytest.raises(
        ValueError,
        match="load must be 15",
    ):
        calculate_repeatability(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )