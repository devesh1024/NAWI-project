# backend/app/services/audit_service.py
#
# Shared audit-trail helper. Same behaviour as the helper inside
# api/reports/routes.py; the new update/delete endpoints import it from here.
# It only ADDS the row to the session: the caller commits, so the audit entry
# and the change it describes are saved (or rolled back) together.

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User


def json_safe(value):
    """Make a value storable in a JSON column (UUID/datetime/Decimal -> str/float)."""
    if isinstance(value, (UUID, datetime, date)):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def create_audit_log(
    db: Session,
    current_user: User,
    entity_type: str,
    entity_id,
    action: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    remarks: str | None = None,
    request: Request | None = None,
):
    ip_address = None

    if request is not None and request.client:
        ip_address = request.client.host

    audit_log = AuditLog(
        laboratory_id=current_user.laboratory_id,
        user_id=current_user.user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=json_safe(old_value) if old_value is not None else None,
        new_value=json_safe(new_value) if new_value is not None else None,
        ip_address=ip_address,
        remarks=remarks,
    )

    db.add(audit_log)

    return audit_log
