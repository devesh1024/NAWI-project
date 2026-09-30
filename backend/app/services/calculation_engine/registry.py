from __future__ import annotations

from .context import EvaluationContext, InstrumentContext, RuleSet
from .engine import CalculationEngine
from .rules_loader import load_r76_rules

from .creep import calculate_creep
from .discrimination import calculate_discrimination
from .eccentricity import calculate_eccentricity
from .repeatability import calculate_repeatability
from .span_stability import calculate_span_stability
from .tare import calculate_tare
from .temperature import (
    calculate_static_temperatures,
    calculate_temperature_no_load,
)
from .voltage import calculate_voltage
from .warmup import calculate_warmup
from .weighing_performance import calculate_weighing_performance
from .zero_return import calculate_zero_return


def create_calculation_engine(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
    rules: RuleSet,
) -> CalculationEngine:
    """
    Create a CalculationEngine with all supported NAWI
    prototype test calculations registered.
    """

    engine = CalculationEngine(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
    )

    engine.register("WP", calculate_weighing_performance)
    engine.register("TEMP_STATIC", calculate_static_temperatures)
    engine.register("TEMP_NO_LOAD", calculate_temperature_no_load)
    engine.register("ECC_WEIGHT", calculate_eccentricity)
    engine.register("REP", calculate_repeatability)
    engine.register("DIS", calculate_discrimination)
    engine.register("ZR", calculate_zero_return)
    engine.register("CRP", calculate_creep)
    engine.register("TARE", calculate_tare)
    engine.register("WARMUP", calculate_warmup)
    engine.register("VOLT", calculate_voltage)
    engine.register("SPAN", calculate_span_stability)

    return engine


def create_r76_calculation_engine(
    *,
    instrument: InstrumentContext,
    evaluation: EvaluationContext,
) -> CalculationEngine:
    """
    Create a calculation engine using the bundled
    OIML R76-1:2006 ruleset.
    """

    rules = load_r76_rules()

    return create_calculation_engine(
        instrument=instrument,
        evaluation=evaluation,
        rules=rules,
    )