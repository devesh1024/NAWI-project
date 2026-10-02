# backend/app/api/test_sessions/management_routes.py
#
# Update and delete for test sessions (create/read/status live in routes.py).
# Registered in main.py on the same /api/test-sessions prefix.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.attachment import Attachment
from backend.app.models.digital_signature import DigitalSignature
from backend.app.models.environmental_condition import EnvironmentalCondition
from backend.app.models.instrument import Instrument
from backend.app.models.observation_import import ObservationImport
from backend.app.models.report import Report
from backend.app.models.report_version import ReportVersion
from backend.app.models.standard import Standard
from backend.app.models.test_calculation import TestCalculation
from backend.app.models.test_equipment_usage import TestEquipmentUsage
from backend.app.models.test_observation import TestObservation
from backend.app.models.test_result import TestResult
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.user import User
from backend.app.schemas.test_session import (
    TestSessionResponse,
    TestSessionUpdate,
)
from backend.app.services.audit_service import create_audit_log
from backend.app.services.crud_rules import (
    session_actor_block_reason,
    session_delete_block_reason,
    session_edit_block_reason,
    session_relink_block_reason,
)
from backend.app.services.report_files import (
    collect_report_paths,
    remove_report_files,
)
from backend.app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/api/test-sessions",
    tags=["Test Sessions"]
)


def _get_lab_session(db: Session, test_session_id: UUID, user: User) -> TestSession:
    session = db.query(TestSession).filter(
        TestSession.test_session_id == test_session_id,
        TestSession.laboratory_id == user.laboratory_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Test session not found")

    return session


@router.put(
    "/{test_session_id}",
    response_model=TestSessionResponse
)
def update_test_session(
    test_session_id: UUID,
    data: TestSessionUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = _get_lab_session(db, test_session_id, current_user)

    reason = session_actor_block_reason(
        actor_role=current_user.role,
        actor_id=current_user.user_id,
        tester_id=session.tester_id,
        verb="edit"
    )
    if reason:
        raise HTTPException(status_code=403, detail=reason)

    reason = session_edit_block_reason(session.status)
    if reason:
        raise HTTPException(status_code=409, detail=reason)

    update_data = data.model_dump(exclude_unset=True)

    # instrument_id / standard_id are mandatory; an explicit null means "keep".
    for link in ("instrument_id", "standard_id"):
        if link in update_data and update_data[link] is None:
            del update_data[link]

    changed_links = [
        link for link in ("instrument_id", "standard_id")
        if link in update_data and update_data[link] != getattr(session, link)
    ]

    if changed_links:
        test_count = db.query(func.count(TestSessionTest.session_test_id)).filter(
            TestSessionTest.test_session_id == session.test_session_id
        ).scalar()

        reason = session_relink_block_reason(
            changing_instrument_or_standard=True,
            test_count=test_count
        )
        if reason:
            raise HTTPException(status_code=409, detail=reason)

        if "instrument_id" in changed_links:
            instrument = db.query(Instrument).filter(
                Instrument.instrument_id == update_data["instrument_id"],
                Instrument.laboratory_id == current_user.laboratory_id
            ).first()

            if not instrument:
                raise HTTPException(status_code=404, detail="Instrument not found")

            if (instrument.status or "").upper() == "INACTIVE":
                raise HTTPException(
                    status_code=409,
                    detail="This instrument is INACTIVE; reactivate it first."
                )

        if "standard_id" in changed_links:
            standard = db.query(Standard).filter(
                Standard.standard_id == update_data["standard_id"]
            ).first()

            if not standard:
                raise HTTPException(status_code=404, detail="Standard not found")

    old_values = {f: getattr(session, f) for f in update_data}

    for field, value in update_data.items():
        setattr(session, field, value)

    changes = {f: v for f, v in update_data.items() if old_values[f] != v}

    if changes:
        create_audit_log(
            db=db,
            current_user=current_user,
            entity_type="TEST_SESSION",
            entity_id=session.test_session_id,
            action="UPDATE",
            old_value={f: old_values[f] for f in changes},
            new_value=changes,
            request=request
        )

    db.commit()
    db.refresh(session)

    return session


@router.delete("/{test_session_id}")
def delete_test_session(
    test_session_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = _get_lab_session(db, test_session_id, current_user)

    reports = db.query(Report).filter(
        Report.test_session_id == session.test_session_id
    ).all()

    block = session_delete_block_reason(
        status=session.status,
        has_approved_report=any(
            (r.report_status or "").upper() == "APPROVED" for r in reports
        ),
        actor_role=current_user.role,
        actor_id=current_user.user_id,
        tester_id=session.tester_id
    )
    if block:
        raise HTTPException(status_code=block[0], detail=block[1])

    session_test_ids = [
        row[0] for row in db.query(TestSessionTest.session_test_id).filter(
            TestSessionTest.test_session_id == session.test_session_id
        ).all()
    ]
    report_ids = [r.report_id for r in reports]
    versions = (
        db.query(ReportVersion).filter(ReportVersion.report_id.in_(report_ids)).all()
        if report_ids else []
    )
    file_paths = collect_report_paths(*reports, *versions)

    deleted: dict[str, int] = {}

    def remove(label: str, model, condition) -> None:
        deleted[label] = db.query(model).filter(condition).delete(
            synchronize_session=False
        )

    # Most child tables have no database-level cascade, so every one is removed
    # explicitly, children before parents, in one transaction.
    try:
        if report_ids:
            remove("report_signatures", DigitalSignature, DigitalSignature.report_id.in_(report_ids))
            remove("report_versions", ReportVersion, ReportVersion.report_id.in_(report_ids))
            remove("reports", Report, Report.report_id.in_(report_ids))

        if session_test_ids:
            remove("equipment_usage", TestEquipmentUsage, TestEquipmentUsage.session_test_id.in_(session_test_ids))
            remove("results", TestResult, TestResult.session_test_id.in_(session_test_ids))
            remove("calculations", TestCalculation, TestCalculation.session_test_id.in_(session_test_ids))
            remove("observations", TestObservation, TestObservation.session_test_id.in_(session_test_ids))

        attachment_filter = Attachment.test_session_id == session.test_session_id
        if session_test_ids:
            attachment_filter = or_(
                attachment_filter, Attachment.session_test_id.in_(session_test_ids)
            )
        remove("attachments", Attachment, attachment_filter)

        remove("observation_imports", ObservationImport, ObservationImport.test_session_id == session.test_session_id)
        remove("environmental_conditions", EnvironmentalCondition, EnvironmentalCondition.test_session_id == session.test_session_id)
        remove("tests", TestSessionTest, TestSessionTest.test_session_id == session.test_session_id)

        create_audit_log(
            db=db,
            current_user=current_user,
            entity_type="TEST_SESSION",
            entity_id=session.test_session_id,
            action="DELETE",
            old_value={
                "session_number": session.session_number,
                "application_number": session.application_number,
                "status": session.status,
                "instrument_id": session.instrument_id,
                "standard_id": session.standard_id,
                "removed": deleted,
            },
            request=request
        )

        db.delete(session)
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Only after the database commit succeeded.
    remove_report_files(file_paths)

    return {
        "message": "Test session deleted",
        "test_session_id": str(test_session_id),
        "deleted": deleted
    }
