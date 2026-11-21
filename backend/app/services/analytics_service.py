from collections import defaultdict
from typing import Dict, List, Optional
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.academics import AttendanceRecord, Exam, Mark
from backend.app.models.institution import AcademicSession, Class, Enrollment, Student, Subject
from backend.app.schemas.analytics import (
    AttendanceAnalyticsResponse,
    AttendanceTrendPoint,
    BadgeItem,
    DecliningPerformanceResponse,
    DecliningStudentItem,
    ExamAnalyticsResponse,
    ScoreDistributionBin,
    StudentBadgesResponse,
    StudentExamPerformance,
    StudentVsClassAnalytics,
    SubjectAttendanceStat,
)


def get_attendance_analytics(
    db: Session,
    session_id: int,
    class_id: Optional[int] = None,
    student_id: Optional[int] = None
) -> AttendanceAnalyticsResponse:
    query = db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session_id)
    if class_id:
        query = query.filter(AttendanceRecord.class_id == class_id)
    if student_id:
        query = query.filter(AttendanceRecord.student_id == student_id)

    records = query.all()
    total = len(records)
    if total == 0:
        return AttendanceAnalyticsResponse(
            overall_attendance_rate=0.0,
            total_records=0,
            present_count=0,
            absent_count=0,
            late_count=0,
            excused_count=0,
            by_subject=[],
            trends=[]
        )

    pure_present = sum(1 for r in records if r.status == "present")
    late = sum(1 for r in records if r.status == "late")
    absent = sum(1 for r in records if r.status == "absent")
    excused = sum(1 for r in records if r.status == "excused")

    # Present + Late counted toward attendance credit (M-08)
    overall_rate = round(((pure_present + late) / total) * 100, 2)

    # Breakdown by subject
    subject_map = defaultdict(lambda: {"total": 0, "attended": 0, "name": ""})
    subjects = {s.id: s.name for s in db.query(Subject).all()}
    
    for r in records:
        entry = subject_map[r.subject_id]
        entry["total"] += 1
        entry["name"] = subjects.get(r.subject_id, "Subject")
        if r.status in ("present", "late"):
            entry["attended"] += 1

    by_subject = [
        SubjectAttendanceStat(
            subject_id=sub_id,
            subject_name=data["name"],
            total_classes=data["total"],
            present_count=data["attended"],
            attendance_rate=round((data["attended"] / data["total"]) * 100, 2) if data["total"] > 0 else 0.0
        )
        for sub_id, data in subject_map.items()
    ]

    # Trends by date
    trends_map = defaultdict(lambda: {"total": 0, "attended": 0})
    for r in records:
        d_str = str(r.date)
        trends_map[d_str]["total"] += 1
        if r.status in ("present", "late"):
            trends_map[d_str]["attended"] += 1

    sorted_dates = sorted(trends_map.keys())
    trends = [
        AttendanceTrendPoint(
            period=d,
            attendance_rate=round((trends_map[d]["attended"] / trends_map[d]["total"]) * 100, 2),
            total_sessions=trends_map[d]["total"]
        )
        for d in sorted_dates
    ]

    return AttendanceAnalyticsResponse(
        overall_attendance_rate=overall_rate,
        total_records=total,
        present_count=pure_present,
        absent_count=absent,
        late_count=late,
        excused_count=excused,
        by_subject=by_subject,
        trends=trends
    )


