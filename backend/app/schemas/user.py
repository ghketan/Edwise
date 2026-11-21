from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from backend.app.models.user import UserRole


class UserBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: UserRole
    is_active: bool = True
    is_verified: bool = False


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8, max_length=72)
    role: UserRole
    is_active: bool = True
    is_verified: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=72)


class StudentProfileSummary(BaseModel):
    id: int
    admission_number: str
    full_name: str
    class_id: Optional[int] = None
    section_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TeacherProfileSummary(BaseModel):
    id: int
    employee_id: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    student_profile: Optional[StudentProfileSummary] = None
    teacher_profile: Optional[TeacherProfileSummary] = None

    model_config = ConfigDict(from_attributes=True)
