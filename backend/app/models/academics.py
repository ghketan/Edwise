from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin


class AttendanceRecord(Base, TimestampMixin):
    """
    Attendance records per student, class, subject, date (API-001, R-004, R-014).
    """
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False)  # present, absent, late, excused
    recorded_by = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    notes = Column(String(255), nullable=True)

    session = relationship("AcademicSession")
    class_obj = relationship("Class")
    section = relationship("Section")
    subject = relationship("Subject", back_populates="attendance_records")
    student = relationship("Student", back_populates="attendance_records")
    teacher = relationship("Teacher")

    __table_args__ = (
        UniqueConstraint("student_id", "session_id", "subject_id", "date", name="uq_attendance_student_sub_date"),
    )


class Exam(Base, TimestampMixin):
    """
    Exams created by teachers within their assigned subject/class (R-005).
    """
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(150), nullable=False)  # e.g., "Unit Test 1", "Midterm"
    exam_type = Column(String(50), default="exam", nullable=False)  # quiz, midterm, final, assignment_test
    date = Column(Date, nullable=False)
    time_slot = Column(String(50), default="09:00 AM - 12:00 PM", nullable=True)
    datesheet_filename = Column(String(255), nullable=True)
    max_marks = Column(Float, nullable=False)
    weightage = Column(Float, default=1.0, nullable=False)

    session = relationship("AcademicSession")
    class_obj = relationship("Class")
    section = relationship("Section")
    subject = relationship("Subject", back_populates="exams")
    teacher = relationship("Teacher", back_populates="exams_created")
    marks = relationship("Mark", back_populates="exam", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("max_marks > 0", name="chk_exam_max_marks_positive"),
    )


class Mark(Base, TimestampMixin):
    """
    Marks entered per student per exam. Nullable score allows distinguishing
    between blank (unrecorded) and zero (R-005, UI-004).
    """
    __tablename__ = "marks"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=True)  # Null if unrecorded/blank; 0 is an actual zero score
    is_absent = Column(Boolean, default=False, nullable=False)
    remarks = Column(String(255), nullable=True)
    entered_by = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)

    exam = relationship("Exam", back_populates="marks")
    student = relationship("Student", back_populates="marks")
    teacher = relationship("Teacher")

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_mark_exam_student"),
        CheckConstraint("score IS NULL OR score >= 0", name="chk_mark_score_non_negative"),
    )


class Assignment(Base, TimestampMixin):
    """
    Assignments created by teachers (R-006).
    """
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    max_points = Column(Float, default=100.0, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)

    session = relationship("AcademicSession")
    class_obj = relationship("Class")
    section = relationship("Section")
    subject = relationship("Subject", back_populates="assignments")
    teacher = relationship("Teacher", back_populates="assignments_created")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")


class Submission(Base, TimestampMixin):
    """
    Submissions made by students and graded by teachers (R-006).
    """
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    content = Column(Text, nullable=True)
    attachment_url = Column(String(500), nullable=True)
    status = Column(String(20), default="submitted", nullable=False)  # submitted, graded, late
    points_awarded = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    graded_by = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    graded_at = Column(DateTime(timezone=True), nullable=True)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("Student", back_populates="submissions")
    teacher = relationship("Teacher")

    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_submission_assignment_student"),
    )


class DoubtQuestion(Base, TimestampMixin):
    """
    Student-to-faculty doubt clearing forum.
    """
    __tablename__ = "doubt_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    answered_by = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False)

    session = relationship("AcademicSession")
    student = relationship("Student", back_populates="doubts")
    subject = relationship("Subject", back_populates="doubts")
    teacher = relationship("Teacher", back_populates="doubts_answered")


class Announcement(Base, TimestampMixin):
    """
    Teacher notice board broadcasts targeted to a class or all classes.
    """
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=True)  # Null = All Classes
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String(20), default="Normal", nullable=False)  # Normal, High

    session = relationship("AcademicSession")
    class_obj = relationship("Class")
    section = relationship("Section")
    teacher = relationship("Teacher", back_populates="announcements")


