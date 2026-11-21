from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
import math
import numpy as np
from sqlalchemy.orm import Session
from backend.app.api.deps import check_teacher_scope
from backend.app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from backend.app.models.academics import (
    Announcement,
    Assignment,
    AttendanceRecord,
    DoubtQuestion,
    Exam,
    Mark,
    Submission,
)
from backend.app.models.institution import (
    AcademicSession,
    Class,
    ClassSubjectTeacher,
    Enrollment,
    Section,
    Student,
    Subject,
)
from backend.app.models.user import User, UserRole
from backend.app.schemas.academics import (
    AILessonPlanResponse,
    AssignmentCreate,
    AttendanceBulkSave,
    AttendanceGoalResponse,
    ExamCreate,
    ExamUpdate,
    MarksBulkSave,
    SubmissionCreate,
    SubmissionGrade,
)
from backend.app.services.audit_service import create_audit_entry


# Attendance Service
def save_attendance(
    db: Session,
    attendance_in: AttendanceBulkSave,
    recorded_by_teacher_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> int:
    """
    Contract API-001, R-004, R-014, H-02, M-05:
    Upsert attendance records with enrollment validation and audit logging.
    All entries pre-validated before database modifications.
    """
    # 1. Pre-validate student uniqueness within the bulk request (M-05)
    seen_students = set()
    for entry in attendance_in.entries:
        if entry.student_id in seen_students:
            raise ValidationError(f"Duplicate student_id {entry.student_id} in attendance entries")
        seen_students.add(entry.student_id)

    # 2. Pre-validate student enrollment in target class and session (H-02)
    for entry in attendance_in.entries:
        enrollment = db.query(Enrollment).filter(
            Enrollment.student_id == entry.student_id,
            Enrollment.session_id == attendance_in.session_id,
            Enrollment.class_id == attendance_in.class_id,
            Enrollment.status == "active"
        ).first()
        if not enrollment:
            # Fall back to checking Student record default class
            st = db.query(Student).filter(Student.id == entry.student_id).first()
            if not st or st.class_id != attendance_in.class_id:
                raise ValidationError(
                    f"Student {entry.student_id} is not actively enrolled in class {attendance_in.class_id}"
                )

    saved_count = 0
    for entry in attendance_in.entries:
        existing = db.query(AttendanceRecord).filter(
            AttendanceRecord.student_id == entry.student_id,
            AttendanceRecord.session_id == attendance_in.session_id,
            AttendanceRecord.subject_id == attendance_in.subject_id,
            AttendanceRecord.date == attendance_in.date
        ).first()

        if existing:
            if existing.status != entry.status or existing.notes != entry.notes or existing.class_id != attendance_in.class_id:
                old_val = {"status": existing.status, "notes": existing.notes}
                existing.status = entry.status
                existing.notes = entry.notes
                existing.class_id = attendance_in.class_id
                existing.section_id = attendance_in.section_id
                existing.recorded_by = recorded_by_teacher_id
                db.flush()

                create_audit_entry(
                    db=db,
                    user_id=user_id,
                    action="attendance.changed",
                    entity_name="attendance",
                    entity_id=existing.id,
                    old_values=old_val,
                    new_values={"status": entry.status, "notes": entry.notes},
                    reason="Teacher updated attendance record"
                )
            saved_count += 1
        else:
            new_rec = AttendanceRecord(
                session_id=attendance_in.session_id,
                class_id=attendance_in.class_id,
                section_id=attendance_in.section_id,
                subject_id=attendance_in.subject_id,
                student_id=entry.student_id,
                date=attendance_in.date,
                status=entry.status,
                recorded_by=recorded_by_teacher_id,
                notes=entry.notes
            )
            db.add(new_rec)
            db.flush()

            create_audit_entry(
                db=db,
                user_id=user_id,
                action="attendance.created",
                entity_name="attendance",
                entity_id=new_rec.id,
                new_values={"status": entry.status, "date": str(attendance_in.date)},
                reason="Teacher recorded attendance"
            )
            saved_count += 1

    db.commit()
    return saved_count


def get_attendance_records(
    db: Session,
    session_id: int,
    class_id: Optional[int] = None,
    section_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    student_id: Optional[int] = None,
    date_val: Optional[date] = None
) -> List[AttendanceRecord]:
    query = db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session_id)
    if class_id:
        query = query.filter(AttendanceRecord.class_id == class_id)
    if section_id:
        query = query.filter(AttendanceRecord.section_id == section_id)
    if subject_id:
        query = query.filter(AttendanceRecord.subject_id == subject_id)
    if student_id:
        query = query.filter(AttendanceRecord.student_id == student_id)
    if date_val:
        query = query.filter(AttendanceRecord.date == date_val)
    return query.order_by(AttendanceRecord.date.desc()).all()


