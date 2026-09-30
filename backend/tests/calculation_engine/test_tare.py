from decimal import Decimal

import pytest

from backend.app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from backend.app.services.calculation_engine.tare import calculate_tare


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


def make_measurements(
    *,
    loads: list[str],
    error: str = "0",
):
    result = []

    for load in loads:
        load_decimal = Decimal(load)
        error_decimal = Decimal(error)

        result.append(
            {
                "load": load_decimal,
                "indication": load_decimal + error_decimal,
                "additional_load": Decimal("0"),
                "zero_error": Decimal("0.005"),
            }
        )

    return result


def test_tare_passes_for_valid_subtractive_tare(
    instrument,
    evaluation,
    rules,
):
    loads = [
        "0.2",
        "5",
        "7.5",
        "10",
        "15",
    ]

    result = calculate_tare(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "tare_value": Decimal("15"),
            "maximum_tare": Decimal("30"),
            "loading_measurements": make_measurements(
                loads=loads
            ),
            "unloading_measurements": make_measurements(
                loads=list(reversed(loads))
            ),
        },
    )

    assert result.test_code == "TARE"
    assert result.status == "PASS"
    assert result.details["tare_value"] == Decimal("15")
    assert result.details["maximum_possible_net_load"] == Decimal("15")
    assert result.details["measurement_count"] == 10
    assert result.details["failed_measurements"] == 0


def test_tare_fails_when_one_net_measurement_exceeds_mpe(
    instrument,
    evaluation,
    rules,
):
    loads = [
        "0.2",
        "5",
        "7.5",
        "10",
        "15",
    ]

    loading = make_measurements(loads=loads)

    loading[1]["indication"] = Decimal("5.020")

    result = calculate_tare(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs={
            "tare_value": Decimal("15"),
            "maximum_tare": Decimal("30"),
            "loading_measurements": loading,
            "unloading_measurements": make_measurements(
                loads=list(reversed(loads))
            ),
        },
    )

    assert result.test_code == "TARE"
    assert result.status == "FAIL"
    assert result.details["failed_measurements"] == 1


def test_tare_requires_maximum_tare(
    instrument,
    evaluation,
    rules,
):
    loads = [
        "0.2",
        "5",
        "7.5",
        "10",
        "15",
    ]

    with pytest.raises(ValueError, match="maximum_tare is required"):
        calculate_tare(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "tare_value": Decimal("15"),
                "loading_measurements": make_measurements(
                    loads=loads
                ),
                "unloading_measurements": make_measurements(
                    loads=list(reversed(loads))
                ),
            },
        )


def test_tare_rejects_tare_below_one_third(
    instrument,
    evaluation,
    rules,
):
    loads = [
        "0.2",
        "5",
        "7.5",
        "10",
        "15",
    ]

    with pytest.raises(
        ValueError,
        match="between 1/3 and 2/3",
    ):
        calculate_tare(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "tare_value": Decimal("9"),
                "maximum_tare": Decimal("30"),
                "loading_measurements": make_measurements(
                    loads=loads
                ),
                "unloading_measurements": make_measurements(
                    loads=list(reversed(loads))
                ),
            },
        )


def test_tare_rejects_tare_above_two_thirds(
    instrument,
    evaluation,
    rules,
):
    loads = [
        "0.2",
        "5",
        "7.5",
        "10",
        "15",
    ]

    with pytest.raises(
        ValueError,
        match="between 1/3 and 2/3",
    ):
        calculate_tare(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "tare_value": Decimal("21"),
                "maximum_tare": Decimal("30"),
                "loading_measurements": make_measurements(
                    loads=loads
                ),
                "unloading_measurements": make_measurements(
                    loads=list(reversed(loads))
                ),
            },
        )


def test_tare_requires_at_least_five_loading_steps(
    instrument,
    evaluation,
    rules,
):
    loads = [
        "0.2",
        "5",
        "10",
        "15",
    ]

    with pytest.raises(
        ValueError,
        match="loading_measurements must contain at least 5",
    ):
        calculate_tare(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "tare_value": Decimal("15"),
                "maximum_tare": Decimal("30"),
                "loading_measurements": make_measurements(
                    loads=loads
                ),
                "unloading_measurements": make_measurements(
                    loads=[
                        "0.2",
                        "5",
                        "7.5",
                        "10",
                        "15",
                    ]
                ),
            },
        )


def test_tare_rejects_net_load_above_maximum_possible_net_load(
    instrument,
    evaluation,
    rules,
):
    loads = [
        "0.2",
        "5",
        "7.5",
        "10",
        "16",
    ]

    with pytest.raises(
        ValueError,
        match="exceeds maximum possible net load",
    ):
        calculate_tare(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "tare_value": Decimal("15"),
                "maximum_tare": Decimal("30"),
                "loading_measurements": make_measurements(
                    loads=loads
                ),
                "unloading_measurements": make_measurements(
                    loads=[
                        "0.2",
                        "5",
                        "7.5",
                        "10",
                        "15",
                    ]
                ),
            },
        )


def test_tare_rejects_wrong_tare_type(
    instrument,
    evaluation,
    rules,
):
    instrument = InstrumentContext(
        accuracy_class=instrument.accuracy_class,
        max_capacity=instrument.max_capacity,
        min_capacity=instrument.min_capacity,
        e=instrument.e,
        d=instrument.d,
        tare_type="PRESET",
    )

    with pytest.raises(
        ValueError,
        match="semi-automatic subtractive tare",
    ):
        calculate_tare(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "tare_value": Decimal("15"),
                "maximum_tare": Decimal("30"),
                "loading_measurements": [],
                "unloading_measurements": [],
            },
        )
