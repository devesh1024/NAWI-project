from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.laboratory import Laboratory
from backend.app.models.user import User
from backend.app.schemas.auth import (
    LabAdminRegister,
    RegisterResponse,
    LoginRequest,
    LoginResponse
)
from backend.app.utils.security import (
    hash_password,
    verify_password,
    create_access_token
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=RegisterResponse
)
def register_lab_admin(
    data: LabAdminRegister,
    db: Session = Depends(get_db)
):
    # Check laboratory code
    existing_lab = (
        db.query(Laboratory)
        .filter(
            Laboratory.laboratory_code == data.laboratory_code
        )
        .first()
    )

    if existing_lab:
        raise HTTPException(
            status_code=400,
            detail="Laboratory code already exists"
        )

    # Check email
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

    # Create laboratory
    laboratory = Laboratory(
        laboratory_code=data.laboratory_code,
        name=data.laboratory_name,
        registration_number=data.registration_number,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        country=data.country,
        phone=data.phone,
        email=data.laboratory_email,
        website=data.website,
        accreditation_fields=data.accreditation_fields,
        status="ACTIVE"
    )

    db.add(laboratory)
    db.flush()

    # Create Lab Admin
    admin = User(
        laboratory_id=laboratory.laboratory_id,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.admin_phone,
        password_hash=hash_password(data.password),
        role="LAB_ADMIN",
        designation=data.designation,
        qualification=data.qualification,
        status="ACTIVE"
    )

    db.add(admin)

    db.commit()

    db.refresh(laboratory)
    db.refresh(admin)

    return RegisterResponse(
        message="Laboratory and Lab Admin registered successfully",
        laboratory_id=str(laboratory.laboratory_id),
        user_id=str(admin.user_id)
    )


@router.post(
    "/login",
    response_model=LoginResponse
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    # Find user by email
    user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(
        data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Check user status
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="User account is not active"
        )

    # Create JWT
    access_token = create_access_token({
        "user_id": str(user.user_id),
        "laboratory_id": str(user.laboratory_id),
        "role": user.role
    })

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.user_id),
        laboratory_id=str(user.laboratory_id),
        role=user.role
    )