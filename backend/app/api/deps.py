from typing import List, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from backend.app.core.logging import request_id_ctx, user_id_ctx
from backend.app.core.security import decode_token
from backend.app.models.institution import ClassSubjectTeacher, Enrollment, Student, Teacher
from backend.app.models.user import User, UserRole

security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates JWT token and fetches user from database.
    Enforces that user is both active and verified (C-05).
    Injects user_id into logging context and request state (H-01).
    """
    if not credentials or not credentials.credentials:
        raise UnauthorizedError("Authentication token is missing")

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception as e:
        raise UnauthorizedError(str(e))

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type: access token required")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Token missing user subject")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid user subject format")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnauthorizedError("User does not exist")
    if not user.is_active:
        raise UnauthorizedError("User account is inactive")
    if not user.is_verified:
        raise UnauthorizedError("User account is unverified")

    # Set contextvar and request state for structured logging (D-014, H-01)
    user_id_ctx.set(user.id)
    request.state.user_id = user.id
    return user


def require_roles(*allowed_roles: UserRole):
    """
    Role-based access control dependency (R-001, D-004).
    Server-enforces role boundaries.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(f"Action requires one of roles: {[r.value for r in allowed_roles]}")
        return current_user
    return role_checker


require_admin = require_roles(UserRole.ADMINISTRATOR)
require_teacher = require_roles(UserRole.TEACHER)
require_teacher_or_admin = require_roles(UserRole.TEACHER, UserRole.ADMINISTRATOR)
require_student = require_roles(UserRole.STUDENT)


def check_teacher_scope(
    db: Session,
    user: User,
    class_id: int,
    subject_id: int,
    session_id: int,
    section_id: Optional[int] = None
) -> bool:
    """
    Object-level authorization scoping for teachers (D-004, R-004, M-01).
    Validates subject, class, and section assignments.
    Returns 404 on out-of-scope access to prevent ID enumeration.
    """
    if user.role == UserRole.ADMINISTRATOR:
        return True

    if user.role != UserRole.TEACHER or not user.teacher_profile:
        raise NotFoundError("Resource not found or out of scope")

    query = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.teacher_id == user.teacher_profile.id,
        ClassSubjectTeacher.class_id == class_id,
        ClassSubjectTeacher.subject_id == subject_id,
        ClassSubjectTeacher.session_id == session_id
    )

    if section_id is not None:
        # Teacher must have class-wide assignment (section_id is None) OR matching section
        query = query.filter(
            (ClassSubjectTeacher.section_id == section_id) | (ClassSubjectTeacher.section_id.is_(None))
        )

    assignment = query.first()
    if not assignment:
        raise NotFoundError("Resource not found or out of scope")
    return True


def check_teacher_class_scope(
    db: Session,
    user: User,
    class_id: int,
    session_id: Optional[int] = None,
    section_id: Optional[int] = None
) -> bool:
    """
    Verifies that a teacher teaches at least one subject in the given class (C-02, M-01).
    Returns 404 if out of scope.
    """
    if user.role == UserRole.ADMINISTRATOR:
        return True

    if user.role != UserRole.TEACHER or not user.teacher_profile:
        raise NotFoundError("Resource not found or out of scope")

    query = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.teacher_id == user.teacher_profile.id,
        ClassSubjectTeacher.class_id == class_id
    )
    if session_id:
        query = query.filter(ClassSubjectTeacher.session_id == session_id)
    if section_id is not None:
        query = query.filter(
            (ClassSubjectTeacher.section_id == section_id) | (ClassSubjectTeacher.section_id.is_(None))
        )

    has_assignment = query.first()
    if not has_assignment:
        raise NotFoundError("Resource not found or out of scope")
    return True


