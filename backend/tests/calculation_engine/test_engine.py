# backend/tests/calculation_engine/test_engine.py

from decimal import Decimal

import pytest

from app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from app.services.calculation_engine.engine import (
    CalculationEngine,
    CalculationRequest,
)
from app.services.calculation_engine.result_builder import (
    build_pass_result,
)


@pytest.fixture
def instrument_context():
    return InstrumentContext(
        accuracy_class="III",
        max_capacity=Decimal("30"),
        min_capacity=Decimal("0.2"),
        e=Decimal("0.01"),
        d=Decimal("0.01"),
    )


@pytest.fixture
def evaluation_context():
    return EvaluationContext()


@pytest.fixture
def ruleset():
    return RuleSet(
        ruleset_version="R76-1:2006",
    )


@pytest.fixture
def engine(
    instrument_context,
    evaluation_context,
    ruleset,
):
    return CalculationEngine(
        instrument=instrument_context,
        evaluation=evaluation_context,
        rules=ruleset,
    )


def dummy_calculation(
    *,
    instrument,
    evaluation,
    rules,
    inputs,
):
    return build_pass_result(
        test_code="DUMMY",
        message="Dummy calculation executed.",
        details={
            "input": inputs,
            "accuracy_class": instrument.accuracy_class,
        },
    )


def test_engine_starts_with_no_registered_calculations(engine):
    assert engine.registered_tests() == ()


def test_calculation_can_be_registered(engine):
    engine.register(
        "DUMMY",
        dummy_calculation,
    )

    assert engine.is_registered("DUMMY")
    assert engine.registered_tests() == ("DUMMY",)


def test_registered_calculation_is_executed(engine):
    engine.register(
        "DUMMY",
        dummy_calculation,
    )

    request = CalculationRequest(
        test_code="DUMMY",
        inputs={
            "load": Decimal("10"),
        },
    )

    result = engine.calculate(request)

    assert result.status == "PASS"
    assert result.test_code == "DUMMY"
    assert result.message == "Dummy calculation executed."
    assert result.details["input"]["load"] == Decimal("10")
    assert result.details["accuracy_class"] == "III"


def test_test_code_is_normalized(engine):
    engine.register(
        "DUMMY",
        dummy_calculation,
    )

    request = CalculationRequest(
        test_code=" dummy ",
        inputs={},
    )

    result = engine.calculate(request)

    assert result.status == "PASS"
    assert result.test_code == "DUMMY"


def test_unregistered_test_returns_na(engine):
    request = CalculationRequest(
        test_code="WP",
        inputs={},
    )

    result = engine.calculate(request)

    assert result.status == "N/A"
    assert result.test_code == "WP"
    assert "No calculation registered" in result.message


def test_duplicate_registration_is_rejected(engine):
    engine.register(
        "DUMMY",
        dummy_calculation,
    )

    with pytest.raises(
        ValueError,
        match="Calculation already registered",
    ):
        engine.register(
            "DUMMY",
            dummy_calculation,
        )


def test_unregister_removes_calculation(engine):
    engine.register(
        "DUMMY",
        dummy_calculation,
    )

    assert engine.is_registered("DUMMY")

    engine.unregister("DUMMY")

    assert not engine.is_registered("DUMMY")
    assert engine.registered_tests() == ()


def test_unregister_unknown_calculation_is_rejected(engine):
    with pytest.raises(
        ValueError,
        match="Calculation not registered",
    ):
        engine.unregister("DUMMY")


def test_empty_test_code_is_rejected_when_registering(engine):
    with pytest.raises(
        ValueError,
        match="test_code is required",
    ):
        engine.register(
            "",
            dummy_calculation,
        )


def test_empty_test_code_is_rejected_when_calculating(engine):
    request = CalculationRequest(
        test_code="",
        inputs={},
    )

    with pytest.raises(
        ValueError,
        match="test_code is required",
    ):
        engine.calculate(request)