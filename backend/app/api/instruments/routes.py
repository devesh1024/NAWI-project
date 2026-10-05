from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.instrument import Instrument
from backend.app.models.test_session import TestSession
from backend.app.models.user import User
from backend.app.schemas.instrument import (
    InstrumentCreate,
    InstrumentUpdate,
    InstrumentResponse,
)
from backend.app.services.audit_service import create_audit_log
from backend.app.services.crud_rules import (
    changed_locked_fields,
    instrument_delete_block_reason,
    instrument_edit_block_reason,
    normalize_instrument_status,
)
from backend.app.services import permissions as perm
from backend.app.utils.dependencies import get_current_user, require_capability


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
    current_user: User = Depends(require_capability("instruments.register")),
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
    request: Request,
    current_user: User = Depends(require_capability("instruments.register")),
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

    # A cleared field arrives as null; refuse it for columns that cannot be null.
    for field, value in update_data.items():
        column = Instrument.__table__.columns.get(field)
        if value is None and column is not None and not column.nullable:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be empty"
            )

    if "status" in update_data:
        try:
            update_data["status"] = normalize_instrument_status(
                update_data["status"]
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    # Metrological fields are frozen once results exist that depend on them.
    locked = changed_locked_fields(instrument, update_data)

    if locked:
        sessions_past_draft = (
            db.query(func.count(TestSession.test_session_id))
            .filter(
                TestSession.instrument_id == instrument.instrument_id,
                TestSession.laboratory_id == current_user.laboratory_id,
                func.upper(TestSession.status) != "DRAFT"
            )
            .scalar()
        )

        reason = instrument_edit_block_reason(locked, sessions_past_draft)

        if reason:
            raise HTTPException(status_code=409, detail=reason)

    old_values = {f: getattr(instrument, f) for f in update_data}

    for field, value in update_data.items():
        setattr(instrument, field, value)

    changes = {
        f: v for f, v in update_data.items() if old_values[f] != v
    }

    if changes:
        create_audit_log(
            db=db,
            current_user=current_user,
            entity_type="INSTRUMENT",
            entity_id=instrument.instrument_id,
            action="UPDATE",
            old_value={f: old_values[f] for f in changes},
            new_value=changes,
            request=request
        )

    db.commit()
    db.refresh(instrument)

    return instrument


@router.delete("/{instrument_id}")
def delete_instrument(
    instrument_id: UUID,
    request: Request,
    current_user: User = Depends(require_capability("instruments.delete")),
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

    # test_sessions.instrument_id has no database foreign key, so nothing would
    # stop a delete from leaving sessions pointing at a missing instrument.
    session_count = (
        db.query(func.count(TestSession.test_session_id))
        .filter(
            TestSession.instrument_id == instrument.instrument_id,
            TestSession.laboratory_id == current_user.laboratory_id
        )
        .scalar()
    )

    reason = instrument_delete_block_reason(session_count)

    if reason:
        raise HTTPException(status_code=409, detail=reason)

    create_audit_log(
        db=db,
        current_user=current_user,
        entity_type="INSTRUMENT",
        entity_id=instrument.instrument_id,
        action="DELETE",
        old_value={
            "instrument_code": instrument.instrument_code,
            "manufacturer": instrument.manufacturer,
            "model": getattr(instrument, "model", None),
            "serial_number": getattr(instrument, "serial_number", None),
        },
        request=request
    )

    db.delete(instrument)
    db.commit()

    return {
        "message": "Instrument deleted",
        "instrument_id": str(instrument_id)
    }