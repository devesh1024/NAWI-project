from datetime import datetime, timezone

# Synthetic demonstration data for the NAWI PDF generator.
# These values are for software/report-format testing only.

UTC = timezone.utc


def obs(observation_id, name, code, value, unit, sequence, remarks=""):
    return {
        "observation_id": observation_id,
        "parameter_name": name,
        "parameter_code": code,
        "value_numeric": value,
        "value_text": None,
        "unit": unit,
        "sequence_no": sequence,
        "source": "manual",
        "remarks": remarks,
    }


def calc(calculation_id, calculation_type, value, unit, formula, version="v1.0"):
    return {
        "calculation_id": calculation_id,
        "calculation_type": calculation_type,
        "calculated_value": value,
        "unit": unit,
        "formula": formula,
        "calculation_version": version,
    }


def result(
    result_id,
    measured,
    mpe,
    error,
    corrected_error,
    acceptance,
    pass_fail,
    summary,
    version="v1.0",
):
    return {
        "result_id": result_id,
        "measured_value": measured,
        "mpe_value": mpe,
        "error_value": error,
        "corrected_error": corrected_error,
        "acceptance_condition": acceptance,
        "pass_fail": pass_fail,
        "result_summary": summary,
        "calculation_version": version,
    }


def test_record(
    session_test_id,
    definition_id,
    code,
    name,
    category,
    procedure,
    observations,
    calculations,
    results,
    requirement=None,
    remarks="Synthetic demonstration record.",
):
    return {
        "session_test_id": session_test_id,
        "test_definition_id": definition_id,
        "test_code": code,
        "test_name": name,
        "category": category,
        "reference_clause": "OIML R 76-1:2006 — applicable test definition",
        "procedure": procedure,
        "applicability_status": "APPLICABLE",
        "na_reason": None,
        "status": "COMPLETED",
        "result": "PASS",
        "observations": observations,
        "calculations": calculations,
        "results": results,
        "requirement": requirement,
        "remarks": remarks,
        "calculation_version": "v1.0",
        "ruleset_version": "R76-2006-v1.0",
    }


