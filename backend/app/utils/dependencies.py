from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.user import User
from backend.app.utils.security import SECRET_KEY, ALGORITHM


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # The JWT carries the user id as a string. Convert it to a UUID before
    # querying: the column is a UUID type, and comparing it to a plain str
    # works on Postgres but raises on SQLite. A missing or malformed id is a
    # bad token (401), not a server error.
    try:
        user_id = UUID(str(payload.get("user_id")))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )

    return user


def require_lab_admin(
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "LAB_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lab Admin access required"
        )

    return current_user


def require_capability(capability: str):
    """
    Dependency factory: only roles holding `capability` (see
    services/permissions.py) may call the endpoint.

        current_user: User = Depends(require_capability("equipment.manage"))
    """
    from backend.app.services.permissions import label_for, user_can

    def checker(current_user: User = Depends(get_current_user)):
        if not user_can(current_user, capability):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your role ({label_for(current_user.role)}) is not permitted "
                    f"to do this."
                ),
            )
        return current_user

    return checker
