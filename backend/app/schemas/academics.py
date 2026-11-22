from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Attendance
class AttendanceEntry(BaseModel):
    student_id: int
    status: str  # present, absent, late, excused
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = {"present", "absent", "late", "excused"}
        if v.lower() not in valid_statuses:
            raise ValueError(f"Invalid status '{v}'. Allowed: {valid_statuses}")
        return v.lower()


class AttendanceBulkSave(BaseModel):
    """
    Contract API-001: Teacher saves attendance for one class, section, subject, and date.
    Supports single subject or full-day (all subjects) recording.
    """
    session_id: int
    class_id: int
    section_id: Optional[int] = None
    subject_id: Optional[int] = None
    is_full_day: bool = False
    date: date
    reason: Optional[str] = None
    entries: Optional[List[AttendanceEntry]] = None
    records: Optional[List[AttendanceEntry]] = None

    @model_validator(mode="before")
    @classmethod
    def unify_entries(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("entries") and data.get("records"):
                data["entries"] = data["records"]
            if data.get("subject_id") in ("all", "", 0):
                data["subject_id"] = None
                data["is_full_day"] = True
            elif data.get("subject_id") is None:
                data["is_full_day"] = True
        return data


class AttendanceRecordResponse(BaseModel):
    id: int
    session_id: int
    class_id: int
    section_id: Optional[int] = None
    subject_id: int
    student_id: int
    date: date
    status: str
    recorded_by: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceSaveResponse(BaseModel):
    status: str = "success"
    saved_count: int
    server_timestamp: datetime


# Exam
class ExamBase(BaseModel):
    session_id: int
    class_id: int
    section_id: Optional[int] = None
    subject_id: int
    name: str
    exam_type: str = "exam"
    date: date
    time_slot: Optional[str] = "09:00 AM - 12:00 PM"
    datesheet_filename: Optional[str] = None
    max_marks: float
    weightage: float = 1.0

    @field_validator("max_marks")
    @classmethod
    def validate_max_marks(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("max_marks must be greater than 0")
        return v


class ExamCreate(ExamBase):
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Exam name cannot be empty")
        if len(cleaned) > 200:
            raise ValueError("Exam name must be 200 characters or fewer")
        return cleaned


class ExamUpdate(BaseModel):
    name: Optional[str] = None
    exam_type: Optional[str] = None
    date: Optional[date] = None
    time_slot: Optional[str] = None
    datesheet_filename: Optional[str] = None
    max_marks: Optional[float] = None
    weightage: Optional[float] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Exam name cannot be empty")
        if len(cleaned) > 200:
            raise ValueError("Exam name must be 200 characters or fewer")
        return cleaned


class ExamResponse(ExamBase):
    id: int
    teacher_id: Optional[int] = None
    created_at: datetime
    days_left: Optional[int] = None
    countdown_status: Optional[str] = None
    subject_name: Optional[str] = None
    class_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Mark
class MarkEntry(BaseModel):
    student_id: int
    score: Optional[float] = None  # None indicates blank/unrecorded; 0.0 is an explicit zero
    is_absent: bool = False
    remarks: Optional[str] = None


class MarksBulkSave(BaseModel):
    """
    Marks entry and editing with audit reason (R-005, R-014, UI-004).
    """
    exam_id: int
    entries: List[MarkEntry]
    reason: Optional[str] = None


class MarkResponse(BaseModel):
    id: int
    exam_id: int
    student_id: int
    score: Optional[float] = None
    is_absent: bool
    remarks: Optional[str] = None
    entered_by: Optional[int] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Assignment
class AssignmentBase(BaseModel):
    session_id: int
    class_id: int
    section_id: Optional[int] = None
    subject_id: int
    title: str
    description: Optional[str] = None
    max_points: float = 100.0
    due_date: datetime


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentResponse(AssignmentBase):
    id: int
    teacher_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Submission
class SubmissionCreate(BaseModel):
    assignment_id: int
    content: Optional[str] = Field(None, max_length=10000)
    attachment_url: Optional[str] = Field(None, max_length=500)

    @field_validator("attachment_url")
    @classmethod
    def validate_attachment_url(cls, v: Optional[str]) -> Optional[str]:
        """Only external http(s) links may be client-supplied; internal file paths are server-generated."""
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return None
        lowered = cleaned.lower()
        if not (lowered.startswith("http://") or lowered.startswith("https://")):
            raise ValueError("attachment_url must be an http(s) link")
        return cleaned


class SubmissionGrade(BaseModel):
    points_awarded: float
    feedback: Optional[str] = None
    reason: Optional[str] = None


class SubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    submitted_at: datetime
    content: Optional[str] = None
    attachment_url: Optional[str] = None
    status: str
    points_awarded: Optional[float] = None
    feedback: Optional[str] = None
    graded_by: Optional[int] = None
    graded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Doubt Questions
class DoubtCreate(BaseModel):
    session_id: int
    subject_id: int
    question: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty")
        if len(cleaned) > 2000:
            raise ValueError("Question must be 2000 characters or fewer")
        return cleaned


class DoubtAnswer(BaseModel):
    answer: str

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Answer cannot be empty")
        if len(cleaned) > 2000:
            raise ValueError("Answer must be 2000 characters or fewer")
        return cleaned


class DoubtResponse(BaseModel):
    id: int
    session_id: int
    student_id: int
    subject_id: int
    question: str
    answer: Optional[str] = None
    answered_by: Optional[int] = None
    answered_by_name: Optional[str] = None
    answered_at: Optional[datetime] = None
    is_resolved: bool
    created_at: datetime
    updated_at: datetime
    student_name: Optional[str] = None
    student_roll: Optional[str] = None
    subject_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Announcements
class AnnouncementCreate(BaseModel):
    session_id: int
    class_id: Optional[int] = None
    section_id: Optional[int] = None
    title: str
    content: str
    priority: str = "Normal"  # Normal, High

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty")
        if len(cleaned) > 200:
            raise ValueError("Title must be 200 characters or fewer")
        return cleaned

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Content cannot be empty")
        if len(cleaned) > 5000:
            raise ValueError("Content must be 5000 characters or fewer")
        return cleaned

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        normalized = v.strip().lower()
        mapping = {"normal": "Normal", "high": "High"}
        if normalized not in mapping:
            raise ValueError("Priority must be 'Normal' or 'High'")
        return mapping[normalized]


class AnnouncementResponse(BaseModel):
    id: int
    session_id: int
    class_id: Optional[int] = None
    section_id: Optional[int] = None
    teacher_id: Optional[int] = None
    title: str
    content: str
    priority: str
    created_at: datetime
    teacher_name: Optional[str] = None
    class_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Attendance 75% Target Goal Planner
class AttendanceGoalResponse(BaseModel):
    current_rate: float
    total_conducted: int
    current_attended: int
    target_rate: float = 75.0
    needed_consecutive_classes: int
    safe_skips_available: int
    status_message: str
    is_warning: bool


# AI Lesson Plan
class AILessonPlanResponse(BaseModel):
    focus_subject: str
    class_id: int
    avg_score: float
    performance_status: str
    key_recommendation: str
    weekly_schedule: List[dict]

