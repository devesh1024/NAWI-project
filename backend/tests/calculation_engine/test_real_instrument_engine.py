from decimal import Decimal

from backend.app.database.connection import SessionLocal
from backend.app.models.instrument import Instrument
from backend.app.services.calculation_engine.context import EvaluationContext
from backend.app.services.calculation_engine.engine import CalculationRequest
from backend.app.services.calculation_engine.instrument_context_adapter import (
    instrument_to_context,
)
from backend.app.services.calculation_engine.registry import (
    create_r76_calculation_engine,
)


def test_real_database_instrument_runs_new_wp_engine():
    db = SessionLocal()

    try:
        instrument = (
            db.query(Instrument)
            .filter(
                Instrument.instrument_code == "NAWI-P3-001"
            )
            .first()
        )

        assert instrument is not None

        context = instrument_to_context(instrument)

        assert context.accuracy_class == "III"
        assert context.max_capacity == Decimal("30.0")
        assert context.min_capacity == Decimal("0.2")
        assert context.e == Decimal("0.01")
        assert context.d == Decimal("0.01")

        evaluation = EvaluationContext(
            mode="TYPE_EVALUATION",
            mpe_basis="INITIAL_VERIFICATION",
        )

        engine = create_r76_calculation_engine(
            instrument=context,
            evaluation=evaluation,
        )

        result = engine.calculate(
            CalculationRequest(
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

        assert result.status == "PASS"
        assert result.test_code == "WP"
        assert result.unit == "kg"

        calculations = result.details["calculations"]

        assert len(calculations) == 1

        calculation = calculations[0]

        assert calculation["load"] == Decimal("10")
        assert calculation["conventional_true_value"] == Decimal("10.005")
        assert calculation["error"] == Decimal("0.005")
        assert calculation["corrected_error"] == Decimal("0.005")
        assert calculation["mpe"] == Decimal("0.010")
        assert calculation["pass"] is True

        assert result.details["measurement_count"] == 1
        assert result.details["failed_measurements"] == 0

    finally:
        db.close()