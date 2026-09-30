# backend/app/services/calculation_engine/common_error.py

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CommonErrorResult:
    """
    Result of the common error calculation for a digital indication.
    """

    indicated_value: Decimal
    e: Decimal
    additional_load: Decimal
    conventional_true_value: Decimal
    reference_load: Decimal
    error: Decimal
    zero_error: Decimal
    corrected_error: Decimal


def calculate_conventional_true_value(
    *,
    indicated_value: Decimal,
    e: Decimal,
    additional_load: Decimal,
) -> Decimal:
    """
    Calculate the conventional true value P.

    Formula:
        P = I + 1/2 e - ΔL

    Parameters
    ----------
    indicated_value:
        Indicated value I.

    e:
        Verification scale interval.

    additional_load:
        Additional load ΔL used to determine the indication
        between scale intervals.
    """

    if e <= Decimal("0"):
        raise ValueError("e must be greater than zero")

    if additional_load < Decimal("0"):
        raise ValueError("additional_load cannot be negative")

    return (
        indicated_value
        + (e / Decimal("2"))
        - additional_load
    )


def calculate_error(
    *,
    conventional_true_value: Decimal,
    reference_load: Decimal,
) -> Decimal:
    """
    Calculate the error E.

    Formula:
        E = P - L
    """

    return conventional_true_value - reference_load


def calculate_corrected_error(
    *,
    error: Decimal,
    zero_error: Decimal,
) -> Decimal:
    """
    Calculate the corrected error Ec.

    Formula:
        Ec = E - E0
    """

    return error - zero_error


def calculate_common_error(
    *,
    indicated_value: Decimal,
    e: Decimal,
    additional_load: Decimal,
    reference_load: Decimal,
    zero_error: Decimal = Decimal("0"),
) -> CommonErrorResult:
    """
    Perform the complete common-error calculation.

    Steps:
        1. Calculate conventional true value P.
        2. Calculate error E.
        3. Apply zero-error correction to obtain Ec.
    """

    if not isinstance(indicated_value, Decimal):
        raise TypeError("indicated_value must be a Decimal")

    if not isinstance(e, Decimal):
        raise TypeError("e must be a Decimal")

    if not isinstance(additional_load, Decimal):
        raise TypeError("additional_load must be a Decimal")

    if not isinstance(reference_load, Decimal):
        raise TypeError("reference_load must be a Decimal")

    if not isinstance(zero_error, Decimal):
        raise TypeError("zero_error must be a Decimal")

    conventional_true_value = calculate_conventional_true_value(
        indicated_value=indicated_value,
        e=e,
        additional_load=additional_load,
    )

    error = calculate_error(
        conventional_true_value=conventional_true_value,
        reference_load=reference_load,
    )

    corrected_error = calculate_corrected_error(
        error=error,
        zero_error=zero_error,
    )

    return CommonErrorResult(
        indicated_value=indicated_value,
        e=e,
        additional_load=additional_load,
        conventional_true_value=conventional_true_value,
        reference_load=reference_load,
        error=error,
        zero_error=zero_error,
        corrected_error=corrected_error,
    )