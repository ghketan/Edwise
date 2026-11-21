from datetime import date, timedelta
import pytest
from backend.app.core.config import settings
from backend.app.core.security import get_password_hash
from backend.app.models.academics import AttendanceRecord, Exam, Mark
from backend.app.models.audit import AuditLog
from backend.app.models.institution import ClassSubjectTeacher, Enrollment, Section, Student
from backend.app.models.user import User, UserRole
from backend.tests.conftest import make_token


# ==============================================================================
# F1: Doubts API Tests
# ==============================================================================
def test_doubts_lifecycle_and_rbac(client, test_data):
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    s2_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_2'], student_id=test_data['student_2'].id)}"}
    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}

    # 1. Student 1 creates a doubt
    resp = client.post(
        "/api/v1/doubts",
        json={
            "session_id": test_data["session"].id,
            "subject_id": test_data["subj_math"].id,
            "question": "  How do I solve quadratic equations by completing the square?  ",
        },
        headers=s1_headers,
    )
    assert resp.status_code == 200
    doubt = resp.json()
    assert doubt["is_resolved"] is False
    assert doubt["answered_by"] is None
    assert doubt["answered_by_name"] is None
    assert doubt["question"] == "How do I solve quadratic equations by completing the square?"
    doubt_id = doubt["id"]

    # 2. Student 2 cannot see Student 1's doubt
    s2_list = client.get(f"/api/v1/doubts?session_id={test_data['session'].id}", headers=s2_headers)
    assert s2_list.status_code == 200
    assert all(d["id"] != doubt_id for d in s2_list.json())

    # 3. Teacher cannot create a doubt (403)
    t_create = client.post(
        "/api/v1/doubts",
        json={
            "session_id": test_data["session"].id,
            "subject_id": test_data["subj_math"].id,
            "question": "Teacher asking question",
        },
        headers=t1_headers,
    )
    assert t_create.status_code == 403

    # 4. Student cannot answer a doubt (403)
    s_ans = client.post(f"/api/v1/doubts/{doubt_id}/answer", json={"answer": "Self answer"}, headers=s1_headers)
    assert s_ans.status_code == 403

    # 5. Teacher 1 lists & answers doubt
    t_list = client.get(
        f"/api/v1/doubts?session_id={test_data['session'].id}&subject_id={test_data['subj_math'].id}",
        headers=t1_headers,
    )
    assert t_list.status_code == 200
    assert any(d["id"] == doubt_id for d in t_list.json())

    ans_resp = client.post(
        f"/api/v1/doubts/{doubt_id}/answer",
        json={"answer": "  Divide by leading coefficient and add (b/2a)^2 to both sides.  "},
        headers=t1_headers,
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data["is_resolved"] is True
    assert ans_data["answered_by"] == test_data["teacher_1"].id
    assert ans_data["answered_by_name"] == test_data["teacher_1"].full_name
    assert ans_data["answer"] == "Divide by leading coefficient and add (b/2a)^2 to both sides."


def test_doubts_admin_answer_no_misattribution_and_validation(client, db, test_data):
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}

    # Unlinked student user (student_profile=None)
    unlinked_user = User(
        username="unlinked_student_doubts",
        hashed_password=get_password_hash("password123"),
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True,
    )
    db.add(unlinked_user)
    db.commit()
    unlinked_headers = {"Authorization": f"Bearer {make_token(unlinked_user)}"}

    # Create doubt as Student 1
    d_resp = client.post(
        "/api/v1/doubts",
        json={
            "session_id": test_data["session"].id,
            "subject_id": test_data["subj_math"].id,
            "question": "Need help with trigonometry identities",
        },
        headers=s1_headers,
    )
    assert d_resp.status_code == 200
    doubt_id = d_resp.json()["id"]

    # Unlinked student sees [] (does not leak Student 1's doubt)
    leak_check = client.get(f"/api/v1/doubts?session_id={test_data['session'].id}", headers=unlinked_headers)
    assert leak_check.status_code == 200
    assert leak_check.json() == []

    # Admin answers doubt -> answered_by must be None (not 1!)
    admin_ans = client.post(
        f"/api/v1/doubts/{doubt_id}/answer",
        json={"answer": "Start from sin^2(x) + cos^2(x) = 1."},
        headers=admin_headers,
    )
    assert admin_ans.status_code == 200
    ans_data = admin_ans.json()
    assert ans_data["answered_by"] is None
    assert ans_data["answered_by_name"] == "Administration"
    assert ans_data["is_resolved"] is True

    # Whitespace-only question/answer rejected with 422
    assert client.post(
        "/api/v1/doubts",
        json={
            "session_id": test_data["session"].id,
            "subject_id": test_data["subj_math"].id,
            "question": "   \t  ",
        },
        headers=s1_headers,
    ).status_code == 422

    assert client.post(
        f"/api/v1/doubts/{doubt_id}/answer",
        json={"answer": "   "},
        headers=admin_headers,
    ).status_code == 422

    # Missing FK -> 404 (not 500 IntegrityError)
    assert client.post(
        "/api/v1/doubts",
        json={
            "session_id": 99999,
            "subject_id": test_data["subj_math"].id,
            "question": "Valid question?",
        },
        headers=s1_headers,
    ).status_code == 404

    assert client.post(
        "/api/v1/doubts",
        json={
            "session_id": test_data["session"].id,
            "subject_id": 99999,
            "question": "Valid question?",
        },
        headers=s1_headers,
    ).status_code == 404

    assert client.post(
        "/api/v1/doubts/99999/answer",
        json={"answer": "Valid answer"},
        headers=admin_headers,
    ).status_code == 404


