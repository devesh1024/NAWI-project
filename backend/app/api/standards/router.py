from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.standard import Standard
from backend.app.models.user import User
from backend.app.schemas.standard import (
    StandardResponse,
    StandardCreate,
    StandardUpdate,
)
from backend.app.utils.dependencies import (
    get_current_user,
    require_capability,
)


router = APIRouter(
    prefix="/api/standards",
    tags=["Standards"],
)


@router.get("", response_model=list[StandardResponse])
def list_standards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    standards = (
        db.query(Standard)
        .order_by(Standard.edition_year.desc().nullslast())
        .all()
    )

    return standards


@router.get("/{standard_id}", response_model=StandardResponse)
def get_standard(
    standard_id,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    standard = (
        db.query(Standard)
        .filter(Standard.standard_id == standard_id)
        .first()
    )

    if not standard:
        raise HTTPException(
            status_code=404,
            detail="Standard not found",
        )

    return standard


@router.post(
    "",
    response_model=StandardResponse,
    status_code=201,
)
def create_standard(
    data: StandardCreate,
    current_user: User = Depends(require_capability("methods.manage")),
    db: Session = Depends(get_db),
):
    existing_standard = (
        db.query(Standard)
        .filter(
            Standard.standard_code == data.standard_code,
            Standard.version == data.version,
        )
        .first()
    )

    if existing_standard:
        raise HTTPException(
            status_code=400,
            detail="Standard with this code and version already exists",
        )

    standard = Standard(
        standard_code=data.standard_code,
        title=data.title,
        version=data.version,
        edition_year=data.edition_year,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        source_document=data.source_document,
        source_url=data.source_url,
        status=data.status,
    )

    db.add(standard)
    db.commit()
    db.refresh(standard)

    return standard


@router.put(
    "/{standard_id}",
    response_model=StandardResponse,
)
def update_standard(
    standard_id,
    data: StandardUpdate,
    current_user: User = Depends(require_capability("methods.manage")),
    db: Session = Depends(get_db),
):
    standard = (
        db.query(Standard)
        .filter(Standard.standard_id == standard_id)
        .first()
    )

    if not standard:
        raise HTTPException(
            status_code=404,
            detail="Standard not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(standard, field, value)

    db.commit()
    db.refresh(standard)

    return standard