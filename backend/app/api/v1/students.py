from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.deps import check_student_scope, get_current_user, get_db, require_teacher_or_admin
from backend.app.core.exceptions import NotFoundError
from backend.app.models.institution import Student
from backend.app.models.user import User
from backend.app.schemas.institution import StudentResponse
from backend.app.schemas.ml import StudentEstimateResponse
from backend.app.services.ml_service import get_student_prediction

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/{student_id}", response_model=StudentResponse)
def api_get_student_detail(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    R-007, C-02: Get student profile.
    Students can only view their own profile.
    Teachers can only view students enrolled in classes they teach.
    """
    check_student_scope(db=db, user=current_user, student_id=student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")
    return student


@router.get("/{student_id}/estimate", response_model=StudentEstimateResponse)
def api_get_estimate_direct(
    student_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Contract API-003, C-02: Teacher with scope over the student's class, or Administrator.
    """
    check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
    return get_student_prediction(db=db, student_id=student_id, session_id=session_id)
