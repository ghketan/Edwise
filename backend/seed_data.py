import os
import sys
from datetime import date, datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.core.database import Base, SessionLocal, engine
from backend.app.core.security import get_password_hash
from backend.app.ml_engine.trainer import train_and_save_artifacts
from backend.app.models.academics import (
    Announcement,
    Assignment,
    AttendanceRecord,
    DoubtQuestion,
    Exam,
    Mark,
    Submission,
)
from backend.app.models.audit import AuditLog
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
from backend.app.models.ml import ModelRegistry
from backend.app.models.recommendations import RecommendationRule, StudentRecommendation
from backend.app.models.user import User, UserRole


def seed_database():
    print("Beginning EDWISE database seeding...")
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            from sqlalchemy import text
            res_exams = conn.execute(text("PRAGMA table_info(exams)")).fetchall()
            exam_cols = [r[1] for r in res_exams]
            if exam_cols and "time_slot" not in exam_cols:
                conn.execute(text("ALTER TABLE exams ADD COLUMN time_slot VARCHAR(50) DEFAULT '09:00 AM - 12:00 PM'"))
            if exam_cols and "datesheet_filename" not in exam_cols:
                conn.execute(text("ALTER TABLE exams ADD COLUMN datesheet_filename VARCHAR(255)"))
    except Exception as e:
        print(f"Migration note: {e}")
    db = SessionLocal()

    try:
        # 1. Admin User
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@edwise.internal",
                hashed_password=get_password_hash("Admin@123"),
                role=UserRole.ADMINISTRATOR,
                is_active=True,
                is_verified=True
            )
            db.add(admin_user)
            db.flush()
            print("Created Admin user: admin / Admin@123")

        # 2. Academic Session
        session = db.query(AcademicSession).filter(AcademicSession.name == "2026-2027").first()
        if not session:
            session = AcademicSession(
                name="2026-2027",
                start_date=date(2026, 6, 1),
                end_date=date(2027, 4, 30),
                is_active=True
            )
            db.add(session)
            db.flush()
            print("Created Active Session: 2026-2027")

        # 3. Classes and Sections
        class_10 = db.query(Class).filter(Class.name == "Grade 10", Class.session_id == session.id).first()
        if not class_10:
            class_10 = Class(name="Grade 10", session_id=session.id)
            db.add(class_10)
            db.flush()

        section_a = db.query(Section).filter(Section.name == "A", Section.class_id == class_10.id).first()
        if not section_a:
            section_a = Section(name="A", class_id=class_10.id)
            db.add(section_a)
            db.flush()

        section_b = db.query(Section).filter(Section.name == "B", Section.class_id == class_10.id).first()
        if not section_b:
            section_b = Section(name="B", class_id=class_10.id)
            db.add(section_b)
            db.flush()

        # 4. Subjects
        subjects_data = [
            ("Mathematics", "MATH101", "Core high-school algebra and geometry"),
            ("Science", "SCI101", "Physics, Chemistry and Biology foundation"),
            ("English", "ENG101", "Language and literary analysis"),
            ("History", "HIST101", "World and national history"),
        ]
        created_subjects = {}
        for name, code, desc in subjects_data:
            sub = db.query(Subject).filter(Subject.code == code).first()
            if not sub:
                sub = Subject(name=name, code=code, description=desc)
                db.add(sub)
                db.flush()
            created_subjects[code] = sub

        # 5. Teachers & User Accounts
        # Teacher 1: Sarah
        t1_user = db.query(User).filter(User.username == "teacher_sarah").first()
        if not t1_user:
            t1_user = User(
                username="teacher_sarah",
                email="sarah.jenkins@edwise.internal",
                hashed_password=get_password_hash("Teacher@123"),
                role=UserRole.TEACHER,
                is_active=True,
                is_verified=True
            )
            db.add(t1_user)
            db.flush()

        teacher_sarah = db.query(Teacher).filter(Teacher.employee_id == "T101").first()
        if not teacher_sarah:
            teacher_sarah = Teacher(
                employee_id="T101",
                full_name="Dr. Sarah Jenkins",
                user_id=t1_user.id,
                department="Mathematics",
                email="sarah.jenkins@edwise.internal"
            )
            db.add(teacher_sarah)
            db.flush()
            print("Created Teacher user: teacher_sarah / Teacher@123")

        # Teacher 2: Alan
        t2_user = db.query(User).filter(User.username == "teacher_alan").first()
        if not t2_user:
            t2_user = User(
                username="teacher_alan",
                email="alan.smith@edwise.internal",
                hashed_password=get_password_hash("Teacher@123"),
                role=UserRole.TEACHER,
                is_active=True,
                is_verified=True
            )
            db.add(t2_user)
            db.flush()

        teacher_alan = db.query(Teacher).filter(Teacher.employee_id == "T102").first()
        if not teacher_alan:
            teacher_alan = Teacher(
                employee_id="T102",
                full_name="Prof. Alan Smith",
                user_id=t2_user.id,
                department="Science",
                email="alan.smith@edwise.internal"
            )
            db.add(teacher_alan)
            db.flush()
            print("Created Teacher user: teacher_alan / Teacher@123")

        # 6. Teacher Scope Assignments (ClassSubjectTeacher)
        # Sarah teaches Math to Grade 10 A
        cst_math = db.query(ClassSubjectTeacher).filter(
            ClassSubjectTeacher.session_id == session.id,
            ClassSubjectTeacher.class_id == class_10.id,
            ClassSubjectTeacher.section_id == section_a.id,
            ClassSubjectTeacher.subject_id == created_subjects["MATH101"].id,
            ClassSubjectTeacher.teacher_id == teacher_sarah.id
        ).first()
        if not cst_math:
            cst_math = ClassSubjectTeacher(
                session_id=session.id,
                class_id=class_10.id,
                section_id=section_a.id,
                subject_id=created_subjects["MATH101"].id,
                teacher_id=teacher_sarah.id
            )
            db.add(cst_math)

        # Alan teaches Science to Grade 10 A
        cst_sci = db.query(ClassSubjectTeacher).filter(
            ClassSubjectTeacher.session_id == session.id,
            ClassSubjectTeacher.class_id == class_10.id,
            ClassSubjectTeacher.section_id == section_a.id,
            ClassSubjectTeacher.subject_id == created_subjects["SCI101"].id,
            ClassSubjectTeacher.teacher_id == teacher_alan.id
        ).first()
        if not cst_sci:
            cst_sci = ClassSubjectTeacher(
                session_id=session.id,
                class_id=class_10.id,
                section_id=section_a.id,
                subject_id=created_subjects["SCI101"].id,
                teacher_id=teacher_alan.id
            )
            db.add(cst_sci)
        db.flush()

        # 7. Student Roster, Claimed Accounts, and Enrollments
        # Synthetic demo students (R-015)
        students_roster = [
            ("STU1001", "Alex Carter", "alex.carter@student.edwise.internal", True),
            ("STU1002", "Priya Sharma", "priya.sharma@student.edwise.internal", True),
            ("STU1003", "David Miller", "david.miller@student.edwise.internal", False), # unclaimed roster
            ("STU1004", "Emma Watson", "emma.watson@student.edwise.internal", False),
            ("STU1005", "Lucas Silva", "lucas.silva@student.edwise.internal", False),
            ("STU1006", "Aisha Khan", "aisha.khan@student.edwise.internal", False),
        ]

        created_students = []
        for idx, (adm_no, name, email, should_claim) in enumerate(students_roster, 1):
            student = db.query(Student).filter(Student.admission_number == adm_no).first()
            if not student:
                user_id = None
                if should_claim:
                    s_user = db.query(User).filter(User.username == adm_no).first()
                    if not s_user:
                        s_user = User(
                            username=adm_no,
                            email=email,
                            hashed_password=get_password_hash("Student@123"),
                            role=UserRole.STUDENT,
                            is_active=True,
                            is_verified=True
                        )
                        db.add(s_user)
                        db.flush()
                    user_id = s_user.id

                student = Student(
                    admission_number=adm_no,
                    full_name=name,
                    user_id=user_id,
                    class_id=class_10.id,
                    section_id=section_a.id,
                    contact_email=email,
                    is_roster_claimed=should_claim,
                    is_synthetic=True
                )
                db.add(student)
                db.flush()

                # Enroll in session
                enrollment = Enrollment(
                    student_id=student.id,
                    session_id=session.id,
                    class_id=class_10.id,
                    section_id=section_a.id,
                    roll_number=f"10A-{idx:02d}",
                    status="active"
                )
                db.add(enrollment)
                db.flush()

            created_students.append(student)

        print(f"Created {len(created_students)} student roster records.")

        # 8. Attendance Records (10 days of classes)
        base_date = date(2026, 10, 1)
        for day_offset in range(10):
            att_date = base_date + timedelta(days=day_offset)
            if att_date.weekday() >= 5:  # skip weekends
                continue

            for st in created_students:
                for sub_code in ["MATH101", "SCI101"]:
                    sub_id = created_subjects[sub_code].id
                    existing_att = db.query(AttendanceRecord).filter(
                        AttendanceRecord.student_id == st.id,
                        AttendanceRecord.session_id == session.id,
                        AttendanceRecord.subject_id == sub_id,
                        AttendanceRecord.date == att_date
                    ).first()

                    if not existing_att:
                        # Alex and Priya have high attendance; David has sporadic
                        if st.admission_number in ("STU1001", "STU1002"):
                            st_status = "present"
                        elif st.admission_number == "STU1003":
                            st_status = "absent" if day_offset % 2 == 0 else "present"
                        else:
                            st_status = "present" if day_offset % 3 != 0 else "absent"

                        teacher_recorder = teacher_sarah.id if sub_code == "MATH101" else teacher_alan.id
                        att_rec = AttendanceRecord(
                            session_id=session.id,
                            class_id=class_10.id,
                            section_id=section_a.id,
                            subject_id=sub_id,
                            student_id=st.id,
                            date=att_date,
                            status=st_status,
                            recorded_by=teacher_recorder
                        )
                        db.add(att_rec)

        db.flush()
        print("Populated multi-day attendance records.")

        # 9. Exams and Marks
        # Exam 1: Unit Test 1 (Math)
        exam_1 = db.query(Exam).filter(Exam.name == "Unit Test 1 - Algebra").first()
        if not exam_1:
            exam_1 = Exam(
                session_id=session.id,
                class_id=class_10.id,
                section_id=section_a.id,
                subject_id=created_subjects["MATH101"].id,
                teacher_id=teacher_sarah.id,
                name="Unit Test 1 - Algebra",
                exam_type="quiz",
                date=date(2026, 9, 20),
                max_marks=50.0,
                weightage=1.0
            )
            db.add(exam_1)
            db.flush()

        # Exam 2: Midterm Exam (Math)
        exam_2 = db.query(Exam).filter(Exam.name == "Midterm Examination - Mathematics").first()
        if not exam_2:
            exam_2 = Exam(
                session_id=session.id,
                class_id=class_10.id,
                section_id=section_a.id,
                subject_id=created_subjects["MATH101"].id,
                teacher_id=teacher_sarah.id,
                name="Midterm Examination - Mathematics",
                exam_type="midterm",
                date=date(2026, 10, 25),
                max_marks=100.0,
                weightage=2.0
            )
            db.add(exam_2)
            db.flush()

        # Seed scores
        # Alex Carter: 44/50 (88%), 89/100 (89%)
        # Priya Sharma: 48/50 (96%), 95/100 (95%)
        # David Miller: 24/50 (48%), 38/100 (38% - at risk)
        student_scores = {
            "STU1001": (44.0, 89.0),
            "STU1002": (48.0, 95.0),
            "STU1003": (24.0, 38.0),
            "STU1004": (35.0, 72.0),
            "STU1005": (38.0, 78.0),
            "STU1006": (40.0, 82.0),
        }

        for st in created_students:
            scores = student_scores.get(st.admission_number, (35.0, 70.0))
            
            # Exam 1 mark
            m1 = db.query(Mark).filter(Mark.exam_id == exam_1.id, Mark.student_id == st.id).first()
            if not m1:
                db.add(Mark(
                    exam_id=exam_1.id,
                    student_id=st.id,
                    score=scores[0],
                    is_absent=False,
                    entered_by=teacher_sarah.id
                ))

            # Exam 2 mark
            m2 = db.query(Mark).filter(Mark.exam_id == exam_2.id, Mark.student_id == st.id).first()
            if not m2:
                db.add(Mark(
                    exam_id=exam_2.id,
                    student_id=st.id,
                    score=scores[1],
                    is_absent=False,
                    entered_by=teacher_sarah.id
                ))

        db.flush()
        print("Populated exams and student marks.")

        # 10. Assignments
        assignment = db.query(Assignment).filter(Assignment.title == "Quadratic Equations Problem Set").first()
        if not assignment:
            assignment = Assignment(
                session_id=session.id,
                class_id=class_10.id,
                section_id=section_a.id,
                subject_id=created_subjects["MATH101"].id,
                teacher_id=teacher_sarah.id,
                title="Quadratic Equations Problem Set",
                description="Complete exercises 1 to 15 from Chapter 4.",
                max_points=50.0,
                due_date=datetime.now(timezone.utc) + timedelta(days=7)
            )
            db.add(assignment)
            db.flush()

            # Add submission for Alex
            alex_student = created_students[0]
            submission = Submission(
                assignment_id=assignment.id,
                student_id=alex_student.id,
                content="Here are my completed solutions for exercises 1 to 15.",
                status="graded",
                points_awarded=48.0,
                feedback="Excellent work on the quadratic formula derivation.",
                graded_by=teacher_sarah.id,
                graded_at=datetime.now(timezone.utc)
            )
            db.add(submission)
            db.flush()
            print("Populated assignment and graded submission.")

        # 11. Recommendation Rules (R-012, D-008)
        rules_data = [
            (
                "REC_ATTENDANCE_LOW",
                "Low Attendance Warning",
                "attendance_rate",
                "<",
                75.0,
                "high",
                "Student attendance is {value}%, which has fallen below the 75% required minimum."
            ),
            (
                "REC_SCORE_DROP",
                "Performance Drop Alert",
                "score_drop",
                ">",
                15.0,
                "medium",
                "Assessment score dropped by {value}% across sequential exams."
            ),
            (
                "REC_MISSING_ASSIGNMENTS",
                "Unsubmitted Assignments",
                "missing_assignments",
                ">=",
                2.0,
                "medium",
                "Student has {value} unsubmitted assignments requiring follow-up."
            ),
        ]
        for r_code, r_title, r_ind, r_op, r_thresh, r_sev, r_tmpl in rules_data:
            rule = db.query(RecommendationRule).filter(RecommendationRule.rule_code == r_code).first()
            if not rule:
                rule = RecommendationRule(
                    rule_code=r_code,
                    title=r_title,
                    indicator=r_ind,
                    operator=r_op,
                    threshold_value=r_thresh,
                    severity=r_sev,
                    template_message=r_tmpl,
                    is_active=True
                )
                db.add(rule)
        db.flush()
        print("Populated recommendation rules.")

        # 12. Train and Register ML Models (D-005, R-015)
        print("Training baseline ML models and registering in model_registry...")
        meta = train_and_save_artifacts()

        for task_name, task_data in meta.items():
            existing_reg = db.query(ModelRegistry).filter(ModelRegistry.version == task_data["version"]).first()
            if not existing_reg:
                new_reg = ModelRegistry(
                    model_name=task_data["model_name"],
                    version=task_data["version"],
                    task=task_data["task"],
                    data_source=task_data["data_source"],
                    is_synthetic=task_data["is_synthetic"],
                    feature_list=task_data["features"],
                    split_method=task_data["split_method"],
                    metrics=task_data["metrics"],
                    artifact_path=task_data["artifact_path"],
                    is_active=(task_data["task"] != "regression" or task_name == "regression"),
                    trained_by="seed_script"
                )
                db.add(new_reg)
        db.flush()
        print("Registered ML models in database.")

        # 13. Seed Announcements
        if not db.query(Announcement).filter(Announcement.session_id == session.id).first():
            ann1 = Announcement(
                session_id=session.id,
                class_id=None,
                teacher_id=teacher_sarah.id if 'teacher_sarah' in locals() else None,
                title="Mid-Term Examination Datesheet Released",
                content="The finalized datesheet for upcoming term evaluations is now uploaded. Please review time slots and download your copy.",
                priority="High"
            )
            ann2 = Announcement(
                session_id=session.id,
                class_id=class_10.id,
                teacher_id=teacher_sarah.id if 'teacher_sarah' in locals() else None,
                title="Mathematics Remedial & Problem Solving Clinic",
                content="Extra revision session this Wednesday at 3:00 PM in Room 204 covering quadratic equations and exam problem sets.",
                priority="Normal"
            )
            db.add_all([ann1, ann2])
            db.flush()
            print("Populated class notices and announcements.")

        # 14. Seed Doubt Questions
        if not db.query(DoubtQuestion).filter(DoubtQuestion.session_id == session.id).first():
            stu1 = db.query(Student).filter(Student.admission_number == "STU1001").first()
            math_sub = created_subjects.get("MATH101")
            sci_sub = created_subjects.get("SCI101")
            if stu1 and math_sub:
                d1 = DoubtQuestion(
                    session_id=session.id,
                    student_id=stu1.id,
                    subject_id=math_sub.id,
                    question="Can you please explain quadratic factorisation using the quadratic root formula?",
                    answer="Sure Alex! When D = b^2 - 4ac >= 0, roots are (-b +- sqrt(D))/(2a). We will review practice problems in Wednesday's clinic.",
                    answered_by=teacher_sarah.id if 'teacher_sarah' in locals() else None,
                    answered_at=datetime.now(timezone.utc),
                    is_resolved=True
                )
                db.add(d1)
            if stu1 and sci_sub:
                d2 = DoubtQuestion(
                    session_id=session.id,
                    student_id=stu1.id,
                    subject_id=sci_sub.id,
                    question="What chapters and experiment setups are covered in next week's practical assessment?",
                    is_resolved=False
                )
                db.add(d2)
            db.flush()
            print("Populated student doubts and teacher answers.")

        db.commit()
        print("\n=== EDWISE Database Seeding Completed Successfully! ===")
        print("Default accounts:")
        print("  Administrator: admin / Admin@123")
        print("  Teacher:       teacher_sarah / Teacher@123")
        print("  Teacher:       teacher_alan / Teacher@123")
        print("  Student:       STU1001 / Student@123")
        print("  Student:       STU1002 / Student@123")
        print("  Unclaimed Roster: STU1003 (David Miller, Class 10)")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