# Exams Service
def create_exam(
    db: Session,
    exam_in: ExamCreate,
    teacher_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Exam:
    cleaned_name = (exam_in.name or "").strip()
    if not cleaned_name:
        raise ValidationError("Exam name cannot be empty")
    if len(cleaned_name) > 200:
        raise ValidationError("Exam name must be 200 characters or fewer")
    if exam_in.max_marks <= 0 or math.isnan(exam_in.max_marks) or math.isinf(exam_in.max_marks):
        raise ValidationError("max_marks must be a positive finite number")
    if exam_in.weightage <= 0 or math.isnan(exam_in.weightage) or math.isinf(exam_in.weightage):
        raise ValidationError("weightage must be a positive finite number")

    acad_session = db.query(AcademicSession).filter(AcademicSession.id == exam_in.session_id).first()
    if not acad_session:
        raise NotFoundError("Academic session not found")

    cls_obj = db.query(Class).filter(Class.id == exam_in.class_id).first()
    if not cls_obj:
        raise NotFoundError("Class not found")
    if cls_obj.session_id != exam_in.session_id:
        raise ValidationError("Class does not belong to the specified academic session")

    subj_obj = db.query(Subject).filter(Subject.id == exam_in.subject_id).first()
    if not subj_obj:
        raise NotFoundError("Subject not found")

    if exam_in.section_id is not None:
        sec_obj = db.query(Section).filter(Section.id == exam_in.section_id).first()
        if not sec_obj:
            raise NotFoundError("Section not found")
        if sec_obj.class_id != exam_in.class_id:
            raise ValidationError("Section does not belong to the specified class")

    exam_data = exam_in.model_dump()
    exam_data["name"] = cleaned_name
    exam = Exam(**exam_data, teacher_id=teacher_id)
    db.add(exam)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="exam.created",
        entity_name="exam",
        entity_id=exam.id,
        new_values=exam_in.model_dump(mode="json"),
        reason="Teacher scheduled exam"
    )
    db.commit()
    db.refresh(exam)
    return exam


def get_exams(
    db: Session,
    session_id: int,
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None
) -> List[Exam]:
    query = db.query(Exam).filter(Exam.session_id == session_id)
    if class_id:
        query = query.filter(Exam.class_id == class_id)
    if subject_id:
        query = query.filter(Exam.subject_id == subject_id)
    return query.order_by(Exam.date.desc()).all()


