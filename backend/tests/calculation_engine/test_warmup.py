from decimal import Decimal

import pytest

from app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from app.services.calculation_engine.warmup import calculate_warmup


@pytest.fixture
def instrument() -> InstrumentContext:
    return InstrumentContext(
        accuracy_class="III",
        max_capacity=Decimal("30"),
        min_capacity=Decimal("0.2"),
        e=Decimal("0.01"),
        d=Decimal("0.01"),
        instrument_type="ELECTRONIC",
        indication_type="DIGITAL",
        self_indicating=True,
        single_range=True,
        multi_interval=False,
        platform_type="CONVENTIONAL",
        support_points=4,
        tare_type="SEMI_AUTOMATIC_SUBTRACTIVE",
        power_supply="AC",
        nominal_voltage=Decimal("230"),
        mobile=False,
    )


@pytest.fixture
def evaluation() -> EvaluationContext:
    return EvaluationContext(
        mode="TYPE_EVALUATION",
        mpe_basis="INITIAL_VERIFICATION",
        ruleset_version="R76-1:2006",
    )


@pytest.fixture
def rules() -> RuleSet:
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


def make_observations(
    *,
    indications: list[str],
    zero_errors: list[str],
):
    times = [5, 15, 30]

    return [
        {
            "elapsed_minutes": minute,
            "indication": Decimal(indication),
            "zero_error": Decimal(zero_error),
            "additional_load": Decimal("0"),
        }
        for minute, indication, zero_error in zip(
            times,
            indications,
            zero_errors,
        )
    ]


def test_warmup_passes(
    instrument,
    evaluation,
    rules,
):
    result = calculate_warmup(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "power_off_hours": Decimal("8"),
            "load": Decimal("30"),
            "observations": make_observations(
                indications=[
                    "30.005",
                    "30.006",
                    "30.004",
                ],
                zero_errors=[
                    "0.001",
                    "0.002",
                    "0.001",
                ],
            ),
        },
    )

    assert result.test_code == "WARMUP"
    assert result.status == "PASS"
    assert result.details["measurement_count"] == 3
    assert result.details["failed_measurements"] == 0


def test_warmup_fails_when_one_measurement_exceeds_mpe(
    instrument,
    evaluation,
    rules,
):
    result = calculate_warmup(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "power_off_hours": Decimal("8"),
            "load": Decimal("30"),
            "observations": make_observations(
                indications=[
                    "30.005",
                    "30.020",
                    "30.004",
                ],
                zero_errors=[
                    "0.001",
                    "0.002",
                    "0.001",
                ],
            ),
        },
    )

    assert result.status == "FAIL"
    assert result.details["failed_measurements"] == 1


def test_warmup_requires_eight_hour_power_off(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="at least 8 hours",
    ):
        calculate_warmup(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "power_off_hours": Decimal("7.5"),
                "load": Decimal("30"),
                "observations": make_observations(
                    indications=[
                        "30.005",
                        "30.006",
                        "30.004",
                    ],
                    zero_errors=[
                        "0.001",
                        "0.002",
                        "0.001",
                    ],
                ),
            },
        )


def test_warmup_requires_all_three_times(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="30 minutes is required",
    ):
        calculate_warmup(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "power_off_hours": Decimal("8"),
                "load": Decimal("30"),
                "observations": [
                    {
                        "elapsed_minutes": 5,
                        "indication": Decimal("30.005"),
                        "zero_error": Decimal("0.001"),
                        "additional_load": Decimal("0"),
                    },
                    {
                        "elapsed_minutes": 15,
                        "indication": Decimal("30.006"),
                        "zero_error": Decimal("0.002"),
                        "additional_load": Decimal("0"),
                    },
                ],
            },
        )


def test_warmup_requires_zero_error_at_each_time(
    instrument,
    evaluation,
    rules,
):
    observations = make_observations(
        indications=[
            "30.005",
            "30.006",
            "30.004",
        ],
        zero_errors=[
            "0.001",
            "0.002",
            "0.001",
        ],
    )

    del observations[1]["zero_error"]

    with pytest.raises(
        ValueError,
        match="zero_error is required at 15 minutes",
    ):
        calculate_warmup(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "power_off_hours": Decimal("8"),
                "load": Decimal("30"),
                "observations": observations,
            },
        )


def test_warmup_uses_time_specific_zero_error(
    instrument,
    evaluation,
    rules,
):
    result = calculate_warmup(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "power_off_hours": Decimal("8"),
            "load": Decimal("30"),
            "observations": make_observations(
                indications=[
                    "30.010",
                    "30.010",
                    "30.010",
                ],
                zero_errors=[
                    "0.005",
                    "0.005",
                    "0.005",
                ],
            ),
        },
    )

    assert result.status == "PASS"

    for observation in result.details["observations"]:
        assert observation["error"] == Decimal("0.015")
        assert observation["corrected_error"] == Decimal("0.010")


def test_warmup_rejects_load_above_max(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="cannot exceed maximum capacity",
    ):
        calculate_warmup(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "power_off_hours": Decimal("8"),
                "load": Decimal("30.1"),
                "observations": make_observations(
                    indications=[
                        "30.005",
                        "30.006",
                        "30.004",
                    ],
                    zero_errors=[
                        "0.001",
                        "0.002",
                        "0.001",
                    ],
                ),
            },
        )