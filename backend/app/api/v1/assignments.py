from datetime import datetime, timezone
import os
import re
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    check_teacher_class_scope,
    check_teacher_scope,
    get_current_user,
    get_db,
    require_student,
    require_teacher_or_admin,
)
from backend.app.core.config import settings
from backend.app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from backend.app.models.academics import Assignment, Submission
from backend.app.models.institution import ClassSubjectTeacher, Enrollment, Student
from backend.app.models.user import User, UserRole
from backend.app.schemas.academics import (
    AssignmentCreate,
    AssignmentResponse,
    SubmissionCreate,
    SubmissionGrade,
    SubmissionResponse,
)
from backend.app.services.academics_service import (
    create_assignment,
    grade_submission,
    submit_assignment,
)

router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.post("", response_model=AssignmentResponse)
def api_create_assignment(
    assign_in: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    check_teacher_scope(
        db=db,
        user=current_user,
        class_id=assign_in.class_id,
        subject_id=assign_in.subject_id,
        session_id=assign_in.session_id,
        section_id=assign_in.section_id
    )
    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    return create_assignment(db, assign_in, teacher_id=teacher_id, user_id=current_user.id)


@router.get("", response_model=List[AssignmentResponse])
def api_get_assignments(
    session_id: int,
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    C-02: Scoped assignment listing.
    - Students see assignments for their class and section.
    - Teachers see assignments for classes/subjects they teach.
    """
    query = db.query(Assignment).filter(Assignment.session_id == session_id)

    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            return []
        st = current_user.student_profile
        # Find active enrollment or student class
        enr = db.query(Enrollment).filter(
            Enrollment.student_id == st.id,
            Enrollment.session_id == session_id
        ).first()
        st_class_id = enr.class_id if enr else st.class_id
        st_section_id = (enr.section_id if enr and enr.section_id is not None else st.section_id)

        query = query.filter(Assignment.class_id == st_class_id)
        if st_section_id:
            query = query.filter(
                (Assignment.section_id == st_section_id) | (Assignment.section_id.is_(None))
            )
    elif current_user.role == UserRole.TEACHER:
        if not current_user.teacher_profile:
            return []
        assignments = db.query(ClassSubjectTeacher).filter(
            ClassSubjectTeacher.teacher_id == current_user.teacher_profile.id,
            ClassSubjectTeacher.session_id == session_id
        ).all()
        if class_id:
            check_teacher_class_scope(db=db, user=current_user, class_id=class_id, session_id=session_id)
            query = query.filter(Assignment.class_id == class_id)
        if not assignments:
            return []
        # Subject-level scope: only (class, subject[, section]) combinations the teacher is assigned to
        scope_filters = []
        for a in assignments:
            cond = (Assignment.class_id == a.class_id) & (Assignment.subject_id == a.subject_id)
            if a.section_id is not None:
                cond = cond & ((Assignment.section_id == a.section_id) | (Assignment.section_id.is_(None)))
            scope_filters.append(cond)
        query = query.filter(or_(*scope_filters))
    elif current_user.role != UserRole.ADMINISTRATOR:
        return []

    if class_id and current_user.role == UserRole.ADMINISTRATOR:
        query = query.filter(Assignment.class_id == class_id)
    if subject_id:
        query = query.filter(Assignment.subject_id == subject_id)

    return query.order_by(Assignment.due_date.desc()).all()


@router.get("/{assignment_id}/submissions", response_model=List[SubmissionResponse])
def api_get_assignment_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List submissions for an assignment.
    - Students see only their own submission.
    - Teachers see all submissions for assignments in their scoped classes/subjects.
    - Administrators and Principals see all submissions.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise NotFoundError("Assignment not found")

    query = db.query(Submission).filter(Submission.assignment_id == assignment_id)

    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            raise ForbiddenError("User is not associated with a student record")
        query = query.filter(Submission.student_id == current_user.student_profile.id)
    elif current_user.role == UserRole.TEACHER:
        check_teacher_scope(
            db=db,
            user=current_user,
            class_id=assignment.class_id,
            subject_id=assignment.subject_id,
            session_id=assignment.session_id,
            section_id=assignment.section_id
        )

    return query.order_by(Submission.submitted_at.desc()).all()


@router.post("/{assignment_id}/submit", response_model=SubmissionResponse)
def api_submit_assignment(
    assignment_id: int,
    submission_in: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """
    R-006, H-02: Student submits an assignment.
    Verifies assignment exists and student is enrolled in that class.
    """
    if not current_user.student_profile:
        raise ForbiddenError("User is not associated with a student record")

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise NotFoundError("Assignment not found")

    student = current_user.student_profile
    # Verify student is in this assignment's class
    enr = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.session_id == assignment.session_id,
        Enrollment.class_id == assignment.class_id
    ).first()
    if not enr and student.class_id != assignment.class_id:
        raise ForbiddenError("Student is not enrolled in the class for this assignment")

    submission_in.assignment_id = assignment_id
    return submit_assignment(
        db=db,
        submission_in=submission_in,
        student_id=student.id,
        user_id=current_user.id
    )


ALLOWED_SUBMISSION_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".txt"}


@router.post("/{assignment_id}/submit-file", response_model=SubmissionResponse)
def api_submit_assignment_file(
    assignment_id: int,
    file: UploadFile = File(...),
    content: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """
    Student submits an assignment with an uploaded file (e.g. photo of handwritten work, PDF, document).
    """
    if not current_user.student_profile:
        raise ForbiddenError("User is not associated with a student record")

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise NotFoundError("Assignment not found")

    student = current_user.student_profile
    enr = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.session_id == assignment.session_id,
        Enrollment.class_id == assignment.class_id
    ).first()
    if not enr and student.class_id != assignment.class_id:
        raise ForbiddenError("Student is not enrolled in the class for this assignment")

    raw_name = os.path.basename(file.filename or "submission")
    _, ext = os.path.splitext(raw_name)
    if not ext or ext.lower() not in ALLOWED_SUBMISSION_EXTENSIONS:
        raise ValidationError(
            f"Invalid file extension '{ext or 'none'}'. Allowed extensions: {sorted(ALLOWED_SUBMISSION_EXTENSIONS)}"
        )

    file_bytes = file.file.read()
    if not file_bytes:
        raise ValidationError("Uploaded assignment file is empty")

    upload_dir = os.path.join(settings.BASE_DIR, "uploads", "assignments")
    os.makedirs(upload_dir, exist_ok=True)
    safe_base = re.sub(r"[^a-zA-Z0-9._-]", "_", raw_name)
    while ".." in safe_base:
        safe_base = safe_base.replace("..", "_")

    filename = f"{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:8]}_{safe_base}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    attachment_url = f"/api/v1/assignments/files/{filename}"
    submission_in = SubmissionCreate(
        assignment_id=assignment_id,
        content=content or None,
        attachment_url=attachment_url
    )

    return submit_assignment(
        db=db,
        submission_in=submission_in,
        student_id=student.id,
        user_id=current_user.id
    )


@router.get("/files/{filename}")
def api_get_assignment_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Securely serves uploaded assignment submission files with strict role-based scoping (A2).
    """
    safe_filename = os.path.basename(filename)
    if not safe_filename or safe_filename != filename:
        raise NotFoundError("Submission file not found")

    file_path = os.path.join(settings.BASE_DIR, "uploads", "assignments", safe_filename)
    if not os.path.isfile(file_path):
        raise NotFoundError("Submission file not found")

    submission = db.query(Submission).filter(Submission.attachment_url.like(f"%{safe_filename}")).first()
    if not submission:
        raise NotFoundError("Submission file not found")

    if current_user.role == UserRole.ADMINISTRATOR:
        pass
    elif current_user.role == UserRole.STUDENT:
        if not current_user.student_profile or submission.student_id != current_user.student_profile.id:
            raise ForbiddenError("You are not authorized to view this submission file")
    elif current_user.role == UserRole.TEACHER:
        check_teacher_scope(
            db=db,
            user=current_user,
            class_id=submission.assignment.class_id,
            subject_id=submission.assignment.subject_id,
            session_id=submission.assignment.session_id,
            section_id=submission.assignment.section_id
        )
    else:
        raise ForbiddenError("Access denied")

    return FileResponse(file_path, filename=safe_filename)


@router.put("/submissions/{submission_id}/grade", response_model=SubmissionResponse)
def api_grade_submission(
    submission_id: int,
    grade_in: SubmissionGrade,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    C-03: Arbitrary teacher grading prevention.
    Verifies that teacher is assigned to the class, section, and subject of the assignment.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise NotFoundError("Submission not found")

    assignment = submission.assignment
    check_teacher_scope(
        db=db,
        user=current_user,
        class_id=assignment.class_id,
        subject_id=assignment.subject_id,
        session_id=assignment.session_id,
        section_id=assignment.section_id
    )

    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    return grade_submission(
        db=db,
        submission_id=submission_id,
        grade_in=grade_in,
        teacher_id=teacher_id,
        user_id=current_user.id
    )
