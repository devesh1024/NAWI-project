from decimal import Decimal

import pytest

from backend.app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from backend.app.services.calculation_engine.discrimination import (
    calculate_discrimination,
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


def make_load(
    load: str,
    initial: str,
    decreased: str,
    increased: str,
):
    return {
        "load": Decimal(load),
        "initial_indication": Decimal(initial),
        "decreased_indication": Decimal(decreased),
        "increased_indication": Decimal(increased),
    }


def test_discrimination_passes(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "loads": [
            make_load(
                "0.2",
                "0.200",
                "0.190",
                "0.210",
            ),
            make_load(
                "15",
                "15.000",
                "14.990",
                "15.010",
            ),
            make_load(
                "30",
                "30.000",
                "29.990",
                "30.010",
            ),
        ]
    }

    result = calculate_discrimination(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.test_code == "DIS"
    assert result.status == "PASS"

    assert result.details["load_count"] == 3
    assert result.details["failed_loads"] == 0


def test_discrimination_fails_when_decrease_is_wrong(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "loads": [
            make_load(
                "0.2",
                "0.200",
                "0.195",
                "0.210",
            ),
            make_load(
                "15",
                "15.000",
                "14.990",
                "15.010",
            ),
            make_load(
                "30",
                "30.000",
                "29.990",
                "30.010",
            ),
        ]
    }

    result = calculate_discrimination(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.status == "FAIL"

    first_load = result.details["calculations"][0]

    assert first_load["decrease_pass"] is False
    assert first_load["increase_pass"] is True
    assert first_load["load_pass"] is False


def test_discrimination_fails_when_increase_is_wrong(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "loads": [
            make_load(
                "0.2",
                "0.200",
                "0.190",
                "0.205",
            ),
            make_load(
                "15",
                "15.000",
                "14.990",
                "15.010",
            ),
            make_load(
                "30",
                "30.000",
                "29.990",
                "30.010",
            ),
        ]
    }

    result = calculate_discrimination(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
        inputs=inputs,
    )

    assert result.status == "FAIL"

    first_load = result.details["calculations"][0]

    assert first_load["decrease_pass"] is True
    assert first_load["increase_pass"] is False


def test_discrimination_requires_three_loads(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "loads": [
            make_load(
                "0.2",
                "0.200",
                "0.190",
                "0.210",
            ),
            make_load(
                "15",
                "15.000",
                "14.990",
                "15.010",
            ),
        ]
    }

    with pytest.raises(
        ValueError,
        match="exactly 3 load points",
    ):
        calculate_discrimination(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_discrimination_rejects_wrong_load(
    instrument,
    evaluation,
    rules,
):
    inputs = {
        "loads": [
            make_load(
                "10",
                "10.000",
                "9.990",
                "10.010",
            ),
            make_load(
                "15",
                "15.000",
                "14.990",
                "15.010",
            ),
            make_load(
                "30",
                "30.000",
                "29.990",
                "30.010",
            ),
        ]
    }

    with pytest.raises(
        ValueError,
        match="expected MIN load",
    ):
        calculate_discrimination(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs=inputs,
        )


def test_discrimination_requires_loads(
    instrument,
    evaluation,
    rules,
):
    with pytest.raises(
        ValueError,
        match="loads are required",
    ):
        calculate_discrimination(
            instrument=instrument,
            evaluation=evaluation,
            rules=rules,
            inputs={},
        )
