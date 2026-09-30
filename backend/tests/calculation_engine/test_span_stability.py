from decimal import Decimal

import pytest

from backend.app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from backend.app.services.calculation_engine.span_stability import (
    calculate_span_stability,
)


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


def make_initial_readings(
    *,
    indications: list[str],
):
    return [
        {
            "indication": Decimal(indication),
            "additional_load": Decimal("0"),
            "zero_error": Decimal("0"),
        }
        for indication in indications
    ]


def make_measurements(
    *,
    indications: list[str],
):
    return [
        {
            "indication": Decimal(indication),
            "additional_load": Decimal("0"),
            "zero_error": Decimal("0"),
        }
        for indication in indications
    ]


def base_inputs():
    return {
        "load": Decimal("30"),
        "power_disconnections": [
            Decimal("8"),
            Decimal("8"),
        ],
        "initial_readings": make_initial_readings(
            indications=[
                "30.005",
                "30.005",
                "30.005",
                "30.005",
                "30.005",
            ]
        ),
        "measurements": make_measurements(
            indications=[
                "30.005",
                "30.005",
                "30.006",
                "30.004",
                "30.005",
                "30.006",
                "30.004",
                "30.005",
            ]
        ),
    }


def test_span_stability_passes(
    instrument,
    evaluation,
    rules,
):
    result = calculate_span_stability(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=base_inputs(),
    )

    assert result.test_code == "SPAN"
    assert result.status == "PASS"
    assert result.details["measurement_count"] == 8
    assert result.details["individual_mpe_failures"] == 0
    assert result.details["variation_pass"] is True


def test_span_stability_fails_when_error_range_exceeds_limit(
    instrument,
    evaluation,
    rules,
):
    inputs = base_inputs()

    inputs["measurements"] = make_measurements(
        indications=[
            "30.005",
            "30.005",
            "30.006",
            "30.004",
            "30.005",
            "30.020",
            "30.004",
            "30.005",
        ]
    )

    result = calculate_span_stability(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.status == "FAIL"
    assert result.details["variation_pass"] is False


def test_span_stability_fails_when_error_exceeds_mpe(
    instrument,
    evaluation,
    rules,
):
    inputs = base_inputs()

    inputs["measurements"] = make_measurements(
        indications=[
            "30.005",
            "30.005",
            "30.006",
            "30.004",
            "30.005",
            "30.020",
            "30.004",
            "30.005",
        ]
    )

    result = calculate_span_stability(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.status == "FAIL"
    assert result.details["individual_mpe_failures"] == 1


def test_span_stability_requires_eight_measurements(
    instrument,
    evaluation,
    rules,
):
    inputs = base_inputs()

    inputs["measurements"] = make_measurements(
        indications=[
            "30.005",
            "30.005",
            "30.006",
            "30.004",
            "30.005",
            "30.006",
            "30.004",
        ]
    )

    with pytest.raises(
        ValueError,
        match="at least 8 span measurements",
    ):
        calculate_span_stability(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_span_stability_requires_two_power_disconnections(
    instrument,
    evaluation,
    rules,
):
    inputs = base_inputs()
    inputs["power_disconnections"] = [
        Decimal("8"),
    ]

    with pytest.raises(
        ValueError,
        match="at least two power disconnections",
    ):
        calculate_span_stability(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_span_stability_requires_eight_hour_disconnections(
    instrument,
    evaluation,
    rules,
):
    inputs = base_inputs()

    inputs["power_disconnections"] = [
        Decimal("7"),
        Decimal("8"),
    ]

    with pytest.raises(
        ValueError,
        match="at least 8 hours",
    ):
        calculate_span_stability(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_span_stability_requires_five_initial_readings(
    instrument,
    evaluation,
    rules,
):
    inputs = base_inputs()

    inputs["initial_readings"] = make_initial_readings(
        indications=[
            "30.005",
            "30.005",
            "30.005",
            "30.005",
        ]
    )

    with pytest.raises(
        ValueError,
        match="exactly 5 readings",
    ):
        calculate_span_stability(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_span_stability_not_applicable_to_class_i(
    evaluation,
    rules,
):
    instrument = InstrumentContext(
        accuracy_class="I",
        max_capacity=Decimal("30"),
        min_capacity=Decimal("0.2"),
        e=Decimal("0.01"),
        d=Decimal("0.01"),
    )

    with pytest.raises(
        ValueError,
        match="not applicable to class I",
    ):
        calculate_span_stability(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=base_inputs(),
        )
