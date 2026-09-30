# backend/app/services/calculation_engine/context.py

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping


@dataclass(frozen=True)
class InstrumentContext:
    """
    Fixed instrument configuration supplied to the calculation engine.

    This represents the prototype-supported NAWI configuration.
    It is intentionally independent of database ORM models.
    """

    accuracy_class: str
    max_capacity: Decimal
    min_capacity: Decimal
    e: Decimal
    d: Decimal

    instrument_type: str = "ELECTRONIC"
    indication_type: str = "DIGITAL"
    self_indicating: bool = True
    single_range: bool = True
    multi_interval: bool = False

    platform_type: str = "CONVENTIONAL"
    support_points: int = 4
    tare_type: str = "SEMI_AUTOMATIC_SUBTRACTIVE"

    power_supply: str = "AC"
    nominal_voltage: Decimal = Decimal("230")
    mobile: bool = False

    @property
    def max_capacity_in_e(self) -> Decimal:
        """Maximum capacity expressed in verification scale intervals."""
        return self.max_capacity / self.e

    @property
    def min_capacity_in_e(self) -> Decimal:
        """Minimum capacity expressed in verification scale intervals."""
        return self.min_capacity / self.e


@dataclass(frozen=True)
class EnvironmentContext:
    """
    Environmental conditions associated with a test execution.
    """

    temperature: Decimal | None = None
    humidity: Decimal | None = None
    voltage: Decimal | None = None

    temperature_unit: str = "°C"
    humidity_unit: str = "%"
    voltage_unit: str = "V"

    additional: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationContext:
    """
    Context describing how the test is being evaluated.
    """

    mode: str = "TYPE_EVALUATION"
    mpe_basis: str = "INITIAL_VERIFICATION"

    ruleset_version: str = "R76-1:2006"
    calculation_version: str = "1.0.0"
    mpe_rule_version: str = "1.0.0"

    additional: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuleSet:
    """
    Versioned OIML rule data loaded by the calculation engine.

    The calculation modules should consume rules through this object
    rather than hard-coding rule values wherever possible.
    """

    ruleset_version: str
    tests: Mapping[str, Any] = field(default_factory=dict)
    mpe_rules: Mapping[str, Any] = field(default_factory=dict)
    applicability: Mapping[str, Any] = field(default_factory=dict)
    requirements: Mapping[str, Any] = field(default_factory=dict)
    calculations: Mapping[str, Any] = field(default_factory=dict)