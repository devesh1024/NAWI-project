from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.user import User
from backend.app.schemas.user import (
    UserAdminUpdate,
    UserResponse,
    UserUpdate,
    UserCreate,
)
from backend.app.services import permissions as perm
from backend.app.services.audit_service import create_audit_log
from backend.app.utils.dependencies import (
    get_current_user,
    require_capability,
)
from backend.app.utils.security import hash_password


router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)

USER_STATUSES = {"ACTIVE", "INACTIVE", "SUSPENDED"}


def _present(user: User) -> UserResponse:
    """A user row plus what their role means (label, level, capabilities)."""
    response = UserResponse.model_validate(user)
    role = perm.role_def(user.role)
    response.role_label = perm.label_for(user.role)
    response.role_level = role.level if role else None
    response.capabilities = sorted(perm.capabilities_for(user.role))
    return response


@router.get("/roles")
def list_roles(current_user: User = Depends(get_current_user)):
    """The laboratory roles, what each is responsible for, and what it may do."""
    return perm.catalogue()


@router.get(
    "/me",
    response_model=UserResponse
)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return _present(current_user)


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

    # Authorisation is granted by the Technical Manager, never self-assigned.
    update_data.pop("authorization_scope", None)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return _present(current_user)


@router.get(
    "",
    response_model=list[UserResponse]
)
def list_users(
    current_user: User = Depends(require_capability(perm.USERS_VIEW)),
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

    return [_present(u) for u in users]


@router.post(
    "",
    response_model=UserResponse,
    status_code=201
)
def create_user(
    data: UserCreate,
    request: Request,
    current_user: User = Depends(require_capability(perm.USERS_MANAGE)),
    db: Session = Depends(get_db)
):
    # The Lab Head account is created once, when the laboratory is registered.
    role = (data.role or "").upper()

    if role not in perm.ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid user role. Choose one of: {', '.join(perm.ASSIGNABLE_ROLES)}"
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
        role=role,
        designation=data.designation or perm.label_for(role),
        qualification=data.qualification,
        authorization_scope=data.authorization_scope,
        status="ACTIVE",
        created_by=current_user.user_id,
    )

    db.add(user)
    db.flush()

    create_audit_log(
        db=db,
        current_user=current_user,
        entity_type="USER",
        entity_id=user.user_id,
        action="CREATE",
        new_value={"email": user.email, "role": role},
        request=request,
    )

    db.commit()
    db.refresh(user)

    return _present(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse
)
def update_user(
    user_id: UUID,
    data: UserAdminUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change a colleague's role, status, designation or test authorisation.

    - The Lab Head manages everything below.
    - The Technical Manager may only set which tests a person is authorised
      for (ISO 17025 competence), nothing else.
    """
    can_manage = perm.user_can(current_user, perm.USERS_MANAGE)
    can_authorise = perm.user_can(current_user, perm.USERS_AUTHORIZE)

    if not (can_manage or can_authorise):
        raise HTTPException(
            status_code=403,
            detail=f"Your role ({perm.label_for(current_user.role)}) cannot change users."
        )

    target = (
        db.query(User)
        .filter(
            User.user_id == user_id,
            User.laboratory_id == current_user.laboratory_id,
        )
        .first()
    )

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    changes = data.model_dump(exclude_unset=True)

    if not can_manage:
        extra = set(changes) - {"authorization_scope"}
        if extra:
            raise HTTPException(
                status_code=403,
                detail="You may only set test authorisation. Role, status and "
                       "other details are managed by the Lab Head."
            )

    is_self = str(target.user_id) == str(current_user.user_id)

    if "role" in changes and changes["role"] is not None:
        new_role = changes["role"].upper()

        if new_role not in perm.ASSIGNABLE_ROLES:
            raise HTTPException(status_code=400, detail="Invalid user role")
        if is_self:
            raise HTTPException(
                status_code=409,
                detail="You cannot change your own role."
            )
        if target.role == "LAB_ADMIN":
            raise HTTPException(
                status_code=409,
                detail="The Lab Head's role cannot be changed here."
            )
        changes["role"] = new_role

    if "status" in changes and changes["status"] is not None:
        new_status = changes["status"].upper()

        if new_status not in USER_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"status must be one of {sorted(USER_STATUSES)}"
            )
        if is_self and new_status != "ACTIVE":
            raise HTTPException(
                status_code=409,
                detail="You cannot deactivate your own account."
            )
        if target.role == "LAB_ADMIN" and new_status != "ACTIVE":
            raise HTTPException(
                status_code=409,
                detail="The Lab Head account cannot be deactivated."
            )
        changes["status"] = new_status

    before = {k: getattr(target, k) for k in changes}

    for field, value in changes.items():
        setattr(target, field, value)

    create_audit_log(
        db=db,
        current_user=current_user,
        entity_type="USER",
        entity_id=target.user_id,
        action="UPDATE",
        old_value=before,
        new_value=changes,
        request=request,
    )

    db.commit()
    db.refresh(target)

    return _present(target)
