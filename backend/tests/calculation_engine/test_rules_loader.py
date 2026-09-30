from app.services.calculation_engine.rules_loader import load_r76_rules


def test_load_r76_rules():
    rules = load_r76_rules()

    assert rules.ruleset_version == "R76-1:2006"

    assert "tests" in rules.tests
    assert "tests" in rules.applicability
    assert "tests" in rules.requirements
    assert "calculations" in rules.calculations
    assert "initial_verification" in rules.mpe_rules


def test_all_12_tests_are_present_in_loaded_rules():
    rules = load_r76_rules()

    expected_tests = {
        "WP",
        "TEMP_STATIC",
        "TEMP_NO_LOAD",
        "ECC_WEIGHT",
        "REP",
        "DIS",
        "ZR",
        "CRP",
        "TARE",
        "WARMUP",
        "VOLT",
        "SPAN",
    }

    actual_tests = {
        test["test_code"]
        for test in rules.tests["tests"]
    }

    assert actual_tests == expected_tests