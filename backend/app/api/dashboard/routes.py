from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.user import User
from backend.app.services.dashboard_service import build_dashboard
from backend.app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("")
def my_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The dashboard for the signed-in user's role, built from live data."""
    return build_dashboard(db, current_user)
