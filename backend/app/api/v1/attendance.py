from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    check_student_scope,
    check_teacher_class_scope,
    check_teacher_scope,
    check_teacher_students_section_scope,
    get_current_user,
    get_db,
    get_teacher_subject_ids,
    require_teacher_or_admin,
)
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.institution import ClassSubjectTeacher
from backend.app.models.user import User, UserRole
from backend.app.schemas.academics import (
    AttendanceBulkSave,
    AttendanceGoalResponse,
    AttendanceRecordResponse,
    AttendanceSaveResponse,
)
from backend.app.services.academics_service import (
    calculate_attendance_goal,
    get_attendance_records,
    save_attendance,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])

MAX_FUTURE_ATTENDANCE_DAYS = 1


@router.put("", response_model=AttendanceSaveResponse)
def api_save_attendance(
    attendance_in: AttendanceBulkSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Contract API-001: Teacher saves attendance for one class, section, subject, and date.
    Enforces object-level scoping and writes audit log in the same transaction.
    """
    if not attendance_in.entries:
        raise ValidationError("At least one attendance entry is required")
    if attendance_in.date > (datetime.now(timezone.utc).date() + timedelta(days=MAX_FUTURE_ATTENDANCE_DAYS)):
        raise ValidationError("Attendance cannot be recorded for a future date")

    allowed_subject_ids = None
    if attendance_in.subject_id:
        check_teacher_scope(
            db=db,
            user=current_user,
            class_id=attendance_in.class_id,
            subject_id=attendance_in.subject_id,
            session_id=attendance_in.session_id,
            section_id=attendance_in.section_id
        )
    else:
        check_teacher_class_scope(
            db=db,
            user=current_user,
            class_id=attendance_in.class_id,
            session_id=attendance_in.session_id,
            section_id=attendance_in.section_id
        )
        # Full-day save: teachers may only touch subjects they are assigned to teach in this class
        allowed_subject_ids = get_teacher_subject_ids(
            db,
            current_user,
            class_id=attendance_in.class_id,
            session_id=attendance_in.session_id,
            section_id=attendance_in.section_id
        )

    check_teacher_students_section_scope(
        db=db,
        user=current_user,
        student_ids=[e.student_id for e in attendance_in.entries],
        class_id=attendance_in.class_id,
        subject_id=attendance_in.subject_id,
        session_id=attendance_in.session_id
    )

    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    count = save_attendance(
        db=db,
        attendance_in=attendance_in,
        recorded_by_teacher_id=teacher_id,
        user_id=current_user.id,
        allowed_subject_ids=allowed_subject_ids
    )

    return AttendanceSaveResponse(
        status="success",
        saved_count=count,
        server_timestamp=datetime.now(timezone.utc)
    )


@router.get("", response_model=List[AttendanceRecordResponse])
def api_get_attendance(
    session_id: int,
    class_id: Optional[int] = None,
    section_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    student_id: Optional[int] = None,
    date_val: Optional[date] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve attendance records.
    R-007, C-02: Scoped by role.
    - Students only see their own attendance.
    - Teachers only see attendance for their assigned classes/students.
    """
    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            return []
        student_id = current_user.student_profile.id
        class_id = None
        section_id = None
    elif current_user.role == UserRole.TEACHER:
        if not current_user.teacher_profile:
            return []
        if student_id:
            check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
        elif class_id:
            check_teacher_class_scope(
                db=db,
                user=current_user,
                class_id=class_id,
                session_id=session_id,
                section_id=section_id
            )
        else:
            # Restrict to assigned classes
            assignments = db.query(ClassSubjectTeacher).filter(
                ClassSubjectTeacher.teacher_id == current_user.teacher_profile.id,
                ClassSubjectTeacher.session_id == session_id
            ).all()
            allowed_class_ids = list(set(a.class_id for a in assignments))
            if not allowed_class_ids:
                return []
            all_records = []
            for cid in allowed_class_ids:
                all_records.extend(get_attendance_records(
                    db=db,
                    session_id=session_id,
                    class_id=cid,
                    section_id=section_id,
                    subject_id=subject_id,
                    student_id=student_id,
                    date_val=date_val
                ))
            return _filter_records_for_teacher(db, current_user, session_id, all_records)

        records = get_attendance_records(
            db=db,
            session_id=session_id,
            class_id=class_id,
            section_id=section_id,
            subject_id=subject_id,
            student_id=student_id,
            date_val=date_val
        )
        return _filter_records_for_teacher(db, current_user, session_id, records)

    return get_attendance_records(
        db=db,
        session_id=session_id,
        class_id=class_id,
        section_id=section_id,
        subject_id=subject_id,
        student_id=student_id,
        date_val=date_val
    )


@router.get("/goal/{student_id}", response_model=AttendanceGoalResponse)
def api_get_attendance_goal(
    student_id: int,
    session_id: int,
    target_pct: float = Query(75.0, ge=50.0, le=100.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    75% Attendance Goal Calculator: calculates required consecutive classes or safe skips.
    """
    check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
    return calculate_attendance_goal(
        db=db,
        student_id=student_id,
        session_id=session_id,
        target_pct=target_pct
    )

