import mimetypes
import os
import re
from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from backend.app.api.deps import (
    check_teacher_class_scope,
    check_teacher_scope,
    get_current_user,
    get_db,
    require_teacher_or_admin,
)
from backend.app.core.config import settings
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.academics import Exam
from backend.app.models.institution import ClassSubjectTeacher, Enrollment
from backend.app.models.user import User, UserRole
from backend.app.schemas.academics import ExamCreate, ExamResponse
from backend.app.services.academics_service import create_exam

router = APIRouter(prefix="/exams", tags=["Exams"])

ALLOWED_DATESHEET_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".csv"}


def _enrich_exam(exam: Exam, today: date) -> Exam:
    days = (exam.date - today).days
    exam.days_left = days
    exam.countdown_status = "Today!" if days == 0 else (f"{days} Days Left" if days > 0 else "Completed")
    exam.subject_name = exam.subject.name if exam.subject else None
    exam.class_name = exam.class_obj.name if exam.class_obj else None
    return exam


@router.post("", response_model=ExamResponse)
def api_create_exam(
    exam_in: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    R-005, M-01: Teacher creates an exam with defined max_marks.
    Enforces teacher assignment scope including section_id.
    """
    check_teacher_scope(
        db=db,
        user=current_user,
        class_id=exam_in.class_id,
        subject_id=exam_in.subject_id,
        session_id=exam_in.session_id,
        section_id=exam_in.section_id
    )

    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    created = create_exam(
        db=db,
        exam_in=exam_in,
        teacher_id=teacher_id,
        user_id=current_user.id
    )
    exam = db.query(Exam).options(
        joinedload(Exam.subject),
        joinedload(Exam.class_obj)
    ).filter(Exam.id == created.id).first()
    return _enrich_exam(exam, datetime.now(timezone.utc).date())


@router.get("", response_model=List[ExamResponse])
def api_get_exams(
    session_id: int,
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    C-02: Scoped exam listing.
    - Students see exams for their class and section (or class-wide exams).
    - Teachers see exams for their assigned classes/subjects/sections.
    """
    query = db.query(Exam).options(
        joinedload(Exam.subject),
        joinedload(Exam.class_obj)
    ).filter(Exam.session_id == session_id)

    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            return []
        st = current_user.student_profile
        enr = db.query(Enrollment).filter(
            Enrollment.student_id == st.id,
            Enrollment.session_id == session_id
        ).first()
        st_class_id = enr.class_id if enr else st.class_id
        st_section_id = (enr.section_id if enr and enr.section_id is not None else st.section_id)
        query = query.filter(Exam.class_id == st_class_id)
        if st_section_id is not None:
            query = query.filter((Exam.section_id == st_section_id) | (Exam.section_id.is_(None)))
    elif current_user.role == UserRole.TEACHER:
        if not current_user.teacher_profile:
            return []
        if class_id is not None:
            check_teacher_class_scope(db=db, user=current_user, class_id=class_id, session_id=session_id)
        assignments = db.query(ClassSubjectTeacher).filter(
            ClassSubjectTeacher.teacher_id == current_user.teacher_profile.id,
            ClassSubjectTeacher.session_id == session_id
        ).all()
        if not assignments:
            return []
        scope_filters = []
        for a in assignments:
            if class_id is not None and a.class_id != class_id:
                continue
            cond = (Exam.class_id == a.class_id) & (Exam.subject_id == a.subject_id)
            if a.section_id is not None:
                cond = cond & ((Exam.section_id == a.section_id) | (Exam.section_id.is_(None)))
            scope_filters.append(cond)
        if not scope_filters:
            return []
        query = query.filter(or_(*scope_filters))

    if class_id is not None and current_user.role == UserRole.ADMINISTRATOR:
        query = query.filter(Exam.class_id == class_id)
    if subject_id is not None:
        query = query.filter(Exam.subject_id == subject_id)

    exams = query.order_by(Exam.date.asc()).all()
    today = datetime.now(timezone.utc).date()
    for ex in exams:
        _enrich_exam(ex, today)
    return exams


@router.get("/{exam_id}", response_model=ExamResponse)
def api_get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    C-02: Scoped exam detail.
    """
    exam = db.query(Exam).options(
        joinedload(Exam.subject),
        joinedload(Exam.class_obj)
    ).filter(Exam.id == exam_id).first()
    if not exam:
        raise NotFoundError("Exam not found")

    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            raise NotFoundError("Exam not found or out of scope")
        st = current_user.student_profile
        enr = db.query(Enrollment).filter(
            Enrollment.student_id == st.id,
            Enrollment.session_id == exam.session_id
        ).first()
        st_class_id = enr.class_id if enr else st.class_id
        st_section_id = (enr.section_id if enr and enr.section_id is not None else st.section_id)
        if exam.class_id != st_class_id:
            raise NotFoundError("Exam not found or out of scope")
        if exam.section_id is not None and st_section_id is not None and exam.section_id != st_section_id:
            raise NotFoundError("Exam not found or out of scope")
    elif current_user.role == UserRole.TEACHER:
        check_teacher_scope(
            db=db,
            user=current_user,
            class_id=exam.class_id,
            subject_id=exam.subject_id,
            session_id=exam.session_id,
            section_id=exam.section_id
        )

    today = datetime.now(timezone.utc).date()
    return _enrich_exam(exam, today)


@router.post("/{exam_id}/datesheet")
def api_upload_exam_datesheet(
    exam_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Upload a datesheet attachment (PDF, image, text/csv) for an exam schedule.
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

    raw_name = os.path.basename(file.filename or "")
    _, ext = os.path.splitext(raw_name)
    if not ext or ext.lower() not in ALLOWED_DATESHEET_EXTENSIONS:
        raise ValidationError(
            f"Invalid file extension '{ext or 'none'}'. Allowed extensions: {sorted(ALLOWED_DATESHEET_EXTENSIONS)}"
        )

    content = file.file.read()
    if not content:
        raise ValidationError("Uploaded datesheet file is empty")

    upload_dir = os.path.join(settings.BASE_DIR, "uploads", "datesheets")
    os.makedirs(upload_dir, exist_ok=True)
    safe_base = re.sub(r"[^a-zA-Z0-9._-]", "_", raw_name)
    while ".." in safe_base:
        safe_base = safe_base.replace("..", "_")
    filename = f"{int(datetime.now(timezone.utc).timestamp())}_{safe_base}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    exam.datesheet_filename = filename
    db.commit()
    return {"status": "success", "datesheet_filename": filename}


@router.get("/{exam_id}/datesheet")
def api_download_exam_datesheet(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Authenticated, role-scoped download of an exam datesheet attachment.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise NotFoundError("Exam not found")

    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            raise NotFoundError("Exam not found or out of scope")
        st = current_user.student_profile
        enr = db.query(Enrollment).filter(
            Enrollment.student_id == st.id,
            Enrollment.session_id == exam.session_id
        ).first()
        st_class_id = enr.class_id if enr else st.class_id
        st_section_id = (enr.section_id if enr and enr.section_id is not None else st.section_id)
        if exam.class_id != st_class_id:
            raise NotFoundError("Exam not found or out of scope")
        if exam.section_id is not None and st_section_id is not None and exam.section_id != st_section_id:
            raise NotFoundError("Exam not found or out of scope")
    elif current_user.role == UserRole.TEACHER:
        check_teacher_scope(
            db=db,
            user=current_user,
            class_id=exam.class_id,
            subject_id=exam.subject_id,
            session_id=exam.session_id,
            section_id=exam.section_id
        )
    elif current_user.role != UserRole.ADMINISTRATOR:
        raise NotFoundError("Exam not found or out of scope")

    if not exam.datesheet_filename:
        raise NotFoundError("Datesheet not uploaded for this exam")

    upload_dir = os.path.realpath(os.path.join(settings.BASE_DIR, "uploads", "datesheets"))
    safe_filename = os.path.basename(exam.datesheet_filename)
    if not safe_filename or safe_filename != exam.datesheet_filename:
        raise NotFoundError("Datesheet file not found")

    file_path = os.path.realpath(os.path.join(upload_dir, safe_filename))
    if not file_path.startswith(upload_dir + os.sep) or not os.path.isfile(file_path):
        raise NotFoundError("Datesheet file not found")

    media_type, _ = mimetypes.guess_type(file_path)
    return FileResponse(
        path=file_path,
        media_type=media_type or "application/octet-stream",
        filename=safe_filename
    )

