# backend/app/schemas/report.py

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportResponse(BaseModel):
    report_id: UUID
    test_session_id: UUID
    report_number: Optional[str] = None
    report_version: Optional[str] = None
    report_status: Optional[str] = None
    overall_result: Optional[str] = None
    generated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    remarks: Optional[str] = None

    # From the report's test session, for display
    session_number: Optional[str] = None
    application_number: Optional[str] = None
    instrument_id: Optional[UUID] = None
    session_status: Optional[str] = None


class ReportUpdate(BaseModel):
    """
    Only the remarks of a report are editable. Its result, status and content
    are produced by the system; change them by regenerating the report.
    Any other field in the request is rejected (422), not silently ignored.
    """
    model_config = ConfigDict(extra="forbid")

    remarks: Optional[str] = None
