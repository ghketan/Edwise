import operator as op_module
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.core.exceptions import NotFoundError
from backend.app.models.academics import Assignment, Exam, Mark, Submission
from backend.app.models.institution import Enrollment, Student
from backend.app.models.recommendations import RecommendationRule, StudentRecommendation
from backend.app.schemas.recommendations import RecommendationReviewRequest, RecommendationRuleCreate, StudentRecommendationResponse
from backend.app.services.analytics_service import get_attendance_analytics
from backend.app.services.audit_service import create_audit_entry

OPERATOR_MAP = {
    "<": op_module.lt,
    "<=": op_module.le,
    ">": op_module.gt,
    ">=": op_module.ge
}


def create_recommendation_rule(db: Session, rule_in: RecommendationRuleCreate) -> RecommendationRule:
    rule = RecommendationRule(**rule_in.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_recommendation_rules(db: Session) -> List[RecommendationRule]:
    return db.query(RecommendationRule).filter(RecommendationRule.is_active.is_(True)).all()


def evaluate_rules_for_student(
    db: Session,
    student_id: int,
    session_id: int
) -> List[StudentRecommendation]:
    """
    Evaluates configurable indicator rules for a student (D-008, R-012, C-06, C-07).
    - C-06: Scoped strictly to student's class and session.
    - C-07: Never fires on missing data.
    - C-07: Calculates score_drop per subject in chronological order.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    rules = db.query(RecommendationRule).filter(RecommendationRule.is_active.is_(True)).all()
    if not rules:
        return []

    # 1. Attendance Indicator
    att = get_attendance_analytics(db, session_id=session_id, student_id=student_id)
    has_attendance = att.total_records > 0
    att_rate = att.overall_attendance_rate

    # 2. Assignment Indicator (C-06 scoped to class & session)
    enr = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.session_id == session_id
    ).first()
    class_id = enr.class_id if enr else student.class_id
    section_id = enr.section_id if enr else student.section_id

    assign_q = db.query(Assignment).filter(
        Assignment.session_id == session_id,
        Assignment.class_id == class_id
    )
    if section_id:
        assign_q = assign_q.filter(
            (Assignment.section_id == section_id) | (Assignment.section_id.is_(None))
        )
    class_assignments = assign_q.all()
    class_assign_ids = [a.id for a in class_assignments]

    has_assignments = len(class_assign_ids) > 0
    if has_assignments:
        submitted_count = db.query(Submission).filter(
            Submission.student_id == student_id,
            Submission.assignment_id.in_(class_assign_ids)
        ).count()
        missing_assignments = max(0, len(class_assign_ids) - submitted_count)
    else:
        missing_assignments = 0

    # 3. Score Drop Indicator (C-07: per subject, chronological order within session)
    # Find max score drop across subjects
    exams_in_session = db.query(Exam).filter(
        Exam.session_id == session_id,
        Exam.class_id == class_id
    ).order_by(Exam.date.asc(), Exam.id.asc()).all()

    exams_by_subject = defaultdict(list)
    for ex in exams_in_session:
        exams_by_subject[ex.subject_id].append(ex)

    max_score_drop = 0.0
    has_score_history = False

    for sub_id, sub_exams in exams_by_subject.items():
        sub_marks = []
        for ex in sub_exams:
            mark = db.query(Mark).filter(
                Mark.exam_id == ex.id,
                Mark.student_id == student_id,
                Mark.score.isnot(None),
                Mark.is_absent.is_(False)
            ).first()
            if mark and ex.max_marks > 0:
                sub_marks.append((mark.score / ex.max_marks) * 100)

        if len(sub_marks) >= 2:
            has_score_history = True
            # Compare the last two exams in this subject
            drop = sub_marks[-2] - sub_marks[-1]
            if drop > max_score_drop:
                max_score_drop = round(drop, 2)

    generated = []

    for rule in rules:
        comp_fn = OPERATOR_MAP.get(rule.operator)
        if not comp_fn:
            continue

        triggered = False
        trigger_val = 0.0

        # C-07: Never trigger if underlying data is missing
        if rule.indicator == "attendance_rate":
            if not has_attendance:
                continue  # Never fire on missing attendance
            trigger_val = att_rate
            triggered = comp_fn(att_rate, rule.threshold_value)
        elif rule.indicator == "score_drop":
            if not has_score_history:
                continue  # Never fire on missing exam history
            trigger_val = max_score_drop
            triggered = comp_fn(max_score_drop, rule.threshold_value)
        elif rule.indicator == "missing_assignments":
            if not has_assignments:
                continue  # Never fire if no assignments exist
            trigger_val = float(missing_assignments)
            triggered = comp_fn(missing_assignments, rule.threshold_value)

        if triggered:
            existing = db.query(StudentRecommendation).filter(
                StudentRecommendation.student_id == student_id,
                StudentRecommendation.session_id == session_id,
                StudentRecommendation.rule_id == rule.id,
                StudentRecommendation.review_status == "pending"
            ).first()

            formatted_msg = rule.template_message.replace("{value}", str(trigger_val)).replace("{threshold}", str(rule.threshold_value))

            if existing:
                existing.trigger_value = trigger_val
                existing.message = formatted_msg
                db.flush()
                generated.append(existing)
            else:
                rec = StudentRecommendation(
                    student_id=student_id,
                    session_id=session_id,
                    rule_id=rule.id,
                    trigger_value=trigger_val,
                    message=formatted_msg,
                    review_status="pending"
                )
                db.add(rec)
                db.flush()
                generated.append(rec)

    db.commit()
    return generated


def review_recommendation(
    db: Session,
    rec_id: int,
    review_in: RecommendationReviewRequest,
    teacher_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> StudentRecommendation:
    """
    Teacher reviews a recommendation and records 'reviewed_no_action' or 'action_taken' (D-008, §6.3).
    """
    rec = db.query(StudentRecommendation).filter(StudentRecommendation.id == rec_id).first()
    if not rec:
        raise NotFoundError("Recommendation not found")

    old_status = rec.review_status
    rec.review_status = review_in.review_status
    rec.review_notes = review_in.review_notes
    rec.reviewed_by = teacher_id
    rec.reviewed_at = datetime.now(timezone.utc)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="recommendation.reviewed",
        entity_name="student_recommendation",
        entity_id=rec.id,
        old_values={"status": old_status},
        new_values={"status": review_in.review_status, "notes": review_in.review_notes},
        reason="Teacher reviewed student recommendation card"
    )
    db.commit()
    db.refresh(rec)
    return rec


def get_recommendations_for_student(
    db: Session,
    student_id: int,
    session_id: int
) -> List[StudentRecommendationResponse]:
    recs = db.query(StudentRecommendation).filter(
        StudentRecommendation.student_id == student_id,
        StudentRecommendation.session_id == session_id
    ).all()

    student = db.query(Student).filter(Student.id == student_id).first()
    s_name = student.full_name if student else "Student"
    adm_no = student.admission_number if student else ""

    result = []
    for r in recs:
        result.append(
            StudentRecommendationResponse(
                id=r.id,
                student_id=r.student_id,
                student_name=s_name,
                admission_number=adm_no,
                rule_code=r.rule.rule_code,
                title=r.rule.title,
                trigger_value=r.trigger_value,
                message=r.message,
                severity=r.rule.severity,
                review_status=r.review_status,
                review_notes=r.review_notes,
                reviewed_by=r.reviewed_by,
                generated_at=r.generated_at,
                reviewed_at=r.reviewed_at
            )
        )
    return result
