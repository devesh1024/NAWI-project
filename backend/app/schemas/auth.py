from pydantic import BaseModel, EmailStr


class LabAdminRegister(BaseModel):
    # Laboratory details
    laboratory_code: str
    laboratory_name: str
    registration_number: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    country: str | None = None
    phone: str | None = None
    laboratory_email: EmailStr | None = None
    website: str | None = None
    accreditation_fields: str | None = None

    # Lab Admin details
    first_name: str
    last_name: str | None = None
    email: EmailStr
    admin_phone: str | None = None
    password: str
    designation: str | None = None
    qualification: str | None = None


class RegisterResponse(BaseModel):
    message: str
    laboratory_id: str
    user_id: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    laboratory_id: str
    role: str