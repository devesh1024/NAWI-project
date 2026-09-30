from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.mpe_rule import MPERule
from backend.app.models.standard import Standard
from backend.app.models.user import User
from backend.app.schemas.mpe_rule import (
    MPERuleResponse,
    MPERuleCreate,
    MPERuleUpdate,
)
from backend.app.utils.dependencies import (
    get_current_user,
    require_lab_admin,
)

router = APIRouter(
    prefix="/api/mpe-rules",
    tags=["MPE Rules"],
)


@router.get("", response_model=list[MPERuleResponse])
def list_mpe_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(MPERule)
        .order_by(MPERule.accuracy_class, MPERule.range_min_e)
        .all()
    )


@router.get("/{mpe_rule_id}", response_model=MPERuleResponse)
def get_mpe_rule(
    mpe_rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mpe_rule = (
        db.query(MPERule)
        .filter(MPERule.mpe_rule_id == mpe_rule_id)
        .first()
    )

    if not mpe_rule:
        raise HTTPException(
            status_code=404,
            detail="MPE rule not found",
        )

    return mpe_rule


@router.post("", response_model=MPERuleResponse, status_code=201)
def create_mpe_rule(
    data: MPERuleCreate,
    current_user: User = Depends(require_lab_admin),
    db: Session = Depends(get_db),
):
    standard = (
        db.query(Standard)
        .filter(Standard.standard_id == data.standard_id)
        .first()
    )

    if not standard:
        raise HTTPException(
            status_code=404,
            detail="Standard not found",
        )

    mpe_rule = MPERule(
        standard_id=data.standard_id,
        accuracy_class=data.accuracy_class,
        range_min_e=data.range_min_e,
        range_max_e=data.range_max_e,
        mpe_value_e=data.mpe_value_e,
        mpe_unit_type=data.mpe_unit_type,
        condition=data.condition,
        test_type=data.test_type,
        reference_clause=data.reference_clause,
    )

    db.add(mpe_rule)
    db.commit()
    db.refresh(mpe_rule)

    return mpe_rule


@router.put("/{mpe_rule_id}", response_model=MPERuleResponse)
def update_mpe_rule(
    mpe_rule_id: UUID,
    data: MPERuleUpdate,
    current_user: User = Depends(require_lab_admin),
    db: Session = Depends(get_db),
):
    mpe_rule = (
        db.query(MPERule)
        .filter(MPERule.mpe_rule_id == mpe_rule_id)
        .first()
    )

    if not mpe_rule:
        raise HTTPException(
            status_code=404,
            detail="MPE rule not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(mpe_rule, field, value)

    db.commit()
    db.refresh(mpe_rule)

    return mpe_rule