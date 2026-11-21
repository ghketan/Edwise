from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr


# Academic Session
class AcademicSessionBase(BaseModel):
    name: str
    start_date: date
    end_date: date
    is_active: bool = False


class AcademicSessionCreate(AcademicSessionBase):
    pass


class AcademicSessionUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class AcademicSessionResponse(AcademicSessionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Class
class ClassBase(BaseModel):
    name: str
    session_id: int


class ClassCreate(ClassBase):
    subject_ids: Optional[List[int]] = None


class ClassSubjectAssign(BaseModel):
    subject_id: Optional[int] = None
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None


class ClassResponse(ClassBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Section
class SectionBase(BaseModel):
    name: str
    class_id: int


class SectionCreate(SectionBase):
    pass


class SectionResponse(SectionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Subject
class SubjectBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class SubjectCreate(SubjectBase):
    pass


class SubjectResponse(SubjectBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Teacher
class TeacherBase(BaseModel):
    employee_id: str
    full_name: str
    department: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class TeacherCreate(TeacherBase):
    user_id: Optional[int] = None
    create_user_account: bool = False
    initial_password: Optional[str] = "Teacher@123"


class TeacherResponse(TeacherBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Student
class StudentBase(BaseModel):
    admission_number: str
    full_name: str
    class_id: int
    section_id: Optional[int] = None
    gender: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    is_synthetic: bool = False


class StudentCreate(StudentBase):
    pass


class StudentRosterItem(BaseModel):
    admission_number: str
    full_name: str
    class_id: int
    section_id: Optional[int] = None
    gender: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class StudentRosterImport(BaseModel):
    students: List[StudentRosterItem]


class StudentResponse(StudentBase):
    id: int
    user_id: Optional[int] = None
    is_roster_claimed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Enrollment
class EnrollmentCreate(BaseModel):
    student_id: int
    session_id: int
    class_id: int
    section_id: Optional[int] = None
    roll_number: Optional[str] = None


class EnrollmentResponse(EnrollmentCreate):
    id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ClassSubjectTeacher Assignment
class TeacherAssignmentCreate(BaseModel):
    session_id: int
    class_id: int
    section_id: Optional[int] = None
    subject_id: int
    teacher_id: int


class TeacherAssignmentResponse(TeacherAssignmentCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
