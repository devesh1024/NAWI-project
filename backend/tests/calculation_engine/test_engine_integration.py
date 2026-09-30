from decimal import Decimal
from uuid import uuid4

from backend.app.models.instrument import Instrument
from backend.app.services.calculation_engine.context import EvaluationContext
from backend.app.services.calculation_engine.engine import CalculationRequest
from backend.app.services.calculation_engine.instrument_context_adapter import (
    instrument_to_context,
)
from backend.app.services.calculation_engine.registry import (
    create_r76_calculation_engine,
)


def make_instrument() -> Instrument:
    return Instrument(
        instrument_id=uuid4(),
        laboratory_id=uuid4(),
        instrument_code="NAWI-001",
        accuracy_class="III",
        max_capacity=30.0,
        min_capacity=0.2,
        verification_scale_interval=0.01,
        scale_interval=0.01,
        instrument_type="ELECTRONIC",
        indication_type="DIGITAL",
        tare_type="SEMI_AUTOMATIC_SUBTRACTIVE",
        power_supply="AC",
    )


def make_evaluation_context() -> EvaluationContext:
    return EvaluationContext(
        mode="TYPE_EVALUATION",
        mpe_basis="INITIAL_VERIFICATION",
    )


def test_database_instrument_can_create_r76_engine():
    instrument = make_instrument()

    context = instrument_to_context(instrument)
    evaluation = make_evaluation_context()

    engine = create_r76_calculation_engine(
        instrument=context,
        evaluation=evaluation,
    )

    assert engine.instrument == context

    assert engine.is_registered("WP")
    assert engine.is_registered("TEMP_STATIC")
    assert engine.is_registered("ECC_WEIGHT")
    assert engine.is_registered("SPAN")


def test_database_instrument_can_execute_weighing_performance():
    instrument = make_instrument()

    context = instrument_to_context(instrument)
    evaluation = make_evaluation_context()

    engine = create_r76_calculation_engine(
        instrument=context,
        evaluation=evaluation,
    )

    result = engine.calculate(
        request=CalculationRequest(
            test_code="WP",
            inputs={
                "measurements": [
                    {
                        "load": Decimal("10"),
                        "indication": Decimal("10"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    }
                ]
            },
        )
    )

    assert result.test_code == "WP"
    assert result.status == "PASS"
