from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.app.core.security import get_password_hash
from backend.app.models.institution import (
    AcademicSession,
    Class,
    ClassSubject,
    ClassSubjectTeacher,
    Enrollment,
    Section,
    Student,
    Subject,
    Teacher,
)
from backend.app.models.user import User, UserRole
from backend.app.schemas.institution import (
    AcademicSessionCreate,
    AcademicSessionUpdate,
    ClassCreate,
    EnrollmentCreate,
    SectionCreate,
    StudentCreate,
    StudentRosterItem,
    SubjectCreate,
    TeacherAssignmentCreate,
    TeacherCreate,
)
from backend.app.services.audit_service import create_audit_entry


# Academic Session
def create_session(db: Session, session_in: AcademicSessionCreate, user_id: Optional[int] = None) -> AcademicSession:
    existing = db.query(AcademicSession).filter(AcademicSession.name == session_in.name).first()
    if existing:
        raise ConflictError(f"Session with name '{session_in.name}' already exists")
    
    if session_in.is_active:
        # Deactivate all other sessions
        db.query(AcademicSession).update({"is_active": False})

    session = AcademicSession(**session_in.model_dump())
    db.add(session)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="session.created",
        entity_name="academic_session",
        entity_id=session.id,
        new_values=session_in.model_dump(mode="json"),
        reason="Administrative setup"
    )
    db.commit()
    db.refresh(session)
    return session


def get_active_session(db: Session) -> Optional[AcademicSession]:
    return db.query(AcademicSession).filter(AcademicSession.is_active.is_(True)).first()


def get_sessions(db: Session) -> List[AcademicSession]:
    return db.query(AcademicSession).order_by(AcademicSession.start_date.desc()).all()


# Class & Section
def create_class(db: Session, class_in: ClassCreate, user_id: Optional[int] = None) -> Class:
    existing = db.query(Class).filter(
        Class.name == class_in.name,
        Class.session_id == class_in.session_id
    ).first()
    if existing:
        raise ConflictError(f"Class '{class_in.name}' already exists in this session")

    data = class_in.model_dump(exclude={"subject_ids"})
    new_class = Class(**data)
    db.add(new_class)
    db.flush()

    # Link initial subjects if provided
    if class_in.subject_ids:
        for sub_id in class_in.subject_ids:
            cs = ClassSubject(class_id=new_class.id, subject_id=sub_id)
            db.add(cs)
        db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="class.created",
        entity_name="class",
        entity_id=new_class.id,
        new_values=class_in.model_dump(mode="json"),
        reason="Admin added class"
    )
    db.commit()
    db.refresh(new_class)
    return new_class


def get_class_subjects(db: Session, class_id: int) -> List[Subject]:
    """
    Get subjects configured for this class/grade.
    If no explicit ClassSubject links exist, falls back to subjects taught in this class
    via ClassSubjectTeacher, and then to all subjects for backward compatibility.
    """
    explicit = (
        db.query(Subject)
        .join(ClassSubject, ClassSubject.subject_id == Subject.id)
        .filter(ClassSubject.class_id == class_id)
        .all()
    )
    if explicit:
        return explicit

    via_teacher = (
        db.query(Subject)
        .join(ClassSubjectTeacher, ClassSubjectTeacher.subject_id == Subject.id)
        .filter(ClassSubjectTeacher.class_id == class_id)
        .distinct()
        .all()
    )
    if via_teacher:
        return via_teacher

    return db.query(Subject).all()


