# backend/tests/calculation_engine/test_result_builder.py

from decimal import Decimal

import pytest

from backend.app.services.calculation_engine.result_builder import (
    CalculationResult,
    build_fail_result,
    build_na_result,
    build_pass_result,
    build_result,
)


def test_build_result_creates_standard_result():
    result = build_result(
        test_code="WP",
        status="PASS",
        measured_value=Decimal("0.003"),
        limit=Decimal("0.005"),
        error=Decimal("0.003"),
        unit="kg",
        rule_id="MPE_III_001",
        clause_reference="3.5",
        message="Within permissible error.",
    )

    assert isinstance(result, CalculationResult)
    assert result.test_code == "WP"
    assert result.status == "PASS"
    assert result.measured_value == Decimal("0.003")
    assert result.limit == Decimal("0.005")
    assert result.error == Decimal("0.003")
    assert result.unit == "kg"
    assert result.rule_id == "MPE_III_001"
    assert result.clause_reference == "3.5"


def test_status_is_normalized():
    result = build_result(
        test_code="WP",
        status=" pass ",
    )

    assert result.status == "PASS"


def test_invalid_status_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unsupported result status",
    ):
        build_result(
            test_code="WP",
            status="UNKNOWN",
        )


def test_missing_test_code_is_rejected():
    with pytest.raises(
        ValueError,
        match="test_code is required",
    ):
        build_result(
            test_code="",
            status="PASS",
        )


def test_pass_result_builder():
    result = build_pass_result(
        test_code="REP",
        measured_value=Decimal("0.01"),
        limit=Decimal("0.02"),
    )

    assert result.status == "PASS"
    assert result.test_code == "REP"


def test_fail_result_builder():
    result = build_fail_result(
        test_code="DIS",
        measured_value=Decimal("0.03"),
        limit=Decimal("0.02"),
    )

    assert result.status == "FAIL"
    assert result.test_code == "DIS"


def test_na_result_builder():
    result = build_na_result(
        test_code="ECC_WEIGHT",
        message="Test not applicable.",
    )

    assert result.status == "N/A"
    assert result.test_code == "ECC_WEIGHT"
    assert result.message == "Test not applicable."


def test_details_default_to_empty_mapping():
    result = build_result(
        test_code="WP",
        status="PASS",
    )

    assert result.details == {}


def test_details_are_preserved():
    details = {
        "load": Decimal("10"),
        "mpe": Decimal("0.01"),
    }

    result = build_result(
        test_code="WP",
        status="PASS",
        details=details,
    )

    assert result.details == details
