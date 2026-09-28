sample_report_data = {
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
        "email": "lab@example.com"
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
        "unit": "kg"
    },
    "tester": {
        "user_id": "user-001",
        "employee_id": "EMP-102",
        "first_name": "Ramesh",
        "last_name": "Kumar",
        "email": "ramesh@example.com",
        "designation": "Senior Metrologist"
    },
    "standard": {
        "standard_id": "std-001",
        "standard_code": "OIML R 76-1",
        "title": "Non-automatic weighing instruments",
        "version": "2006",
        "edition_year": 2006,
        "source_document": "OIML R 76-1",
        "source_url": "https://www.oiml.org/"
    },
    "test_session": {
        "test_session_id": "session-001",
        "session_number": "TS-2026-001",
        "application_number": "APP-2026-001",
        "test_type": "Initial Verification",
        "status": "COMPLETED",
        "overall_result": "PASS",
        "remarks": "Instrument tested under normal laboratory conditions."
    },
    "tests": [
        {
            "session_test_id": "session-test-001",
            "test_definition_id": "test-def-001",
            "applicability_status": "APPLICABLE",
            "na_reason": None,
            "status": "COMPLETED",
            "result": "PASS",
            "observations": [
                {"observation_id": "obs-001", "parameter_name": "Test Load", "parameter_code": "LOAD", "value_numeric": 100.0, "value_text": None, "unit": "kg", "sequence_no": 1, "source": "manual", "remarks": ""},
                {"observation_id": "obs-002", "parameter_name": "Indicated Value", "parameter_code": "IND", "value_numeric": 100.1, "value_text": None, "unit": "kg", "sequence_no": 2, "source": "manual", "remarks": ""}
            ],
            "calculations": [
                {"calculation_id": "calc-001", "calculation_type": "Error Calculation", "calculated_value": 0.1, "unit": "kg", "formula": "Indicated Value - Test Load", "calculation_version": "v1.0"}
            ],
            "results": [
                {"result_id": "result-001", "measured_value": 100.1, "mpe_value": 0.5, "error_value": 0.1, "corrected_error": 0.1, "acceptance_condition": "Absolute error ≤ MPE", "pass_fail": "PASS", "result_summary": "The instrument satisfies the permissible error requirement.", "calculation_version": "v1.0"}
            ]
        },
        {
            "session_test_id": "session-test-002",
            "test_definition_id": "test-def-002",
            "applicability_status": "NOT_APPLICABLE",
            "na_reason": "Test not applicable to this instrument configuration.",
            "status": "COMPLETED",
            "result": "N/A",
            "observations": [],
            "calculations": [],
            "results": []
        }
    ]
}
