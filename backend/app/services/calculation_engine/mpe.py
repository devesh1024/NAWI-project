# backend/app/services/calculation_engine/mpe.py

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping


@dataclass(frozen=True)
class MPEResolution:
    """
    Resolved Maximum Permissible Error (MPE) for a given load.
    """

    value: Decimal
    unit: str
    accuracy_class: str
    load: Decimal
    e: Decimal
    basis: str
    range_min: Decimal
    range_max: Decimal | None
    multiplier: Decimal
    rule_id: str


def resolve_mpe(
    *,
    accuracy_class: str,
    load: Decimal,
    e: Decimal,
    basis: str,
    rules: Mapping[str, Any],
) -> MPEResolution:
    """
    Resolve the applicable MPE from the supplied OIML rule data.

    Parameters
    ----------
    accuracy_class:
        NAWI accuracy class: I, II, III or IIII.

    load:
        Load being evaluated.

    e:
        Verification scale interval.

    basis:
        MPE basis, for example "initial_verification".

    rules:
        MPE rule mapping loaded from mpe_rules.json.
    """

    if not isinstance(load, Decimal):
        raise TypeError("load must be a Decimal")

    if not isinstance(e, Decimal):
        raise TypeError("e must be a Decimal")

    if e <= Decimal("0"):
        raise ValueError("e must be greater than zero")

    if load < Decimal("0"):
        raise ValueError("load cannot be negative")

    accuracy_class = accuracy_class.strip().upper()

    if accuracy_class not in {"I", "II", "III", "IIII"}:
        raise ValueError(
            f"Unsupported accuracy class: {accuracy_class}"
        )

    if not basis:
        raise ValueError("MPE basis is required")

    # The JSON structure is:
    #
    # {
    #     "initial_verification": {
    #         "III": [...]
    #     }
    # }
    #
    basis_rules = rules.get(basis.lower())

    if basis_rules is None:
        raise ValueError(
            f"No MPE rules found for basis '{basis}'"
        )

    class_rules = basis_rules.get(accuracy_class)

    if class_rules is None:
        raise ValueError(
            f"No MPE rules found for accuracy class "
            f"'{accuracy_class}' and basis '{basis}'"
        )

    if not isinstance(class_rules, list) or not class_rules:
        raise ValueError(
            f"No MPE rules available for accuracy class "
            f"'{accuracy_class}' and basis '{basis}'"
        )

    # Convert load into verification scale intervals.
    load_in_e = load / e

    selected_rule = None

    for rule in class_rules:
        min_e = Decimal(str(rule["min_e"]))
        max_e = Decimal(str(rule["max_e"]))

        if min_e <= load_in_e <= max_e:
            selected_rule = rule
            break

    if selected_rule is None:
        raise ValueError(
            f"No applicable MPE range found for "
            f"{load_in_e}e in accuracy class "
            f"{accuracy_class}"
        )

    multiplier = Decimal(
        str(selected_rule["mpe_multiplier_e"])
    )

    mpe = e * multiplier

    return MPEResolution(
        value=mpe,
        unit="kg",
        accuracy_class=accuracy_class,
        load=load,
        e=e,
        basis=basis,
        range_min=Decimal(
            str(selected_rule["min_e"])
        ),
        range_max=Decimal(
            str(selected_rule["max_e"])
        ),
        multiplier=multiplier,
        rule_id=str(selected_rule["rule_id"]),
    )