# ==============================================================================
# F2: Announcements API Tests
# ==============================================================================
def test_announcements_crud_targeting_and_rbac(client, db, test_data):
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}
    t2_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_2'], teacher_id=test_data['teacher_2'].id)}"}
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}

    unlinked_user = User(
        username="unlinked_student_ann",
        hashed_password=get_password_hash("password123"),
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True,
    )
    db.add(unlinked_user)
    db.commit()
    unlinked_headers = {"Authorization": f"Bearer {make_token(unlinked_user)}"}

    # Teacher 1 creates Class 10 announcement
    r_c1 = client.post(
        "/api/v1/announcements",
        json={
            "session_id": test_data["session"].id,
            "class_id": test_data["class_1"].id,
            "title": "Math Test Reminder",
            "content": "Bring geometry kits tomorrow.",
            "priority": "high",
        },
        headers=t1_headers,
    )
    assert r_c1.status_code == 200
    assert r_c1.json()["priority"] == "High"
    ann_c1_id = r_c1.json()["id"]

    # Teacher 1 cannot create announcement for unassigned Class 11 (404)
    r_forbidden_class = client.post(
        "/api/v1/announcements",
        json={
            "session_id": test_data["session"].id,
            "class_id": test_data["class_2"].id,
            "title": "Unauthorized Class Notice",
            "content": "Should fail.",
            "priority": "Normal",
        },
        headers=t1_headers,
    )
    assert r_forbidden_class.status_code == 404

    # Admin creates global announcement and Class 11 announcement
    r_global = client.post(
        "/api/v1/announcements",
        json={
            "session_id": test_data["session"].id,
            "class_id": None,
            "title": "School Assembly",
            "content": "Friday 8:30 AM in the main hall.",
            "priority": "normal",
        },
        headers=admin_headers,
    )
    assert r_global.status_code == 200
    assert r_global.json()["teacher_name"] == "Administration"
    assert r_global.json()["priority"] == "Normal"
    ann_global_id = r_global.json()["id"]

    r_c2 = client.post(
        "/api/v1/announcements",
        json={
            "session_id": test_data["session"].id,
            "class_id": test_data["class_2"].id,
            "title": "Class 11 Lab",
            "content": "Physics lab rescheduled.",
            "priority": "Normal",
        },
        headers=admin_headers,
    )
    assert r_c2.status_code == 200
    ann_c2_id = r_c2.json()["id"]

    # Student 1 (Class 10) sees Class 10 + global, NOT Class 11 (even if ?class_id=class_2 passed)
    s1_list = client.get(
        f"/api/v1/announcements?session_id={test_data['session'].id}&class_id={test_data['class_2'].id}",
        headers=s1_headers,
    )
    assert s1_list.status_code == 200
    s1_ids = {a["id"] for a in s1_list.json()}
    assert ann_c1_id in s1_ids
    assert ann_global_id in s1_ids
    assert ann_c2_id not in s1_ids

    # Unlinked student gets []
    assert client.get(
        f"/api/v1/announcements?session_id={test_data['session'].id}&class_id={test_data['class_1'].id}",
        headers=unlinked_headers,
    ).json() == []

    # Student cannot POST or DELETE
    assert client.post(
        "/api/v1/announcements",
        json={"session_id": test_data["session"].id, "title": "Hack", "content": "Hack"},
        headers=s1_headers,
    ).status_code == 403
    assert client.delete(f"/api/v1/announcements/{ann_c1_id}", headers=s1_headers).status_code == 403

    # Non-creator Teacher 2 cannot DELETE Teacher 1's or Admin's announcement (403)
    assert client.delete(f"/api/v1/announcements/{ann_c1_id}", headers=t2_headers).status_code == 403
    assert client.delete(f"/api/v1/announcements/{ann_global_id}", headers=t2_headers).status_code == 403

    # Creator Teacher 1 can delete own; Admin can delete any; missing returns 404
    assert client.delete(f"/api/v1/announcements/{ann_c1_id}", headers=t1_headers).status_code == 200
    assert client.delete(f"/api/v1/announcements/{ann_c2_id}", headers=admin_headers).status_code == 200
    assert client.delete(f"/api/v1/announcements/{ann_c1_id}", headers=admin_headers).status_code == 404


