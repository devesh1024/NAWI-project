from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_equipment import TestEquipment
from backend.app.models.test_equipment_usage import TestEquipmentUsage
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
from backend.app.schemas.test_equipment import (
    TestEquipmentCreate,
    TestEquipmentResponse,
    TestEquipmentUpdate,
    TestEquipmentUsageCreate,
    TestEquipmentUsageResponse,
)
from backend.app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/api/test-equipment",
    tags=["Test Equipment"],
)


# ---------------------------------------------------------
# Equipment Master
# ---------------------------------------------------------

@router.post(
    "",
    response_model=TestEquipmentResponse,
    status_code=status.HTTP_200_OK,
)
def create_equipment(
    data: TestEquipmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    equipment = TestEquipment(
        laboratory_id=current_user.laboratory_id,
        **data.model_dump(),
    )

    db.add(equipment)
    db.commit()
    db.refresh(equipment)

    return equipment


@router.get(
    "",
    response_model=list[TestEquipmentResponse],
)
def get_equipment_list(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(TestEquipment)
        .filter(
            TestEquipment.laboratory_id == current_user.laboratory_id
        )
        .order_by(TestEquipment.created_at.desc())
        .all()
    )


@router.get(
    "/{equipment_id}",
    response_model=TestEquipmentResponse,
)
def get_equipment(
    equipment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    equipment = (
        db.query(TestEquipment)
        .filter(
            TestEquipment.equipment_id == equipment_id,
            TestEquipment.laboratory_id == current_user.laboratory_id,
        )
        .first()
    )

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Test equipment not found",
        )

    return equipment


@router.put(
    "/{equipment_id}",
    response_model=TestEquipmentResponse,
)
def update_equipment(
    equipment_id: UUID,
    data: TestEquipmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    equipment = (
        db.query(TestEquipment)
        .filter(
            TestEquipment.equipment_id == equipment_id,
            TestEquipment.laboratory_id == current_user.laboratory_id,
        )
        .first()
    )

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Test equipment not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(equipment, field, value)

    db.commit()
    db.refresh(equipment)

    return equipment


@router.delete(
    "/{equipment_id}",
)
def delete_equipment(
    equipment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    equipment = (
        db.query(TestEquipment)
        .filter(
            TestEquipment.equipment_id == equipment_id,
            TestEquipment.laboratory_id == current_user.laboratory_id,
        )
        .first()
    )

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Test equipment not found",
        )

    db.delete(equipment)
    db.commit()

    return {
        "message": "Test equipment deleted successfully"
    }


# ---------------------------------------------------------
# Equipment Usage
# ---------------------------------------------------------

@router.post(
    "/usage",
    response_model=TestEquipmentUsageResponse,
    status_code=status.HTTP_200_OK,
)
def assign_equipment_to_test(
    data: TestEquipmentUsageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Verify equipment belongs to current laboratory
    equipment = (
        db.query(TestEquipment)
        .filter(
            TestEquipment.equipment_id == data.equipment_id,
            TestEquipment.laboratory_id == current_user.laboratory_id,
        )
        .first()
    )

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Test equipment not found",
        )

    # Verify test belongs to current laboratory
    session_test = (
        db.query(TestSessionTest)
        .join(
            TestSession,
            TestSession.test_session_id == TestSessionTest.test_session_id,
        )
        .filter(
            TestSessionTest.session_test_id == data.session_test_id,
            TestSession.laboratory_id == current_user.laboratory_id,
        )
        .first()
    )

    if not session_test:
        raise HTTPException(
            status_code=404,
            detail="Test session test not found",
        )

    usage = TestEquipmentUsage(
        session_test_id=data.session_test_id,
        equipment_id=data.equipment_id,
        used_from=data.used_from,
        used_to=data.used_to,
        remarks=data.remarks,
    )

    db.add(usage)
    db.commit()
    db.refresh(usage)

    return usage


@router.get(
    "/usage/test/{session_test_id}",
    response_model=list[TestEquipmentUsageResponse],
)
def get_test_equipment_usage(
    session_test_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    session_test = (
        db.query(TestSessionTest)
        .join(
            TestSession,
            TestSession.test_session_id == TestSessionTest.test_session_id,
        )
        .filter(
            TestSessionTest.session_test_id == session_test_id,
            TestSession.laboratory_id == current_user.laboratory_id,
        )
        .first()
    )

    if not session_test:
        raise HTTPException(
            status_code=404,
            detail="Test session test not found",
        )

    return (
        db.query(TestEquipmentUsage)
        .filter(
            TestEquipmentUsage.session_test_id == session_test_id
        )
        .order_by(TestEquipmentUsage.created_at.desc())
        .all()
    )