def assign_subject_to_class(
    db: Session,
    class_id: int,
    subject_id: Optional[int] = None,
    subject_data: Optional[dict] = None,
    user_id: Optional[int] = None
) -> Subject:
    target_class = db.query(Class).filter(Class.id == class_id).first()
    if not target_class:
        raise NotFoundError("Class not found")

    if subject_id:
        sub = db.query(Subject).filter(Subject.id == subject_id).first()
        if not sub:
            raise NotFoundError("Subject not found")
    elif subject_data:
        existing = db.query(Subject).filter(Subject.code == subject_data.get("code")).first()
        if existing:
            sub = existing
        else:
            sub = Subject(
                name=subject_data["name"],
                code=subject_data["code"].upper(),
                description=subject_data.get("description")
            )
            db.add(sub)
            db.flush()
    else:
        raise ValidationError("Either subject_id or subject details must be provided")

    link = db.query(ClassSubject).filter(
        ClassSubject.class_id == class_id,
        ClassSubject.subject_id == sub.id
    ).first()
    if not link:
        link = ClassSubject(class_id=class_id, subject_id=sub.id)
        db.add(link)
        db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="class_subject.assigned",
        entity_name="class_subject",
        entity_id=link.id,
        new_values={"class_id": class_id, "subject_id": sub.id, "subject_name": sub.name},
        reason="Assigned subject to class"
    )
    db.commit()
    db.refresh(sub)
    return sub


def remove_subject_from_class(db: Session, class_id: int, subject_id: int, user_id: Optional[int] = None):
    link = db.query(ClassSubject).filter(
        ClassSubject.class_id == class_id,
        ClassSubject.subject_id == subject_id
    ).first()
    if link:
        db.delete(link)
        create_audit_entry(
            db=db,
            user_id=user_id,
            action="class_subject.removed",
            entity_name="class_subject",
            entity_id=link.id,
            old_values={"class_id": class_id, "subject_id": subject_id},
            reason="Removed subject from class"
        )
        db.commit()
    return {"status": "success", "message": "Subject removed from class"}


def get_classes(db: Session, session_id: Optional[int] = None) -> List[Class]:
    query = db.query(Class)
    if session_id:
        query = query.filter(Class.session_id == session_id)
    return query.all()


def create_section(db: Session, section_in: SectionCreate, user_id: Optional[int] = None) -> Section:
    existing = db.query(Section).filter(
        Section.name == section_in.name,
        Section.class_id == section_in.class_id
    ).first()
    if existing:
        raise ConflictError(f"Section '{section_in.name}' already exists in this class")

    section = Section(**section_in.model_dump())
    db.add(section)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="section.created",
        entity_name="section",
        entity_id=section.id,
        new_values=section_in.model_dump(mode="json"),
        reason="Admin added section"
    )
    db.commit()
    db.refresh(section)
    return section


def get_sections(db: Session, class_id: int) -> List[Section]:
    return db.query(Section).filter(Section.class_id == class_id).all()


# Subject
def create_subject(db: Session, subject_in: SubjectCreate, user_id: Optional[int] = None) -> Subject:
    existing = db.query(Subject).filter(Subject.code == subject_in.code).first()
    if existing:
        raise ConflictError(f"Subject with code '{subject_in.code}' already exists")

    subject = Subject(**subject_in.model_dump())
    db.add(subject)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="subject.created",
        entity_name="subject",
        entity_id=subject.id,
        new_values=subject_in.model_dump(mode="json"),
        reason="Admin added subject"
    )
    db.commit()
    db.refresh(subject)
    return subject


def get_subjects(db: Session) -> List[Subject]:
    return db.query(Subject).all()


# Teacher
def create_teacher(db: Session, teacher_in: TeacherCreate, admin_user_id: Optional[int] = None) -> Teacher:
    existing = db.query(Teacher).filter(Teacher.employee_id == teacher_in.employee_id).first()
    if existing:
        raise ConflictError(f"Teacher with employee ID '{teacher_in.employee_id}' already exists")

    created_user_id = teacher_in.user_id
    if teacher_in.create_user_account and not created_user_id:
        user_pwd = teacher_in.initial_password or "Teacher@123"
        user = User(
            username=teacher_in.employee_id,
            email=str(teacher_in.email) if teacher_in.email else None,
            hashed_password=get_password_hash(user_pwd),
            role=UserRole.TEACHER,
            is_active=True,
            is_verified=True
        )
        db.add(user)
        db.flush()
        created_user_id = user.id

    teacher_data = teacher_in.model_dump(exclude={"create_user_account", "initial_password", "user_id"})
    teacher = Teacher(**teacher_data, user_id=created_user_id)
    db.add(teacher)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=admin_user_id,
        action="teacher.created",
        entity_name="teacher",
        entity_id=teacher.id,
        new_values={"employee_id": teacher.employee_id, "full_name": teacher.full_name},
        reason="Admin added teacher"
    )
    db.commit()
    db.refresh(teacher)
    return teacher


