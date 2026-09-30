# backend/tests/calculation_engine/test_common_error.py

from decimal import Decimal

import pytest

from app.services.calculation_engine.common_error import (
    calculate_common_error,
    calculate_conventional_true_value,
    calculate_corrected_error,
    calculate_error,
)


def test_conventional_true_value():
    result = calculate_conventional_true_value(
        indicated_value=Decimal("10.00"),
        e=Decimal("0.01"),
        additional_load=Decimal("0.002"),
    )

    # P = I + 1/2 e - ΔL
    # P = 10.00 + 0.005 - 0.002
    # P = 10.003
    assert result == Decimal("10.003")


def test_error():
    result = calculate_error(
        conventional_true_value=Decimal("10.003"),
        reference_load=Decimal("10.000"),
    )

    # E = P - L
    assert result == Decimal("0.003")


def test_corrected_error():
    result = calculate_corrected_error(
        error=Decimal("0.003"),
        zero_error=Decimal("0.001"),
    )

    # Ec = E - E0
    assert result == Decimal("0.002")


def test_complete_common_error_calculation():
    result = calculate_common_error(
        indicated_value=Decimal("10.00"),
        e=Decimal("0.01"),
        additional_load=Decimal("0.002"),
        reference_load=Decimal("10.000"),
        zero_error=Decimal("0.001"),
    )

    assert result.conventional_true_value == Decimal("10.003")
    assert result.error == Decimal("0.003")
    assert result.zero_error == Decimal("0.001")
    assert result.corrected_error == Decimal("0.002")


def test_zero_error_defaults_to_zero():
    result = calculate_common_error(
        indicated_value=Decimal("10.00"),
        e=Decimal("0.01"),
        additional_load=Decimal("0.002"),
        reference_load=Decimal("10.000"),
    )

    assert result.zero_error == Decimal("0")
    assert result.corrected_error == Decimal("0.003")


def test_zero_e_is_rejected():
    with pytest.raises(ValueError, match="e must be greater than zero"):
        calculate_conventional_true_value(
            indicated_value=Decimal("10.00"),
            e=Decimal("0"),
            additional_load=Decimal("0"),
        )


def test_negative_additional_load_is_rejected():
    with pytest.raises(
        ValueError,
        match="additional_load cannot be negative",
    ):
        calculate_conventional_true_value(
            indicated_value=Decimal("10.00"),
            e=Decimal("0.01"),
            additional_load=Decimal("-0.001"),
        )