# Marks Service
def save_marks(
    db: Session,
    marks_in: MarksBulkSave,
    teacher_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> int:
    """
    R-005, R-014, UI-004, Invariant 3, H-02, H-03, M-05:
    Marks entry with strict enrollment verification, bounds checking,
    distinction between blank and zero, and transactional audit logging.
    """
    exam = db.query(Exam).filter(Exam.id == marks_in.exam_id).first()
    if not exam:
        raise NotFoundError("Exam not found")

    # 1. Pre-validate student uniqueness within bulk entries (M-05)
    seen_students = set()
    for entry in marks_in.entries:
        if entry.student_id in seen_students:
            raise ValidationError(f"Duplicate student_id {entry.student_id} in marks entries")
        seen_students.add(entry.student_id)

    # 2. Pre-validate all scores and enrollment before modifying database (Invariant 3, H-02, H-03)
    for entry in marks_in.entries:
        if entry.is_absent and entry.score is not None:
            raise ValidationError("Student marked absent cannot simultaneously have a recorded score")

        if entry.score is not None:
            if math.isnan(entry.score) or math.isinf(entry.score):
                raise ValidationError("Score must be a finite number")
            if entry.score < 0 or entry.score > exam.max_marks:
                raise ValidationError(
                    f"Score {entry.score} is out of bounds for exam max marks {exam.max_marks}"
                )

        # Invariant 3: Verify student is actively enrolled in the exam's class and session
        enrollment = db.query(Enrollment).filter(
            Enrollment.student_id == entry.student_id,
            Enrollment.session_id == exam.session_id,
            Enrollment.class_id == exam.class_id,
            Enrollment.status == "active"
        ).first()
        if not enrollment:
            st = db.query(Student).filter(Student.id == entry.student_id).first()
            if not st or st.class_id != exam.class_id:
                raise ValidationError(
                    f"Student {entry.student_id} is not actively enrolled in class {exam.class_id} for this session"
                )

    saved_count = 0
    for entry in marks_in.entries:
        existing = db.query(Mark).filter(
            Mark.exam_id == marks_in.exam_id,
            Mark.student_id == entry.student_id
        ).first()

        if existing:
            if existing.score != entry.score or existing.is_absent != entry.is_absent or existing.remarks != entry.remarks:
                old_val = {"score": existing.score, "is_absent": existing.is_absent, "remarks": existing.remarks}
                existing.score = entry.score
                existing.is_absent = entry.is_absent
                existing.remarks = entry.remarks
                existing.entered_by = teacher_id
                db.flush()

                create_audit_entry(
                    db=db,
                    user_id=user_id,
                    action="mark.updated",
                    entity_name="mark",
                    entity_id=existing.id,
                    old_values=old_val,
                    new_values={"score": entry.score, "is_absent": entry.is_absent, "remarks": entry.remarks},
                    reason=marks_in.reason or "Score updated by teacher"
                )
            saved_count += 1
        else:
            new_mark = Mark(
                exam_id=marks_in.exam_id,
                student_id=entry.student_id,
                score=entry.score,
                is_absent=entry.is_absent,
                remarks=entry.remarks,
                entered_by=teacher_id
            )
            db.add(new_mark)
            db.flush()

            create_audit_entry(
                db=db,
                user_id=user_id,
                action="mark.created",
                entity_name="mark",
                entity_id=new_mark.id,
                new_values={"score": entry.score, "is_absent": entry.is_absent},
                reason=marks_in.reason or "Score entered by teacher"
            )
            saved_count += 1

    db.commit()
    return saved_count


def get_marks_for_exam(db: Session, exam_id: int) -> List[Mark]:
    return db.query(Mark).filter(Mark.exam_id == exam_id).all()


def get_marks_for_student(db: Session, student_id: int, session_id: Optional[int] = None) -> List[Mark]:
    query = db.query(Mark).join(Exam, Mark.exam_id == Exam.id).filter(Mark.student_id == student_id)
    if session_id:
        query = query.filter(Exam.session_id == session_id)
    return query.order_by(Exam.date.desc()).all()


# Assignments Service
def create_assignment(
    db: Session,
    assign_in: AssignmentCreate,
    teacher_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Assignment:
    if assign_in.max_points <= 0 or math.isnan(assign_in.max_points) or math.isinf(assign_in.max_points):
        raise ValidationError("max_points must be a positive finite number")

    assignment = Assignment(**assign_in.model_dump(), teacher_id=teacher_id)
    db.add(assignment)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="assignment.created",
        entity_name="assignment",
        entity_id=assignment.id,
        new_values=assign_in.model_dump(mode="json"),
        reason="Teacher posted assignment"
    )
    db.commit()
    db.refresh(assignment)
    return assignment


def submit_assignment(
    db: Session,
    submission_in: SubmissionCreate,
    student_id: int,
    user_id: Optional[int] = None
) -> Submission:
    assignment = db.query(Assignment).filter(Assignment.id == submission_in.assignment_id).first()
    if not assignment:
        raise NotFoundError("Assignment not found")

    existing = db.query(Submission).filter(
        Submission.assignment_id == submission_in.assignment_id,
        Submission.student_id == student_id
    ).first()

    now = datetime.now(timezone.utc)
    # Determine if late
    due = assignment.due_date
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    is_late = now > due

    if existing:
        if existing.status == "graded":
            raise ConflictError("Cannot overwrite an already graded submission")
        existing.content = submission_in.content
        existing.attachment_url = submission_in.attachment_url
        existing.submitted_at = now
        existing.status = "late" if is_late else "submitted"
        db.flush()
        submission = existing
    else:
        submission = Submission(
            assignment_id=submission_in.assignment_id,
            student_id=student_id,
            content=submission_in.content,
            attachment_url=submission_in.attachment_url,
            submitted_at=now,
            status="late" if is_late else "submitted"
        )
        db.add(submission)
        db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="submission.created",
        entity_name="submission",
        entity_id=submission.id,
        new_values={"assignment_id": submission_in.assignment_id, "status": submission.status},
        reason="Student submitted assignment"
    )
    db.commit()
    db.refresh(submission)
    return submission