def get_student_class_section(
    db: Session,
    student_id: int,
    session_id: Optional[int] = None
):
    """Returns (class_id, section_id) effective for the student in the session."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return None, None
    class_id = student.class_id
    section_id = student.section_id
    if session_id:
        enrollment = db.query(Enrollment).filter(
            Enrollment.student_id == student_id,
            Enrollment.session_id == session_id
        ).first()
        if enrollment:
            class_id = enrollment.class_id
            section_id = enrollment.section_id if enrollment.section_id is not None else student.section_id
    return class_id, section_id


def get_teacher_subject_ids(
    db: Session,
    user: User,
    class_id: Optional[int] = None,
    session_id: Optional[int] = None,
    section_id: Optional[int] = None
) -> Optional[set]:
    """
    Subject-level scope helper. Returns None for administrators (unrestricted),
    otherwise the set of subject ids the teacher is assigned to
    (optionally narrowed by class / session / section).
    """
    if user.role == UserRole.ADMINISTRATOR:
        return None
    if user.role != UserRole.TEACHER or not user.teacher_profile:
        return set()
    query = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.teacher_id == user.teacher_profile.id
    )
    if class_id is not None:
        query = query.filter(ClassSubjectTeacher.class_id == class_id)
    if session_id is not None:
        query = query.filter(ClassSubjectTeacher.session_id == session_id)
    if section_id is not None:
        query = query.filter(
            (ClassSubjectTeacher.section_id == section_id) | (ClassSubjectTeacher.section_id.is_(None))
        )
    return {a.subject_id for a in query.all()}


def check_teacher_students_section_scope(
    db: Session,
    user: User,
    student_ids: List[int],
    class_id: int,
    subject_id: Optional[int],
    session_id: int
) -> bool:
    """
    Section-level object authorization for bulk writes (marks / attendance).
    Every student written must sit in a section the teacher is assigned to
    (class-wide assignments cover all sections). Out-of-scope -> 404.
    """
    if user.role == UserRole.ADMINISTRATOR:
        return True
    if user.role != UserRole.TEACHER or not user.teacher_profile:
        raise NotFoundError("Resource not found or out of scope")

    query = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.teacher_id == user.teacher_profile.id,
        ClassSubjectTeacher.class_id == class_id,
        ClassSubjectTeacher.session_id == session_id
    )
    if subject_id is not None:
        query = query.filter(ClassSubjectTeacher.subject_id == subject_id)
    assignments = query.all()
    if not assignments:
        raise NotFoundError("Resource not found or out of scope")
    if any(a.section_id is None for a in assignments):
        return True
    allowed_sections = {a.section_id for a in assignments}
    for sid in student_ids:
        _, sec = get_student_class_section(db, sid, session_id)
        if sec is None or sec not in allowed_sections:
            raise NotFoundError("Resource not found or out of scope")
    return True


def teacher_allowed_sections(
    db: Session,
    user: User,
    class_id: int,
    subject_id: Optional[int],
    session_id: int
) -> Optional[set]:
    """None => all sections allowed (admin or class-wide assignment); else the allowed section ids."""
    if user.role == UserRole.ADMINISTRATOR:
        return None
    if user.role != UserRole.TEACHER or not user.teacher_profile:
        return set()
    query = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.teacher_id == user.teacher_profile.id,
        ClassSubjectTeacher.class_id == class_id,
        ClassSubjectTeacher.session_id == session_id
    )
    if subject_id is not None:
        query = query.filter(ClassSubjectTeacher.subject_id == subject_id)
    assignments = query.all()
    if any(a.section_id is None for a in assignments):
        return None
    return {a.section_id for a in assignments}


def check_student_scope(
    db: Session,
    user: User,
    student_id: int,
    session_id: Optional[int] = None
) -> bool:
    """
    Object-level scoping for student records (C-02, R-007, T-004).
    - Students can ONLY view their own records.
    - Teachers can ONLY view students who belong to classes/sections they teach.
    - Administrators have institutional access.
    Returns 404 on out-of-scope access.
    """
    if user.role == UserRole.ADMINISTRATOR:
        return True

    if user.role == UserRole.STUDENT:
        if not user.student_profile or user.student_profile.id != student_id:
            raise NotFoundError("Resource not found or out of scope")
        return True

    if user.role == UserRole.TEACHER:
        if not user.teacher_profile:
            raise NotFoundError("Resource not found or out of scope")

        # Find student's class and section
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise NotFoundError("Resource not found or out of scope")

        # If session_id provided, check enrollment class/section
        class_id = student.class_id
        section_id = student.section_id
        if session_id:
            enrollment = db.query(Enrollment).filter(
                Enrollment.student_id == student_id,
                Enrollment.session_id == session_id
            ).first()
            if enrollment:
                class_id = enrollment.class_id
                section_id = enrollment.section_id if enrollment.section_id is not None else student.section_id

        # Verify teacher teaches this class and section
        return check_teacher_class_scope(
            db=db,
            user=user,
            class_id=class_id,
            session_id=session_id,
            section_id=section_id
        )

    raise NotFoundError("Resource not found or out of scope")
