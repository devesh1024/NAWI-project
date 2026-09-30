from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.user import User
from backend.app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserCreate,
)
from backend.app.utils.dependencies import (
    get_current_user,
    require_lab_admin,
)
from backend.app.utils.security import hash_password


router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)


@router.get(
    "/me",
    response_model=UserResponse
)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.put(
    "/me",
    response_model=UserResponse
)
def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    update_data = data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.get(
    "",
    response_model=list[UserResponse]
)
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    users = (
        db.query(User)
        .filter(
            User.laboratory_id == current_user.laboratory_id
        )
        .order_by(User.created_at.desc())
        .all()
    )

    return users


@router.post(
    "",
    response_model=UserResponse,
    status_code=201
)
def create_user(
    data: UserCreate,
    current_user: User = Depends(require_lab_admin),
    db: Session = Depends(get_db)
):
    # Only allow non-admin staff to be created here.
    allowed_roles = {
        "TESTER",
        "REVIEWER",
        "APPROVER",
    }

    if data.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid user role"
        )

    # Email must be unique.
    existing_user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user = User(
        laboratory_id=current_user.laboratory_id,
        employee_id=data.employee_id,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=data.role,
        designation=data.designation,
        qualification=data.qualification,
        authorization_scope=data.authorization_scope,
        status="ACTIVE",
        created_by=current_user.user_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user