def test_announcements_validation(client, db, test_data):
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}
    sec_c2 = Section(name="B", class_id=test_data["class_2"].id)
    db.add(sec_c2)
    db.commit()

    # Whitespace title/content and invalid priority -> 422
    assert client.post(
        "/api/v1/announcements",
        json={"session_id": test_data["session"].id, "title": "   ", "content": "Valid"},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        "/api/v1/announcements",
        json={"session_id": test_data["session"].id, "title": "Valid", "content": "   "},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        "/api/v1/announcements",
        json={"session_id": test_data["session"].id, "title": "Valid", "content": "Valid", "priority": "Urgent"},
        headers=admin_headers,
    ).status_code == 422

    # Missing FKs -> 404
    assert client.post(
        "/api/v1/announcements",
        json={"session_id": 99999, "title": "Valid", "content": "Valid"},
        headers=admin_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/announcements",
        json={"session_id": test_data["session"].id, "class_id": 99999, "title": "Valid", "content": "Valid"},
        headers=admin_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/announcements",
        json={
            "session_id": test_data["session"].id,
            "class_id": test_data["class_1"].id,
            "section_id": 99999,
            "title": "Valid",
            "content": "Valid",
        },
        headers=admin_headers,
    ).status_code == 404

    # Section without class_id or mismatched class_id -> 422
    assert client.post(
        "/api/v1/announcements",
        json={
            "session_id": test_data["session"].id,
            "class_id": None,
            "section_id": test_data["section_1"].id,
            "title": "Valid",
            "content": "Valid",
        },
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        "/api/v1/announcements",
        json={
            "session_id": test_data["session"].id,
            "class_id": test_data["class_1"].id,
            "section_id": sec_c2.id,
            "title": "Valid",
            "content": "Valid",
        },
        headers=admin_headers,
    ).status_code == 422


# ==============================================================================
# F3: Exam Datesheet Upload/Download, Scoping & ExamResponse Names
# ==============================================================================
def test_exam_response_includes_names_and_countdown(client, db, test_data):
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}
    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}
    t2_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_2'], teacher_id=test_data['teacher_2'].id)}"}
    today = date.today()

    e_past = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_math"].id,
        name="Past Math Quiz",
        date=today - timedelta(days=2),
        max_marks=50.0,
    )
    e_today = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_math"].id,
        name="Today Math Exam",
        date=today,
        max_marks=100.0,
    )
    e_future_sci = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_sci"].id,
        name="Future Science Exam",
        date=today + timedelta(days=5),
        max_marks=100.0,
    )
    db.add_all([e_past, e_today, e_future_sci])
    db.commit()

    admin_list = client.get(f"/api/v1/exams?session_id={test_data['session'].id}", headers=admin_headers)
    assert admin_list.status_code == 200
    by_name = {ex["name"]: ex for ex in admin_list.json()}
    assert by_name["Past Math Quiz"]["countdown_status"] == "Completed"
    assert by_name["Past Math Quiz"]["subject_name"] == "Math"
    assert by_name["Past Math Quiz"]["class_name"] == "Class 10"
    assert by_name["Today Math Exam"]["countdown_status"] == "Today!"
    assert by_name["Future Science Exam"]["countdown_status"] == "5 Days Left"
    assert by_name["Future Science Exam"]["subject_name"] == "Sci"

    # Teacher 1 (assigned only to Class 10 Math) should NOT see Class 10 Science exam in list
    t1_list = client.get(f"/api/v1/exams?session_id={test_data['session'].id}", headers=t1_headers)
    assert t1_list.status_code == 200
    t1_names = {ex["name"] for ex in t1_list.json()}
    assert "Today Math Exam" in t1_names
    assert "Future Science Exam" not in t1_names

    # Teacher 2 (unassigned) sees []
    t2_list = client.get(f"/api/v1/exams?session_id={test_data['session'].id}", headers=t2_headers)
    assert t2_list.status_code == 200
    assert t2_list.json() == []


