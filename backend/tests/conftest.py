import os
import sys
from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Ensure backend is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.main import app
from backend.app.models.academics import AttendanceRecord, Exam, Mark
from backend.app.models.institution import (
    AcademicSession,
    Class,
    ClassSubjectTeacher,
    Enrollment,
    Section,
    Student,
    Subject,
    Teacher,
)
from backend.app.models.recommendations import RecommendationRule
from backend.app.models.user import User, UserRole

# Test database in memory with foreign key enforcement
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Dependency override
    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture
def client(db):
    return TestClient(app)


@pytest.fixture
def test_data(db):
    """Seed test fixtures."""
    # 1. Admin
    admin = User(
        username="test_admin",
        hashed_password=get_password_hash("password123"),
        role=UserRole.ADMINISTRATOR,
        is_active=True,
        is_verified=True
    )
    db.add(admin)

    # 2. Teachers
    t1_user = User(
        username="teacher_1",
        hashed_password=get_password_hash("password123"),
        role=UserRole.TEACHER,
        is_active=True,
        is_verified=True
    )
    t2_user = User(
        username="teacher_2",
        hashed_password=get_password_hash("password123"),
        role=UserRole.TEACHER,
        is_active=True,
        is_verified=True
    )
    db.add_all([t1_user, t2_user])
    db.flush()

    teacher_1 = Teacher(
        employee_id="EMP001",
        full_name="Teacher One",
        user_id=t1_user.id
    )
    teacher_2 = Teacher(
        employee_id="EMP002",
        full_name="Teacher Two",
        user_id=t2_user.id
    )
    db.add_all([teacher_1, teacher_2])

    # 3. Session, Classes, Sections, Subjects
    session = AcademicSession(
        name="2026-Test",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_active=True
    )
    db.add(session)
    db.flush()

    class_1 = Class(name="Class 10", session_id=session.id)
    class_2 = Class(name="Class 11", session_id=session.id)
    db.add_all([class_1, class_2])
    db.flush()

    section_1 = Section(name="A", class_id=class_1.id)
    db.add(section_1)

    subj_math = Subject(name="Math", code="M101")
    subj_sci = Subject(name="Sci", code="S101")
    db.add_all([subj_math, subj_sci])
    db.flush()

    # Teacher 1 assigned to Class 10 Math
    assign_1 = ClassSubjectTeacher(
        session_id=session.id,
        class_id=class_1.id,
        section_id=section_1.id,
        subject_id=subj_math.id,
        teacher_id=teacher_1.id
    )
    db.add(assign_1)

    # 4. Students
    s1_user = User(
        username="STU001",
        hashed_password=get_password_hash("password123"),
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True
    )
    s2_user = User(
        username="STU002",
        hashed_password=get_password_hash("password123"),
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True
    )
    db.add_all([s1_user, s2_user])
    db.flush()

    student_1 = Student(
        admission_number="STU001",
        full_name="Student One",
        user_id=s1_user.id,
        class_id=class_1.id,
        section_id=section_1.id,
        is_roster_claimed=True
    )
    student_2 = Student(
        admission_number="STU002",
        full_name="Student Two",
        user_id=s2_user.id,
        class_id=class_1.id,
        section_id=section_1.id,
        is_roster_claimed=True
    )
    # Unclaimed roster student
    student_unclaimed = Student(
        admission_number="STU999",
        full_name="Unclaimed Student",
        user_id=None,
        class_id=class_1.id,
        section_id=section_1.id,
        is_roster_claimed=False
    )
    db.add_all([student_1, student_2, student_unclaimed])
    db.flush()

    # Enrollments
    enr_1 = Enrollment(student_id=student_1.id, session_id=session.id, class_id=class_1.id, roll_number="01")
    enr_2 = Enrollment(student_id=student_2.id, session_id=session.id, class_id=class_1.id, roll_number="02")
    db.add_all([enr_1, enr_2])

    # Recommendation rule
    rule = RecommendationRule(
        rule_code="TEST_ATT_LOW",
        title="Low Attendance",
        indicator="attendance_rate",
        operator="<",
        threshold_value=75.0,
        severity="high",
        template_message="Attendance is {value}% (< {threshold}%)"
    )
    db.add(rule)

    db.commit()

    return {
        "admin": admin,
        "teacher_1": teacher_1,
        "teacher_2": teacher_2,
        "student_1": student_1,
        "student_2": student_2,
        "student_unclaimed": student_unclaimed,
        "session": session,
        "class_1": class_1,
        "class_2": class_2,
        "section_1": section_1,
        "subj_math": subj_math,
        "subj_sci": subj_sci,
        "user_admin": admin,
        "user_teacher_1": t1_user,
        "user_teacher_2": t2_user,
        "user_student_1": s1_user,
        "user_student_2": s2_user,
    }


def make_token(user: User, student_id=None, teacher_id=None):
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "student_id": student_id,
        "teacher_id": teacher_id
    }
    return create_access_token(payload)
