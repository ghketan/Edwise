from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    get_current_user,
    get_db,
    require_student,
    require_teacher_or_admin,
)
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.academics import DoubtQuestion
from backend.app.models.institution import Subject
from backend.app.models.user import User, UserRole
from backend.app.schemas.academics import DoubtAnswer, DoubtCreate, DoubtResponse
from backend.app.services.academics_service import answer_doubt, create_doubt, get_doubts

router = APIRouter(prefix="/doubts", tags=["Doubts & Guidance"])


@router.post("", response_model=DoubtResponse)
def api_create_doubt(
    payload: DoubtCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """
    Student submits an academic question/doubt tagged to a subject.
    """
    if not current_user.student_profile:
        raise ValidationError("Student profile required to submit doubts")

    doubt = create_doubt(
        db=db,
        student_id=current_user.student_profile.id,
        session_id=payload.session_id,
        subject_id=payload.subject_id,
        question=payload.question
    )

    subj = db.query(Subject).filter(Subject.id == doubt.subject_id).first()
    return DoubtResponse(
        id=doubt.id,
        session_id=doubt.session_id,
        student_id=doubt.student_id,
        subject_id=doubt.subject_id,
        question=doubt.question,
        answer=doubt.answer,
        answered_by=doubt.answered_by,
        answered_by_name=None,
        answered_at=doubt.answered_at,
        is_resolved=doubt.is_resolved,
        created_at=doubt.created_at,
        updated_at=doubt.updated_at,
        student_name=current_user.student_profile.full_name,
        student_roll=current_user.student_profile.admission_number,
        subject_name=subj.name if subj else "Subject"
    )


@router.get("", response_model=List[DoubtResponse])
def api_get_doubts(
    session_id: int,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve doubts:
    - Students see only their own doubts and teacher responses.
    - Teachers and Admins see class and subject doubts to review and answer.
    """
    student_id = None
    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            return []
        student_id = current_user.student_profile.id

    doubts = get_doubts(
        db=db,
        session_id=session_id,
        student_id=student_id,
        subject_id=subject_id
    )

    res = []
    for d in doubts:
        res.append(DoubtResponse(
            id=d.id,
            session_id=d.session_id,
            student_id=d.student_id,
            subject_id=d.subject_id,
            question=d.question,
            answer=d.answer,
            answered_by=d.answered_by,
            answered_by_name=d.teacher.full_name if d.teacher else ("Administration" if d.is_resolved else None),
            answered_at=d.answered_at,
            is_resolved=d.is_resolved,
            created_at=d.created_at,
            updated_at=d.updated_at,
            student_name=d.student.full_name if d.student else "Student",
            student_roll=d.student.admission_number if d.student else "N/A",
            subject_name=d.subject.name if d.subject else "Subject"
        ))
    return res


@router.post("/{doubt_id}/answer", response_model=DoubtResponse)
def api_answer_doubt(
    doubt_id: int,
    payload: DoubtAnswer,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Teacher or Administrator submits resolution answer to student doubt.
    """
    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    doubt = answer_doubt(
        db=db,
        doubt_id=doubt_id,
        teacher_id=teacher_id,
        answer=payload.answer
    )
    return DoubtResponse(
        id=doubt.id,
        session_id=doubt.session_id,
        student_id=doubt.student_id,
        subject_id=doubt.subject_id,
        question=doubt.question,
        answer=doubt.answer,
        answered_by=doubt.answered_by,
        answered_by_name=doubt.teacher.full_name if doubt.teacher else ("Administration" if doubt.is_resolved else None),
        answered_at=doubt.answered_at,
        is_resolved=doubt.is_resolved,
        created_at=doubt.created_at,
        updated_at=doubt.updated_at,
        student_name=doubt.student.full_name if doubt.student else "Student",
        student_roll=doubt.student.admission_number if doubt.student else "N/A",
        subject_name=doubt.subject.name if doubt.subject else "Subject"
    )
