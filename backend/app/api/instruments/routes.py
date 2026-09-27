from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.instrument import Instrument
from backend.app.models.user import User
from backend.app.schemas.instrument import (
    InstrumentCreate,
    InstrumentUpdate,
    InstrumentResponse,
)
from backend.app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/api/instruments",
    tags=["Instruments"]
)


@router.post(
    "",
    response_model=InstrumentResponse,
    status_code=status.HTTP_201_CREATED
)
def create_instrument(
    data: InstrumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check duplicate instrument code within the same laboratory
    existing = (
        db.query(Instrument)
        .filter(
            Instrument.instrument_code == data.instrument_code,
            Instrument.laboratory_id == current_user.laboratory_id
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Instrument code already exists in this laboratory"
        )

    instrument = Instrument(
        laboratory_id=current_user.laboratory_id,
        created_by=current_user.user_id,
        **data.model_dump()
    )

    db.add(instrument)
    db.commit()
    db.refresh(instrument)

    return instrument


@router.get(
    "",
    response_model=list[InstrumentResponse]
)
def get_instruments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    instruments = (
        db.query(Instrument)
        .filter(
            Instrument.laboratory_id == current_user.laboratory_id
        )
        .all()
    )

    return instruments


@router.get(
    "/{instrument_id}",
    response_model=InstrumentResponse
)
def get_instrument(
    instrument_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    instrument = (
        db.query(Instrument)
        .filter(
            Instrument.instrument_id == instrument_id,
            Instrument.laboratory_id == current_user.laboratory_id
        )
        .first()
    )

    if not instrument:
        raise HTTPException(
            status_code=404,
            detail="Instrument not found"
        )

    return instrument


@router.put(
    "/{instrument_id}",
    response_model=InstrumentResponse
)
def update_instrument(
    instrument_id: UUID,
    data: InstrumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    instrument = (
        db.query(Instrument)
        .filter(
            Instrument.instrument_id == instrument_id,
            Instrument.laboratory_id == current_user.laboratory_id
        )
        .first()
    )

    if not instrument:
        raise HTTPException(
            status_code=404,
            detail="Instrument not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(instrument, field, value)

    db.commit()
    db.refresh(instrument)

    return instrument