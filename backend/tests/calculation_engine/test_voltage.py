from decimal import Decimal

import pytest

from backend.app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from backend.app.services.calculation_engine.voltage import calculate_voltage


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
    voltages: list[str],
    indications: list[str],
):
    return [
        {
            "voltage": Decimal(voltage),
            "indication": Decimal(indication),
            "additional_load": Decimal("0"),
            "zero_error": Decimal("0"),
        }
        for voltage, indication in zip(
            voltages,
            indications,
        )
    ]


def test_voltage_passes(
    instrument,
    evaluation,
    rules,
):
    result = calculate_voltage(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "load": Decimal("0.10"),
            "observations": make_observations(
                voltages=[
                    "195.5",
                    "230",
                    "253",
                ],
                indications=[
                    "0.100",
                    "0.100",
                    "0.100",
                ],
            ),
        },
    )

    assert result.test_code == "VOLT"
    assert result.status == "PASS"
    assert result.details["lower_voltage"] == Decimal("195.50")
    assert result.details["upper_voltage"] == Decimal("253.0")
    assert result.details["measurement_count"] == 3
    assert result.details["failed_measurements"] == 0


def test_voltage_fails_when_measurement_exceeds_mpe(
    instrument,
    evaluation,
    rules,
):
    result = calculate_voltage(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "load": Decimal("0.10"),
            "observations": make_observations(
                voltages=[
                    "195.5",
                    "230",
                    "253",
                ],
                indications=[
                    "0.100",
                    "0.120",
                    "0.100",
                ],
            ),
        },
    )

    assert result.status == "FAIL"
    assert result.details["failed_measurements"] == 1


def test_voltage_requires_exactly_ten_e_load(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="exactly 0.10 kg",
    ):
        calculate_voltage(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "load": Decimal("1.00"),
                "observations": make_observations(
                    voltages=["230"],
                    indications=["1.000"],
                ),
            },
        )


def test_voltage_rejects_below_lower_limit(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="outside the permitted range",
    ):
        calculate_voltage(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "load": Decimal("0.10"),
                "observations": make_observations(
                    voltages=["195.4"],
                    indications=["0.100"],
                ),
            },
        )


def test_voltage_rejects_above_upper_limit(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="outside the permitted range",
    ):
        calculate_voltage(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "load": Decimal("0.10"),
                "observations": make_observations(
                    voltages=["253.1"],
                    indications=["0.100"],
                ),
            },
        )


def test_voltage_requires_observations(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="observations cannot be empty",
    ):
        calculate_voltage(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "load": Decimal("0.10"),
                "observations": [],
            },
        )


def test_voltage_rejects_non_ac_supply(
    evaluation,
    rules,
):
    instrument = InstrumentContext(
        accuracy_class="III",
        max_capacity=Decimal("30"),
        min_capacity=Decimal("0.2"),
        e=Decimal("0.01"),
        d=Decimal("0.01"),
        power_supply="BATTERY",
        nominal_voltage=Decimal("230"),
    )

    with pytest.raises(
        ValueError,
        match="AC power supply only",
    ):
        calculate_voltage(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "load": Decimal("0.10"),
                "observations": make_observations(
                    voltages=["230"],
                    indications=["0.100"],
                ),
            },
        )