def grade_submission(
    db: Session,
    submission_id: int,
    grade_in: SubmissionGrade,
    teacher_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Submission:
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise NotFoundError("Submission not found")

    # Bounds validation (H-03)
    if math.isnan(grade_in.points_awarded) or math.isinf(grade_in.points_awarded):
        raise ValidationError("Points awarded must be a finite number")
    if grade_in.points_awarded < 0 or grade_in.points_awarded > submission.assignment.max_points:
        raise ValidationError(
            f"Points awarded {grade_in.points_awarded} must be between 0 and assignment max points {submission.assignment.max_points}"
        )

    old_val = {"points": submission.points_awarded, "feedback": submission.feedback}
    submission.points_awarded = grade_in.points_awarded
    submission.feedback = grade_in.feedback
    submission.graded_by = teacher_id
    submission.graded_at = datetime.now(timezone.utc)
    submission.status = "graded"
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="submission.graded",
        entity_name="submission",
        entity_id=submission.id,
        old_values=old_val,
        new_values={"points": grade_in.points_awarded, "feedback": grade_in.feedback},
        reason="Teacher evaluated submission"
    )
    db.commit()
    db.refresh(submission)
    return submission


# Doubt Questions Service
def create_doubt(
    db: Session,
    student_id: int,
    session_id: int,
    subject_id: int,
    question: str
) -> DoubtQuestion:
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        raise ValidationError("Question cannot be empty")
    if len(cleaned_question) > 2000:
        raise ValidationError("Question must be 2000 characters or fewer")

    acad_session = db.query(AcademicSession).filter(AcademicSession.id == session_id).first()
    if not acad_session:
        raise NotFoundError("Academic session not found")

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise NotFoundError("Subject not found")

    doubt = DoubtQuestion(
        session_id=session_id,
        student_id=student_id,
        subject_id=subject_id,
        question=cleaned_question,
        is_resolved=False
    )
    db.add(doubt)
    db.commit()
    db.refresh(doubt)
    return doubt


def get_doubts(
    db: Session,
    session_id: Optional[int] = None,
    student_id: Optional[int] = None,
    subject_id: Optional[int] = None
) -> List[DoubtQuestion]:
    query = db.query(DoubtQuestion)
    if session_id:
        query = query.filter(DoubtQuestion.session_id == session_id)
    if student_id:
        query = query.filter(DoubtQuestion.student_id == student_id)
    if subject_id:
        query = query.filter(DoubtQuestion.subject_id == subject_id)
    return query.order_by(DoubtQuestion.is_resolved.asc(), DoubtQuestion.created_at.desc()).all()


def answer_doubt(
    db: Session,
    doubt_id: int,
    teacher_id: Optional[int],
    answer: str
) -> DoubtQuestion:
    cleaned_answer = (answer or "").strip()
    if not cleaned_answer:
        raise ValidationError("Answer cannot be empty")
    if len(cleaned_answer) > 2000:
        raise ValidationError("Answer must be 2000 characters or fewer")

    doubt = db.query(DoubtQuestion).filter(DoubtQuestion.id == doubt_id).first()
    if not doubt:
        raise NotFoundError("Doubt not found")
    doubt.answer = cleaned_answer
    doubt.answered_by = teacher_id
    doubt.answered_at = datetime.now(timezone.utc)
    doubt.is_resolved = True
    db.commit()
    db.refresh(doubt)
    return doubt