def get_teachers(db: Session) -> List[Teacher]:
    return db.query(Teacher).all()


# Student Roster Import
def import_student_roster(
    db: Session,
    roster: List[StudentRosterItem],
    admin_user_id: Optional[int] = None
) -> dict:
    """
    Admin imports a student roster (admission number, full name, class, section) (D-006, UI-002).
    """
    imported = 0
    skipped = 0
    errors = []

    for item in roster:
        # Check existing admission number
        existing = db.query(Student).filter(Student.admission_number == item.admission_number).first()
        if existing:
            skipped += 1
            continue

        student = Student(
            admission_number=item.admission_number,
            full_name=item.full_name,
            class_id=item.class_id,
            section_id=item.section_id,
            gender=item.gender,
            contact_email=item.contact_email,
            contact_phone=item.contact_phone,
            is_roster_claimed=False,
            is_synthetic=False
        )
        db.add(student)
        imported += 1

    create_audit_entry(
        db=db,
        user_id=admin_user_id,
        action="roster.imported",
        entity_name="student",
        new_values={"imported_count": imported, "skipped_count": skipped},
        reason="Admin imported student roster"
    )
    db.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors}


def get_students(db: Session, class_id: Optional[int] = None, section_id: Optional[int] = None) -> List[Student]:
    query = db.query(Student)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    if section_id:
        query = query.filter(Student.section_id == section_id)
    return query.all()


# Enrollment
def enroll_student(db: Session, enroll_in: EnrollmentCreate, user_id: Optional[int] = None) -> Enrollment:
    existing = db.query(Enrollment).filter(
        Enrollment.student_id == enroll_in.student_id,
        Enrollment.session_id == enroll_in.session_id
    ).first()
    if existing:
        raise ConflictError("Student is already enrolled in this academic session")

    enrollment = Enrollment(**enroll_in.model_dump())
    db.add(enrollment)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="student.enrolled",
        entity_name="enrollment",
        entity_id=enrollment.id,
        new_values=enroll_in.model_dump(mode="json"),
        reason="Admin enrolled student"
    )
    db.commit()
    db.refresh(enrollment)
    return enrollment


# ClassSubjectTeacher Assignment
def assign_teacher_to_subject(
    db: Session,
    assignment_in: TeacherAssignmentCreate,
    user_id: Optional[int] = None
) -> ClassSubjectTeacher:
    existing = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.session_id == assignment_in.session_id,
        ClassSubjectTeacher.class_id == assignment_in.class_id,
        ClassSubjectTeacher.section_id == assignment_in.section_id,
        ClassSubjectTeacher.subject_id == assignment_in.subject_id,
        ClassSubjectTeacher.teacher_id == assignment_in.teacher_id,
    ).first()
    if existing:
        raise ConflictError("Teacher assignment already exists for this combination")

    assignment = ClassSubjectTeacher(**assignment_in.model_dump())
    db.add(assignment)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="teacher_assignment.created",
        entity_name="class_subject_teacher",
        entity_id=assignment.id,
        new_values=assignment_in.model_dump(mode="json"),
        reason="Admin assigned teacher to subject"
    )
    db.commit()
    db.refresh(assignment)
    return assignment


def get_teacher_assignments(db: Session, teacher_id: int, session_id: Optional[int] = None) -> List[ClassSubjectTeacher]:
    query = db.query(ClassSubjectTeacher).filter(ClassSubjectTeacher.teacher_id == teacher_id)
    if session_id:
        query = query.filter(ClassSubjectTeacher.session_id == session_id)
    return query.all()

