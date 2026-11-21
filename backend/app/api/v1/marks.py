from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    check_student_scope,
    check_teacher_scope,
    get_current_user,
    get_db,
    require_teacher_or_admin,
)
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.academics import Exam
from backend.app.models.user import User, UserRole
from backend.app.schemas.academics import MarkResponse, MarksBulkSave
from backend.app.services.academics_service import (
    get_marks_for_exam,
    get_marks_for_student,
    import_marks_csv,
    save_marks,
)

router = APIRouter(prefix="/marks", tags=["Marks"])


@router.put("")
def api_save_marks(
    marks_in: MarksBulkSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    R-005, R-014, UI-004: Record and update marks.
    Enforces score validation, distinguishes blank from 0,
    and logs audit entry with reason in the same transaction.
    """
    exam = db.query(Exam).filter(Exam.id == marks_in.exam_id).first()
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

    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    count = save_marks(
        db=db,
        marks_in=marks_in,
        teacher_id=teacher_id,
        user_id=current_user.id
    )
    return {"status": "success", "saved_count": count}


@router.get("/exam/{exam_id}", response_model=List[MarkResponse])
def api_get_exam_marks(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    C-02: Teachers can only view marks for exams in classes/subjects they teach.
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

    return get_marks_for_exam(db, exam_id=exam_id)


@router.get("/student/{student_id}", response_model=List[MarkResponse])
def api_get_student_marks(
    student_id: int,
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    R-007, C-02: Student can only view their own marks.
    Teachers can only view marks for students in classes they teach.
    Out-of-scope access returns 404 (T-004).
    """
    check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
    return get_marks_for_student(db, student_id=student_id, session_id=session_id)


@router.post("/upload-csv")
async def api_upload_marks_csv(
    file: UploadFile = File(...),
    session_id: int = Form(...),
    exam_id: Optional[int] = Form(None),
    reason: str = Form("Bulk marks CSV import"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Bulk import marks from CSV file with automatic audit trail recording.
    """
    if exam_id is not None:
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise NotFoundError("Exam not found")
        if exam.session_id != session_id:
            raise ValidationError(f"Exam {exam_id} does not belong to session {session_id}")
        check_teacher_scope(
            db=db,
            user=current_user,
            class_id=exam.class_id,
            subject_id=exam.subject_id,
            session_id=exam.session_id,
            section_id=exam.section_id
        )

    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    content = await file.read()
    if not content or not content.strip():
        raise ValidationError("Uploaded CSV file is empty")
    csv_text = content.decode("utf-8-sig", errors="ignore")
    count = import_marks_csv(
        db=db,
        csv_text=csv_text,
        session_id=session_id,
        entered_by_teacher_id=teacher_id,
        user_id=current_user.id,
        reason=reason,
        current_user=current_user,
        default_exam_id=exam_id
    )
    return {"status": "success", "imported_count": count}

