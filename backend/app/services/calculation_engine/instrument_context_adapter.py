from __future__ import annotations

from decimal import Decimal

from backend.app.models.instrument import Instrument

from .context import InstrumentContext


def instrument_to_context(instrument: Instrument) -> InstrumentContext:
    """
    Convert a database Instrument into the calculation engine's
    InstrumentContext.

    Database-backed instrument properties are read from the Instrument
    model. Prototype-specific R76 configuration is supplied here until
    those properties become part of the instrument data model.
    """

    required_fields = {
        "accuracy_class": instrument.accuracy_class,
        "max_capacity": instrument.max_capacity,
        "min_capacity": instrument.min_capacity,
        "verification_scale_interval": instrument.verification_scale_interval,
        "scale_interval": instrument.scale_interval,
    }

    missing_fields = [
        field_name
        for field_name, value in required_fields.items()
        if value is None
    ]

    if missing_fields:
        raise ValueError(
            "Instrument is missing required calculation fields: "
            + ", ".join(missing_fields)
        )

    return InstrumentContext(
        accuracy_class=instrument.accuracy_class,
        max_capacity=Decimal(str(instrument.max_capacity)),
        min_capacity=Decimal(str(instrument.min_capacity)),
        e=Decimal(str(instrument.verification_scale_interval)),
        d=Decimal(str(instrument.scale_interval)),

        instrument_type=(
            instrument.instrument_type
            or "ELECTRONIC"
        ),
        indication_type=(
            instrument.indication_type
            or "DIGITAL"
        ),

        # Prototype configuration
        self_indicating=True,
        single_range=True,
        multi_interval=False,

        platform_type="CONVENTIONAL",
        support_points=4,

        tare_type=(
            instrument.tare_type
            or "SEMI_AUTOMATIC_SUBTRACTIVE"
        ),

        power_supply=(
            instrument.power_supply
            or "AC"
        ),
        nominal_voltage=Decimal("230"),
        mobile=False,
    )