# Announcements Service
def create_announcement(
    db: Session,
    teacher_id: Optional[int],
    session_id: int,
    title: str,
    content: str,
    class_id: Optional[int] = None,
    section_id: Optional[int] = None,
    priority: str = "Normal"
) -> Announcement:
    cleaned_title = (title or "").strip()
    cleaned_content = (content or "").strip()
    if not cleaned_title:
        raise ValidationError("Title cannot be empty")
    if len(cleaned_title) > 200:
        raise ValidationError("Title must be 200 characters or fewer")
    if not cleaned_content:
        raise ValidationError("Content cannot be empty")
    if len(cleaned_content) > 5000:
        raise ValidationError("Content must be 5000 characters or fewer")

    norm_priority = (priority or "").strip().lower()
    if norm_priority not in {"normal", "high"}:
        raise ValidationError("Priority must be 'Normal' or 'High'")
    final_priority = "High" if norm_priority == "high" else "Normal"

    acad_session = db.query(AcademicSession).filter(AcademicSession.id == session_id).first()
    if not acad_session:
        raise NotFoundError("Academic session not found")

    if class_id is not None:
        cls_obj = db.query(Class).filter(Class.id == class_id).first()
        if not cls_obj:
            raise NotFoundError("Class not found")
        if cls_obj.session_id != session_id:
            raise ValidationError("Class does not belong to the specified academic session")

    if section_id is not None:
        if class_id is None:
            raise ValidationError("class_id is required when section_id is provided")
        sec_obj = db.query(Section).filter(Section.id == section_id).first()
        if not sec_obj:
            raise NotFoundError("Section not found")
        if sec_obj.class_id != class_id:
            raise ValidationError("Section does not belong to the specified class")

    ann = Announcement(
        session_id=session_id,
        class_id=class_id,
        section_id=section_id,
        teacher_id=teacher_id,
        title=cleaned_title,
        content=cleaned_content,
        priority=final_priority
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


def get_announcements(
    db: Session,
    session_id: int,
    class_id: Optional[int] = None
) -> List[Announcement]:
    query = db.query(Announcement).filter(Announcement.session_id == session_id)
    if class_id:
        query = query.filter((Announcement.class_id == class_id) | (Announcement.class_id.is_(None)))
    return query.order_by(Announcement.created_at.desc()).all()


def delete_announcement(
    db: Session,
    announcement_id: int,
    teacher_id: Optional[int] = None,
    is_admin: bool = False
) -> bool:
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        raise NotFoundError("Announcement not found")
    if not is_admin and (teacher_id is None or ann.teacher_id != teacher_id):
        raise ForbiddenError("Unauthorized to delete this announcement")
    db.delete(ann)
    db.commit()
    return True


# Attendance Goal Planner Service
def calculate_attendance_goal(
    db: Session,
    student_id: int,
    session_id: int,
    target_pct: float = 75.0
) -> AttendanceGoalResponse:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    acad_session = db.query(AcademicSession).filter(AcademicSession.id == session_id).first()
    if not acad_session:
        raise NotFoundError("Academic session not found")

    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.session_id == session_id
    ).all()

    total = len(records)
    present = len([r for r in records if r.status in ["present", "late"]])

    if total == 0:
        return AttendanceGoalResponse(
            current_rate=100.0,
            total_conducted=0,
            current_attended=0,
            target_rate=target_pct,
            needed_consecutive_classes=0,
            safe_skips_available=0,
            status_message="No attendance sessions logged yet for this academic session.",
            is_warning=False
        )

    current_rate = round((present / total) * 100.0, 1)
    p_dec = Decimal(str(target_pct)) / Decimal("100")
    actual_ratio = Decimal(present) / Decimal(total)

    if actual_ratio < p_dec:
        if p_dec >= Decimal("1"):
            missed = total - present
            needed = 0
            safe_skips = 0
            is_warning = True
            msg = (
                f"Alert: Current attendance is {current_rate}% ({missed} missed). "
                f"Reaching 100.0% is no longer mathematically possible once a class has been missed."
            )
        else:
            needed = math.ceil((p_dec * total - present) / (Decimal("1") - p_dec))
            needed = max(1, needed)
            msg = f"Alert: Current attendance is {current_rate}%. You must attend the next {needed} classes consecutively to reach the {target_pct}% requirement."
            is_warning = True
            safe_skips = 0
    else:
        safe_skips = max(0, math.floor(Decimal(present) / p_dec - Decimal(total)))
        msg = f"Great work! Attendance is at {current_rate}%. You meet the {target_pct}% threshold with a buffer of {safe_skips} safe missed classes."
        is_warning = False
        needed = 0

    return AttendanceGoalResponse(
        current_rate=current_rate,
        total_conducted=total,
        current_attended=present,
        target_rate=target_pct,
        needed_consecutive_classes=needed,
        safe_skips_available=safe_skips,
        status_message=msg,
        is_warning=is_warning
    )