def get_exam_analytics(db: Session, exam_id: int) -> ExamAnalyticsResponse:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise NotFoundError("Exam not found")

    marks = db.query(Mark).filter(Mark.exam_id == exam_id).all()
    subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()
    subject_name = subject.name if subject else "Unknown"

    valid_scores = [m.score for m in marks if m.score is not None and not m.is_absent]
    student_count = len(valid_scores)

    if student_count == 0:
        return ExamAnalyticsResponse(
            exam_id=exam.id,
            exam_name=exam.name,
            subject_name=subject_name,
            max_marks=exam.max_marks,
            student_count=0,
            average_score=0.0,
            median_score=0.0,
            highest_score=0.0,
            lowest_score=0.0,
            pass_rate=0.0,
            distribution=[]
        )

    avg_score = round(float(np.mean(valid_scores)), 2)
    median_score = round(float(np.median(valid_scores)), 2)
    highest_score = round(float(max(valid_scores)), 2)
    lowest_score = round(float(min(valid_scores)), 2)
    
    # 40% as passing criteria standard
    pass_cutoff = exam.max_marks * 0.40
    passed_count = sum(1 for s in valid_scores if s >= pass_cutoff)
    pass_rate = round((passed_count / student_count) * 100, 2)

    # Score distribution bins aligned cleanly (M-08)
    pcts = [(s / exam.max_marks) * 100 for s in valid_scores]
    bins = [
        {"label": "0-39%", "count": sum(1 for p in pcts if p < 40)},
        {"label": "40-59%", "count": sum(1 for p in pcts if 40 <= p < 60)},
        {"label": "60-79%", "count": sum(1 for p in pcts if 60 <= p < 80)},
        {"label": "80-100%", "count": sum(1 for p in pcts if p >= 80)},
    ]
    distribution = [
        ScoreDistributionBin(
            range_label=b["label"],
            count=b["count"],
            percentage=round((b["count"] / student_count) * 100, 2)
        )
        for b in bins
    ]

    return ExamAnalyticsResponse(
        exam_id=exam.id,
        exam_name=exam.name,
        subject_name=subject_name,
        max_marks=exam.max_marks,
        student_count=student_count,
        average_score=avg_score,
        median_score=median_score,
        highest_score=highest_score,
        lowest_score=lowest_score,
        pass_rate=pass_rate,
        distribution=distribution
    )


def get_student_vs_class_analytics(
    db: Session,
    student_id: int,
    session_id: int
) -> StudentVsClassAnalytics:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    # Get student's class
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.session_id == session_id
    ).first()
    class_id = enrollment.class_id if enrollment else student.class_id

    # Class exams ordered chronologically
    exams = db.query(Exam).filter(
        Exam.session_id == session_id,
        Exam.class_id == class_id
    ).order_by(Exam.date.asc(), Exam.id.asc()).all()

    student_exams = []
    student_pcts = []
    class_all_pcts = []

    for exam in exams:
        subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()
        sub_name = subject.name if subject else "Subject"

        # All non-absent marks for this exam (M-08)
        all_marks = db.query(Mark).filter(
            Mark.exam_id == exam.id,
            Mark.score.isnot(None),
            Mark.is_absent.is_(False)
        ).all()
        class_avg = round(float(np.mean([m.score for m in all_marks])), 2) if all_marks else 0.0

        # Student mark
        s_mark = db.query(Mark).filter(Mark.exam_id == exam.id, Mark.student_id == student_id).first()
        score = s_mark.score if s_mark else None
        is_absent = s_mark.is_absent if s_mark else False
        pct = round((score / exam.max_marks) * 100, 2) if (score is not None and not is_absent and exam.max_marks > 0) else None

        if pct is not None:
            student_pcts.append(pct)
        if all_marks and exam.max_marks > 0:
            for m in all_marks:
                class_all_pcts.append((m.score / exam.max_marks) * 100)

        student_exams.append(
            StudentExamPerformance(
                exam_id=exam.id,
                exam_name=exam.name,
                subject_name=sub_name,
                date=str(exam.date),
                max_marks=exam.max_marks,
                score=score,
                percentage=pct,
                class_average=class_avg,
                is_absent=is_absent
            )
        )

    student_overall_pct = round(float(np.mean(student_pcts)), 2) if student_pcts else 0.0
    class_overall_avg = round(float(np.mean(class_all_pcts)), 2) if class_all_pcts else 0.0

    # Attendance
    student_att = get_attendance_analytics(db, session_id=session_id, student_id=student_id)
    class_att = get_attendance_analytics(db, session_id=session_id, class_id=class_id)

    return StudentVsClassAnalytics(
        student_id=student.id,
        student_name=student.full_name,
        overall_percentage=student_overall_pct,
        class_overall_average=class_overall_avg,
        attendance_rate=student_att.overall_attendance_rate,
        class_attendance_average=class_att.overall_attendance_rate,
        exams=student_exams
    )


