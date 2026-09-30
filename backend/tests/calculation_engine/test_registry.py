from decimal import Decimal

from backend.app.services.calculation_engine.context import (
    EvaluationContext,
    InstrumentContext,
    RuleSet,
)
from backend.app.services.calculation_engine.engine import CalculationRequest
from backend.app.services.calculation_engine.registry import (
    create_calculation_engine,
    create_r76_calculation_engine,
)


def make_instrument() -> InstrumentContext:
    return InstrumentContext(
        accuracy_class="III",
        max_capacity=Decimal("30"),
        min_capacity=Decimal("0.2"),
        e=Decimal("0.01"),
        d=Decimal("0.01"),
    )


def make_evaluation() -> EvaluationContext:
    return EvaluationContext()


def make_engine():
    return create_r76_calculation_engine(
        instrument=make_instrument(),
        evaluation=make_evaluation(),
    )


def test_all_prototype_tests_are_registered():
    engine = create_calculation_engine(
        instrument=make_instrument(),
        evaluation=make_evaluation(),
        rules=RuleSet(
            ruleset_version="R76-1:2006",
        ),
    )

    expected = {
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

    assert set(engine.registered_tests()) == expected


def test_create_r76_calculation_engine_loads_real_rules():
    engine = create_r76_calculation_engine(
        instrument=make_instrument(),
        evaluation=make_evaluation(),
    )

    assert engine.rules.ruleset_version == "R76-1:2006"
    assert len(engine.registered_tests()) == 12
    assert len(engine.rules.tests["tests"]) == 12
    assert "initial_verification" in engine.rules.mpe_rules


def test_create_r76_calculation_engine_executes_wp():
    engine = make_engine()

    result = engine.calculate(
        CalculationRequest(
            test_code="WP",
            inputs={
                "measurements": [
                    {
                        "load": Decimal("10"),
                        "indication": Decimal("10.005"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0.001"),
                    }
                ],
            },
        )
    )

    assert result.test_code == "WP"
    assert result.status == "PASS"


# ---------------------------------------------------------------------------
# Individual calculation-engine integration tests
# ---------------------------------------------------------------------------


def test_registry_executes_temp_static():
    engine = make_engine()

    observations = []

    for temperature in (
        Decimal("20"),
        Decimal("40"),
        Decimal("-10"),
        Decimal("5"),
        Decimal("20"),
    ):
        observations.append(
            {
                "temperature": temperature,
                "loading": {
                    "indicated_value": Decimal("9.995"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
                "unloading": {
                    "indicated_value": Decimal("9.995"),
                    "additional_load": Decimal("0"),
                    "zero_error": Decimal("0"),
                },
            }
        )

    result = engine.calculate(
        CalculationRequest(
            test_code="TEMP_STATIC",
            inputs={
                "load": Decimal("10"),
                "observations": observations,
            },
        )
    )

    assert result.test_code == "TEMP_STATIC"
    assert result.status == "PASS"
    assert result.details["failed_observations"] == 0


def test_registry_executes_temp_no_load():
    engine = make_engine()

    result = engine.calculate(
        CalculationRequest(
            test_code="TEMP_NO_LOAD",
            inputs={
                "observations": [
                    {
                        "temperature": Decimal("20"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "temperature": Decimal("40"),
                        "zero_error": Decimal("0.005"),
                    },
                    {
                        "temperature": Decimal("-10"),
                        "zero_error": Decimal("0.005"),
                    },
                ],
            },
        )
    )

    assert result.test_code == "TEMP_NO_LOAD"
    assert result.status == "PASS"
    assert result.details["failed_intervals"] == 0


def test_registry_executes_eccentricity():
    engine = make_engine()

    result = engine.calculate(
        CalculationRequest(
            test_code="ECC_WEIGHT",
            inputs={
                "measurements": [
                    {
                        "position": "Q1",
                        "load": Decimal("10"),
                        "indication": Decimal("10.005"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "position": "Q2",
                        "load": Decimal("10"),
                        "indication": Decimal("10.000"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "position": "Q3",
                        "load": Decimal("10"),
                        "indication": Decimal("10.003"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "position": "Q4",
                        "load": Decimal("10"),
                        "indication": Decimal("9.995"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                ],
            },
        )
    )

    assert result.test_code == "ECC_WEIGHT"
    assert result.status == "PASS"
    assert result.details["position_count"] == 4
    assert result.details["failed_positions"] == 0


def test_registry_executes_repeatability():
    engine = make_engine()

    def make_series(series_id: str, load: Decimal):
        return {
            "series_id": series_id,
            "measurements": [
                {
                    "load": load,
                    "indication": load - Decimal("0.005"),
                    "additional_load": Decimal("0"),
                }
                for _ in range(10)
            ],
        }

    result = engine.calculate(
        CalculationRequest(
            test_code="REP",
            inputs={
                "series": [
                    make_series(
                        "50_PERCENT_MAX",
                        Decimal("15"),
                    ),
                    make_series(
                        "100_PERCENT_MAX",
                        Decimal("30"),
                    ),
                ],
            },
        )
    )

    assert result.test_code == "REP"
    assert result.status == "PASS"
    assert result.details["series_count"] == 2
    assert result.details["total_failed_measurements"] == 0


def test_registry_executes_discrimination():
    engine = make_engine()

    d = Decimal("0.01")

    result = engine.calculate(
        CalculationRequest(
            test_code="DIS",
            inputs={
                "loads": [
                    {
                        "load": Decimal("0.2"),
                        "initial_indication": Decimal("0.2"),
                        "decreased_indication": Decimal("0.19"),
                        "increased_indication": Decimal("0.21"),
                    },
                    {
                        "load": Decimal("15"),
                        "initial_indication": Decimal("15"),
                        "decreased_indication": Decimal("14.99"),
                        "increased_indication": Decimal("15.01"),
                    },
                    {
                        "load": Decimal("30"),
                        "initial_indication": Decimal("30"),
                        "decreased_indication": Decimal("29.99"),
                        "increased_indication": Decimal("30.01"),
                    },
                ],
            },
        )
    )

    assert result.test_code == "DIS"
    assert result.status == "PASS"
    assert result.details["load_count"] == 3
    assert result.details["failed_loads"] == 0
    assert result.details["d"] == d


def test_registry_executes_zero_return():
    engine = make_engine()

    result = engine.calculate(
        CalculationRequest(
            test_code="ZR",
            inputs={
                "load": Decimal("30"),
                "zero_before": Decimal("0"),
                "zero_after": Decimal("0.002"),
                "automatic_zero_tracking_disabled": True,
            },
        )
    )

    assert result.test_code == "ZR"
    assert result.status == "PASS"
    assert result.measured_value == Decimal("0.002")
    assert result.limit == Decimal("0.005")


def test_registry_executes_creep():
    engine = make_engine()

    result = engine.calculate(
        CalculationRequest(
            test_code="CRP",
            inputs={
                "load": Decimal("30"),
                "readings": [
                    {
                        "time_minutes": Decimal("0"),
                        "indication": Decimal("29.995"),
                        "additional_load": Decimal("0"),
                    },
                    {
                        "time_minutes": Decimal("5"),
                        "indication": Decimal("29.995"),
                        "additional_load": Decimal("0"),
                    },
                    {
                        "time_minutes": Decimal("15"),
                        "indication": Decimal("29.995"),
                        "additional_load": Decimal("0"),
                    },
                    {
                        "time_minutes": Decimal("30"),
                        "indication": Decimal("29.995"),
                        "additional_load": Decimal("0"),
                    },
                ],
                "temperatures": [
                    Decimal("20"),
                    Decimal("20"),
                    Decimal("20"),
                    Decimal("20"),
                ],
            },
        )
    )

    assert result.test_code == "CRP"
    assert result.status == "PASS"
    assert result.details["termination"] == "30_MINUTES"
    assert result.details["early_condition_pass"] is True


def test_registry_executes_tare():
    engine = make_engine()

    tare_value = Decimal("10")
    maximum_tare = Decimal("15")

    loads = [
        Decimal("0.2"),
        Decimal("5"),
        Decimal("10"),
        Decimal("15"),
        Decimal("20"),
    ]

    def make_measurements():
        return [
            {
                "load": load,
                "indication": load - Decimal("0.005"),
                "additional_load": Decimal("0"),
                "zero_error": Decimal("0"),
            }
            for load in loads
        ]

    result = engine.calculate(
        CalculationRequest(
            test_code="TARE",
            inputs={
                "tare_value": tare_value,
                "maximum_tare": maximum_tare,
                "loading_measurements": make_measurements(),
                "unloading_measurements": make_measurements(),
            },
        )
    )

    assert result.test_code == "TARE"
    assert result.status == "PASS"
    assert result.details["loading_count"] == 5
    assert result.details["unloading_count"] == 5
    assert result.details["failed_measurements"] == 0


def test_registry_executes_warmup():
    engine = make_engine()

    result = engine.calculate(
        CalculationRequest(
            test_code="WARMUP",
            inputs={
                "power_off_hours": Decimal("8"),
                "load": Decimal("30"),
                "observations": [
                    {
                        "elapsed_minutes": 5,
                        "indication": Decimal("29.995"),
                        "zero_error": Decimal("0"),
                        "additional_load": Decimal("0"),
                    },
                    {
                        "elapsed_minutes": 15,
                        "indication": Decimal("29.995"),
                        "zero_error": Decimal("0"),
                        "additional_load": Decimal("0"),
                    },
                    {
                        "elapsed_minutes": 30,
                        "indication": Decimal("29.995"),
                        "zero_error": Decimal("0"),
                        "additional_load": Decimal("0"),
                    },
                ],
            },
        )
    )

    assert result.test_code == "WARMUP"
    assert result.status == "PASS"
    assert result.details["measurement_count"] == 3
    assert result.details["failed_measurements"] == 0


def test_registry_executes_voltage():
    engine = make_engine()

    result = engine.calculate(
        CalculationRequest(
            test_code="VOLT",
            inputs={
                "load": Decimal("0.10"),
                "observations": [
                    {
                        "voltage": Decimal("195.5"),
                        "indication": Decimal("0.095"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "voltage": Decimal("230"),
                        "indication": Decimal("0.095"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                    {
                        "voltage": Decimal("253"),
                        "indication": Decimal("0.095"),
                        "additional_load": Decimal("0"),
                        "zero_error": Decimal("0"),
                    },
                ],
            },
        )
    )

    assert result.test_code == "VOLT"
    assert result.status == "PASS"
    assert result.details["lower_voltage"] == Decimal("195.50")
    assert result.details["upper_voltage"] == Decimal("253.0")
    assert result.details["measurement_count"] == 3
    assert result.details["failed_measurements"] == 0


def test_registry_executes_span_stability():
    engine = make_engine()

    initial_readings = [
        {
            "indication": Decimal("29.995"),
            "additional_load": Decimal("0"),
            "zero_error": Decimal("0"),
        }
        for _ in range(5)
    ]

    measurements = [
        {
            "indication": Decimal("29.995"),
            "additional_load": Decimal("0"),
            "zero_error": Decimal("0"),
        }
        for _ in range(8)
    ]

    result = engine.calculate(
        CalculationRequest(
            test_code="SPAN",
            inputs={
                "load": Decimal("30"),
                "power_disconnections": [
                    Decimal("8"),
                    Decimal("8"),
                ],
                "initial_readings": initial_readings,
                "measurements": measurements,
            },
        )
    )

    assert result.test_code == "SPAN"
    assert result.status == "PASS"
    assert result.details["individual_mpe_failures"] == 0
    assert result.details["variation_pass"] is True
