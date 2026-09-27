from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_session import TestSession
from backend.app.models.laboratory import Laboratory
from backend.app.models.instrument import Instrument
from backend.app.models.user import User
from backend.app.models.standard import Standard
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.test_observation import TestObservation
from backend.app.models.test_calculation import TestCalculation
from backend.app.models.test_result import TestResult
from backend.app.utils.dependencies import get_current_user

router = APIRouter(
    prefix="/api/test-sessions",
    tags=["Reports"]
)


@router.get("/{test_session_id}/report-data")
def get_report_data(
    test_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get test session
    session = (
        db.query(TestSession)
        .filter(
            TestSession.test_session_id == test_session_id,
            TestSession.laboratory_id == current_user.laboratory_id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found"
        )

    # Get related data
    laboratory = db.query(Laboratory).filter(
        Laboratory.laboratory_id == session.laboratory_id
    ).first()

    instrument = db.query(Instrument).filter(
        Instrument.instrument_id == session.instrument_id
    ).first()

    tester = db.query(User).filter(
        User.user_id == session.tester_id
    ).first()

    standard = db.query(Standard).filter(
        Standard.standard_id == session.standard_id
    ).first()

    # Get tests
    session_tests = db.query(TestSessionTest).filter(
        TestSessionTest.test_session_id == session.test_session_id
    ).all()

    tests = []

    for session_test in session_tests:

        observations = db.query(TestObservation).filter(
            TestObservation.session_test_id == session_test.session_test_id
        ).all()

        calculations = db.query(TestCalculation).filter(
            TestCalculation.session_test_id == session_test.session_test_id
        ).all()

        results = db.query(TestResult).filter(
            TestResult.session_test_id == session_test.session_test_id
        ).all()

        tests.append({
            "session_test_id": str(session_test.session_test_id),
            "test_definition_id": str(session_test.test_definition_id),
            "applicability_status": session_test.applicability_status,
            "na_reason": session_test.na_reason,
            "status": session_test.status,
            "result": session_test.result,

            "observations": [
                {
                    "observation_id": str(o.observation_id),
                    "parameter_name": o.parameter_name,
                    "parameter_code": o.parameter_code,
                    "value_numeric": o.value_numeric,
                    "value_text": o.value_text,
                    "unit": o.unit,
                    "sequence_no": o.sequence_no,
                    "source": o.source,
                    "remarks": o.remarks
                }
                for o in observations
            ],

            "calculations": [
                {
                    "calculation_id": str(c.calculation_id),
                    "calculation_type": c.calculation_type,
                    "calculated_value": c.calculated_value,
                    "unit": c.unit,
                    "formula": c.formula,
                    "calculation_version": c.calculation_version
                }
                for c in calculations
            ],

            "results": [
                {
                    "result_id": str(r.result_id),
                    "measured_value": r.measured_value,
                    "mpe_value": r.mpe_value,
                    "error_value": r.error_value,
                    "corrected_error": r.corrected_error,
                    "acceptance_condition": r.acceptance_condition,
                    "pass_fail": r.pass_fail,
                    "result_summary": r.result_summary,
                    "calculation_version": r.calculation_version
                }
                for r in results
            ]
        })

    return {
        "laboratory": {
            "laboratory_id": str(laboratory.laboratory_id),
            "laboratory_code": laboratory.laboratory_code,
            "name": laboratory.name,
            "registration_number": laboratory.registration_number,
            "address": laboratory.address,
            "city": laboratory.city,
            "state": laboratory.state,
            "pincode": laboratory.pincode,
            "country": laboratory.country,
            "phone": laboratory.phone,
            "email": laboratory.email
        },

        "instrument": {
            "instrument_id": str(instrument.instrument_id),
            "instrument_code": instrument.instrument_code,
            "manufacturer": instrument.manufacturer,
            "model": instrument.model,
            "type_designation": instrument.type_designation,
            "serial_number": instrument.serial_number,
            "instrument_type": instrument.instrument_type,
            "category": instrument.category,
            "accuracy_class": instrument.accuracy_class,
            "max_capacity": instrument.max_capacity,
            "min_capacity": instrument.min_capacity,
            "verification_scale_interval": instrument.verification_scale_interval,
            "scale_interval": instrument.scale_interval,
            "number_of_intervals": instrument.number_of_intervals,
            "unit": instrument.unit
        },

        "tester": {
            "user_id": str(tester.user_id),
            "employee_id": tester.employee_id,
            "first_name": tester.first_name,
            "last_name": tester.last_name,
            "email": tester.email,
            "designation": tester.designation
        },

        "standard": {
            "standard_id": str(standard.standard_id),
            "standard_code": standard.standard_code,
            "title": standard.title,
            "version": standard.version,
            "edition_year": standard.edition_year,
            "source_document": standard.source_document,
            "source_url": standard.source_url
        },

        "test_session": {
            "test_session_id": str(session.test_session_id),
            "session_number": session.session_number,
            "application_number": session.application_number,
            "test_type": session.test_type,
            "status": session.status,
            "overall_result": session.overall_result,
            "remarks": session.remarks
        },

        "tests": tests
    }