SAMPLE_REPORT_DATA = {
    "laboratory": {
        "laboratory_id": "lab-001",
        "laboratory_code": "LAB-001",
        "name": "National Weighing Instruments Laboratory",
        "registration_number": "LAB/2026/001",
        "address": "Industrial Area, Sector 5",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "pincode": "452001",
        "country": "India",
        "phone": "+91-9876543210",
        "email": "lab@example.com",
    },

    "instrument": {
        "instrument_id": "inst-001",
        "instrument_code": "NAWI-001",
        "manufacturer": "ABC Instruments",
        "model": "W-500",
        "type_designation": "W500-Series",
        "serial_number": "SN20260001",
        "instrument_type": "Non-Automatic Weighing Instrument",
        "category": "Electronic Weighing Instrument",
        "accuracy_class": "III",
        "max_capacity": 500,
        "min_capacity": 20,
        "verification_scale_interval": 0.1,
        "scale_interval": 0.1,
        "number_of_intervals": 4800,
        "unit": "kg",
        "indication_type": "Digital",
        "software_firmware": "FW-2.4.1",
    },

    "tester": {
        "user_id": "user-001",
        "employee_id": "EMP-102",
        "first_name": "Ramesh",
        "last_name": "Kumar",
        "name": "Ramesh Kumar",
        "email": "ramesh@example.com",
        "designation": "Senior Metrologist",
    },

    "standard": {
        "standard_id": "std-001",
        "standard_code": "OIML R 76-1",
        "title": "Non-automatic weighing instruments",
        "version": "2006",
        "edition_year": 2006,
        "source_document": "OIML R 76-1:2006",
        "source_url": "https://www.oiml.org/",
    },

    "test_session": {
        "test_session_id": "session-001",
        "session_number": "TS-2026-001",
        "application_number": "APP-2026-001",
        "test_type": "Initial Verification",
        "started_at": "2026-09-29T09:15:00+00:00",
        "completed_at": "2026-09-29T16:35:00+00:00",
        "status": "COMPLETED",
        "overall_result": "PASS",
        "remarks": "Instrument tested under controlled laboratory conditions.",
    },

    "report": {
        "report_number": "NAWI-2026-0007",
        "report_version": "1.0",
        "report_date": "2026-09-29T16:45:00+00:00",
        "generated_at": "2026-09-29T16:45:00+00:00",
        "generated_by": "NAWI Test & Compliance System",
        "report_status": "APPROVED",
        "overall_result": "PASS",
        "remarks": "All applicable prototype tests recorded in this demonstration report are within the stored acceptance criteria.",
        "reviewer": {
            "name": "Aparna Patel",
            "designation": "Laboratory Reviewer",
        },
        "reviewer_name": "Aparna Patel",
        "approved_by_name": "Aparna Patel",
        "approval_date": "2026-09-29T17:10:00+00:00",
        "approved_at": "2026-09-29T17:10:00+00:00",
        "report_hash": "DEMO-SHA256-9D7A-2026-0007",
        "digital_signatures": [
            {
                "status": "APPROVED",
                "signed_at": "2026-09-29T17:10:00+00:00",
            }
        ],
    },

    "test_equipment": [
        {
            "equipment_code": "EQ-WGT-001",
            "equipment_name": "Standard Test Weights M1",
            "model": "Weight Set WS-2026-019",
            "serial_number": "WS-2026-019",
            "identification_number": "EQ-WGT-001",
            "calibration_status": "VALID",
            "calibration_date": "2026-07-01",
            "calibration_due_date": "2027-06-30",
            "used_from": "2026-09-29T09:20:00+00:00",
            "used_to": "2026-09-29T16:00:00+00:00",
            "remarks": "Calibration certificate verified before use.",
        },
        {
            "equipment_code": "EQ-TMP-001",
            "equipment_name": "Temperature / RH Logger",
            "model": "TH-500",
            "serial_number": "TH500-2218",
            "identification_number": "EQ-TMP-001",
            "calibration_status": "VALID",
            "calibration_date": "2026-08-15",
            "calibration_due_date": "2027-08-14",
            "used_from": "2026-09-29T09:00:00+00:00",
            "used_to": "2026-09-29T16:30:00+00:00",
            "remarks": "Environmental logger active throughout the session.",
        },
        {
            "equipment_code": "EQ-DMM-001",
            "equipment_name": "Digital Multimeter",
            "model": "DMM-850",
            "serial_number": "DMM850-4402",
            "identification_number": "EQ-DMM-001",
            "calibration_status": "VALID",
            "calibration_date": "2026-06-20",
            "calibration_due_date": "2027-06-19",
            "used_from": "2026-09-29T12:00:00+00:00",
            "used_to": "2026-09-29T15:30:00+00:00",
            "remarks": "Voltage verification completed before use.",
        },
    ],

    "environmental_conditions": [
        {
            "temperature": 23.1,
            "humidity": 48,
            "pressure": 1008,
            "recorded_at": "2026-09-29T09:20:00+00:00",
            "recorded_by": "EMP-102",
            "source": "EQ-TMP-001",
            "remarks": "Conditions stable at session start.",
        },
        {
            "temperature": 23.4,
            "humidity": 50,
            "pressure": 1007,
            "recorded_at": "2026-09-29T16:30:00+00:00",
            "recorded_by": "EMP-102",
            "source": "EQ-TMP-001",
            "remarks": "Conditions remained within laboratory operating range.",
        },
    ],

    "tests": [
        test_record(
            "session-test-001",
            "test-def-001",
            "WP",
            "Weighing Performance",
            "Performance",
            "Apply selected test loads over the measurement range and compare the indication with the reference test load.",
            [
                obs("obs-wp-1", "Test Load", "LOAD", 100.0, "kg", 1),
                obs("obs-wp-2", "Indicated Value", "IND", 100.1, "kg", 2),
                obs("obs-wp-3", "Test Load", "LOAD", 300.0, "kg", 3),
                obs("obs-wp-4", "Indicated Value", "IND", 300.2, "kg", 4),
            ],
            [
                calc("calc-wp-1", "Error at 100 kg", 0.1, "kg", "Indicated Value - Test Load"),
                calc("calc-wp-2", "Error at 300 kg", 0.2, "kg", "Indicated Value - Test Load"),
            ],
            [
                result("result-wp", 300.2, 0.5, 0.2, 0.2, "Absolute error ≤ MPE", "PASS",
                       "Observed errors remain within the stored permissible error criterion.")
            ],
            requirement="Absolute error ≤ MPE",
        ),

        test_record(
            "session-test-002",
            "test-def-002",
            "TEMP_STATIC",
            "Static Temperatures",
            "Temperature",
            "Expose the instrument to the selected static temperature points and verify stable indication.",
            [
                obs("obs-ts-1", "Temperature Point 1", "TEMP1", 10.0, "°C", 1),
                obs("obs-ts-2", "Indication at 10 °C", "IND1", 100.0, "kg", 2),
                obs("obs-ts-3", "Temperature Point 2", "TEMP2", 20.0, "°C", 3),
                obs("obs-ts-4", "Indication at 20 °C", "IND2", 100.1, "kg", 4),
                obs("obs-ts-5", "Temperature Point 3", "TEMP3", 30.0, "°C", 5),
                obs("obs-ts-6", "Indication at 30 °C", "IND3", 100.1, "kg", 6),
            ],
            [
                calc("calc-ts-1", "Maximum indication variation", 0.1, "kg", "Maximum indication - minimum indication"),
            ],
            [
                result("result-ts", 100.1, 0.5, 0.1, 0.1, "Maximum variation ≤ MPE", "PASS",
                       "Indication remained stable over the selected temperature points.")
            ],
            requirement="Maximum indication variation ≤ MPE",
        ),

        test_record(
            "session-test-003",
            "test-def-003",
            "TEMP_NO_LOAD",
            "Temperature Effect on No-Load Indication",
            "Temperature",
            "Record the no-load indication at the selected temperature points and determine the maximum zero shift.",
            [
                obs("obs-tnl-1", "Temperature Point 1", "TEMP1", 10.0, "°C", 1),
                obs("obs-tnl-2", "Zero Indication", "ZERO1", 0.0, "kg", 2),
                obs("obs-tnl-3", "Temperature Point 2", "TEMP2", 20.0, "°C", 3),
                obs("obs-tnl-4", "Zero Indication", "ZERO2", 0.1, "kg", 4),
                obs("obs-tnl-5", "Temperature Point 3", "TEMP3", 30.0, "°C", 5),
                obs("obs-tnl-6", "Zero Indication", "ZERO3", 0.1, "kg", 6),
            ],
            [
                calc("calc-tnl-1", "Maximum zero shift", 0.1, "kg", "Maximum zero indication - minimum zero indication"),
            ],
            [
                result("result-tnl", 0.1, 0.5, 0.1, 0.1, "Zero indication variation ≤ MPE", "PASS",
                       "No-load indication remained within the stored acceptance criterion.")
            ],
            requirement="Zero indication variation ≤ MPE",
        ),

        test_record(
            "session-test-004",
            "test-def-004",
            "ECC_WEIGHT",
            "Eccentricity Using Weights",
            "Eccentricity",
            "Apply the specified eccentric load successively at each corner/position and compare the indications.",
            [
                obs("obs-ecc-1", "Q1", "Q1", 50.1, "kg", 1),
                obs("obs-ecc-2", "Q2", "Q2", 49.9, "kg", 2),
                obs("obs-ecc-3", "Q3", "Q3", 50.0, "kg", 3),
                obs("obs-ecc-4", "Q4", "Q4", 50.1, "kg", 4),
                obs("obs-ecc-5", "Reference Load", "REF", 50.0, "kg", 5),
            ],
            [
                calc("calc-ecc-1", "Maximum eccentric error", 0.1, "kg", "Maximum absolute deviation from reference load"),
            ],
            [
                result("result-ecc", 50.1, 0.5, 0.1, 0.1, "Maximum eccentric error ≤ MPE", "PASS",
                       "All four test positions remain within the stored permissible error criterion.")
            ],
            requirement="Maximum eccentric error ≤ MPE",
        ),

        test_record(
            "session-test-005",
            "test-def-005",
            "REP",
            "Repeatability",
            "Repeatability",
            "Apply the specified test load repeatedly under the same conditions and evaluate the spread of indications.",
            [
                obs("obs-rep-1", "Trial 1", "T1", 50.0, "kg", 1),
                obs("obs-rep-2", "Trial 2", "T2", 50.1, "kg", 2),
                obs("obs-rep-3", "Trial 3", "T3", 49.9, "kg", 3),
                obs("obs-rep-4", "Trial 4", "T4", 50.0, "kg", 4),
                obs("obs-rep-5", "Trial 5", "T5", 50.1, "kg", 5),
            ],
            [
                calc("calc-rep-1", "Indication spread", 0.2, "kg", "Maximum indication - minimum indication"),
            ],
            [
                result("result-rep", 50.1, 0.5, 0.2, 0.2, "Indication spread ≤ MPE", "PASS",
                       "Repeated indications show acceptable repeatability.")
            ],
            requirement="Indication spread ≤ MPE",
        ),

        test_record(
            "session-test-006",
            "test-def-006",
            "DIS",
            "Discrimination",
            "Discrimination",
            "Introduce a small additional load near the selected test point and verify a detectable indication change.",
            [
                obs("obs-dis-1", "Initial Load", "LOAD", 20.0, "kg", 1),
                obs("obs-dis-2", "Initial Indication", "IND1", 20.0, "kg", 2),
                obs("obs-dis-3", "Added Load", "ADD", 0.1, "kg", 3),
                obs("obs-dis-4", "Final Indication", "IND2", 20.1, "kg", 4),
            ],
            [
                calc("calc-dis-1", "Indication change", 0.1, "kg", "Final indication - initial indication"),
            ],
            [
                result("result-dis", 20.1, 0.5, 0.1, 0.1, "Required indication change is achieved", "PASS",
                       "The selected small load produced the required indication change.")
            ],
            requirement="Required indication change is achieved",
        ),

        test_record(
            "session-test-007",
            "test-def-007",
            "ZR",
            "Zero Return",
            "Zero",
            "Apply a test load, remove it, and verify the returned no-load indication.",
            [
                obs("obs-zr-1", "Applied Load", "LOAD", 100.0, "kg", 1),
                obs("obs-zr-2", "Indication Before Removal", "BEFORE", 100.1, "kg", 2),
                obs("obs-zr-3", "Returned Zero", "ZERO", 0.1, "kg", 3),
            ],
            [
                calc("calc-zr-1", "Zero return deviation", 0.1, "kg", "Returned zero indication - nominal zero"),
            ],
            [
                result("result-zr", 0.1, 0.5, 0.1, 0.1, "Zero return deviation ≤ MPE", "PASS",
                       "The instrument returned within the stored zero-return criterion.")
            ],
            requirement="Zero return deviation ≤ MPE",
        ),

        test_record(
            "session-test-008",
            "test-def-008",
            "CRP",
            "Creep",
            "Time Stability",
            "Apply the specified load and compare the indication at the start and end of the observation period.",
            [
                obs("obs-crp-1", "Applied Load", "LOAD", 200.0, "kg", 1),
                obs("obs-crp-2", "Initial Indication", "I0", 200.1, "kg", 2),
                obs("obs-crp-3", "Final Indication", "I30", 200.2, "kg", 3),
                obs("obs-crp-4", "Observation Time", "TIME", 30, "min", 4),
            ],
            [
                calc("calc-crp-1", "Creep", 0.1, "kg", "Final indication - initial indication"),
            ],
            [
                result("result-crp", 200.2, 0.5, 0.1, 0.1, "Creep ≤ MPE", "PASS",
                       "Indication drift during the observation interval remained within the stored criterion.")
            ],
            requirement="Creep ≤ MPE",
        ),

        test_record(
            "session-test-009",
            "test-def-009",
            "TARE",
            "Tare Weighing Test",
            "Tare",
            "Determine tare indication and verify the net indication after application of a known gross load.",
            [
                obs("obs-tare-1", "Tare Load", "TARE", 5.0, "kg", 1),
                obs("obs-tare-2", "Gross Load", "GROSS", 25.0, "kg", 2),
                obs("obs-tare-3", "Net Indication", "NET", 20.0, "kg", 3),
                obs("obs-tare-4", "Expected Net", "EXPECTED", 20.0, "kg", 4),
            ],
            [
                calc("calc-tare-1", "Tare error", 0.0, "kg", "Net indication - expected net indication"),
            ],
            [
                result("result-tare", 20.0, 0.5, 0.0, 0.0, "Tare error ≤ MPE", "PASS",
                       "Tare subtraction produces the expected net indication.")
            ],
            requirement="Tare error ≤ MPE",
        ),

        test_record(
            "session-test-010",
            "test-def-010",
            "WARMUP",
            "Warm-up Time",
            "Warm-up",
            "Record the instrument indication immediately after power-on and after the specified warm-up period.",
            [
                obs("obs-wu-1", "Warm-up Start", "T0", 0.0, "kg", 1),
                obs("obs-wu-2", "Warm-up Time", "TIME", 15, "min", 2),
                obs("obs-wu-3", "Post Warm-up Indication", "T15", 0.0, "kg", 3),
            ],
            [
                calc("calc-wu-1", "Warm-up zero drift", 0.0, "kg", "Post warm-up indication - initial indication"),
            ],
            [
                result("result-wu", 0.0, 0.5, 0.0, 0.0, "Warm-up drift ≤ MPE", "PASS",
                       "No material zero drift was observed after the selected warm-up period.")
            ],
            requirement="Warm-up drift ≤ MPE",
        ),

        test_record(
            "session-test-011",
            "test-def-011",
            "VOLT",
            "Voltage Variations",
            "Electrical",
            "Operate the instrument at the selected supply-voltage conditions and record the resulting indication.",
            [
                obs("obs-v-1", "Supply Voltage Low", "VLOW", 198.0, "V", 1),
                obs("obs-v-2", "Indication at Low Voltage", "ILOW", 100.0, "kg", 2),
                obs("obs-v-3", "Nominal Supply Voltage", "VNOM", 230.0, "V", 3),
                obs("obs-v-4", "Indication at Nominal Voltage", "INOM", 100.1, "kg", 4),
                obs("obs-v-5", "Supply Voltage High", "VHIGH", 242.0, "V", 5),
                obs("obs-v-6", "Indication at High Voltage", "IHIGH", 100.2, "kg", 6),
            ],
            [
                calc("calc-v-1", "Maximum voltage-related indication error", 0.2, "kg", "Maximum absolute indication error across voltage points"),
            ],
            [
                result("result-v", 100.2, 0.5, 0.2, 0.2, "Maximum voltage-related error ≤ MPE", "PASS",
                       "The selected supply-voltage variations did not produce an indication error beyond the stored criterion.")
            ],
            requirement="Maximum voltage-related error ≤ MPE",
        ),

        test_record(
            "session-test-012",
            "test-def-012",
            "SPAN",
            "Span Stability",
            "Stability",
            "Compare the indication of a selected test load before and after the stability interval.",
            [
                obs("obs-span-1", "Initial Test Load", "LOAD", 100.0, "kg", 1),
                obs("obs-span-2", "Initial Indication", "I0", 100.0, "kg", 2),
                obs("obs-span-3", "Repeat Indication", "I1", 100.1, "kg", 3),
                obs("obs-span-4", "Stability Interval", "TIME", 120, "min", 4),
            ],
            [
                calc("calc-span-1", "Span drift", 0.1, "kg", "Repeat indication - initial indication"),
            ],
            [
                result("result-span", 100.1, 0.5, 0.1, 0.1, "Span drift ≤ MPE", "PASS",
                       "The indicated span remained within the stored stability criterion.")
            ],
            requirement="Span drift ≤ MPE",
        ),
    ],

    "construction_examination": [
        {
            "item": "Identification / marking",
            "status": "PASS",
            "remarks": "Required instrument identification markings are present in the demonstration record.",
        },
        {
            "item": "Indicating device and display",
            "status": "PASS",
            "remarks": "Display and indication functions are recorded as satisfactory.",
        },
        {
            "item": "Sealing / protection provisions",
            "status": "PASS",
            "remarks": "Protection and sealing provisions are recorded as satisfactory for the prototype record.",
        },
        {
            "item": "General construction condition",
            "status": "PASS",
            "remarks": "No visible construction non-conformity recorded in the demonstration record.",
        },
    ],

    "remarks": "Synthetic demonstration report containing all 12 prototype test records.",

    "non_conformities": [],

    "attachments": [
        {
            "attachment_id": "A1",
            "file_name": "Calibration_Certificate_EQ-WGT-001.pdf",
            "attachment_type": "Calibration Certificate",
            "description": "Demonstration reference for standard test weight set.",
        },
        {
            "attachment_id": "A2",
            "file_name": "Environmental_Log_TS-2026-001.pdf",
            "attachment_type": "Environmental Record",
            "description": "Demonstration environmental monitoring record for the test session.",
        },
    ],
}
