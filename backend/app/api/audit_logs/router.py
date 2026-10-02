from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User
from backend.app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/api/audit-logs",
    tags=["Audit Logs"]
)


@router.get("")
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    audit_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.laboratory_id == current_user.laboratory_id
        )
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    return [
        {
            "audit_id": str(log.audit_id),
            "laboratory_id": str(log.laboratory_id),
            "user_id": str(log.user_id),
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id),
            "action": log.action,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "timestamp": log.timestamp,
            "ip_address": log.ip_address,
            "remarks": log.remarks
        }
        for log in audit_logs
    ]