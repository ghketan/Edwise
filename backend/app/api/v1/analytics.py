from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    check_student_scope,
    check_teacher_class_scope,
    check_teacher_scope,
    get_current_user,
    get_db,
    require_teacher_or_admin,
)
from backend.app.core.exceptions import NotFoundError
from backend.app.models.academics import Exam
from backend.app.models.user import User, UserRole
from backend.app.schemas.academics import AILessonPlanResponse
from backend.app.schemas.analytics import (
    AttendanceAnalyticsResponse,
    DecliningPerformanceResponse,
    ExamAnalyticsResponse,
    StudentBadgesResponse,
    StudentVsClassAnalytics,
)
from backend.app.services.academics_service import generate_ai_lesson_plan
from backend.app.services.analytics_service import (
    get_attendance_analytics,
    get_declining_students,
    get_exam_analytics,
    get_student_badges,
    get_student_vs_class_analytics,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/attendance", response_model=AttendanceAnalyticsResponse)
def api_attendance_analytics(
    session_id: int,
    class_id: Optional[int] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    R-008, C-01, C-02: Scoped attendance analytics.
    Unlinked student accounts cannot view institution-wide attendance (C-01).
    Teachers can only view assigned classes/students (C-02).
    """
    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            raise NotFoundError("Resource not found or out of scope")
        student_id = current_user.student_profile.id
        class_id = None
    elif current_user.role == UserRole.TEACHER:
        if student_id:
            check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
        elif class_id:
            check_teacher_class_scope(db=db, user=current_user, class_id=class_id, session_id=session_id)
    elif student_id:
        check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)

    return get_attendance_analytics(
        db=db,
        session_id=session_id,
        class_id=class_id,
        student_id=student_id
    )


@router.get("/exams/{exam_id}", response_model=ExamAnalyticsResponse)
def api_exam_analytics(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    C-02: Teachers can only view exam analytics for exams they teach.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise NotFoundError("Exam not found")

    check_teacher_scope(
        db=db,
        user=current_user,
        class_id=exam.class_id,
        subject_id=exam.subject_id,
        session_id=exam.session_id,
        section_id=exam.section_id
    )

    return get_exam_analytics(db=db, exam_id=exam_id)


@router.get("/student-vs-class/{student_id}", response_model=StudentVsClassAnalytics)
def api_student_vs_class_analytics(
    student_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    R-007, R-008, C-02: Student vs Class comparative analytics.
    Enforces student scope (students see only their own record, teachers only their students).
    """
    check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
    return get_student_vs_class_analytics(
        db=db,
        student_id=student_id,
        session_id=session_id
    )


@router.get("/declining-performance/{class_id}", response_model=DecliningPerformanceResponse)
def api_declining_performance(
    class_id: int,
    session_id: int,
    min_consecutive_drops: int = Query(2, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    R-008, C-02, M-08: Detects students whose exam performance has dropped across consecutive assessments.
    Enforces teacher class scope and validates min_consecutive_drops >= 1.
    """
    check_teacher_class_scope(db=db, user=current_user, class_id=class_id, session_id=session_id)
    return get_declining_students(
        db=db,
        session_id=session_id,
        class_id=class_id,
        min_consecutive_drops=min_consecutive_drops
    )


@router.get("/ai-lesson-plan/{class_id}", response_model=AILessonPlanResponse)
def api_ai_lesson_plan(
    class_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    AI Remedial Lesson Plan Generator: analyzes class assessment distributions,
    identifies lowest performing subject, and builds a targeted weekly remediation schedule.
    """
    check_teacher_class_scope(db=db, user=current_user, class_id=class_id, session_id=session_id)
    return generate_ai_lesson_plan(db=db, class_id=class_id, session_id=session_id)


@router.get("/student-badges/{student_id}", response_model=StudentBadgesResponse)
def api_student_badges(
    student_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Student Achievement Badges: computes earned badges and class rank without exposing peer PII.
    """
    check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
    return get_student_badges(db=db, student_id=student_id, session_id=session_id)

