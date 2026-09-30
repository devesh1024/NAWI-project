from decimal import Decimal

import pytest

from backend.app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from backend.app.services.calculation_engine.temperature import (
    calculate_static_temperatures,
    calculate_temperature_no_load,
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
    return EvaluationContext()


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


def make_static_measurement(indication):
    return {
        "indicated_value": Decimal(indication),
        "additional_load": Decimal("0"),
        "zero_error": Decimal("0"),
    }


def make_static_observation(temperature, indication="10.005"):
    return {
        "temperature": Decimal(temperature),
        "loading": make_static_measurement(indication),
        "unloading": make_static_measurement(indication),
    }


def base_static_inputs():
    return {
        "load": Decimal("10"),
        "observations": [
            make_static_observation("20"),
            make_static_observation("40"),
            make_static_observation("-10"),
            make_static_observation("5"),
            make_static_observation("20"),
        ],
    }


def test_static_temperatures_pass(
    instrument,
    evaluation,
    rules,
):
    result = calculate_static_temperatures(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=base_static_inputs(),
    )

    assert result.test_code == "TEMP_STATIC"
    assert result.status == "PASS"
    assert result.measured_value == Decimal("0.010")
    assert result.limit == Decimal("0.010")


def test_static_temperatures_fail_when_error_exceeds_mpe(
    instrument,
    evaluation,
    rules,
):
    inputs = base_static_inputs()

    inputs["observations"][1] = make_static_observation(
        "40",
        indication="10.020",
    )

    result = calculate_static_temperatures(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.test_code == "TEMP_STATIC"
    assert result.status == "FAIL"
    assert result.measured_value == Decimal("0.025")


def test_static_temperatures_requires_five_temperatures(
    instrument,
    evaluation,
    rules,
):
    inputs = base_static_inputs()
    inputs["observations"] = inputs["observations"][:4]

    with pytest.raises(
        ValueError,
        match="requires exactly 5 temperature observations",
    ):
        calculate_static_temperatures(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_static_temperatures_requires_correct_sequence(
    instrument,
    evaluation,
    rules,
):
    inputs = base_static_inputs()

    inputs["observations"][2]["temperature"] = Decimal("0")

    with pytest.raises(
        ValueError,
        match="Expected temperature -10 °C",
    ):
        calculate_static_temperatures(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_static_temperatures_requires_loading_and_unloading(
    instrument,
    evaluation,
    rules,
):
    inputs = base_static_inputs()
    del inputs["observations"][0]["unloading"]

    with pytest.raises(
        ValueError,
        match="unloading.*required",
    ):
        calculate_static_temperatures(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_static_temperatures_rejects_out_of_range_load(
    instrument,
    evaluation,
    rules,
):
    inputs = base_static_inputs()
    inputs["load"] = Decimal("31")

    with pytest.raises(
        ValueError,
        match="outside the instrument capacity range",
    ):
        calculate_static_temperatures(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def make_no_load_observation(temperature, zero_error):
    return {
        "temperature": Decimal(temperature),
        "zero_error": Decimal(zero_error),
    }


def base_no_load_inputs():
    return {
        "observations": [
            make_no_load_observation("20", "0.000"),
            make_no_load_observation("40", "0.010"),
            make_no_load_observation("-10", "0.000"),
        ]
    }


def test_temperature_no_load_passes(
    instrument,
    evaluation,
    rules,
):
    result = calculate_temperature_no_load(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=base_no_load_inputs(),
    )

    assert result.test_code == "TEMP_NO_LOAD"
    assert result.status == "PASS"
    assert result.limit == Decimal("0.01")


def test_temperature_no_load_fails_when_zero_change_exceeds_limit(
    instrument,
    evaluation,
    rules,
):
    inputs = base_no_load_inputs()

    inputs["observations"][1]["zero_error"] = Decimal("0.050")

    result = calculate_temperature_no_load(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.test_code == "TEMP_NO_LOAD"
    assert result.status == "FAIL"
    assert result.measured_value == Decimal("0.0125")


def test_temperature_no_load_requires_three_temperatures(
    instrument,
    evaluation,
    rules,
):
    inputs = base_no_load_inputs()
    inputs["observations"] = inputs["observations"][:2]

    with pytest.raises(
        ValueError,
        match="requires exactly 3 temperature observations",
    ):
        calculate_temperature_no_load(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_temperature_no_load_requires_correct_sequence(
    instrument,
    evaluation,
    rules,
):
    inputs = base_no_load_inputs()

    inputs["observations"][1]["temperature"] = Decimal("30")

    with pytest.raises(
        ValueError,
        match="Expected temperature 40 °C",
    ):
        calculate_temperature_no_load(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )
