from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin
from backend.app.models.user import User, UserRole
from backend.app.models.institution import (
    AcademicSession,
    Class,
    Section,
    Subject,
    Teacher,
    Student,
    Enrollment,
    ClassSubjectTeacher,
)
from backend.app.models.academics import (
    AttendanceRecord,
    Exam,
    Mark,
    Assignment,
    Submission,
    DoubtQuestion,
    Announcement,
)
from backend.app.models.audit import AuditLog
from backend.app.models.ml import ModelRegistry, Prediction
from backend.app.models.recommendations import RecommendationRule, StudentRecommendation

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "AcademicSession",
    "Class",
    "Section",
    "Subject",
    "Teacher",
    "Student",
    "Enrollment",
    "ClassSubjectTeacher",
    "AttendanceRecord",
    "Exam",
    "Mark",
    "Assignment",
    "Submission",
    "DoubtQuestion",
    "Announcement",
    "AuditLog",
    "ModelRegistry",
    "Prediction",
    "RecommendationRule",
    "StudentRecommendation",
]