# AI Remedial Lesson Plan Generator
def generate_ai_lesson_plan(
    db: Session,
    class_id: int,
    session_id: int
) -> AILessonPlanResponse:
    acad_session = db.query(AcademicSession).filter(AcademicSession.id == session_id).first()
    if not acad_session:
        raise NotFoundError("Academic session not found")

    cls_obj = db.query(Class).filter(Class.id == class_id, Class.session_id == session_id).first()
    if not cls_obj:
        raise NotFoundError("Class not found in this academic session")

    exams = db.query(Exam).filter(Exam.class_id == class_id, Exam.session_id == session_id).all()
    subject_scores = {}

    for exam in exams:
        subj = db.query(Subject).filter(Subject.id == exam.subject_id).first()
        s_name = subj.name if subj else f"Subject #{exam.subject_id}"
        marks = db.query(Mark).filter(Mark.exam_id == exam.id, Mark.score.isnot(None), Mark.is_absent.is_(False)).all()
        if marks and exam.max_marks > 0:
            pcts = [(m.score / exam.max_marks) * 100 for m in marks]
            if s_name not in subject_scores:
                subject_scores[s_name] = []
            subject_scores[s_name].extend(pcts)

    if not subject_scores:
        focus_subj = "Mathematics"
        avg = 68.0
    else:
        subject_averages = {s: round(float(np.mean(vals)), 1) for s, vals in subject_scores.items()}
        sorted_subjs = sorted(subject_averages.items(), key=lambda x: x[1])
        focus_subj, avg = sorted_subjs[0]

    status = "Challenging" if avg < 65.0 else ("Moderate" if avg < 78.0 else "High Performance")

    weekly_schedule = [
        {"day": "Monday", "topic": f"Core Foundations & Remedial Concepts in {focus_subj}", "hours": 1.5},
        {"day": "Wednesday", "topic": f"Targeted Problem Solving & Worksheet Review ({focus_subj})", "hours": 1.0},
        {"day": "Friday", "topic": f"Formative Mock Quiz & Peer Group Learning ({focus_subj})", "hours": 1.0}
    ]

    rec = f"Class cohort average in {focus_subj} is {avg}%. Allocate 3.5 extra hours this week for guided problem sets."

    return AILessonPlanResponse(
        focus_subject=focus_subj,
        class_id=class_id,
        avg_score=avg,
        performance_status=status,
        key_recommendation=rec,
        weekly_schedule=weekly_schedule
    )


