from typing import Dict, List, Optional
from pydantic import BaseModel


class SubjectAttendanceStat(BaseModel):
    subject_id: int
    subject_name: str
    total_classes: int
    present_count: int
    attendance_rate: float


class AttendanceTrendPoint(BaseModel):
    period: str  # e.g., "2026-11-01" or "Week 45"
    attendance_rate: float
    total_sessions: int


class AttendanceAnalyticsResponse(BaseModel):
    overall_attendance_rate: float
    total_records: int
    present_count: int
    absent_count: int
    late_count: int
    excused_count: int
    by_subject: List[SubjectAttendanceStat]
    trends: List[AttendanceTrendPoint]


class ScoreDistributionBin(BaseModel):
    range_label: str  # e.g. "0-40", "41-60", "61-80", "81-100"
    count: int
    percentage: float


class ExamAnalyticsResponse(BaseModel):
    exam_id: int
    exam_name: str
    subject_name: str
    max_marks: float
    student_count: int
    average_score: float
    median_score: float
    highest_score: float
    lowest_score: float
    pass_rate: float
    distribution: List[ScoreDistributionBin]


class StudentExamPerformance(BaseModel):
    exam_id: int
    exam_name: str
    subject_name: str
    date: str
    max_marks: float
    score: Optional[float] = None
    percentage: Optional[float] = None
    class_average: float
    is_absent: bool


class StudentVsClassAnalytics(BaseModel):
    student_id: int
    student_name: str
    overall_percentage: float
    class_overall_average: float
    attendance_rate: float
    class_attendance_average: float
    exams: List[StudentExamPerformance]


class DecliningStudentItem(BaseModel):
    student_id: int
    student_name: str
    admission_number: str
    subject_name: str
    recent_scores: List[float]
    score_drop: float
    consecutive_declines: int


class DecliningPerformanceResponse(BaseModel):
    class_id: int
    count: int
    declining_students: List[DecliningStudentItem]


class BadgeItem(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    unlocked: bool
    color: str


class StudentBadgesResponse(BaseModel):
    student_id: int
    session_id: int
    rank: Optional[int] = None
    total_students_in_class: int
    badges: List[BadgeItem]

