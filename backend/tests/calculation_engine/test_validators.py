# backend/tests/calculation_engine/test_validators.py

from decimal import Decimal

import pytest

from app.services.calculation_engine.validators import (
    validate_accuracy_class,
    validate_decimal,
    validate_load,
    validate_load_within_range,
    validate_non_negative_decimal,
    validate_positive_decimal,
    validate_positive_e,
    validate_sequence_not_empty,
)


def test_validate_decimal_accepts_decimal():
    validate_decimal(
        Decimal("10"),
        field_name="value",
    )


def test_validate_decimal_rejects_non_decimal():
    with pytest.raises(
        TypeError,
        match="value must be a Decimal",
    ):
        validate_decimal(
            10,
            field_name="value",
        )


def test_positive_decimal_accepts_positive_value():
    validate_positive_decimal(
        Decimal("0.01"),
        field_name="value",
    )


def test_positive_decimal_rejects_zero():
    with pytest.raises(
        ValueError,
        match="value must be greater than zero",
    ):
        validate_positive_decimal(
            Decimal("0"),
            field_name="value",
        )


def test_non_negative_decimal_accepts_zero():
    validate_non_negative_decimal(
        Decimal("0"),
        field_name="value",
    )


def test_non_negative_decimal_rejects_negative_value():
    with pytest.raises(
        ValueError,
        match="value cannot be negative",
    ):
        validate_non_negative_decimal(
            Decimal("-1"),
            field_name="value",
        )


def test_accuracy_class_is_normalized():
    result = validate_accuracy_class(" iii ")

    assert result == "III"


def test_invalid_accuracy_class_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unsupported accuracy class",
    ):
        validate_accuracy_class("V")


def test_positive_e_is_valid():
    validate_positive_e(Decimal("0.01"))


def test_load_validation():
    validate_load(Decimal("10"))

    with pytest.raises(
        ValueError,
        match="load cannot be negative",
    ):
        validate_load(Decimal("-1"))


def test_load_within_range():
    validate_load_within_range(
        load=Decimal("10"),
        min_capacity=Decimal("0.2"),
        max_capacity=Decimal("30"),
    )


def test_load_below_minimum_is_rejected():
    with pytest.raises(
        ValueError,
        match="outside the instrument capacity range",
    ):
        validate_load_within_range(
            load=Decimal("0.1"),
            min_capacity=Decimal("0.2"),
            max_capacity=Decimal("30"),
        )


def test_load_above_maximum_is_rejected():
    with pytest.raises(
        ValueError,
        match="outside the instrument capacity range",
    ):
        validate_load_within_range(
            load=Decimal("30.01"),
            min_capacity=Decimal("0.2"),
            max_capacity=Decimal("30"),
        )


def test_invalid_capacity_range_is_rejected():
    with pytest.raises(
        ValueError,
        match="min_capacity cannot exceed max_capacity",
    ):
        validate_load_within_range(
            load=Decimal("10"),
            min_capacity=Decimal("30"),
            max_capacity=Decimal("20"),
        )


def test_non_empty_sequence_is_valid():
    validate_sequence_not_empty(
        [Decimal("1"), Decimal("2")],
        field_name="observations",
    )


def test_empty_sequence_is_rejected():
    with pytest.raises(
        ValueError,
        match="observations cannot be empty",
    ):
        validate_sequence_not_empty(
            [],
            field_name="observations",
        )