# Bulk Marks CSV Import
def import_marks_csv(
    db: Session,
    csv_text: str,
    session_id: int,
    entered_by_teacher_id: Optional[int] = None,
    user_id: Optional[int] = None,
    reason: str = "Bulk CSV marks import",
    current_user: Optional[User] = None,
    default_exam_id: Optional[int] = None
) -> int:
    import csv, io

    if not csv_text or not csv_text.strip():
        raise ValidationError("Uploaded CSV file is empty")

    acad_session = db.query(AcademicSession).filter(AcademicSession.id == session_id).first()
    if not acad_session:
        raise NotFoundError("Academic session not found")

    default_exam: Optional[Exam] = None
    if default_exam_id is not None:
        default_exam = db.query(Exam).filter(Exam.id == default_exam_id).first()
        if not default_exam:
            raise NotFoundError("Exam not found")
        if default_exam.session_id != session_id:
            raise ValidationError(f"Exam {default_exam_id} does not belong to session {session_id}")
        if current_user is not None:
            check_teacher_scope(
                db=db,
                user=current_user,
                class_id=default_exam.class_id,
                subject_id=default_exam.subject_id,
                session_id=default_exam.session_id,
                section_id=default_exam.section_id
            )

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValidationError("CSV file has no header row")

    validated_rows = []
    seen_pairs = set()
    checked_exam_ids = set()
    if default_exam is not None:
        checked_exam_ids.add(default_exam.id)

    for row_num, row in enumerate(reader, start=2):
        # Skip completely blank rows
        if all(v is None or str(v).strip() == "" for v in row.values()):
            continue

        adm = next(
            (
                str(row[k]).strip()
                for k in ("Admission Number", "admission_number", "Roll Number", "roll_number", "StudentID", "roll")
                if row.get(k) is not None and str(row[k]).strip() != ""
            ),
            None,
        )
        exam_id_val = next(
            (
                str(row[k]).strip()
                for k in ("Exam ID", "exam_id")
                if row.get(k) is not None and str(row[k]).strip() != ""
            ),
            None,
        )
        exam_name = next(
            (
                str(row[k]).strip()
                for k in ("Exam Name", "exam_name", "Exam", "subject")
                if row.get(k) is not None and str(row[k]).strip() != ""
            ),
            None,
        )
        score_val = next(
            (
                str(row[k]).strip()
                for k in ("Score", "score", "Marks", "marks", "latest_exam_marks", "LatestExam")
                if row.get(k) is not None and str(row[k]).strip() != ""
            ),
            None,
        )

        if not adm:
            raise ValidationError(f"Row {row_num}: Missing student admission number")
        if score_val is None:
            raise ValidationError(f"Row {row_num}: Missing score for student '{adm}'")

        if adm.isascii() and adm.isdigit():
            student = db.query(Student).filter(
                (Student.admission_number == adm) | (Student.id == int(adm))
            ).first()
        else:
            student = db.query(Student).filter(Student.admission_number == adm).first()

        if not student:
            raise ValidationError(f"Row {row_num}: Student '{adm}' not found")

        any_enr = db.query(Enrollment).filter(
            Enrollment.student_id == student.id,
            Enrollment.session_id == session_id
        ).first()
        if any_enr:
            target_class_id = any_enr.class_id
            effective_section_id = any_enr.section_id if any_enr.section_id is not None else student.section_id
        else:
            target_class_id = student.class_id
            effective_section_id = student.section_id

        # Resolve exam deterministically
        exam: Optional[Exam] = None
        if default_exam is not None:
            if exam_id_val is not None:
                try:
                    parsed_eid = int(exam_id_val)
                except ValueError:
                    raise ValidationError(f"Row {row_num}: Invalid Exam ID '{exam_id_val}'")
                if parsed_eid != default_exam.id:
                    raise ValidationError(
                        f"Row {row_num}: CSV Exam ID {parsed_eid} conflicts with selected exam {default_exam.id}"
                    )
            exam = default_exam
        elif exam_id_val is not None:
            try:
                parsed_eid = int(exam_id_val)
            except ValueError:
                raise ValidationError(f"Row {row_num}: Invalid Exam ID '{exam_id_val}'")
            exam = db.query(Exam).filter(Exam.id == parsed_eid).first()
            if not exam:
                raise ValidationError(f"Row {row_num}: Exam ID {parsed_eid} not found")
            if exam.session_id != session_id:
                raise ValidationError(f"Row {row_num}: Exam ID {parsed_eid} does not belong to session {session_id}")
        elif exam_name is not None:
            exam_name_clean = exam_name.strip()
            q = db.query(Exam).filter(
                Exam.name.ilike(f"%{exam_name_clean}%"),
                Exam.session_id == session_id,
                Exam.class_id == target_class_id,
            )
            if effective_section_id is not None:
                q = q.filter((Exam.section_id == effective_section_id) | (Exam.section_id.is_(None)))
            else:
                q = q.filter(Exam.section_id.is_(None))
            if current_user is not None and current_user.role == UserRole.TEACHER and current_user.teacher_profile:
                cst_query = db.query(ClassSubjectTeacher).filter(
                    ClassSubjectTeacher.teacher_id == current_user.teacher_profile.id,
                    ClassSubjectTeacher.session_id == session_id,
                    ClassSubjectTeacher.class_id == target_class_id,
                )
                if effective_section_id is not None:
                    cst_query = cst_query.filter(
                        (ClassSubjectTeacher.section_id == effective_section_id)
                        | (ClassSubjectTeacher.section_id.is_(None))
                    )
                assigned_subj_ids = [a.subject_id for a in cst_query.all()]
                if assigned_subj_ids:
                    exam = q.filter(Exam.subject_id.in_(assigned_subj_ids)).first()
            if not exam:
                exam = q.first()
            if not exam:
                raise ValidationError(f"Row {row_num}: Exam '{exam_name_clean}' not found in session {session_id}")
        else:
            q = db.query(Exam).filter(Exam.class_id == target_class_id, Exam.session_id == session_id)
            if effective_section_id is not None:
                q = q.filter((Exam.section_id == effective_section_id) | (Exam.section_id.is_(None)))
            else:
                q = q.filter(Exam.section_id.is_(None))
            if current_user is not None and current_user.role == UserRole.TEACHER and current_user.teacher_profile:
                cst_query = db.query(ClassSubjectTeacher).filter(
                    ClassSubjectTeacher.teacher_id == current_user.teacher_profile.id,
                    ClassSubjectTeacher.session_id == session_id,
                    ClassSubjectTeacher.class_id == target_class_id,
                )
                if effective_section_id is not None:
                    cst_query = cst_query.filter(
                        (ClassSubjectTeacher.section_id == effective_section_id)
                        | (ClassSubjectTeacher.section_id.is_(None))
                    )
                assigned_subj_ids = [a.subject_id for a in cst_query.all()]
                if assigned_subj_ids:
                    q = q.filter(Exam.subject_id.in_(assigned_subj_ids))
            exam = q.first()
            if not exam:
                raise ValidationError(f"Row {row_num}: No exam found for student '{adm}' in session {session_id}")

        if current_user is not None and exam.id not in checked_exam_ids:
            check_teacher_scope(
                db=db,
                user=current_user,
                class_id=exam.class_id,
                subject_id=exam.subject_id,
                session_id=exam.session_id,
                section_id=exam.section_id
            )
            checked_exam_ids.add(exam.id)

        pair = (exam.id, student.id)
        if pair in seen_pairs:
            raise ValidationError(
                f"Row {row_num}: Duplicate entry for student '{student.admission_number}' in exam '{exam.name}'"
            )
        seen_pairs.add(pair)

        any_enr = db.query(Enrollment).filter(
            Enrollment.student_id == student.id,
            Enrollment.session_id == exam.session_id
        ).first()
        if any_enr:
            if any_enr.status != "active" or any_enr.class_id != exam.class_id:
                raise ValidationError(
                    f"Row {row_num}: Student {student.admission_number} is not actively enrolled in class {exam.class_id} for this session"
                )
            effective_section_id = any_enr.section_id if any_enr.section_id is not None else student.section_id
        else:
            if student.class_id != exam.class_id:
                raise ValidationError(
                    f"Row {row_num}: Student {student.admission_number} is not actively enrolled in class {exam.class_id} for this session"
                )
            effective_section_id = student.section_id

        if exam.section_id is not None and effective_section_id != exam.section_id:
            raise ValidationError(
                f"Row {row_num}: Student {student.admission_number} is not enrolled in section {exam.section_id} for exam '{exam.name}'"
            )

        try:
            score_float = float(score_val)
        except ValueError:
            raise ValidationError(f"Row {row_num}: Invalid score '{score_val}'")

        if math.isnan(score_float) or math.isinf(score_float):
            raise ValidationError(f"Row {row_num}: Score must be a finite number")

        if score_float < 0 or score_float > exam.max_marks:
            raise ValidationError(
                f"Row {row_num}: Score {score_float} is out of bounds for exam max marks {exam.max_marks}"
            )

        validated_rows.append((exam, student, score_float))

    if not validated_rows:
        raise ValidationError("No valid mark rows found in CSV")

    count = 0
    for exam, student, score_float in validated_rows:
        existing_mark = db.query(Mark).filter(Mark.exam_id == exam.id, Mark.student_id == student.id).first()
        if existing_mark:
            old_val = {"score": existing_mark.score}
            existing_mark.score = score_float
            existing_mark.is_absent = False
            existing_mark.entered_by = entered_by_teacher_id
            db.flush()
            create_audit_entry(
                db=db,
                user_id=user_id,
                action="mark.updated",
                entity_name="mark",
                entity_id=existing_mark.id,
                old_values=old_val,
                new_values={"score": score_float},
                reason=reason
            )
        else:
            new_mark = Mark(
                exam_id=exam.id,
                student_id=student.id,
                score=score_float,
                is_absent=False,
                entered_by=entered_by_teacher_id
            )
            db.add(new_mark)
            db.flush()
            create_audit_entry(
                db=db,
                user_id=user_id,
                action="mark.created",
                entity_name="mark",
                entity_id=new_mark.id,
                new_values={"score": score_float},
                reason=reason
            )
        count += 1

    db.commit()
    return count

