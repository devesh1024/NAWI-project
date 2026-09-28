from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.responses import FileResponse
from datetime import datetime, timezone

from backend.app.database.connection import get_db

from backend.app.models.test_session import TestSession
from backend.app.models.laboratory import Laboratory
from backend.app.models.instrument import Instrument
from backend.app.models.user import User
from backend.app.models.standard import Standard
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.test_definition import TestDefinition
from backend.app.models.test_observation import TestObservation
from backend.app.models.test_calculation import TestCalculation
from backend.app.models.test_result import TestResult
from backend.app.models.report import Report

from backend.app.utils.dependencies import get_current_user
from backend.app.services.report_generation.report_generator import create_report


router = APIRouter(
    prefix="/api/test-sessions",
    tags=["Reports"]
)


# ============================================================
# GET REPORT DATA
# ============================================================

@router.get("/{test_session_id}/report-data")
def get_report_data(
    test_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get test session belonging to current user's laboratory
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

    # --------------------------------------------------------
    # Related data
    # --------------------------------------------------------

    laboratory = (
        db.query(Laboratory)
        .filter(
            Laboratory.laboratory_id == session.laboratory_id
        )
        .first()
    )

    instrument = (
        db.query(Instrument)
        .filter(
            Instrument.instrument_id == session.instrument_id
        )
        .first()
    )

    tester = (
        db.query(User)
        .filter(
            User.user_id == session.tester_id
        )
        .first()
    )

    standard = (
        db.query(Standard)
        .filter(
            Standard.standard_id == session.standard_id
        )
        .first()
    )

    # --------------------------------------------------------
    # Get tests
    # --------------------------------------------------------

    session_tests = (
        db.query(TestSessionTest)
        .filter(
            TestSessionTest.test_session_id
            == session.test_session_id
        )
        .all()
    )

    tests = []

    for session_test in session_tests:

        test_definition = (
            db.query(TestDefinition)
            .filter(
                TestDefinition.test_definition_id
                == session_test.test_definition_id
            )
            .first()
        )

        observations = (
            db.query(TestObservation)
            .filter(
                TestObservation.session_test_id
                == session_test.session_test_id
            )
            .all()
        )

        calculations = (
            db.query(TestCalculation)
            .filter(
                TestCalculation.session_test_id
                == session_test.session_test_id
            )
            .all()
        )

        results = (
            db.query(TestResult)
            .filter(
                TestResult.session_test_id
                == session_test.session_test_id
            )
            .all()
        )

        tests.append(
            {
                "session_test_id": str(
                    session_test.session_test_id
                ),

                "test_definition_id": str(
                    session_test.test_definition_id
                ),

                # ------------------------------------------------
                # Test definition
                # ------------------------------------------------

                "test_code": (
                    test_definition.test_code
                    if test_definition
                    else None
                ),

                "test_name": (
                    test_definition.test_name
                    if test_definition
                    else None
                ),

                "category": (
                    test_definition.category
                    if test_definition
                    else None
                ),

                "description": (
                    test_definition.description
                    if test_definition
                    else None
                ),

                "reference_clause": (
                    test_definition.reference_clause
                    if test_definition
                    else None
                ),

                "procedure": (
                    test_definition.procedure
                    if test_definition
                    else None
                ),

                "calculation_type": (
                    test_definition.calculation_type
                    if test_definition
                    else None
                ),

                # ------------------------------------------------
                # Applicability / status
                # ------------------------------------------------

                "applicability_status": (
                    session_test.applicability_status
                ),

                "na_reason": session_test.na_reason,

                "status": session_test.status,

                "result": session_test.result,

                # ------------------------------------------------
                # Observations
                # ------------------------------------------------

                "observations": [
                    {
                        "observation_id": str(
                            o.observation_id
                        ),
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

                # ------------------------------------------------
                # Calculations
                # ------------------------------------------------

                "calculations": [
                    {
                        "calculation_id": str(
                            c.calculation_id
                        ),
                        "calculation_type": c.calculation_type,
                        "calculated_value": c.calculated_value,
                        "unit": c.unit,
                        "formula": c.formula,
                        "input_values": c.input_values,
                        "calculation_version": (
                            c.calculation_version
                        )
                    }
                    for c in calculations
                ],

                # ------------------------------------------------
                # Results
                # ------------------------------------------------

                "results": [
                    {
                        "result_id": str(
                            r.result_id
                        ),
                        "measured_value": r.measured_value,
                        "mpe_value": r.mpe_value,
                        "error_value": r.error_value,
                        "corrected_error": r.corrected_error,
                        "acceptance_condition": (
                            r.acceptance_condition
                        ),
                        "pass_fail": r.pass_fail,
                        "result_summary": r.result_summary,
                        "calculation_version": (
                            r.calculation_version
                        )
                    }
                    for r in results
                ]
            }
        )

    # --------------------------------------------------------
    # Latest report
    # --------------------------------------------------------

    latest_report = (
        db.query(Report)
        .filter(
            Report.test_session_id
            == session.test_session_id
        )
        .order_by(
            Report.generated_at.desc()
        )
        .first()
    )

    # --------------------------------------------------------
    # Reviewer
    # --------------------------------------------------------

    reviewer = None

    if latest_report and latest_report.approved_by:

        reviewer = (
            db.query(User)
            .filter(
                User.user_id
                == latest_report.approved_by
            )
            .first()
        )

    # --------------------------------------------------------
    # Return structured report data
    # --------------------------------------------------------

    return {
        "laboratory": {
            "laboratory_id": str(
                laboratory.laboratory_id
            ),
            "laboratory_code": laboratory.laboratory_code,
            "name": laboratory.name,
            "registration_number": (
                laboratory.registration_number
            ),
            "address": laboratory.address,
            "city": laboratory.city,
            "state": laboratory.state,
            "pincode": laboratory.pincode,
            "country": laboratory.country,
            "phone": laboratory.phone,
            "email": laboratory.email
        },

        "instrument": {
            "instrument_id": str(
                instrument.instrument_id
            ),
            "instrument_code": instrument.instrument_code,
            "manufacturer": instrument.manufacturer,
            "model": instrument.model,
            "type_designation": (
                instrument.type_designation
            ),
            "serial_number": instrument.serial_number,
            "instrument_type": instrument.instrument_type,
            "category": instrument.category,
            "accuracy_class": instrument.accuracy_class,
            "max_capacity": instrument.max_capacity,
            "min_capacity": instrument.min_capacity,
            "verification_scale_interval": (
                instrument.verification_scale_interval
            ),
            "scale_interval": instrument.scale_interval,
            "number_of_intervals": (
                instrument.number_of_intervals
            ),
            "unit": instrument.unit
        },

        "tester": {
            "user_id": str(
                tester.user_id
            ),
            "employee_id": tester.employee_id,
            "first_name": tester.first_name,
            "last_name": tester.last_name,
            "email": tester.email,
            "designation": tester.designation
        },

        "standard": {
            "standard_id": str(
                standard.standard_id
            ),
            "standard_code": standard.standard_code,
            "title": standard.title,
            "version": standard.version,
            "edition_year": standard.edition_year,
            "source_document": (
                standard.source_document
            ),
            "source_url": standard.source_url
        },

        "test_session": {
            "test_session_id": str(
                session.test_session_id
            ),
            "session_number": session.session_number,
            "application_number": (
                session.application_number
            ),
            "test_type": session.test_type,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "status": session.status,
            "overall_result": session.overall_result,
            "remarks": session.remarks
        },

        "report": {
            "report_id": (
                str(latest_report.report_id)
                if latest_report
                else None
            ),

            "report_number": (
                latest_report.report_number
                if latest_report
                else None
            ),

            "report_version": (
                latest_report.report_version
                if latest_report
                else None
            ),

            "report_status": (
                latest_report.report_status
                if latest_report
                else None
            ),

            "generated_at": (
                latest_report.generated_at
                if latest_report
                else None
            ),

            "approved_at": (
                latest_report.approved_at
                if latest_report
                else None
            ),

            "reviewer": (
                {
                    "user_id": str(
                        reviewer.user_id
                    ),
                    "first_name": reviewer.first_name,
                    "last_name": reviewer.last_name,
                    "designation": reviewer.designation,
                    "email": reviewer.email
                }
                if reviewer
                else None
            )
        },

        "tests": tests
    }


# ============================================================
# GENERATE REPORT
# ============================================================

@router.post("/{test_session_id}/generate-report")
def generate_report(
    test_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # --------------------------------------------------------
    # Get test session
    # --------------------------------------------------------

    session = (
        db.query(TestSession)
        .filter(
            TestSession.test_session_id == test_session_id,
            TestSession.laboratory_id
            == current_user.laboratory_id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found"
        )

    # --------------------------------------------------------
    # Get existing report
    # --------------------------------------------------------

    existing_report = (
        db.query(Report)
        .filter(
            Report.test_session_id
            == test_session_id
        )
        .order_by(
            Report.generated_at.desc()
        )
        .first()
    )

    # --------------------------------------------------------
    # Get structured report data
    # --------------------------------------------------------

    report_data = get_report_data(
        test_session_id=test_session_id,
        db=db,
        current_user=current_user
    )

    # --------------------------------------------------------
    # Determine report metadata
    # --------------------------------------------------------

    if existing_report:

        report = existing_report

        report_number = report.report_number
        report_version = report.report_version

        # Find reviewer if already approved
        reviewer = None

        if report.approved_by:

            reviewer = (
                db.query(User)
                .filter(
                    User.user_id
                    == report.approved_by
                )
                .first()
            )

        # Keep the existing approval state.
        # Do NOT reset an approved report to GENERATED.
        report_status = (
            report.report_status
            or "GENERATED"
        )

        approved_at = report.approved_at

        # Use original generation date for report date
        if report.generated_at:
            report_date = report.generated_at.strftime(
                "%d-%m-%Y"
            )
        else:
            report_date = datetime.now().strftime(
                "%d-%m-%Y"
            )

    else:

        # ----------------------------------------------------
        # Create first report number
        # ----------------------------------------------------

        year = datetime.now().year

        report_count = (
            db.query(Report)
            .filter(
                Report.report_number.like(
                    f"NAWI-{year}-%"
                )
            )
            .count()
        )

        report_number = (
            f"NAWI-{year}-{report_count + 1:04d}"
        )

        report_version = "1.0"
        report_status = "GENERATED"
        approved_at = None
        reviewer = None

        report_date = datetime.now().strftime(
            "%d-%m-%Y"
        )

    # --------------------------------------------------------
    # Build report metadata for DOCX generator
    # --------------------------------------------------------

    report_data["report"] = {
        "report_id": (
            str(report.report_id)
            if existing_report
            else None
        ),

        "report_number": report_number,

        "report_version": report_version,

        "report_date": report_date,

        "report_status": report_status,

        "generated_at": (
            report.generated_at
            if existing_report
            else datetime.now(timezone.utc)
        ),

        "approved_at": approved_at,

        "reviewer": (
            {
                "user_id": str(
                    reviewer.user_id
                ),
                "first_name": reviewer.first_name,
                "last_name": reviewer.last_name,
                "designation": reviewer.designation,
                "email": reviewer.email
            }
            if reviewer
            else None
        )
    }

    # --------------------------------------------------------
    # Create generated reports folder
    # --------------------------------------------------------

    reports_dir = Path(
        "generated_reports"
    )

    reports_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Output DOCX path
    # --------------------------------------------------------

    output_path = (
        reports_dir
        / f"NAWI_Report_{test_session_id}.docx"
    )

    # --------------------------------------------------------
    # Generate DOCX
    # --------------------------------------------------------

    create_report(
        report_data,
        output_path=str(output_path)
    )

    # --------------------------------------------------------
    # Create DB record if this is the first report
    # --------------------------------------------------------

    if not existing_report:

        report = Report(
            test_session_id=test_session_id,
            report_number=report_number,
            report_version=report_version,
            report_status="GENERATED",
            overall_result=(
                report_data["test_session"]
                ["overall_result"]
            ),
            generated_by=current_user.user_id,
            docx_path=str(output_path),
            remarks=(
                report_data["test_session"]
                ["remarks"]
            )
        )

        db.add(report)
        db.commit()
        db.refresh(report)

    else:

        # ----------------------------------------------------
        # Existing report:
        # update DOCX path only.
        #
        # IMPORTANT:
        # approval information is preserved.
        # ----------------------------------------------------

        report.docx_path = str(
            output_path
        )

        db.commit()
        db.refresh(report)

    # --------------------------------------------------------
    # Return generated DOCX
    # --------------------------------------------------------

    return FileResponse(
        path=str(output_path),
        filename=(
            f"NAWI_Test_Report_{test_session_id}.docx"
        ),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
    )


# ============================================================
# APPROVE REPORT
# ============================================================

@router.patch("/{test_session_id}/approve-report")
def approve_report(
    test_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # --------------------------------------------------------
    # Only Lab Admin / Reviewer can approve
    # --------------------------------------------------------

    allowed_roles = {
        "LAB_ADMIN",
        "REVIEWER"
    }

    if current_user.role not in allowed_roles:

        raise HTTPException(
            status_code=403,
            detail=(
                "Only a Lab Admin or Reviewer "
                "can approve reports"
            )
        )

    # --------------------------------------------------------
    # Get test session
    # --------------------------------------------------------

    session = (
        db.query(TestSession)
        .filter(
            TestSession.test_session_id == test_session_id,
            TestSession.laboratory_id
            == current_user.laboratory_id
        )
        .first()
    )

    if not session:

        raise HTTPException(
            status_code=404,
            detail="Test session not found"
        )

    # --------------------------------------------------------
    # Get latest report
    # --------------------------------------------------------

    report = (
        db.query(Report)
        .filter(
            Report.test_session_id
            == test_session_id
        )
        .order_by(
            Report.generated_at.desc()
        )
        .first()
    )

    if not report:

        raise HTTPException(
            status_code=404,
            detail=(
                "No generated report found "
                "for this test session"
            )
        )

    # --------------------------------------------------------
    # Prevent duplicate approval
    # --------------------------------------------------------

    if report.report_status == "APPROVED":

        raise HTTPException(
            status_code=400,
            detail="Report is already approved"
        )

    # --------------------------------------------------------
    # Approval timestamp
    # --------------------------------------------------------

    approval_time = datetime.now(
        timezone.utc
    )

    # --------------------------------------------------------
    # Update report
    # --------------------------------------------------------

    report.approved_by = (
        current_user.user_id
    )

    report.approved_at = approval_time

    report.report_status = "APPROVED"

    # --------------------------------------------------------
    # Update session
    # --------------------------------------------------------

    session.status = "APPROVED"

    db.commit()
    db.refresh(report)

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "message": "Report approved successfully",

        "report": {
            "report_id": str(
                report.report_id
            ),

            "report_number": (
                report.report_number
            ),

            "report_version": (
                report.report_version
            ),

            "report_status": (
                report.report_status
            ),

            "overall_result": (
                report.overall_result
            ),

            "approved_by": str(
                report.approved_by
            ),

            "approved_at": (
                report.approved_at
            )
        },

        "test_session": {
            "test_session_id": str(
                session.test_session_id
            ),

            "status": session.status,

            "overall_result": (
                session.overall_result
            )
        }
    }