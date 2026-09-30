from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.laboratory import Laboratory
from backend.app.schemas.laboratory import LaboratoryUpdate


def get_laboratory(
    db: Session,
    laboratory_id: UUID
):
    laboratory = (
        db.query(Laboratory)
        .filter(
            Laboratory.laboratory_id == laboratory_id
        )
        .first()
    )

    if not laboratory:
        raise HTTPException(
            status_code=404,
            detail="Laboratory not found"
        )

    return laboratory


def update_laboratory(
    db: Session,
    laboratory_id: UUID,
    data: LaboratoryUpdate
):
    laboratory = get_laboratory(
        db,
        laboratory_id
    )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(laboratory, field, value)

    db.commit()
    db.refresh(laboratory)

    return laboratory