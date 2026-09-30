# backend/app/services/calculation_engine/validators.py

from __future__ import annotations

from decimal import Decimal
from typing import Iterable


SUPPORTED_ACCURACY_CLASSES = {"I", "II", "III", "IIII"}


def validate_decimal(
    value: Decimal,
    *,
    field_name: str,
) -> None:
    """
    Validate that a value is a Decimal.
    """

    if not isinstance(value, Decimal):
        raise TypeError(
            f"{field_name} must be a Decimal"
        )


def validate_positive_decimal(
    value: Decimal,
    *,
    field_name: str,
) -> None:
    """
    Validate that a Decimal is greater than zero.
    """

    validate_decimal(
        value,
        field_name=field_name,
    )

    if value <= Decimal("0"):
        raise ValueError(
            f"{field_name} must be greater than zero"
        )


def validate_non_negative_decimal(
    value: Decimal,
    *,
    field_name: str,
) -> None:
    """
    Validate that a Decimal is zero or greater.
    """

    validate_decimal(
        value,
        field_name=field_name,
    )

    if value < Decimal("0"):
        raise ValueError(
            f"{field_name} cannot be negative"
        )


def validate_accuracy_class(
    accuracy_class: str,
) -> str:
    """
    Validate and normalize an NAWI accuracy class.
    """

    if not isinstance(accuracy_class, str):
        raise TypeError(
            "accuracy_class must be a string"
        )

    normalized = accuracy_class.strip().upper()

    if normalized not in SUPPORTED_ACCURACY_CLASSES:
        raise ValueError(
            f"Unsupported accuracy class: {normalized}"
        )

    return normalized


def validate_positive_e(
    e: Decimal,
) -> None:
    """
    Validate the verification scale interval e.
    """

    validate_positive_decimal(
        e,
        field_name="e",
    )


def validate_load(
    load: Decimal,
) -> None:
    """
    Validate a load value.
    """

    validate_non_negative_decimal(
        load,
        field_name="load",
    )


def validate_load_within_range(
    *,
    load: Decimal,
    min_capacity: Decimal,
    max_capacity: Decimal,
) -> None:
    """
    Validate that a load lies within the instrument's
    configured weighing range.
    """

    validate_load(load)

    validate_non_negative_decimal(
        min_capacity,
        field_name="min_capacity",
    )

    validate_positive_decimal(
        max_capacity,
        field_name="max_capacity",
    )

    if min_capacity > max_capacity:
        raise ValueError(
            "min_capacity cannot exceed max_capacity"
        )

    if load < min_capacity or load > max_capacity:
        raise ValueError(
            "load is outside the instrument capacity range"
        )


def validate_sequence_not_empty(
    values: Iterable[object],
    *,
    field_name: str,
) -> None:
    """
    Validate that an iterable contains at least one value.
    """

    values = list(values)

    if not values:
        raise ValueError(
            f"{field_name} cannot be empty"
        )