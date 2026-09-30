from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.test_applicability_rule import TestApplicabilityRule
from backend.app.models.test_definition import TestDefinition
from backend.app.models.user import User
from backend.app.schemas.test_applicability_rule import (
    TestApplicabilityRuleResponse,
    TestApplicabilityRuleCreate,
    TestApplicabilityRuleUpdate,
)
from backend.app.utils.dependencies import (
    get_current_user,
    require_lab_admin,
)


router = APIRouter(
    prefix="/api/test-applicability-rules",
    tags=["Test Applicability Rules"],
)


@router.get(
    "",
    response_model=list[TestApplicabilityRuleResponse],
)
def list_applicability_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rules = (
        db.query(TestApplicabilityRule)
        .order_by(TestApplicabilityRule.priority)
        .all()
    )

    return rules


@router.get(
    "/{applicability_rule_id}",
    response_model=TestApplicabilityRuleResponse,
)
def get_applicability_rule(
    applicability_rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rule = (
        db.query(TestApplicabilityRule)
        .filter(
            TestApplicabilityRule.applicability_rule_id
            == applicability_rule_id
        )
        .first()
    )

    if not rule:
        raise HTTPException(
            status_code=404,
            detail="Applicability rule not found",
        )

    return rule


@router.post(
    "",
    response_model=TestApplicabilityRuleResponse,
    status_code=201,
)
def create_applicability_rule(
    data: TestApplicabilityRuleCreate,
    current_user: User = Depends(require_lab_admin),
    db: Session = Depends(get_db),
):
    # Check that the test definition exists
    test_definition = (
        db.query(TestDefinition)
        .filter(
            TestDefinition.test_definition_id
            == data.test_definition_id
        )
        .first()
    )

    if not test_definition:
        raise HTTPException(
            status_code=404,
            detail="Test definition not found",
        )

    # Prevent duplicate priority for the same test definition
    if data.priority is not None:
        existing_rule = (
            db.query(TestApplicabilityRule)
            .filter(
                TestApplicabilityRule.test_definition_id
                == data.test_definition_id,
                TestApplicabilityRule.priority == data.priority,
            )
            .first()
        )

        if existing_rule:
            raise HTTPException(
                status_code=400,
                detail="Applicability rule with this priority already exists for this test",
            )

    rule = TestApplicabilityRule(
        test_definition_id=data.test_definition_id,
        instrument_condition=data.instrument_condition,
        applicable=data.applicable,
        reason=data.reason,
        priority=data.priority,
        standard_clause=data.standard_clause,
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return rule


@router.put(
    "/{applicability_rule_id}",
    response_model=TestApplicabilityRuleResponse,
)
def update_applicability_rule(
    applicability_rule_id: UUID,
    data: TestApplicabilityRuleUpdate,
    current_user: User = Depends(require_lab_admin),
    db: Session = Depends(get_db),
):
    rule = (
        db.query(TestApplicabilityRule)
        .filter(
            TestApplicabilityRule.applicability_rule_id
            == applicability_rule_id
        )
        .first()
    )

    if not rule:
        raise HTTPException(
            status_code=404,
            detail="Applicability rule not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Prevent duplicate priority for the same test
    if "priority" in update_data and update_data["priority"] is not None:
        existing_rule = (
            db.query(TestApplicabilityRule)
            .filter(
                TestApplicabilityRule.test_definition_id
                == rule.test_definition_id,
                TestApplicabilityRule.priority
                == update_data["priority"],
                TestApplicabilityRule.applicability_rule_id
                != applicability_rule_id,
            )
            .first()
        )

        if existing_rule:
            raise HTTPException(
                status_code=400,
                detail="Applicability rule with this priority already exists for this test",
            )

    for field, value in update_data.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)

    return rule