from decimal import Decimal

from app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from app.services.calculation_engine.registry import create_calculation_engine


def make_instrument() -> InstrumentContext:
    return InstrumentContext(
        accuracy_class="III",
        max_capacity=Decimal("30"),
        min_capacity=Decimal("0.2"),
        e=Decimal("0.01"),
        d=Decimal("0.01"),
    )


def make_evaluation() -> EvaluationContext:
    return EvaluationContext()


def make_rules() -> RuleSet:
    return RuleSet(
        ruleset_version="R76-1:2006",
    )


def test_all_prototype_tests_are_registered():
    engine = create_calculation_engine(
        instrument=make_instrument(),
        evaluation=make_evaluation(),
        rules=make_rules(),
    )

    expected = {
        "WP",
        "TEMP_STATIC",
        "TEMP_NO_LOAD",
        "ECC_WEIGHT",
        "REP",
        "DIS",
        "ZR",
        "CRP",
        "TARE",
        "WARMUP",
        "VOLT",
        "SPAN",
    }

    assert set(engine.registered_tests()) == expected