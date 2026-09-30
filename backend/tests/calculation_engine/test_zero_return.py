from decimal import Decimal

import pytest

from backend.app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from backend.app.services.calculation_engine.zero_return import (
    calculate_zero_return,
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
    )


def make_inputs(
    *,
    load: str = "30",
    zero_before: str = "0.000",
    zero_after: str = "0.003",
    automatic_zero_tracking_disabled: bool = True,
):
    return {
        "load": Decimal(load),
        "zero_before": Decimal(zero_before),
        "zero_after": Decimal(zero_after),
        "automatic_zero_tracking_disabled": (
            automatic_zero_tracking_disabled
        ),
    }


def test_zero_return_passes(
    instrument,
    evaluation,
    rules,
):
    result = calculate_zero_return(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=make_inputs(
            zero_before="0.000",
            zero_after="0.003",
        ),
    )

    assert result.test_code == "ZR"
    assert result.status == "PASS"

    assert result.measured_value == Decimal("0.003")
    assert result.limit == Decimal("0.005")

    assert result.details["load"] == Decimal("30")
    assert result.details["load_duration_minutes"] == Decimal("30")


def test_zero_return_passes_at_exact_limit(
    instrument,
    evaluation,
    rules,
):
    result = calculate_zero_return(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=make_inputs(
            zero_before="0.000",
            zero_after="0.005",
        ),
    )

    assert result.status == "PASS"
    assert result.measured_value == Decimal("0.005")
    assert result.limit == Decimal("0.005")


def test_zero_return_fails_when_deviation_exceeds_limit(
    instrument,
    evaluation,
    rules,
):
    result = calculate_zero_return(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=make_inputs(
            zero_before="0.000",
            zero_after="0.006",
        ),
    )

    assert result.status == "FAIL"
    assert result.measured_value == Decimal("0.006")
    assert result.limit == Decimal("0.005")


def test_zero_return_uses_absolute_deviation(
    instrument,
    evaluation,
    rules,
):
    result = calculate_zero_return(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=make_inputs(
            zero_before="0.004",
            zero_after="0.000",
        ),
    )

    assert result.status == "PASS"
    assert result.measured_value == Decimal("0.004")


def test_zero_return_rejects_active_automatic_zero_tracking(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="must be disabled",
    ):
        calculate_zero_return(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=make_inputs(
                automatic_zero_tracking_disabled=False,
            ),
        )


def test_zero_return_requires_all_inputs(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="zero_after is required",
    ):
        calculate_zero_return(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={
                "load": Decimal("30"),
                "zero_before": Decimal("0.000"),
                "automatic_zero_tracking_disabled": True,
            },
        )