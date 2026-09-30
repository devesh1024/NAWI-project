from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.user import User
from backend.app.schemas.laboratory import (
    LaboratoryResponse,
    LaboratoryUpdate,
)
from backend.app.services.laboratory_service import (
    get_laboratory,
    update_laboratory,
)
from backend.app.utils.dependencies import (
    get_current_user,
    require_lab_admin,
)


router = APIRouter(
    prefix="/api/laboratories",
    tags=["Laboratories"]
)


@router.get(
    "/me",
    response_model=LaboratoryResponse
)
def get_my_laboratory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_laboratory(
        db,
        current_user.laboratory_id
    )


@router.put(
    "/me",
    response_model=LaboratoryResponse
)
def update_my_laboratory(
    data: LaboratoryUpdate,
    current_user: User = Depends(require_lab_admin),
    db: Session = Depends(get_db)
):
    return update_laboratory(
        db,
        current_user.laboratory_id,
        data
    )