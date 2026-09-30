# backend/tests/calculation_engine/test_mpe.py

from decimal import Decimal

import pytest

from app.services.calculation_engine.mpe import resolve_mpe


MPE_RULES = {
    "initial_verification": {
        "I": [
            {
                "rule_id": "MPE_I_001",
                "min_e": 0,
                "max_e": 500,
                "mpe_multiplier_e": "0.5",
            },
            {
                "rule_id": "MPE_I_002",
                "min_e": 500,
                "max_e": 2000,
                "mpe_multiplier_e": "1.0",
            },
            {
                "rule_id": "MPE_I_003",
                "min_e": 2000,
                "max_e": 10000,
                "mpe_multiplier_e": "1.5",
            },
        ],
        "II": [],
        "III": [
            {
                "rule_id": "MPE_III_001",
                "min_e": 0,
                "max_e": 500,
                "mpe_multiplier_e": "0.5",
            },
            {
                "rule_id": "MPE_III_002",
                "min_e": 500,
                "max_e": 2000,
                "mpe_multiplier_e": "1.0",
            },
            {
                "rule_id": "MPE_III_003",
                "min_e": 2000,
                "max_e": 10000,
                "mpe_multiplier_e": "1.5",
            },
        ],
        "IIII": [],
    }
}


def test_class_iii_low_load_uses_half_e():
    result = resolve_mpe(
        accuracy_class="III",
        load=Decimal("5"),
        e=Decimal("0.01"),
        basis="initial_verification",
        rules=MPE_RULES,
    )

    assert result.value == Decimal("0.005")
    assert result.multiplier == Decimal("0.5")
    assert result.rule_id == "MPE_III_001"


def test_class_iii_middle_load_uses_one_e():
    result = resolve_mpe(
        accuracy_class="III",
        load=Decimal("10"),
        e=Decimal("0.01"),
        basis="initial_verification",
        rules=MPE_RULES,
    )

    assert result.value == Decimal("0.01")
    assert result.multiplier == Decimal("1.0")
    assert result.rule_id == "MPE_III_002"


def test_class_iii_high_load_uses_one_and_half_e():
    result = resolve_mpe(
        accuracy_class="III",
        load=Decimal("25"),
        e=Decimal("0.01"),
        basis="initial_verification",
        rules=MPE_RULES,
    )

    assert result.value == Decimal("0.015")
    assert result.multiplier == Decimal("1.5")
    assert result.rule_id == "MPE_III_003"


def test_negative_load_is_rejected():
    with pytest.raises(ValueError, match="load cannot be negative"):
        resolve_mpe(
            accuracy_class="III",
            load=Decimal("-1"),
            e=Decimal("0.01"),
            basis="initial_verification",
            rules=MPE_RULES,
        )


def test_zero_e_is_rejected():
    with pytest.raises(ValueError, match="e must be greater than zero"):
        resolve_mpe(
            accuracy_class="III",
            load=Decimal("10"),
            e=Decimal("0"),
            basis="initial_verification",
            rules=MPE_RULES,
        )


def test_invalid_accuracy_class_is_rejected():
    with pytest.raises(ValueError, match="Unsupported accuracy class"):
        resolve_mpe(
            accuracy_class="V",
            load=Decimal("10"),
            e=Decimal("0.01"),
            basis="initial_verification",
            rules=MPE_RULES,
        )


def test_empty_class_rules_are_rejected():
    with pytest.raises(ValueError, match="No MPE rules available"):
        resolve_mpe(
            accuracy_class="II",
            load=Decimal("10"),
            e=Decimal("0.01"),
            basis="initial_verification",
            rules=MPE_RULES,
        )