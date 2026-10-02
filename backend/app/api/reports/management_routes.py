# backend/app/api/reports/management_routes.py
#
# List / read / edit remarks / delete for reports. Generating, downloading and
# approving stay in routes.py under /api/test-sessions/{id}/....

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.digital_signature import DigitalSignature
from backend.app.models.report import Report
from backend.app.models.report_version import ReportVersion
from backend.app.models.test_session import TestSession
from backend.app.models.user import User
from backend.app.schemas.report import ReportResponse, ReportUpdate
from backend.app.services.audit_service import create_audit_log
from backend.app.services.crud_rules import report_change_block_reason
from backend.app.services.report_files import (
    collect_report_paths,
    remove_report_files,
)
from backend.app.utils.dependencies import get_current_user, require_lab_admin


router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"]
)


def _to_response(report: Report, session: TestSession) -> ReportResponse:
    return ReportResponse(
        report_id=report.report_id,
        test_session_id=report.test_session_id,
        report_number=report.report_number,
        report_version=report.report_version,
        report_status=report.report_status,
        overall_result=report.overall_result,
        generated_at=report.generated_at,
        approved_at=report.approved_at,
        remarks=report.remarks,
        session_number=session.session_number,
        application_number=session.application_number,
        instrument_id=session.instrument_id,
        session_status=session.status,
    )


def _get_lab_report(db: Session, report_id: UUID, user: User):
    row = (
        db.query(Report, TestSession)
        .join(TestSession, Report.test_session_id == TestSession.test_session_id)
        .filter(
            Report.report_id == report_id,
            TestSession.laboratory_id == user.laboratory_id
        )
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    return row


@router.get("", response_model=list[ReportResponse])
def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(Report, TestSession)
        .join(TestSession, Report.test_session_id == TestSession.test_session_id)
        .filter(TestSession.laboratory_id == current_user.laboratory_id)
        .order_by(Report.generated_at.desc())
        .all()
    )

    return [_to_response(report, session) for report, session in rows]


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report, session = _get_lab_report(db, report_id, current_user)
    return _to_response(report, session)


@router.put("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: UUID,
    data: ReportUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report, session = _get_lab_report(db, report_id, current_user)

    reason = report_change_block_reason(report.report_status, "edited")
    if reason:
        raise HTTPException(status_code=409, detail=reason)

    update_data = data.model_dump(exclude_unset=True)
    old_value = {"remarks": report.remarks}

    if "remarks" in update_data and update_data["remarks"] != report.remarks:
        report.remarks = update_data["remarks"]

        create_audit_log(
            db=db,
            current_user=current_user,
            entity_type="REPORT",
            entity_id=report.report_id,
            action="UPDATE",
            old_value=old_value,
            new_value={"remarks": report.remarks},
            request=request
        )

    db.commit()
    db.refresh(report)

    return _to_response(report, session)


@router.delete("/{report_id}")
def delete_report(
    report_id: UUID,
    request: Request,
    current_user: User = Depends(require_lab_admin),
    db: Session = Depends(get_db)
):
    report, session = _get_lab_report(db, report_id, current_user)

    reason = report_change_block_reason(report.report_status, "deleted")
    if reason:
        raise HTTPException(status_code=409, detail=reason)

    versions = db.query(ReportVersion).filter(
        ReportVersion.report_id == report.report_id
    ).all()
    file_paths = collect_report_paths(report, *versions)

    snapshot = {
        "report_number": report.report_number,
        "report_version": report.report_version,
        "report_status": report.report_status,
        "overall_result": report.overall_result,
        "test_session_id": report.test_session_id,
    }

    try:
        db.query(DigitalSignature).filter(
            DigitalSignature.report_id == report.report_id
        ).delete(synchronize_session=False)

        db.query(ReportVersion).filter(
            ReportVersion.report_id == report.report_id
        ).delete(synchronize_session=False)

        create_audit_log(
            db=db,
            current_user=current_user,
            entity_type="REPORT",
            entity_id=report.report_id,
            action="DELETE",
            old_value=snapshot,
            request=request
        )

        db.delete(report)
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Only after the database commit succeeded.
    remove_report_files(file_paths)

    return {
        "message": "Report deleted",
        "report_id": str(report_id)
    }