def get_declining_students(
    db: Session,
    session_id: int,
    class_id: int,
    min_consecutive_drops: int = 2
) -> DecliningPerformanceResponse:
    """
    R-008, M-08: Identify students showing downward performance trends across sequential exams.
    Enforces min_consecutive_drops >= 1 and excludes absent exam entries.
    """
    if min_consecutive_drops < 1:
        raise ValidationError("min_consecutive_drops must be at least 1")

    enrollments = db.query(Enrollment).filter(
        Enrollment.session_id == session_id,
        Enrollment.class_id == class_id
    ).all()
    student_ids = [e.student_id for e in enrollments]

    declining_list = []
    exams = db.query(Exam).filter(
        Exam.session_id == session_id,
        Exam.class_id == class_id
    ).order_by(Exam.date.asc(), Exam.id.asc()).all()

    # Group exams by subject
    exams_by_subject = defaultdict(list)
    for exam in exams:
        exams_by_subject[exam.subject_id].append(exam)

    subjects = {s.id: s.name for s in db.query(Subject).all()}
    students = {s.id: s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()}

    for sid in student_ids:
        student = students.get(sid)
        if not student:
            continue

        for sub_id, sub_exams in exams_by_subject.items():
            if len(sub_exams) < min_consecutive_drops + 1:
                continue

            scores = []
            for ex in sub_exams:
                mark = db.query(Mark).filter(
                    Mark.exam_id == ex.id,
                    Mark.student_id == sid,
                    Mark.score.isnot(None),
                    Mark.is_absent.is_(False)
                ).first()
                if mark and ex.max_marks > 0:
                    scores.append(round((mark.score / ex.max_marks) * 100, 2))

            if len(scores) >= min_consecutive_drops + 1:
                # Check for consecutive drops in the most recent scores
                recent = scores[-(min_consecutive_drops + 1):]
                is_declining = all(recent[i] > recent[i + 1] for i in range(len(recent) - 1))
                if is_declining:
                    drop = round(recent[0] - recent[-1], 2)
                    declining_list.append(
                        DecliningStudentItem(
                            student_id=student.id,
                            student_name=student.full_name,
                            admission_number=student.admission_number,
                            subject_name=subjects.get(sub_id, "Subject"),
                            recent_scores=recent,
                            score_drop=drop,
                            consecutive_declines=len(recent) - 1
                        )
                    )

    return DecliningPerformanceResponse(
        class_id=class_id,
        count=len(declining_list),
        declining_students=declining_list
    )


