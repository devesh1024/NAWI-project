from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    user_id: UUID
    laboratory_id: UUID
    employee_id: str | None = None
    first_name: str
    last_name: str | None = None
    email: EmailStr
    phone: str | None = None
    role: str
    designation: str | None = None
    qualification: str | None = None
    authorization_scope: dict | None = None
    status: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    employee_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    designation: str | None = None
    qualification: str | None = None
    authorization_scope: dict | None = None


class UserCreate(BaseModel):
    employee_id: str | None = None
    first_name: str
    last_name: str | None = None
    email: EmailStr
    phone: str | None = None
    password: str
    role: str
    designation: str | None = None
    qualification: str | None = None
    authorization_scope: dict | None = None