from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.models.instrument import Instrument
from backend.app.services.calculation_engine.context import InstrumentContext
from backend.app.services.calculation_engine.instrument_context_adapter import (
    instrument_to_context,
)


def make_instrument(**overrides) -> Instrument:
    values = {
        "instrument_id": uuid4(),
        "laboratory_id": uuid4(),
        "instrument_code": "NAWI-001",
        "accuracy_class": "III",
        "max_capacity": 30.0,
        "min_capacity": 0.2,
        "verification_scale_interval": 0.01,
        "scale_interval": 0.01,
        "instrument_type": "ELECTRONIC",
        "indication_type": "DIGITAL",
        "tare_type": "SEMI_AUTOMATIC_SUBTRACTIVE",
        "power_supply": "AC",
    }

    values.update(overrides)

    return Instrument(**values)


def test_instrument_to_context_maps_database_fields():
    instrument = make_instrument()

    context = instrument_to_context(instrument)

    assert isinstance(context, InstrumentContext)

    assert context.accuracy_class == "III"
    assert context.max_capacity == Decimal("30.0")
    assert context.min_capacity == Decimal("0.2")
    assert context.e == Decimal("0.01")
    assert context.d == Decimal("0.01")

    assert context.instrument_type == "ELECTRONIC"
    assert context.indication_type == "DIGITAL"
    assert context.tare_type == "SEMI_AUTOMATIC_SUBTRACTIVE"
    assert context.power_supply == "AC"


def test_instrument_to_context_applies_prototype_configuration():
    instrument = make_instrument()

    context = instrument_to_context(instrument)

    assert context.self_indicating is True
    assert context.single_range is True
    assert context.multi_interval is False
    assert context.platform_type == "CONVENTIONAL"
    assert context.support_points == 4
    assert context.nominal_voltage == Decimal("230")
    assert context.mobile is False


def test_instrument_to_context_rejects_missing_required_fields():
    instrument = make_instrument(
        max_capacity=None,
    )

    with pytest.raises(
        ValueError,
        match="max_capacity",
    ):
        instrument_to_context(instrument)


def test_instrument_to_context_uses_prototype_defaults_for_optional_fields():
    instrument = make_instrument(
        instrument_type=None,
        indication_type=None,
        tare_type=None,
        power_supply=None,
    )

    context = instrument_to_context(instrument)

    assert context.instrument_type == "ELECTRONIC"
    assert context.indication_type == "DIGITAL"
    assert context.tare_type == "SEMI_AUTOMATIC_SUBTRACTIVE"
    assert context.power_supply == "AC"