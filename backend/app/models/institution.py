from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin


class AcademicSession(Base, TimestampMixin):
    __tablename__ = "academic_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g. "2026-2027"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)

    classes = relationship("Class", back_populates="session", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="session", cascade="all, delete-orphan")
    teacher_assignments = relationship("ClassSubjectTeacher", back_populates="session", cascade="all, delete-orphan")


class Class(Base, TimestampMixin):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g. "Grade 10"
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)

    session = relationship("AcademicSession", back_populates="classes")
    sections = relationship("Section", back_populates="class_obj", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="class_obj")
    teacher_assignments = relationship("ClassSubjectTeacher", back_populates="class_obj")

    __table_args__ = (
        UniqueConstraint("name", "session_id", name="uq_class_name_session"),
    )


class Section(Base, TimestampMixin):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # e.g. "A", "B"
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)

    class_obj = relationship("Class", back_populates="sections")
    enrollments = relationship("Enrollment", back_populates="section")
    teacher_assignments = relationship("ClassSubjectTeacher", back_populates="section")

    __table_args__ = (
        UniqueConstraint("name", "class_id", name="uq_section_name_class"),
    )


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g. "MATH101"
    description = Column(Text, nullable=True)

    teacher_assignments = relationship("ClassSubjectTeacher", back_populates="subject")
    attendance_records = relationship("AttendanceRecord", back_populates="subject")
    exams = relationship("Exam", back_populates="subject")
    assignments = relationship("Assignment", back_populates="subject")
    doubts = relationship("DoubtQuestion", back_populates="subject")


class ClassSubject(Base, TimestampMixin):
    """
    Associates subjects directly with a class/grade.
    Allows independent subject configuration per grade.
    """
    __tablename__ = "class_subjects"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)

    class_obj = relationship("Class", backref="class_subject_associations")
    subject = relationship("Subject", backref="class_associations")

    __table_args__ = (
        UniqueConstraint("class_id", "subject_id", name="uq_class_subject"),
    )


class Teacher(Base, TimestampMixin):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    department = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    user = relationship("User", back_populates="teacher_profile")
    assignments_taught = relationship("ClassSubjectTeacher", back_populates="teacher")
    exams_created = relationship("Exam", back_populates="teacher")
    assignments_created = relationship("Assignment", back_populates="teacher")
    announcements = relationship("Announcement", back_populates="teacher")
    doubts_answered = relationship("DoubtQuestion", back_populates="teacher")


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    admission_number = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    gender = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    is_roster_claimed = Column(Boolean, default=False, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)  # R-015 labeling

    user = relationship("User", back_populates="student_profile")
    current_class = relationship("Class", foreign_keys=[class_id])
    current_section = relationship("Section", foreign_keys=[section_id])
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")
    marks = relationship("Mark", back_populates="student", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="student", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="student", cascade="all, delete-orphan")
    recommendations = relationship("StudentRecommendation", back_populates="student", cascade="all, delete-orphan")
    doubts = relationship("DoubtQuestion", back_populates="student", cascade="all, delete-orphan")


class Enrollment(Base, TimestampMixin):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    roll_number = Column(String(50), nullable=True)
    status = Column(String(20), default="active", nullable=False)  # active, withdrawn, graduated

    student = relationship("Student", back_populates="enrollments")
    session = relationship("AcademicSession", back_populates="enrollments")
    class_obj = relationship("Class", back_populates="enrollments")
    section = relationship("Section", back_populates="enrollments")

    __table_args__ = (
        UniqueConstraint("student_id", "session_id", name="uq_enrollment_student_session"),
    )


class ClassSubjectTeacher(Base, TimestampMixin):
    """
    Grants teacher authorization scope over class + section + subject (D-004).
    """
    __tablename__ = "class_subject_teacher"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)

    session = relationship("AcademicSession", back_populates="teacher_assignments")
    class_obj = relationship("Class", back_populates="teacher_assignments")
    section = relationship("Section", back_populates="teacher_assignments")
    subject = relationship("Subject", back_populates="teacher_assignments")
    teacher = relationship("Teacher", back_populates="assignments_taught")

    __table_args__ = (
        UniqueConstraint(
            "session_id", "class_id", "section_id", "subject_id", "teacher_id",
            name="uq_class_subject_teacher"
        ),
    )

