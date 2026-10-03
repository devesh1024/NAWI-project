from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

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
from backend.app.models.environmental_condition import EnvironmentalCondition
from backend.app.models.test_equipment import TestEquipment
from backend.app.models.test_equipment_usage import TestEquipmentUsage
from backend.app.models.attachment import Attachment
from backend.app.models.report import Report
from backend.app.models.report_version import ReportVersion
from backend.app.models.digital_signature import DigitalSignature
from backend.app.models.audit_log import AuditLog

from backend.app.utils.dependencies import get_current_user
from backend.app.services.report_generation.report_generator import create_report
from backend.app.services.report_generation.pdf_generator import create_pdf
from backend.app.services.verification.signing import sign_pdf_file


router = APIRouter(
    prefix="/api/test-sessions",
    tags=["Reports"]
)


# ============================================================
# HELPERS
# ============================================================


def calculate_file_sha256(file_path: str) -> str:
    """Calculate SHA-256 for a generated report file."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def get_next_report_number(db: Session) -> str:
    """Generate the next NAWI report number for the current year."""
    year = datetime.now().year

    report_count = (
        db.query(Report)
        .filter(Report.report_number.like(f"NAWI-{year}-%"))
        .count()
    )

    return f"NAWI-{year}-{report_count + 1:04d}"


def get_latest_report_version(
    db: Session,
    report_id
):
    return (
        db.query(ReportVersion)
        .filter(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.version_number.desc())
        .first()
    )


def create_audit_log(
    db: Session,
    current_user: User,
    entity_type: str,
    entity_id,
    action: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    remarks: str | None = None,
    request: Request | None = None
):
    """
    Create an audit trail entry.

    Audit logging is application-level logging stored in the audit_logs table.
    """
    ip_address = None

    if request is not None and request.client:
        ip_address = request.client.host

    audit_log = AuditLog(
        laboratory_id=current_user.laboratory_id,
        user_id=current_user.user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        remarks=remarks
    )

    db.add(audit_log)

    return audit_log


# ============================================================
# GET REPORT DATA
# ============================================================

@router.get("/{test_session_id}/report-data")
def get_report_data(
    test_session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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

    laboratory = (
        db.query(Laboratory)
        .filter(Laboratory.laboratory_id == session.laboratory_id)
        .first()
    )

    instrument = (
        db.query(Instrument)
        .filter(Instrument.instrument_id == session.instrument_id)
        .first()
    )

    tester = (
        db.query(User)
        .filter(User.user_id == session.tester_id)
        .first()
    )

    standard = (
        db.query(Standard)
        .filter(Standard.standard_id == session.standard_id)
        .first()
    )

    if not laboratory or not instrument or not tester or not standard:
        raise HTTPException(
            status_code=500,
            detail="Required report master data is missing"
        )

    # --------------------------------------------------------
    # Tests + observations + calculations + results
    # --------------------------------------------------------

    session_tests = (
        db.query(TestSessionTest)
        .filter(
            TestSessionTest.test_session_id == session.test_session_id
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
                "session_test_id": str(session_test.session_test_id),
                "test_definition_id": str(session_test.test_definition_id),
                "test_code": (
                    test_definition.test_code
                    if test_definition else None
                ),
                "test_name": (
                    test_definition.test_name
                    if test_definition else None
                ),
                "category": (
                    test_definition.category
                    if test_definition else None
                ),
                "description": (
                    test_definition.description
                    if test_definition else None
                ),
                "reference_clause": (
                    test_definition.reference_clause
                    if test_definition else None
                ),
                "procedure": (
                    test_definition.procedure
                    if test_definition else None
                ),
                "calculation_type": (
                    test_definition.calculation_type
                    if test_definition else None
                ),
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
                        "input_values": c.input_values,
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
            }
        )

    # --------------------------------------------------------
    # Environmental conditions
    # --------------------------------------------------------

    environmental_conditions = (
        db.query(EnvironmentalCondition)
        .filter(
            EnvironmentalCondition.test_session_id
            == session.test_session_id
        )
        .order_by(EnvironmentalCondition.recorded_at.asc())
        .all()
    )

    # --------------------------------------------------------
    # Test equipment used by tests in this session
    # --------------------------------------------------------

    equipment_rows = (
        db.query(TestEquipmentUsage, TestEquipment)
        .join(
            TestEquipment,
            TestEquipmentUsage.equipment_id
            == TestEquipment.equipment_id
        )
        .join(
            TestSessionTest,
            TestEquipmentUsage.session_test_id
            == TestSessionTest.session_test_id
        )
        .filter(
            TestSessionTest.test_session_id == session.test_session_id,
            TestEquipment.laboratory_id == session.laboratory_id
        )
        .all()
    )

    test_equipment = [
        {
            "usage_id": str(usage.usage_id),
            "equipment_id": str(equipment.equipment_id),
            "equipment_code": equipment.equipment_code,
            "equipment_name": equipment.equipment_name,
            "model": equipment.model,
            "serial_number": equipment.serial_number,
            "identification_number": equipment.identification_number,
            "calibration_status": equipment.calibration_status,
            "calibration_date": equipment.calibration_date,
            "calibration_due_date": equipment.calibration_due_date,
            "used_from": usage.used_from,
            "used_to": usage.used_to,
            "remarks": usage.remarks
        }
        for usage, equipment in equipment_rows
    ]

    # --------------------------------------------------------
    # Attachments
    # --------------------------------------------------------

    attachments = (
        db.query(Attachment)
        .filter(
            Attachment.test_session_id == session.test_session_id,
            Attachment.laboratory_id == session.laboratory_id
        )
        .order_by(Attachment.uploaded_at.asc())
        .all()
    )

    # --------------------------------------------------------
    # Latest report
    # --------------------------------------------------------

    latest_report = (
        db.query(Report)
        .filter(Report.test_session_id == session.test_session_id)
        .order_by(Report.generated_at.desc())
        .first()
    )

    reviewer = None

    if latest_report and latest_report.approved_by:
        reviewer = (
            db.query(User)
            .filter(User.user_id == latest_report.approved_by)
            .first()
        )

    report_versions = []
    digital_signatures = []

    if latest_report:
        report_versions = (
            db.query(ReportVersion)
            .filter(ReportVersion.report_id == latest_report.report_id)
            .order_by(ReportVersion.version_number.asc())
            .all()
        )

        digital_signatures = (
            db.query(DigitalSignature)
            .filter(DigitalSignature.report_id == latest_report.report_id)
            .order_by(DigitalSignature.signed_at.asc())
            .all()
        )

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
            "unit": instrument.unit,
            "tare_type": instrument.tare_type,
            "zero_setting_type": instrument.zero_setting_type,
            "indication_type": instrument.indication_type,
            "load_cell_info": instrument.load_cell_info,
            "software_firmware": instrument.software_firmware,
            "power_supply": instrument.power_supply,
            "interfaces": instrument.interfaces,
            "temperature_min": instrument.temperature_min,
            "temperature_max": instrument.temperature_max,
            "status": instrument.status
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

        "environmental_conditions": [
            {
                "environment_id": str(e.environment_id),
                "temperature": e.temperature,
                "humidity": e.humidity,
                "pressure": e.pressure,
                "recorded_at": e.recorded_at,
                "recorded_by": (
                    str(e.recorded_by) if e.recorded_by else None
                ),
                "source": e.source,
                "remarks": e.remarks
            }
            for e in environmental_conditions
        ],

        "test_equipment": test_equipment,

        "test_session": {
            "test_session_id": str(session.test_session_id),
            "session_number": session.session_number,
            "application_number": session.application_number,
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
                if latest_report else None
            ),
            "report_number": (
                latest_report.report_number
                if latest_report else None
            ),
            "report_version": (
                latest_report.report_version
                if latest_report else None
            ),
            "report_status": (
                latest_report.report_status
                if latest_report else None
            ),
            "overall_result": (
                latest_report.overall_result
                if latest_report else None
            ),
            "generated_at": (
                latest_report.generated_at
                if latest_report else None
            ),
            "generated_by": (
                str(latest_report.generated_by)
                if latest_report and latest_report.generated_by
                else None
            ),
            "approved_by": (
                str(latest_report.approved_by)
                if latest_report and latest_report.approved_by
                else None
            ),
            "approved_at": (
                latest_report.approved_at
                if latest_report else None
            ),
            "docx_path": (
                latest_report.docx_path
                if latest_report else None
            ),
            "pdf_path": (
                latest_report.pdf_path
                if latest_report else None
            ),
            "report_hash": (
                latest_report.report_hash
                if latest_report else None
            ),
            "reviewer": (
                {
                    "user_id": str(reviewer.user_id),
                    "first_name": reviewer.first_name,
                    "last_name": reviewer.last_name,
                    "designation": reviewer.designation,
                    "email": reviewer.email
                }
                if reviewer else None
            ),
            "versions": [
                {
                    "report_version_id": str(v.report_version_id),
                    "version_number": v.version_number,
                    "generated_by": (
                        str(v.generated_by) if v.generated_by else None
                    ),
                    "generated_at": v.generated_at,
                    "reason": v.reason,
                    "docx_path": v.docx_path,
                    "pdf_path": v.pdf_path,
                    "hash": v.hash
                }
                for v in report_versions
            ],
            "digital_signatures": [
                {
                    "signature_id": str(s.signature_id),
                    "user_id": str(s.user_id),
                    "signature_type": s.signature_type,
                    "signature_data": s.signature_data,
                    "signed_at": s.signed_at,
                    "certificate_id": s.certificate_id,
                    "status": s.status
                }
                for s in digital_signatures
            ]
        },

        "attachments": [
            {
                "attachment_id": str(a.attachment_id),
                "session_test_id": (
                    str(a.session_test_id)
                    if a.session_test_id else None
                ),
                "file_name": a.file_name,
                "file_type": a.file_type,
                "file_size": a.file_size,
                "file_path": a.file_path,
                "attachment_type": a.attachment_type,
                "uploaded_by": str(a.uploaded_by),
                "uploaded_at": a.uploaded_at,
                "description": a.description
            }
            for a in attachments
        ],

        "tests": tests
    }


# ============================================================
# GENERATE REPORT
# ============================================================

@router.post("/{test_session_id}/generate-report")
def generate_report(
    test_session_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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

    existing_report = (
        db.query(Report)
        .filter(Report.test_session_id == test_session_id)
        .order_by(Report.generated_at.desc())
        .first()
    )

    # Do not silently overwrite an approved report. A new generated
    # version must go through approval again.
    if existing_report and existing_report.report_status == "APPROVED":
        raise HTTPException(
            status_code=400,
            detail=(
                "Report is already approved. Create a new report version "
                "through the review workflow before regenerating it."
            )
        )

    report_data = get_report_data(
        test_session_id=test_session_id,
        db=db,
        current_user=current_user
    )

    if existing_report:
        report = existing_report
        report_number = report.report_number
        reviewer = None

        if report.approved_by:
            reviewer = (
                db.query(User)
                .filter(User.user_id == report.approved_by)
                .first()
            )

        report_status = report.report_status or "GENERATED"
        approved_at = report.approved_at
        report_date = (
            report.generated_at.strftime("%d-%m-%Y")
            if report.generated_at
            else datetime.now().strftime("%d-%m-%Y")
        )
    else:
        report = None
        report_number = get_next_report_number(db)
        reviewer = None
        report_status = "GENERATED"
        approved_at = None
        report_date = datetime.now().strftime("%d-%m-%Y")

    # The current ReportVersion table is the authoritative numeric version.
    next_version_number = 1

    if report:
        latest_version = get_latest_report_version(
            db,
            report.report_id
        )
        if latest_version:
            next_version_number = latest_version.version_number + 1

    report_version = f"{next_version_number}.0"

    report_data["report"] = {
        "report_id": str(report.report_id) if report else None,
        "report_number": report_number,
        "report_version": report_version,
        "report_date": report_date,
        "report_status": report_status,
        "generated_at": (
            report.generated_at
            if report
            else datetime.now(timezone.utc)
        ),
        "approved_at": approved_at,
        "reviewer": (
            {
                "user_id": str(reviewer.user_id),
                "first_name": reviewer.first_name,
                "last_name": reviewer.last_name,
                "designation": reviewer.designation,
                "email": reviewer.email
            }
            if reviewer else None
        )
    }

    reports_dir = Path("generated_reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    output_path = reports_dir / f"NAWI_Report_{test_session_id}.docx"
    pdf_output_path = reports_dir / f"NAWI_Report_{test_session_id}.pdf"

    create_report(
        report_data,
        output_path=str(output_path)
    )

    create_pdf(
        report_data,
        output_path=str(pdf_output_path)
    )

    # Sign in place: read the plain PDF just written, overwrite it with a
    # digitally-signed version. Must happen before hashing below, so the
    # stored report_hash matches what a verifier will actually check against.
    signed_tmp_path = str(pdf_output_path) + ".signed"
    sign_pdf_file(str(pdf_output_path), signed_tmp_path)
    Path(signed_tmp_path).replace(pdf_output_path)

    # The hash is calculated from the generated PDF, which is the final
    # fixed-format report artifact delivered to the user.
    report_hash = calculate_file_sha256(str(pdf_output_path))

    if not report:
        report = Report(
            test_session_id=test_session_id,
            report_number=report_number,
            report_version=report_version,
            report_status="GENERATED",
            overall_result=report_data["test_session"]["overall_result"],
            generated_by=current_user.user_id,
            docx_path=str(output_path),
            pdf_path=str(pdf_output_path),
            report_hash=report_hash,
            remarks=report_data["test_session"]["remarks"]
        )
        db.add(report)
        db.flush()
    else:
        report.report_version = report_version
        report.report_status = "GENERATED"
        report.generated_by = current_user.user_id
        report.docx_path = str(output_path)
        report.pdf_path = str(pdf_output_path)
        report.report_hash = report_hash
        report.overall_result = report_data["test_session"]["overall_result"]
        report.approved_by = None
        report.approved_at = None

    # Store immutable-ish version metadata for this generated artifact.
    version_record = ReportVersion(
        report_id=report.report_id,
        version_number=next_version_number,
        generated_by=current_user.user_id,
        reason=(
            "Initial report generation"
            if next_version_number == 1
            else "Report regenerated"
        ),
        docx_path=str(output_path),
        pdf_path=str(pdf_output_path),
        hash=report_hash
    )

    db.add(version_record)

    # --------------------------------------------------------
    # AUDIT: REPORT GENERATION
    # --------------------------------------------------------

    create_audit_log(
        db=db,
        current_user=current_user,
        entity_type="REPORT",
        entity_id=report.report_id,
        action="GENERATE_REPORT",
        old_value=(
            {
                "report_status": existing_report.report_status,
                "report_version": existing_report.report_version
            }
            if existing_report
            else None
        ),
        new_value={
            "report_number": report.report_number,
            "report_version": report.report_version,
            "report_status": report.report_status,
            "overall_result": report.overall_result,
            "report_hash": report.report_hash
        },
        remarks=(
            "Initial report generation"
            if next_version_number == 1
            else "Report regenerated"
        ),
        request=request
    )

    db.commit()
    db.refresh(report)

    return FileResponse(
        path=str(output_path),
        filename=f"NAWI_Test_Report_{test_session_id}.docx",
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
    )


# ============================================================
# DOWNLOAD DOCX
# ============================================================

@router.get("/{test_session_id}/report/download-docx")
def download_docx(
    test_session_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = (
        db.query(Report)
        .join(TestSession, Report.test_session_id == TestSession.test_session_id)
        .filter(
            Report.test_session_id == test_session_id,
            TestSession.laboratory_id == current_user.laboratory_id
        )
        .order_by(Report.generated_at.desc())
        .first()
    )

    if not report or not report.docx_path:
        raise HTTPException(
            status_code=404,
            detail="DOCX report not found"
        )

    path = Path(report.docx_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="DOCX file does not exist"
        )

    # --------------------------------------------------------
    # AUDIT: DOCX DOWNLOAD
    # --------------------------------------------------------

    create_audit_log(
        db=db,
        current_user=current_user,
        entity_type="REPORT",
        entity_id=report.report_id,
        action="DOWNLOAD_REPORT",
        new_value={
            "report_number": report.report_number,
            "report_version": report.report_version,
            "file_type": "DOCX",
            "file_name": path.name
        },
        remarks="DOCX report downloaded",
        request=request
    )

    db.commit()

    return FileResponse(
        path=str(path),
        filename=path.name,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
    )


# ============================================================
# DOWNLOAD PDF
# ============================================================

@router.get("/{test_session_id}/report/download-pdf")
def download_pdf(
    test_session_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = (
        db.query(Report)
        .join(TestSession, Report.test_session_id == TestSession.test_session_id)
        .filter(
            Report.test_session_id == test_session_id,
            TestSession.laboratory_id == current_user.laboratory_id
        )
        .order_by(Report.generated_at.desc())
        .first()
    )

    if not report or not report.pdf_path:
        raise HTTPException(
            status_code=404,
            detail="PDF report not found"
        )

    path = Path(report.pdf_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF file does not exist"
        )

    # --------------------------------------------------------
    # AUDIT: PDF DOWNLOAD
    # --------------------------------------------------------

    create_audit_log(
        db=db,
        current_user=current_user,
        entity_type="REPORT",
        entity_id=report.report_id,
        action="DOWNLOAD_REPORT",
        new_value={
            "report_number": report.report_number,
            "report_version": report.report_version,
            "file_type": "PDF",
            "file_name": path.name
        },
        remarks="PDF report downloaded",
        request=request
    )

    db.commit()

    return FileResponse(
        path=str(path),
        filename=path.name,
        media_type="application/pdf"
    )

# ============================================================
# SUBMIT FOR APPROVAL
# ============================================================
@router.patch("/{test_session_id}/submit-for-approval")
def submit_report_for_approval(
    test_session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "REVIEWER":
        raise HTTPException(
            status_code=403,
            detail="Only a Reviewer can submit a report for approval"
        )

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

    if session.status != "UNDER REVIEW":
        raise HTTPException(
            status_code=400,
            detail="Only sessions under review can be submitted for approval"
        )

    report = (
        db.query(Report)
        .filter(
            Report.test_session_id == test_session_id
        )
        .order_by(Report.generated_at.desc())
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No report found for this test session"
        )

    if report.report_status == "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="An approved report cannot be submitted for approval again"
        )

    report.report_status = "PENDING_APPROVAL"

    # Record the reviewer responsible for the review.
    session.reviewer_id = current_user.user_id

    db.commit()
    db.refresh(report)

    return {
        "message": "Report submitted for approval successfully",
        "test_session_id": str(test_session_id),
        "report_status": report.report_status,
        "session_status": session.status
    }



# ============================================================
# APPROVE / REJECT REPORT
# ============================================================

@router.patch("/{test_session_id}/approve-report")
def approve_report(
    test_session_id: UUID,
    request: Request,
    action: str = "APPROVE",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    allowed_roles = {
        "LAB_ADMIN",
        "APPROVER"
    }

    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Only an Approver or Lab Admin can approve or reject reports"
        )

    action = action.upper()

    if action not in {"APPROVE", "REJECT"}:
        raise HTTPException(
            status_code=400,
            detail="Action must be either APPROVE or REJECT"
        )

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

    report = (
        db.query(Report)
        .filter(Report.test_session_id == test_session_id)
        .order_by(Report.generated_at.desc())
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No generated report found for this test session"
        )

    if report.report_status == "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Report is already approved"
        )

    if current_user.role == "APPROVER" and report.report_status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=400,
            detail="Only reports pending approval can be approved or rejected"
        )

    approval_time = datetime.now(timezone.utc)

    old_report_status = report.report_status
    old_session_status = session.status

    # --------------------------------------------------------
    # APPROVE
    # --------------------------------------------------------

    if action == "APPROVE":

        report.approved_by = current_user.user_id
        report.approved_at = approval_time
        report.report_status = "APPROVED"

        signature_data = (
            f"APPROVED_BY:{current_user.user_id};"
            f"REPORT_HASH:{report.report_hash or 'NOT_AVAILABLE'}"
        )

        digital_signature = DigitalSignature(
            report_id=report.report_id,
            user_id=current_user.user_id,
            signature_type="APPLICATION_APPROVAL",
            signature_data=signature_data,
            certificate_id=None,
            status="SIGNED"
        )

        db.add(digital_signature)

        session.status = "APPROVED"

        audit_action = "APPROVE"
        audit_remarks = (
            "Report approved. Application-level approval signature "
            "created; not a PKI/certificate-based cryptographic signature."
        )

    # --------------------------------------------------------
    # REJECT
    # --------------------------------------------------------

    else:

        report.approved_by = None
        report.approved_at = None
        report.report_status = "REJECTED"

        session.status = "REJECTED"

        digital_signature = None

        audit_action = "REJECT"
        audit_remarks = "Report rejected by Approver."

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    create_audit_log(
        db=db,
        current_user=current_user,
        entity_type="REPORT",
        entity_id=report.report_id,
        action=audit_action,
        old_value={
            "report_status": old_report_status,
            "test_session_status": old_session_status
        },
        new_value={
            "report_status": report.report_status,
            "test_session_status": session.status,
            "approved_by": (
                str(current_user.user_id)
                if report.approved_by
                else None
            ),
            "approved_at": (
                report.approved_at.isoformat()
                if report.approved_at
                else None
            ),
            "report_hash": report.report_hash
        },
        remarks=audit_remarks,
        request=request
    )

    db.commit()
    db.refresh(report)

    if digital_signature:
        db.refresh(digital_signature)

    return {
        "message": (
            "Report approved successfully"
            if action == "APPROVE"
            else "Report rejected successfully"
        ),
        "report": {
            "report_id": str(report.report_id),
            "report_number": report.report_number,
            "report_version": report.report_version,
            "report_status": report.report_status,
            "overall_result": report.overall_result,
            "approved_by": (
                str(report.approved_by)
                if report.approved_by
                else None
            ),
            "approved_at": report.approved_at,
            "report_hash": report.report_hash,
            "digital_signature": (
                {
                    "signature_id": str(digital_signature.signature_id),
                    "signature_type": digital_signature.signature_type,
                    "status": digital_signature.status,
                    "signed_at": digital_signature.signed_at
                }
                if digital_signature
                else None
            )
        },
        "test_session": {
            "test_session_id": str(session.test_session_id),
            "status": session.status,
            "overall_result": session.overall_result
        }
    }