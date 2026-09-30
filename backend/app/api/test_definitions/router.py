from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_definition import TestDefinition
from backend.app.models.standard import Standard
from backend.app.models.user import User
from backend.app.schemas.test_definition import (
    TestDefinitionResponse,
    TestDefinitionCreate,
    TestDefinitionUpdate,
)
from backend.app.utils.dependencies import (
    get_current_user,
    require_lab_admin,
)


router = APIRouter(
    prefix="/api/test-definitions",
    tags=["Test Definitions"],
)


@router.get("", response_model=list[TestDefinitionResponse])
def list_test_definitions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test_definitions = (
        db.query(TestDefinition)
        .order_by(TestDefinition.test_code)
        .all()
    )

    return test_definitions


@router.get("/{test_definition_id}", response_model=TestDefinitionResponse)
def get_test_definition(
    test_definition_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test_definition = (
        db.query(TestDefinition)
        .filter(
            TestDefinition.test_definition_id == test_definition_id
        )
        .first()
    )

    if not test_definition:
        raise HTTPException(
            status_code=404,
            detail="Test definition not found",
        )

    return test_definition


@router.post(
    "",
    response_model=TestDefinitionResponse,
    status_code=201,
)
def create_test_definition(
    data: TestDefinitionCreate,
    current_user: User = Depends(require_lab_admin),
    db: Session = Depends(get_db),
):
    # Check that the referenced standard exists
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

    # Prevent duplicate test code for the same standard
    existing_test = (
        db.query(TestDefinition)
        .filter(
            TestDefinition.standard_id == data.standard_id,
            TestDefinition.test_code == data.test_code,
        )
        .first()
    )

    if existing_test:
        raise HTTPException(
            status_code=400,
            detail="Test definition with this code already exists for this standard",
        )

    test_definition = TestDefinition(
        standard_id=data.standard_id,
        test_code=data.test_code,
        test_name=data.test_name,
        category=data.category,
        description=data.description,
        reference_clause=data.reference_clause,
        procedure=data.procedure,
        required_inputs=data.required_inputs,
        calculation_type=data.calculation_type,
        acceptance_rule=data.acceptance_rule,
        required_equipment=data.required_equipment,
        is_mandatory=data.is_mandatory,
        active=data.active,
    )

    db.add(test_definition)
    db.commit()
    db.refresh(test_definition)

    return test_definition


@router.put(
    "/{test_definition_id}",
    response_model=TestDefinitionResponse,
)
def update_test_definition(
    test_definition_id: UUID,
    data: TestDefinitionUpdate,
    current_user: User = Depends(require_lab_admin),
    db: Session = Depends(get_db),
):
    test_definition = (
        db.query(TestDefinition)
        .filter(
            TestDefinition.test_definition_id == test_definition_id
        )
        .first()
    )

    if not test_definition:
        raise HTTPException(
            status_code=404,
            detail="Test definition not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    # If test_code is being changed, prevent duplicate codes
    if "test_code" in update_data:
        existing_test = (
            db.query(TestDefinition)
            .filter(
                TestDefinition.standard_id == test_definition.standard_id,
                TestDefinition.test_code == update_data["test_code"],
                TestDefinition.test_definition_id != test_definition_id,
            )
            .first()
        )

        if existing_test:
            raise HTTPException(
                status_code=400,
                detail="Test definition with this code already exists for this standard",
            )

    for field, value in update_data.items():
        setattr(test_definition, field, value)

    db.commit()
    db.refresh(test_definition)

    return test_definition