def test_datesheet_upload_download_and_scoping(client, db, test_data, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BASE_DIR", str(tmp_path))

    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}
    t2_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_2'], teacher_id=test_data['teacher_2'].id)}"}
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}

    # Create Class 11 student
    c2_user = User(
        username="STU_C2",
        hashed_password=get_password_hash("password123"),
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True,
    )
    db.add(c2_user)
    db.flush()
    c2_student = Student(
        admission_number="STU_C2",
        full_name="Class 11 Student",
        user_id=c2_user.id,
        class_id=test_data["class_2"].id,
        is_roster_claimed=True,
    )
    db.add(c2_student)
    db.flush()
    db.add(Enrollment(student_id=c2_student.id, session_id=test_data["session"].id, class_id=test_data["class_2"].id))

    exam = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        section_id=test_data["section_1"].id,
        subject_id=test_data["subj_math"].id,
        name="Midterm Math",
        date=date.today() + timedelta(days=3),
        max_marks=100.0,
        teacher_id=test_data["teacher_1"].id,
    )
    db.add(exam)
    db.commit()
    c2_headers = {"Authorization": f"Bearer {make_token(c2_user, student_id=c2_student.id)}"}

    # Download before upload -> 404
    assert client.get(f"/api/v1/exams/{exam.id}/datesheet", headers=s1_headers).status_code == 404
    # Unauthenticated download -> 401
    assert client.get(f"/api/v1/exams/{exam.id}/datesheet").status_code == 401

    # Teacher 2 upload -> 404
    assert client.post(
        f"/api/v1/exams/{exam.id}/datesheet",
        files={"file": ("ds.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers=t2_headers,
    ).status_code == 404

    # Invalid extension (.exe) & empty file -> 422
    assert client.post(
        f"/api/v1/exams/{exam.id}/datesheet",
        files={"file": ("malware.exe", b"MZ...", "application/octet-stream")},
        headers=t1_headers,
    ).status_code == 422
    assert client.post(
        f"/api/v1/exams/{exam.id}/datesheet",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=t1_headers,
    ).status_code == 422

    # Valid upload by Teacher 1 -> 200
    pdf_bytes = b"%PDF-1.4\n%Edwise Exam Datesheet Content\n"
    up_resp = client.post(
        f"/api/v1/exams/{exam.id}/datesheet",
        files={"file": ("midterm_datesheet.pdf", pdf_bytes, "application/pdf")},
        headers=t1_headers,
    )
    assert up_resp.status_code == 200
    fname = up_resp.json()["datesheet_filename"]
    assert fname.endswith("midterm_datesheet.pdf")

    # Student 1, Teacher 1, Admin download -> 200 with Content-Disposition & exact bytes
    for hdrs in (s1_headers, t1_headers, admin_headers):
        dl_resp = client.get(f"/api/v1/exams/{exam.id}/datesheet", headers=hdrs)
        assert dl_resp.status_code == 200
        assert "attachment" in dl_resp.headers.get("content-disposition", "").lower()
        assert dl_resp.content == pdf_bytes

    # Out-of-scope Teacher 2 and Class 11 Student -> 404
    assert client.get(f"/api/v1/exams/{exam.id}/datesheet", headers=t2_headers).status_code == 404
    assert client.get(f"/api/v1/exams/{exam.id}/datesheet", headers=c2_headers).status_code == 404
    assert client.get("/api/v1/exams/99999/datesheet", headers=admin_headers).status_code == 404


# ==============================================================================
# F4: Attendance Goal Planner Tests
# ==============================================================================
def test_attendance_goal_empty_records(client, test_data):
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    resp = client.get(
        f"/api/v1/attendance/goal/{test_data['student_1'].id}?session_id={test_data['session'].id}",
        headers=s1_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_rate"] == 100.0
    assert data["needed_consecutive_classes"] == 0
    assert data["safe_skips_available"] == 0
    assert data["is_warning"] is False


def test_attendance_goal_target_100_no_zero_division(client, db, test_data):
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}

    # 3 present, 1 absent (75%)
    for i, st in enumerate(["present", "present", "present", "absent"]):
        db.add(AttendanceRecord(
            session_id=test_data["session"].id,
            class_id=test_data["class_1"].id,
            subject_id=test_data["subj_math"].id,
            student_id=test_data["student_1"].id,
            date=date(2026, 10, 1 + i),
            status=st,
        ))
    db.commit()

    resp = client.get(
        f"/api/v1/attendance/goal/{test_data['student_1'].id}?session_id={test_data['session'].id}&target_pct=100",
        headers=s1_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_warning"] is True
    assert data["needed_consecutive_classes"] == 0
    assert data["safe_skips_available"] == 0
    assert "100.0%" in data["status_message"]

    # Student 2 with 4/4 present (100%) -> is_warning=False, safe_skips=0
    s2_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_2'], student_id=test_data['student_2'].id)}"}
    for i in range(4):
        db.add(AttendanceRecord(
            session_id=test_data["session"].id,
            class_id=test_data["class_1"].id,
            subject_id=test_data["subj_math"].id,
            student_id=test_data["student_2"].id,
            date=date(2026, 10, 1 + i),
            status="present",
        ))
    db.commit()
    resp2 = client.get(
        f"/api/v1/attendance/goal/{test_data['student_2'].id}?session_id={test_data['session'].id}&target_pct=100",
        headers=s2_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["is_warning"] is False
    assert resp2.json()["safe_skips_available"] == 0

    # At target_pct=75, Student 2 (4/4 = 100%) has 1 safe skip
    resp_skips = client.get(
        f"/api/v1/attendance/goal/{test_data['student_2'].id}?session_id={test_data['session'].id}&target_pct=75",
        headers=s2_headers,
    )
    assert resp_skips.status_code == 200
    assert resp_skips.json()["is_warning"] is False
    assert resp_skips.json()["safe_skips_available"] == 1


def test_attendance_goal_boundary_exact_decimal_and_rbac(client, db, test_data):
    # 389 present + 130 absent = 519 (74.9518% -> rounds to 75.0%, yet strictly < 0.75)
    base_d = date(2025, 1, 1)
    records = []
    for i in range(519):
        records.append(AttendanceRecord(
            session_id=test_data["session"].id,
            class_id=test_data["class_1"].id,
            subject_id=test_data["subj_math"].id,
            student_id=test_data["student_1"].id,
            date=base_d + timedelta(days=i),
            status="present" if i < 389 else "absent",
        ))
    db.bulk_save_objects(records)
    db.commit()

    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    t2_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_2'], teacher_id=test_data['teacher_2'].id)}"}

    resp = client.get(
        f"/api/v1/attendance/goal/{test_data['student_1'].id}?session_id={test_data['session'].id}&target_pct=75",
        headers=s1_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_rate"] == 75.0
    assert data["is_warning"] is True
    assert data["needed_consecutive_classes"] == 1

    # RBAC checks: Student 1 cannot view Student 2; Teacher 2 cannot view Student 1
    assert client.get(
        f"/api/v1/attendance/goal/{test_data['student_2'].id}?session_id={test_data['session'].id}",
        headers=s1_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/attendance/goal/{test_data['student_1'].id}?session_id={test_data['session'].id}",
        headers=t2_headers,
    ).status_code == 404


# ==============================================================================
# F5: AI Lesson Plan Tests
# ==============================================================================
def test_ai_lesson_plan_lowest_subject_and_schedule(client, db, test_data):
    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    t2_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_2'], teacher_id=test_data['teacher_2'].id)}"}

    ex_math = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_math"].id,
        name="Math Exam",
        date=date(2026, 10, 1),
        max_marks=100.0,
    )
    ex_sci = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_sci"].id,
        name="Sci Exam",
        date=date(2026, 10, 2),
        max_marks=100.0,
    )
    db.add_all([ex_math, ex_sci])
    db.flush()
    db.add_all([
        Mark(exam_id=ex_math.id, student_id=test_data["student_1"].id, score=85.0),
        Mark(exam_id=ex_sci.id, student_id=test_data["student_1"].id, score=55.0),
    ])
    db.commit()

    resp = client.get(
        f"/api/v1/analytics/ai-lesson-plan/{test_data['class_1'].id}?session_id={test_data['session'].id}",
        headers=t1_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["focus_subject"] == "Sci"
    assert data["avg_score"] == 55.0
    assert data["performance_status"] == "Challenging"
    assert [d["day"] for d in data["weekly_schedule"]] == ["Monday", "Wednesday", "Friday"]

    # Empty marks fallback for Class 11 (Admin)
    empty_resp = client.get(
        f"/api/v1/analytics/ai-lesson-plan/{test_data['class_2'].id}?session_id={test_data['session'].id}",
        headers=admin_headers,
    )
    assert empty_resp.status_code == 200
    assert empty_resp.json()["focus_subject"] == "Mathematics"
    assert empty_resp.json()["avg_score"] == 68.0
    assert empty_resp.json()["performance_status"] == "Moderate"

    # RBAC and invalid IDs
    assert client.get(
        f"/api/v1/analytics/ai-lesson-plan/{test_data['class_1'].id}?session_id={test_data['session'].id}",
        headers=s1_headers,
    ).status_code == 403
    assert client.get(
        f"/api/v1/analytics/ai-lesson-plan/{test_data['class_1'].id}?session_id={test_data['session'].id}",
        headers=t2_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/analytics/ai-lesson-plan/99999?session_id={test_data['session'].id}",
        headers=admin_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/analytics/ai-lesson-plan/{test_data['class_1'].id}?session_id=99999",
        headers=admin_headers,
    ).status_code == 404


# ==============================================================================
# F6: Bulk Marks CSV Upload Tests
# ==============================================================================
def test_marks_upload_csv_alphanumeric_adm_and_audit(client, db, test_data):
    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}

    exam = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        section_id=test_data["section_1"].id,
        subject_id=test_data["subj_math"].id,
        name="CSV Math Test",
        date=date(2026, 10, 15),
        max_marks=50.0,
        teacher_id=test_data["teacher_1"].id,
    )
    db.add(exam)
    db.commit()

    csv_content = f"Admission Number,Exam ID,Score\nSTU001,{exam.id},42.5\nSTU002,{exam.id},49.0\n".encode("utf-8")
    resp = client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks.csv", csv_content, "text/csv")},
        data={"session_id": str(test_data["session"].id), "exam_id": str(exam.id), "reason": "CSV Import 1"},
        headers=t1_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["imported_count"] == 2

    m1 = db.query(Mark).filter(Mark.exam_id == exam.id, Mark.student_id == test_data["student_1"].id).first()
    m2 = db.query(Mark).filter(Mark.exam_id == exam.id, Mark.student_id == test_data["student_2"].id).first()
    assert m1 is not None and m1.score == 42.5
    assert m2 is not None and m2.score == 49.0

    created_audits = db.query(AuditLog).filter(AuditLog.action == "mark.created", AuditLog.entity_name == "mark").all()
    assert len(created_audits) >= 2

    # Re-upload without explicit Form exam_id (resolved from CSV Exam ID or fallback) updates marks & writes mark.updated
    csv_update = "Admission Number,Score\nSTU001,45.0\n".encode("utf-8")
    resp2 = client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks_update.csv", csv_update, "text/csv")},
        data={"session_id": str(test_data["session"].id), "reason": "CSV Update"},
        headers=t1_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["imported_count"] == 1
    db.refresh(m1)
    assert m1.score == 45.0
    updated_audit = db.query(AuditLog).filter(AuditLog.action == "mark.updated", AuditLog.entity_name == "mark").first()
    assert updated_audit is not None


def test_marks_upload_csv_scoping_bounds_and_non_enrolled(client, db, test_data):
    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}
    t2_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_2'], teacher_id=test_data['teacher_2'].id)}"}
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}

    exam = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        section_id=test_data["section_1"].id,
        subject_id=test_data["subj_math"].id,
        name="Bounded CSV Exam",
        date=date(2026, 10, 20),
        max_marks=50.0,
        teacher_id=test_data["teacher_1"].id,
    )
    c2_student = Student(
        admission_number="STU_C11",
        full_name="Class 11 Student",
        class_id=test_data["class_2"].id,
        is_roster_claimed=False,
    )
    db.add_all([exam, c2_student])
    db.commit()

    # Student -> 403
    assert client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks.csv", b"Admission Number,Score\nSTU001,40\n", "text/csv")},
        data={"session_id": str(test_data["session"].id), "exam_id": str(exam.id)},
        headers=s1_headers,
    ).status_code == 403

    # Unassigned Teacher 2 -> 404 (both with Form exam_id and CSV Exam ID)
    assert client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks.csv", b"Admission Number,Score\nSTU001,40\n", "text/csv")},
        data={"session_id": str(test_data["session"].id), "exam_id": str(exam.id)},
        headers=t2_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks.csv", f"Admission Number,Exam ID,Score\nSTU001,{exam.id},40\n".encode(), "text/csv")},
        data={"session_id": str(test_data["session"].id)},
        headers=t2_headers,
    ).status_code == 404

    # Out-of-bounds score (> max_marks) -> 422 & zero partial writes committed
    over_csv = f"Admission Number,Exam ID,Score\nSTU001,{exam.id},40\nSTU002,{exam.id},55.0\n".encode()
    assert client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks.csv", over_csv, "text/csv")},
        data={"session_id": str(test_data["session"].id), "exam_id": str(exam.id)},
        headers=t1_headers,
    ).status_code == 422
    assert db.query(Mark).filter(Mark.exam_id == exam.id).count() == 0

    # Negative score -> 422
    assert client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks.csv", b"Admission Number,Score\nSTU001,-1.0\n", "text/csv")},
        data={"session_id": str(test_data["session"].id), "exam_id": str(exam.id)},
        headers=t1_headers,
    ).status_code == 422

    # Non-enrolled student (Class 11) for Class 10 exam -> 422
    assert client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks.csv", b"Admission Number,Score\nSTU_C11,40\n", "text/csv")},
        data={"session_id": str(test_data["session"].id), "exam_id": str(exam.id)},
        headers=t1_headers,
    ).status_code == 422

    # Unknown alphanumeric admission number -> 422 (no ArgumentError 500!)
    assert client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks.csv", b"Admission Number,Score\nSTU_UNKNOWN,40\n", "text/csv")},
        data={"session_id": str(test_data["session"].id), "exam_id": str(exam.id)},
        headers=t1_headers,
    ).status_code == 422

    # Duplicate student row -> 422
    assert client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("marks.csv", b"Admission Number,Score\nSTU001,40\nSTU001,42\n", "text/csv")},
        data={"session_id": str(test_data["session"].id), "exam_id": str(exam.id)},
        headers=t1_headers,
    ).status_code == 422


