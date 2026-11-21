from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    check_teacher_class_scope,
    get_current_user,
    get_db,
    require_admin,
    require_teacher_or_admin,
)
from backend.app.core.exceptions import ForbiddenError, NotFoundError
from backend.app.models.institution import ClassSubjectTeacher, Enrollment, Student
from backend.app.models.user import User, UserRole
from backend.app.schemas.institution import (
    AcademicSessionCreate,
    AcademicSessionResponse,
    ClassCreate,
    ClassResponse,
    EnrollmentCreate,
    EnrollmentResponse,
    SectionCreate,
    SectionResponse,
    StudentResponse,
    StudentRosterImport,
    SubjectCreate,
    SubjectResponse,
    TeacherAssignmentCreate,
    TeacherAssignmentResponse,
    TeacherCreate,
    TeacherResponse,
)
from backend.app.services.institution_service import (
    assign_teacher_to_subject,
    create_class,
    create_section,
    create_session,
    create_subject,
    create_teacher,
    enroll_student,
    get_active_session,
    get_classes,
    get_sections,
    get_sessions,
    get_students,
    get_subjects,
    get_teacher_assignments,
    get_teachers,
    import_student_roster,
)

router = APIRouter(prefix="/institution", tags=["Institution Management"])


# Academic Sessions
@router.post("/sessions", response_model=AcademicSessionResponse)
def api_create_session(
    session_in: AcademicSessionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return create_session(db, session_in, user_id=admin.id)


@router.get("/sessions", response_model=List[AcademicSessionResponse])
def api_get_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_sessions(db)


@router.get("/sessions/active", response_model=Optional[AcademicSessionResponse])
def api_get_active_session(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_active_session(db)


# Classes & Sections
@router.post("/classes", response_model=ClassResponse)
def api_create_class(
    class_in: ClassCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return create_class(db, class_in, user_id=admin.id)


@router.get("/classes", response_model=List[ClassResponse])
def api_get_classes(
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_classes(db, session_id=session_id)


@router.post("/sections", response_model=SectionResponse)
def api_create_section(
    section_in: SectionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return create_section(db, section_in, user_id=admin.id)


@router.get("/classes/{class_id}/sections", response_model=List[SectionResponse])
def api_get_sections(class_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_sections(db, class_id=class_id)


# Subjects
@router.post("/subjects", response_model=SubjectResponse)
def api_create_subject(
    subject_in: SubjectCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return create_subject(db, subject_in, user_id=admin.id)


@router.get("/subjects", response_model=List[SubjectResponse])
def api_get_subjects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_subjects(db)


# Teachers
@router.post("/teachers", response_model=TeacherResponse)
def api_create_teacher(
    teacher_in: TeacherCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return create_teacher(db, teacher_in, admin_user_id=admin.id)


@router.get("/teachers", response_model=List[TeacherResponse])
def api_get_teachers(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return get_teachers(db)


# Students & Roster
@router.post("/roster/import")
def api_import_roster(
    roster_in: StudentRosterImport,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return import_student_roster(db, roster_in.students, admin_user_id=admin.id)


@router.get("/students", response_model=List[StudentResponse])
def api_get_students(
    class_id: Optional[int] = None,
    section_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    C-02: Teachers can only view student rosters for classes they teach.
    """
    if current_user.role == UserRole.TEACHER:
        if class_id:
            check_teacher_class_scope(db=db, user=current_user, class_id=class_id, section_id=section_id)
            return get_students(db, class_id=class_id, section_id=section_id)
        else:
            assignments = db.query(ClassSubjectTeacher).filter(
                ClassSubjectTeacher.teacher_id == current_user.teacher_profile.id
            ).all()
            allowed_class_ids = list(set(a.class_id for a in assignments))
            if not allowed_class_ids:
                return []
            return db.query(Student).filter(Student.class_id.in_(allowed_class_ids)).all()

    return get_students(db, class_id=class_id, section_id=section_id)


# Enrollments
@router.post("/enrollments", response_model=EnrollmentResponse)
def api_enroll_student(
    enroll_in: EnrollmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return enroll_student(db, enroll_in, user_id=admin.id)


# Teacher Assignments
@router.post("/assignments/teachers", response_model=TeacherAssignmentResponse)
def api_assign_teacher(
    assignment_in: TeacherAssignmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return assign_teacher_to_subject(db, assignment_in, user_id=admin.id)


@router.get("/assignments/teachers", response_model=List[TeacherAssignmentResponse])
def api_get_all_teacher_assignments(
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(ClassSubjectTeacher)
    if session_id:
        query = query.filter(ClassSubjectTeacher.session_id == session_id)
    return query.all()


@router.get("/teachers/{teacher_id}/assignments", response_model=List[TeacherAssignmentResponse])
def api_get_teacher_assignments(
    teacher_id: int,
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    C-02: Teachers can only view their own assignment scopes.
    """
    if current_user.role == UserRole.TEACHER:
        if not current_user.teacher_profile or current_user.teacher_profile.id != teacher_id:
            raise ForbiddenError("Teachers can only inspect their own assignment scopes")

    return get_teacher_assignments(db, teacher_id=teacher_id, session_id=session_id)
