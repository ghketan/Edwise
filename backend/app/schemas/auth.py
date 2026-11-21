from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from backend.app.models.user import UserRole


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    username: str
    student_id: Optional[int] = None
    teacher_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TokenPayload(BaseModel):
    sub: str
    role: str
    type: str
    exp: int


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=72)


class StudentRegisterRequest(BaseModel):
    """
    Contract API-002: Student self-registration by claiming a roster record.
    Generic responses prevent admission number enumeration (R-003, T-006).
    """
    admission_number: str = Field(..., min_length=1, max_length=50)
    class_id: int
    password: str = Field(..., min_length=8, max_length=72)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)


class StudentRegisterResponse(BaseModel):
    message: str = "Registration request received and being processed."
    status: str = "pending_verification"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