# ==============================================================================
# R2 Remediation Regression Tests (Challenger 1 Failures)
# ==============================================================================
def test_marks_upload_csv_exam_name_cross_class_and_unicode_digit(client, db, test_data):
    t2_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_2'], teacher_id=test_data['teacher_2'].id)}"}

    sec_c2 = Section(name="A", class_id=test_data["class_2"].id)
    db.add(sec_c2)
    db.flush()

    # Assign Teacher 1 to Class 10 Sci (already assigned to Math) and Teacher 2 to Class 11 Sci
    db.add_all([
        ClassSubjectTeacher(
            session_id=test_data["session"].id,
            class_id=test_data["class_1"].id,
            section_id=test_data["section_1"].id,
            subject_id=test_data["subj_sci"].id,
            teacher_id=test_data["teacher_1"].id,
        ),
        ClassSubjectTeacher(
            session_id=test_data["session"].id,
            class_id=test_data["class_2"].id,
            section_id=sec_c2.id,
            subject_id=test_data["subj_sci"].id,
            teacher_id=test_data["teacher_2"].id,
        ),
    ])

    stu_c11 = Student(
        admission_number="STU2001",
        full_name="Class 11 Science Student",
        class_id=test_data["class_2"].id,
        section_id=sec_c2.id,
        is_roster_claimed=False,
    )
    db.add(stu_c11)
    db.flush()
    db.add(Enrollment(
        student_id=stu_c11.id,
        session_id=test_data["session"].id,
        class_id=test_data["class_2"].id,
        section_id=sec_c2.id,
        roll_number="11",
    ))

    exam_c10 = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        section_id=test_data["section_1"].id,
        subject_id=test_data["subj_sci"].id,
        name="Midterm",
        date=date(2026, 11, 15),
        max_marks=100.0,
        teacher_id=test_data["teacher_1"].id,
    )
    exam_c11 = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_2"].id,
        section_id=sec_c2.id,
        subject_id=test_data["subj_sci"].id,
        name="Midterm",
        date=date(2026, 11, 15),
        max_marks=100.0,
        teacher_id=test_data["teacher_2"].id,
    )
    db.add_all([exam_c10, exam_c11])
    db.commit()

    # Teacher 2 uploads for Class 11 student using Exam Name "Midterm" (no exam_id) -> 200
    csv_ok = b"Admission Number,Exam Name,Score\nSTU2001,Midterm,84\n"
    resp = client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("midterm.csv", csv_ok, "text/csv")},
        data={"session_id": str(test_data["session"].id)},
        headers=t2_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["imported_count"] == 1
    saved = db.query(Mark).filter(Mark.exam_id == exam_c11.id, Mark.student_id == stu_c11.id).first()
    assert saved is not None and saved.score == 84.0

    # Teacher 2 still blocked from uploading Class 10 student via Exam Name "Midterm" -> 404
    csv_forbidden = b"Admission Number,Exam Name,Score\nSTU001,Midterm,75\n"
    resp_forbidden = client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("midterm_c10.csv", csv_forbidden, "text/csv")},
        data={"session_id": str(test_data["session"].id)},
        headers=t2_headers,
    )
    assert resp_forbidden.status_code == 404

    # Unicode superscript digit ("²") in Admission Number -> 422 (no int() ValueError 500)
    csv_unicode = "Admission Number,Exam Name,Score\n²,Midterm,80\n".encode("utf-8")
    resp_unicode = client.post(
        "/api/v1/marks/upload-csv",
        files={"file": ("unicode.csv", csv_unicode, "text/csv")},
        data={"session_id": str(test_data["session"].id)},
        headers=t2_headers,
    )
    assert resp_unicode.status_code == 422


