"""
Public report verification — NO AUTHENTICATION REQUIRED.

This is deliberately the one set of endpoints in the whole API with no
Depends(get_current_user): anyone with a report (lab staff or an outside
party who received one) needs to be able to check it, logged in or not.
Keep anything added here to non-sensitive fields only — no tester contact
info, no internal user IDs beyond what's already printed on the report
itself.

Three distinct trust levels, intentionally not conflated:

1. GET /api/verify-report/{test_session_id} — the "scan a QR code" path.
   Pure DB lookup, no file involved. Confirms a report with this ID exists
   and shows what it SHOULD say. Does NOT prove the specific copy someone
   is holding hasn't been altered — it's a quick/light check only.

2. POST /api/verify-report/upload with a PDF — the real tamper check.
   Validates the embedded cryptographic signature (see signing.py): if the
   PDF's bytes changed at all since we generated it, this fails, even if
   the DB lookup above would have looked fine.

3. POST /api/verify-report/upload with a DOCX — weaker than #2 by
   necessity. There is no byte-level tamper detection available for DOCX
   via python-docx. This can only confirm the file's embedded metadata
   points to a report that exists in our system — it cannot detect edits
   made to the document after generation. The response says so explicitly;
   the frontend must not present this with the same confidence as the PDF
   path.
"""
import io
import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_session import TestSession
from backend.app.models.instrument import Instrument
from backend.app.models.laboratory import Laboratory
from backend.app.models.report import Report
from backend.app.services.verification.signing import verify_pdf_signature

router = APIRouter(prefix="/api/verify-report", tags=["Report Verification"])

SUBJECT_PATTERN = re.compile(r"NAWI-VERIFY:([0-9a-fA-F-]{36}):(.*)")


def _public_record(db: Session, test_session_id) -> Optional[dict]:
    """Safe, non-sensitive fields only — this is served with no auth."""
    session = db.query(TestSession).filter(TestSession.test_session_id == test_session_id).first()
    if not session:
        return None

    report = (
        db.query(Report)
        .filter(Report.test_session_id == test_session_id)
        .order_by(Report.generated_at.desc())
        .first()
    )
    instrument = db.query(Instrument).filter(Instrument.instrument_id == session.instrument_id).first()
    laboratory = db.query(Laboratory).filter(Laboratory.laboratory_id == session.laboratory_id).first()

    return {
        "test_session_id": str(test_session_id),
        "session_number": session.session_number,
        "overall_result": session.overall_result,
        "laboratory_name": laboratory.name if laboratory else None,
        "laboratory_city": laboratory.city if laboratory else None,
        "instrument_manufacturer": instrument.manufacturer if instrument else None,
        "instrument_model": instrument.model if instrument else None,
        "report_number": report.report_number if report else None,
        "report_version": report.report_version if report else None,
        "report_status": report.report_status if report else None,
        "generated_at": report.generated_at if report else None,
        "approved_at": report.approved_at if report else None,
        "report_hash": report.report_hash if report else None,
    }


@router.get("/{test_session_id}")
def verify_by_id(test_session_id: UUID, db: Session = Depends(get_db)):
    """The QR-scan path: light check, DB lookup only, no file involved."""
    record = _public_record(db, test_session_id)
    if not record:
        raise HTTPException(status_code=404, detail="No report found with this ID.")
    return {
        "verdict": "FOUND",
        "check_type": "LIGHT",
        "message": (
            "A report with this ID exists in our records. This confirms "
            "the report exists — it does not verify that a specific "
            "physical or digital copy you're holding hasn't been altered. "
            "Upload the PDF for a full tamper check."
        ),
        "record": record,
    }


@router.post("/upload")
async def verify_by_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        return _verify_pdf(data, db)
    elif filename.endswith(".docx"):
        return _verify_docx(data, db)
    else:
        raise HTTPException(status_code=400, detail="Only .pdf and .docx files are supported.")


def _extract_test_session_id(subject: Optional[str]) -> Optional[str]:
    if not subject:
        return None
    m = SUBJECT_PATTERN.match(subject)
    return m.group(1) if m else None


def _verify_pdf(data: bytes, db: Session) -> dict:
    # Metadata lookup (which report is this?) — independent of the
    # signature check (is this exact file unmodified?) below.
    from pypdf import PdfReader

    try:
        subject = PdfReader(io.BytesIO(data)).metadata.subject
    except Exception:
        subject = None

    test_session_id = _extract_test_session_id(subject)
    record = _public_record(db, test_session_id) if test_session_id else None

    sig_status = verify_pdf_signature(data)

    if not record:
        verdict = "NOT_FOUND"
        message = "This PDF's embedded report ID doesn't match any report in our system."
    elif sig_status.get("signed") and sig_status.get("bottom_line"):
        verdict = "AUTHENTIC"
        message = "Signature valid and file unmodified since generation. This report is authentic."
    elif sig_status.get("signed") and not sig_status.get("intact"):
        verdict = "TAMPERED"
        message = "This file has been MODIFIED since it was signed. Do not trust its contents."
    elif not sig_status.get("signed"):
        verdict = "UNSIGNED"
        message = (
            "This PDF has no embedded digital signature — either it predates this "
            "feature, or it did not originate from our system's report generator."
        )
    else:
        verdict = "UNVERIFIABLE"
        message = "Could not establish this file's authenticity."

    return {
        "verdict": verdict,
        "check_type": "FULL_PDF_SIGNATURE",
        "message": message,
        "signature": sig_status,
        "record": record,
    }


def _verify_docx(data: bytes, db: Session) -> dict:
    from docx import Document

    try:
        doc = Document(io.BytesIO(data))
        subject = doc.core_properties.subject
    except Exception:
        subject = None

    test_session_id = _extract_test_session_id(subject)
    record = _public_record(db, test_session_id) if test_session_id else None

    return {
        "verdict": "FOUND_IN_SYSTEM" if record else "NOT_FOUND",
        "check_type": "METADATA_ONLY",
        "message": (
            "This Word document's embedded report ID matches a report in our "
            "system. IMPORTANT: unlike the PDF, Word documents cannot be "
            "cryptographically verified — this confirms the document "
            "corresponds to a real report, but cannot detect edits made to "
            "it after generation. For a full tamper check, use the PDF."
            if record
            else "This Word document's embedded report ID doesn't match any report in our system."
        ),
        "record": record,
    }
