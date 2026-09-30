# backend/app/services/calculation_engine/engine.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .context import EvaluationContext, InstrumentContext, RuleSet
from .result_builder import CalculationResult, build_na_result


CalculationFunction = Callable[..., CalculationResult]


@dataclass(frozen=True)
class CalculationRequest:
    """
    Request passed to the calculation engine.

    test_code:
        Identifier of the calculation to execute.

    inputs:
        Test-specific observations and inputs required by the
        selected calculation module.
    """

    test_code: str
    inputs: Mapping[str, Any]


class CalculationEngine:
    """
    Central orchestrator for the OIML calculation engine.

    The engine is responsible for:
        - registering calculation functions
        - selecting a calculation by test code
        - passing the required context and observations
        - returning a standardized CalculationResult

    Individual OIML calculation formulas belong in their
    respective calculation modules, not in this class.
    """

    def __init__(
        self,
        *,
        instrument: InstrumentContext,
        evaluation: EvaluationContext,
        rules: RuleSet,
    ) -> None:
        self.instrument = instrument
        self.evaluation = evaluation
        self.rules = rules

        self._calculations: dict[str, CalculationFunction] = {}

    def register(
        self,
        test_code: str,
        calculation: CalculationFunction,
    ) -> None:
        """
        Register a calculation function for a test code.
        """

        if not test_code:
            raise ValueError("test_code is required")

        normalized_code = test_code.strip().upper()

        if normalized_code in self._calculations:
            raise ValueError(
                f"Calculation already registered: {normalized_code}"
            )

        self._calculations[normalized_code] = calculation

    def unregister(
        self,
        test_code: str,
    ) -> None:
        """
        Remove a registered calculation.
        """

        normalized_code = test_code.strip().upper()

        if normalized_code not in self._calculations:
            raise ValueError(
                f"Calculation not registered: {normalized_code}"
            )

        del self._calculations[normalized_code]

    def is_registered(
        self,
        test_code: str,
    ) -> bool:
        """
        Check whether a calculation is registered.
        """

        normalized_code = test_code.strip().upper()

        return normalized_code in self._calculations

    def registered_tests(self) -> tuple[str, ...]:
        """
        Return registered test codes.
        """

        return tuple(self._calculations.keys())

    def calculate(
        self,
        request: CalculationRequest,
    ) -> CalculationResult:
        """
        Execute the calculation registered for the requested test.
        """

        if not request.test_code:
            raise ValueError("test_code is required")

        normalized_code = request.test_code.strip().upper()

        calculation = self._calculations.get(normalized_code)

        if calculation is None:
            return build_na_result(
                test_code=normalized_code,
                message=(
                    f"No calculation registered for "
                    f"test '{normalized_code}'."
                ),
            )

        return calculation(
            instrument=self.instrument,
            evaluation=self.evaluation,
            rules=self.rules,
            inputs=request.inputs,
        )