def test_datesheet_double_dot_filename_roundtrip(client, db, test_data, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BASE_DIR", str(tmp_path))

    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}

    exam = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        section_id=test_data["section_1"].id,
        subject_id=test_data["subj_math"].id,
        name="Double Dot Datesheet Exam",
        date=date.today() + timedelta(days=4),
        max_marks=100.0,
        teacher_id=test_data["teacher_1"].id,
    )
    db.add(exam)
    db.commit()

    payload = b"%PDF-1.4\n%DoubleDotDatesheet\n"
    up_resp = client.post(
        f"/api/v1/exams/{exam.id}/datesheet",
        files={"file": ("midterm..final.pdf", payload, "application/pdf")},
        headers=t1_headers,
    )
    assert up_resp.status_code == 200
    saved_name = up_resp.json()["datesheet_filename"]
    assert ".." not in saved_name

    dl_resp = client.get(f"/api/v1/exams/{exam.id}/datesheet", headers=s1_headers)
    assert dl_resp.status_code == 200
    assert dl_resp.content == payload


def test_create_exam_fk_checks_and_name_validation(client, db, test_data):
    from backend.app.models.institution import AcademicSession

    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}
    sec_c2 = Section(name="B", class_id=test_data["class_2"].id)
    other_session = AcademicSession(
        name="2027-Other",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
        is_active=False,
    )
    db.add_all([sec_c2, other_session])
    db.commit()

    base_payload = {
        "session_id": test_data["session"].id,
        "class_id": test_data["class_1"].id,
        "subject_id": test_data["subj_math"].id,
        "name": "Valid Exam",
        "date": "2026-11-25",
        "max_marks": 100.0,
    }

    # Whitespace-only name -> 422
    assert client.post(
        "/api/v1/exams",
        json={**base_payload, "name": "   \t  "},
        headers=admin_headers,
    ).status_code == 422

    # Nonexistent FKs -> 404 (not 500 IntegrityError)
    assert client.post(
        "/api/v1/exams",
        json={**base_payload, "session_id": 999999},
        headers=admin_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/exams",
        json={**base_payload, "class_id": 999999},
        headers=admin_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/exams",
        json={**base_payload, "subject_id": 999999},
        headers=admin_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/exams",
        json={**base_payload, "section_id": 999999},
        headers=admin_headers,
    ).status_code == 404

    # Cross-session class_id and cross-class section_id -> 422
    assert client.post(
        "/api/v1/exams",
        json={**base_payload, "session_id": other_session.id},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        "/api/v1/exams",
        json={**base_payload, "section_id": sec_c2.id},
        headers=admin_headers,
    ).status_code == 422

    # Valid exam with padded name -> 200 and stripped
    ok_resp = client.post(
        "/api/v1/exams",
        json={**base_payload, "name": "  Trimmed Exam  "},
        headers=admin_headers,
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["name"] == "Trimmed Exam"


def test_attendance_goal_nonexistent_student_or_session_returns_404(client, test_data):
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}

    assert client.get(
        f"/api/v1/attendance/goal/999999?session_id={test_data['session'].id}",
        headers=admin_headers,
    ).status_code == 404

    assert client.get(
        f"/api/v1/attendance/goal/{test_data['student_1'].id}?session_id=999999",
        headers=admin_headers,
    ).status_code == 404