def get_student_badges(
    db: Session,
    student_id: int,
    session_id: int
) -> StudentBadgesResponse:
    """
    Compute student achievement badges and class cohort rank without exposing peer PII.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    acad_session = db.query(AcademicSession).filter(AcademicSession.id == session_id).first()
    if not acad_session:
        raise NotFoundError("Academic session not found")

    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.session_id == session_id
    ).first()
    class_id = enrollment.class_id if enrollment else student.class_id

    # Build class cohort IDs
    active_enr_ids = {
        e.student_id
        for e in db.query(Enrollment).filter(
            Enrollment.session_id == session_id,
            Enrollment.class_id == class_id,
            Enrollment.status == "active"
        ).all()
    }
    all_session_enrolled_ids = {
        e.student_id
        for e in db.query(Enrollment).filter(Enrollment.session_id == session_id).all()
    }
    fallback_ids = {
        s.id
        for s in db.query(Student).filter(Student.class_id == class_id).all()
        if s.id not in all_session_enrolled_ids
    }
    cohort_ids = active_enr_ids | fallback_ids | {student_id}
    total_students_in_class = len(cohort_ids)

    exams = db.query(Exam).filter(
        Exam.session_id == session_id,
        Exam.class_id == class_id,
        Exam.max_marks > 0
    ).all()
    exam_by_id = {ex.id: ex for ex in exams}

    student_exam_pcts: Dict[int, List[float]] = defaultdict(list)
    my_subject_pcts: Dict[int, List[float]] = defaultdict(list)

    if exam_by_id:
        marks = db.query(Mark).filter(
            Mark.exam_id.in_(list(exam_by_id.keys())),
            Mark.student_id.in_(list(cohort_ids)),
            Mark.score.isnot(None),
            Mark.is_absent.is_(False)
        ).all()

        for m in marks:
            ex = exam_by_id.get(m.exam_id)
            if not ex or ex.max_marks <= 0:
                continue
            pct = (m.score / ex.max_marks) * 100.0
            student_exam_pcts[m.student_id].append(pct)
            if m.student_id == student_id:
                my_subject_pcts[ex.subject_id].append(pct)

    peer_avgs = {
        sid: round(float(np.mean(pcts)), 2)
        for sid, pcts in student_exam_pcts.items()
        if pcts
    }
    has_marks = student_id in peer_avgs

    if has_marks:
        my_overall = peer_avgs[student_id]
        rank: Optional[int] = 1 + sum(
            1 for sid, avg in peer_avgs.items() if sid != student_id and avg > my_overall
        )
    else:
        rank = None

    att = get_attendance_analytics(db, session_id=session_id, student_id=student_id)
    has_attendance = att.total_records > 0
    att_rate = att.overall_attendance_rate

    subject_avgs = {
        sub_id: float(np.mean(pcts))
        for sub_id, pcts in my_subject_pcts.items()
        if pcts
    }

    top_performer_unlocked = has_marks and (rank == 1)
    attendance_champ_unlocked = has_attendance and (att_rate >= 95.0)
    subject_ace_unlocked = has_marks and bool(subject_avgs) and (max(subject_avgs.values()) >= 88.0)
    all_rounder_unlocked = (
        has_marks
        and bool(subject_avgs)
        and all(avg >= 60.0 for avg in subject_avgs.values())
        and (not has_attendance or att_rate >= 70.0)
    )
    active_learner_unlocked = not any([
        top_performer_unlocked,
        attendance_champ_unlocked,
        subject_ace_unlocked,
        all_rounder_unlocked,
    ])

    badges = [
        BadgeItem(
            id="top_performer",
            title="Top Performer",
            description="Ranked #1 in class overall academic percentage",
            icon="trophy",
            unlocked=top_performer_unlocked,
            color="#f59e0b",
        ),
        BadgeItem(
            id="attendance_champ",
            title="Attendance Champ",
            description="Maintained 95%+ attendance rate this session",
            icon="calendar-check",
            unlocked=attendance_champ_unlocked,
            color="#10b981",
        ),
        BadgeItem(
            id="subject_ace",
            title="Subject Ace",
            description="Scored 88%+ average in at least one subject",
            icon="zap",
            unlocked=subject_ace_unlocked,
            color="#8b5cf6",
        ),
        BadgeItem(
            id="all_rounder",
            title="All-Rounder",
            description="No weak subjects (<60%) and steady attendance (>=70%)",
            icon="star",
            unlocked=all_rounder_unlocked,
            color="#3b82f6",
        ),
        BadgeItem(
            id="active_learner",
            title="Active Learner",
            description="Consistent engagement and progression",
            icon="rocket",
            unlocked=active_learner_unlocked,
            color="#64748b",
        ),
    ]

    return StudentBadgesResponse(
        student_id=student_id,
        session_id=session_id,
        rank=rank,
        total_students_in_class=total_students_in_class,
        badges=badges,
    )
