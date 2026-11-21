from __future__ import annotations

from datetime import date, timedelta
import math
from typing import Dict

import httpx
import pytest

from helpers.auth import auth_headers_for
from helpers.seed_helpers import (
    ADMIN_CREDS,
    CLASS_ID,
    EXAM_1_ID,
    SECTION_A_ID,
    SESSION_ID,
    STUDENT_1_CREDS,
    STUDENT_1_ID,
    STUDENT_2_CREDS,
    STUDENT_2_ID,
    STUDENT_3_ID,
    SUBJECT_MATH_ID,
    SUBJECT_SCI_ID,
    TEACHER_ALAN_CREDS,
    TEACHER_ALAN_ID,
    TEACHER_SARAH_CREDS,
    create_announcement,
    create_doubt,
    create_exam,
    create_fresh_class_with_section,
    create_fresh_student,
    get_regression_models,
    save_student_marks,
    unique_tag,
    upload_exam_datesheet,
)

pytestmark = [pytest.mark.tier1, pytest.mark.api]


# ---------------------------------------------------------------------------
# F1: Doubts API Fixes & Tests
# ---------------------------------------------------------------------------

def test_T1_F1_01_student_creates_doubt(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    q = f"How do we factor quadratic polynomials? [{unique_tag()}]"
    resp = api_client.post(
        "/api/v1/doubts",
        json={"session_id": SESSION_ID, "subject_id": SUBJECT_MATH_ID, "question": q},
        headers=student_1_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    assert data["id"] > 0
    assert data["student_id"] == STUDENT_1_ID
    assert data["subject_id"] == SUBJECT_MATH_ID
    assert data["subject_name"] == "Mathematics"
    assert data["is_resolved"] is False
    assert data["answer"] is None
    assert data["student_roll"] == "STU1001"
    assert data["question"] == q


def test_T1_F1_02_student_lists_own_doubts(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        "/api/v1/doubts",
        params={"session_id": SESSION_ID},
        headers=student_1_headers,
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert isinstance(items, list) and len(items) >= 2
    for item in items:
        assert item["student_id"] == STUDENT_1_ID
        assert item["session_id"] == SESSION_ID
        assert isinstance(item["question"], str) and item["question"].strip()
    seeded_resolved = next((d for d in items if d["id"] == 1), None)
    assert seeded_resolved is not None
    assert seeded_resolved["is_resolved"] is True


def test_T1_F1_03_student_filters_doubts_by_subject(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        "/api/v1/doubts",
        params={"session_id": SESSION_ID, "subject_id": SUBJECT_SCI_ID},
        headers=student_1_headers,
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) >= 1
    for item in items:
        assert item["subject_id"] == SUBJECT_SCI_ID
        assert item["student_id"] == STUDENT_1_ID


def test_T1_F1_04_teacher_lists_and_answers_doubt(
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
    teacher_alan_headers: Dict[str, str],
) -> None:
    created = create_doubt(
        api_client,
        student_1_headers,
        subject_id=SUBJECT_SCI_ID,
        question=f"Explain Newton second law [{unique_tag()}]",
    )
    list_resp = api_client.get(
        "/api/v1/doubts",
        params={"session_id": SESSION_ID},
        headers=teacher_alan_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    assert any(d["id"] == created["id"] for d in list_resp.json())

    ans_text = "Review Newton's second law F=ma."
    ans_resp = api_client.post(
        f"/api/v1/doubts/{created['id']}/answer",
        json={"answer": ans_text},
        headers=teacher_alan_headers,
    )
    assert ans_resp.status_code == 200, ans_resp.text
    answered = ans_resp.json()
    assert answered["is_resolved"] is True
    assert answered["answer"] == ans_text
    assert answered["answered_by"] == TEACHER_ALAN_ID
    assert answered["answered_at"] is not None


def test_T1_F1_05_admin_answer_does_not_misattribute_teacher(
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
    admin_headers: Dict[str, str],
) -> None:
    created = create_doubt(
        api_client,
        student_1_headers,
        subject_id=SUBJECT_MATH_ID,
        question=f"Admin answer attribution test [{unique_tag()}]",
    )
    ans_resp = api_client.post(
        f"/api/v1/doubts/{created['id']}/answer",
        json={"answer": "Admin guidance note."},
        headers=admin_headers,
    )
    assert ans_resp.status_code == 200, ans_resp.text
    data = ans_resp.json()
    assert data["is_resolved"] is True
    assert data["answer"] == "Admin guidance note."
    assert data["answered_by"] is None


# ---------------------------------------------------------------------------
# F2: Announcements API Verification & Tests
# ---------------------------------------------------------------------------

def test_T1_F2_01_teacher_creates_class_announcement(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    title = f"Algebra Practice Sheet {unique_tag()}"
    resp = api_client.post(
        "/api/v1/announcements",
        json={
            "session_id": SESSION_ID,
            "class_id": CLASS_ID,
            "title": title,
            "content": "Solve exercises 1 to 10.",
            "priority": "Normal",
        },
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    try:
        assert data["id"] > 0
        assert data["class_id"] == CLASS_ID
        assert data["class_name"] == "Grade 10"
        assert data["priority"] == "Normal"
        assert data["teacher_name"]
    finally:
        api_client.delete(f"/api/v1/announcements/{data['id']}", headers=teacher_sarah_headers)


def test_T1_F2_02_admin_creates_global_high_priority_announcement(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    title = f"Holiday Notice {unique_tag()}"
    resp = api_client.post(
        "/api/v1/announcements",
        json={
            "session_id": SESSION_ID,
            "class_id": None,
            "title": title,
            "content": "School closed Friday.",
            "priority": "High",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    try:
        assert data["class_id"] is None
        assert data["class_name"] == "All Classes"
        assert data["priority"] == "High"
        assert data["teacher_name"] == "Administration"
    finally:
        api_client.delete(f"/api/v1/announcements/{data['id']}", headers=admin_headers)


def test_T1_F2_03_student_gets_scoped_announcements_newest_first(
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    student_1_headers: Dict[str, str],
) -> None:
    created = create_announcement(
        api_client,
        teacher_sarah_headers,
        class_id=CLASS_ID,
        title=f"Newest Student Notice {unique_tag()}",
        priority="Normal",
    )
    try:
        resp = api_client.get(
            "/api/v1/announcements",
            params={"session_id": SESSION_ID},
            headers=student_1_headers,
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert len(items) >= 2
        for item in items:
            assert item["class_id"] in (None, CLASS_ID)
        timestamps = [item["created_at"] for item in items]
        assert timestamps == sorted(timestamps, reverse=True)
    finally:
        api_client.delete(f"/api/v1/announcements/{created['id']}", headers=teacher_sarah_headers)


def test_T1_F2_04_teacher_filters_announcements_by_class(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        "/api/v1/announcements",
        params={"session_id": SESSION_ID, "class_id": CLASS_ID},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) >= 1
    for item in items:
        assert item["session_id"] == SESSION_ID
        assert item["class_id"] in (None, CLASS_ID)


def test_T1_F2_05_teacher_deletes_own_announcement(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    created = create_announcement(
        api_client,
        teacher_sarah_headers,
        class_id=CLASS_ID,
        title=f"Temp Delete Notice {unique_tag()}",
    )
    del_resp = api_client.delete(
        f"/api/v1/announcements/{created['id']}",
        headers=teacher_sarah_headers,
    )
    assert del_resp.status_code == 200, del_resp.text
    assert del_resp.json()["status"] == "success"

    list_resp = api_client.get(
        "/api/v1/announcements",
        params={"session_id": SESSION_ID},
        headers=teacher_sarah_headers,
    )
    assert list_resp.status_code == 200
    assert all(item["id"] != created["id"] for item in list_resp.json())


# ---------------------------------------------------------------------------
# F3: Exam Datesheet Download & Scoping
# ---------------------------------------------------------------------------

def test_T1_F3_01_teacher_uploads_pdf_datesheet(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"Datesheet Exam {unique_tag()}")
    pdf_bytes = b"%PDF-1.4 sample datesheet\n%%EOF"
    resp = api_client.post(
        f"/api/v1/exams/{exam['id']}/datesheet",
        files={"file": ("math_sheet.pdf", pdf_bytes, "application/pdf")},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["datesheet_filename"].endswith("math_sheet.pdf")

    detail = api_client.get(f"/api/v1/exams/{exam['id']}", headers=teacher_sarah_headers)
    assert detail.status_code == 200
    assert detail.json()["datesheet_filename"] == body["datesheet_filename"]


def test_T1_F3_02_student_downloads_uploaded_pdf_datesheet(
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    student_1_headers: Dict[str, str],
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"Download Exam {unique_tag()}")
    pdf_bytes = b"%PDF-1.4 sample student download datesheet\n%%EOF"
    upload_exam_datesheet(
        api_client,
        teacher_sarah_headers,
        exam["id"],
        filename="student_sheet.pdf",
        content=pdf_bytes,
    )
    dl = api_client.get(f"/api/v1/exams/{exam['id']}/datesheet", headers=student_1_headers)
    assert dl.status_code == 200, dl.text
    assert dl.content == pdf_bytes
    disp = dl.headers.get("content-disposition", "")
    assert "student_sheet.pdf" in disp or "attachment" in disp.lower()


def test_T1_F3_03_teacher_uploads_png_and_admin_downloads(
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    admin_headers: Dict[str, str],
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"PNG Exam {unique_tag()}")
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    upload_exam_datesheet(
        api_client,
        teacher_sarah_headers,
        exam["id"],
        filename="schedule.png",
        content=png_bytes,
        content_type="image/png",
    )
    dl = api_client.get(f"/api/v1/exams/{exam['id']}/datesheet", headers=admin_headers)
    assert dl.status_code == 200, dl.text
    assert dl.content == png_bytes
    ctype = dl.headers.get("content-type", "").lower()
    assert any(t in ctype for t in ("image/png", "application/octet-stream"))


def test_T1_F3_04_exam_list_includes_subject_and_class_names(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        "/api/v1/exams",
        params={"session_id": SESSION_ID},
        headers=student_1_headers,
    )
    assert resp.status_code == 200, resp.text
    exams = resp.json()
    assert len(exams) >= 2
    for ex in exams:
        assert ex.get("id")
        assert ex.get("name")
        assert ex.get("date")
        assert ex.get("days_left") is not None
        assert ex.get("countdown_status")
        assert isinstance(ex.get("subject_name"), str) and ex["subject_name"].strip()
        assert ex.get("class_name") == "Grade 10"


def test_T1_F3_05_created_future_exam_countdown_and_enriched_names(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    future_date = date.today() + timedelta(days=5)
    exam = create_exam(
        api_client,
        teacher_sarah_headers,
        name=f"Future 5d Exam {unique_tag()}",
        exam_date=future_date,
        max_marks=50.0,
    )
    detail = api_client.get(f"/api/v1/exams/{exam['id']}", headers=teacher_sarah_headers)
    assert detail.status_code == 200, detail.text
    data = detail.json()
    assert data["days_left"] == 5
    assert data["countdown_status"] == "5 Days Left"
    assert data["subject_name"] == "Mathematics"
    assert data["class_name"] == "Grade 10"


# ---------------------------------------------------------------------------
# F4: Attendance Goal Planner Fix & Tests
# ---------------------------------------------------------------------------

def test_T1_F4_01_student_high_attendance_safe_skips(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/attendance/goal/{STUDENT_1_ID}",
        params={"session_id": SESSION_ID},
        headers=student_1_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["current_rate"] == 100.0
    assert data["total_conducted"] >= 14
    assert data["current_attended"] == data["total_conducted"]
    assert data["target_rate"] == 75.0
    assert data["is_warning"] is False
    assert data["needed_consecutive_classes"] == 0
    expected_skips = math.floor(data["current_attended"] / 0.75 - data["total_conducted"])
    assert data["safe_skips_available"] == expected_skips


def test_T1_F4_02_low_attendance_student_warning_and_needed_classes(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/attendance/goal/{STUDENT_3_ID}",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["current_rate"] < 75.0
    assert data["is_warning"] is True
    assert data["needed_consecutive_classes"] > 0
    assert data["safe_skips_available"] == 0
    assert data["status_message"].strip()


def test_T1_F4_03_custom_target_pct_85(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/attendance/goal/{STUDENT_1_ID}",
        params={"session_id": SESSION_ID, "target_pct": 85.0},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["target_rate"] == 85.0
    assert data["is_warning"] is False
    expected_skips = math.floor(data["current_attended"] / 0.85 - data["total_conducted"])
    assert data["safe_skips_available"] == expected_skips


def test_T1_F4_04_student_2_goal_response_schema(
    api_client: httpx.Client, student_2_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/attendance/goal/{STUDENT_2_ID}",
        params={"session_id": SESSION_ID, "target_pct": 75.0},
        headers=student_2_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data["current_rate"], (int, float))
    assert isinstance(data["needed_consecutive_classes"], int) and data["needed_consecutive_classes"] >= 0
    assert isinstance(data["safe_skips_available"], int) and data["safe_skips_available"] >= 0
    assert isinstance(data["is_warning"], bool)


def test_T1_F4_05_min_boundary_target_pct_50(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/attendance/goal/{STUDENT_1_ID}",
        params={"session_id": SESSION_ID, "target_pct": 50.0},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["target_rate"] == 50.0
    assert data["is_warning"] is False
    assert data["safe_skips_available"] == data["current_attended"]


# ---------------------------------------------------------------------------
# F5: AI Lesson Plan API Verification & Tests
# ---------------------------------------------------------------------------

def test_T1_F5_01_teacher_gets_ai_lesson_plan(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{CLASS_ID}",
        params={"session_id": SESSION_ID},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data["focus_subject"], str) and data["focus_subject"].strip()
    assert data["class_id"] == CLASS_ID
    assert 0.0 <= data["avg_score"] <= 100.0
    assert data["performance_status"] in {"Challenging", "Moderate", "High Performance"}
    assert isinstance(data["key_recommendation"], str) and data["key_recommendation"].strip()
    assert len(data["weekly_schedule"]) == 3


def test_T1_F5_02_ai_lesson_plan_schedule_structure(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{CLASS_ID}",
        params={"session_id": SESSION_ID},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    schedule = data["weekly_schedule"]
    assert [item["day"] for item in schedule] == ["Monday", "Wednesday", "Friday"]
    for item in schedule:
        assert data["focus_subject"] in item["topic"]
        assert item["hours"] > 0


def test_T1_F5_03_assigned_teacher_alan_gets_ai_lesson_plan(
    api_client: httpx.Client, teacher_alan_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{CLASS_ID}",
        params={"session_id": SESSION_ID},
        headers=teacher_alan_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["class_id"] == CLASS_ID


def test_T1_F5_04_admin_gets_identical_ai_lesson_plan(
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    admin_headers: Dict[str, str],
) -> None:
    t_resp = api_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{CLASS_ID}",
        params={"session_id": SESSION_ID},
        headers=teacher_sarah_headers,
    )
    a_resp = api_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{CLASS_ID}",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert t_resp.status_code == 200 and a_resp.status_code == 200
    assert a_resp.json() == t_resp.json()


def test_T1_F5_05_ai_lesson_plan_identifies_lowest_subject_and_challenging_status(
    fresh_backend_client: httpx.Client,
) -> None:
    admin_h = auth_headers_for(fresh_backend_client, ADMIN_CREDS)
    cls_info = create_fresh_class_with_section(fresh_backend_client, admin_h, name="Grade 11 E2E")
    cid = cls_info["class_id"]
    sid = cls_info["section_id"]
    stu = create_fresh_student(fresh_backend_client, admin_h, class_id=cid, section_id=sid)

    # Assign Sarah (teacher_id=1) Math and Alan (teacher_id=2) Science to this class
    for tid, sub_id in ((1, SUBJECT_MATH_ID), (2, SUBJECT_SCI_ID)):
        r = fresh_backend_client.post(
            "/api/v1/institution/assignments/teachers",
            json={
                "session_id": SESSION_ID,
                "class_id": cid,
                "section_id": sid,
                "subject_id": sub_id,
                "teacher_id": tid,
            },
            headers=admin_h,
        )
        assert r.status_code == 200, r.text

    sarah_h = auth_headers_for(fresh_backend_client, TEACHER_SARAH_CREDS)
    alan_h = auth_headers_for(fresh_backend_client, TEACHER_ALAN_CREDS)
    math_exam = create_exam(fresh_backend_client, sarah_h, class_id=cid, section_id=sid, subject_id=SUBJECT_MATH_ID, max_marks=100.0)
    sci_exam = create_exam(fresh_backend_client, alan_h, class_id=cid, section_id=sid, subject_id=SUBJECT_SCI_ID, max_marks=100.0)
    save_student_marks(fresh_backend_client, sarah_h, math_exam["id"], [{"student_id": stu["id"], "score": 88.0}])
    save_student_marks(fresh_backend_client, alan_h, sci_exam["id"], [{"student_id": stu["id"], "score": 40.0}])

    plan_resp = fresh_backend_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{cid}",
        params={"session_id": SESSION_ID},
        headers=sarah_h,
    )
    assert plan_resp.status_code == 200, plan_resp.text
    plan = plan_resp.json()
    assert plan["focus_subject"] == "Science"
    assert plan["avg_score"] == pytest.approx(40.0, abs=0.1)
    assert plan["performance_status"] == "Challenging"


# ---------------------------------------------------------------------------
# F6: Bulk Marks CSV Upload Fix & Tests
# ---------------------------------------------------------------------------

def test_T1_F6_01_csv_upload_alphanumeric_admission_numbers(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"CSV Exam {unique_tag()}", max_marks=50.0)
    csv_data = f"Admission Number,Exam ID,Score\nSTU1001,{exam['id']},46\nSTU1002,{exam['id']},49\n".encode("utf-8")
    resp = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID), "reason": "Unit test import"},
        files={"file": ("marks.csv", csv_data, "text/csv")},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "success"
    assert resp.json()["imported_count"] == 2

    m_resp = api_client.get(f"/api/v1/marks/exam/{exam['id']}", headers=teacher_sarah_headers)
    assert m_resp.status_code == 200
    by_stu = {m["student_id"]: m["score"] for m in m_resp.json()}
    assert by_stu[STUDENT_1_ID] == 46.0
    assert by_stu[STUDENT_2_ID] == 49.0


def test_T1_F6_02_csv_upload_alias_headers_and_exam_name(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    exam_name = f"Alias Exam {unique_tag()}"
    exam = create_exam(api_client, teacher_sarah_headers, name=exam_name, max_marks=50.0)
    csv_data = f"roll_number,exam_name,marks\nSTU1001,{exam_name},42\n".encode("utf-8")
    resp = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID), "reason": "Alias header import"},
        files={"file": ("alias.csv", csv_data, "text/csv")},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["imported_count"] == 1

    m_resp = api_client.get(f"/api/v1/marks/exam/{exam['id']}", headers=teacher_sarah_headers)
    assert m_resp.status_code == 200
    assert any(m["student_id"] == STUDENT_1_ID and m["score"] == 42.0 for m in m_resp.json())


def test_T1_F6_03_csv_upload_numeric_student_id_alias(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"NumericID Exam {unique_tag()}", max_marks=50.0)
    csv_data = f"StudentID,Exam ID,LatestExam\n1,{exam['id']},47\n".encode("utf-8")
    resp = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID)},
        files={"file": ("num_id.csv", csv_data, "text/csv")},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["imported_count"] == 1

    m_resp = api_client.get(f"/api/v1/marks/exam/{exam['id']}", headers=teacher_sarah_headers)
    assert m_resp.status_code == 200
    assert any(m["student_id"] == STUDENT_1_ID and m["score"] == 47.0 for m in m_resp.json())


def test_T1_F6_04_csv_upload_utf8_bom_handled_cleanly(
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
    teacher_sarah_headers: Dict[str, str],
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"BOM Exam {unique_tag()}", max_marks=100.0)
    csv_data = ("\ufeffAdmission Number,Exam ID,Score\n" + f"STU1001,{exam['id']},91\n").encode("utf-8")
    resp = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID)},
        files={"file": ("bom.csv", csv_data, "text/csv")},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["imported_count"] == 1


def test_T1_F6_05_csv_upload_writes_audit_log_with_reason(
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    admin_headers: Dict[str, str],
) -> None:
    reason = f"CSV Audit Reason {unique_tag()}"
    exam = create_exam(api_client, teacher_sarah_headers, name=f"Audit CSV Exam {unique_tag()}", max_marks=50.0)
    csv_data = f"Admission Number,Exam ID,Score\nSTU1001,{exam['id']},44\n".encode("utf-8")
    up = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID), "reason": reason},
        files={"file": ("audit.csv", csv_data, "text/csv")},
        headers=teacher_sarah_headers,
    )
    assert up.status_code == 200, up.text

    audit_resp = api_client.get(
        "/api/v1/audit/logs",
        params={"limit": 100},
        headers=admin_headers,
    )
    assert audit_resp.status_code == 200, audit_resp.text
    logs = audit_resp.json()
    assert any(reason in str(entry.get("reason", "")) or reason in str(entry) for entry in logs)


# ---------------------------------------------------------------------------
# F7: ML Live Predict & Model Switcher Fixes & Tests
# ---------------------------------------------------------------------------

def test_T1_F7_01_predict_live_returns_valid_forecasts_and_low_risk(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    resp = api_client.post(
        "/api/v1/ml/predict-live",
        json={
            "unit_test_score": 80,
            "mid_term_score": 82,
            "assignment_score": 85,
            "practical_score": 84,
            "attendance_pct": 92,
            "previous_exam_score": 76,
            "subject_name": "Mathematics",
        },
        headers=student_1_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["subject_name"] == "Mathematics"
    for k in ("rf_prediction", "xgb_prediction", "linear_prediction", "active_prediction"):
        assert 0.0 <= data[k] <= 100.0
    assert 0.5 <= data["recommended_study_hours"] <= 4.0
    assert data["risk_level"] == "Low Risk"


def test_T1_F7_02_models_registry_has_metrics_and_single_active_regression(
    fresh_backend_client: httpx.Client,
) -> None:
    admin_h = auth_headers_for(fresh_backend_client, ADMIN_CREDS)
    reg_models = get_regression_models(fresh_backend_client, admin_h)
    names = " ".join(m["model_name"].lower() for m in reg_models)
    assert "linear" in names and "random forest" in names and "xgboost" in names
    for m in reg_models:
        assert "mae" in m["metrics"] and "rmse" in m["metrics"] and "r2" in m["metrics"]
    active_reg = [m for m in reg_models if m["is_active"]]
    assert len(active_reg) == 1, f"Expected 1 active regression model, found {len(active_reg)}: {active_reg}"


def test_T1_F7_03_switch_model_to_linear_regression_sets_single_active(
    fresh_backend_client: httpx.Client,
) -> None:
    admin_h = auth_headers_for(fresh_backend_client, ADMIN_CREDS)
    sw = fresh_backend_client.post(
        "/api/v1/ml/switch-model",
        json={"model_name": "linear_regression"},
        headers=admin_h,
    )
    assert sw.status_code == 200, sw.text
    assert sw.json()["status"] == "success"
    assert "linear" in sw.json()["active_model"].lower()

    reg_models = get_regression_models(fresh_backend_client, admin_h)
    active = [m for m in reg_models if m["is_active"]]
    assert len(active) == 1
    assert "linear" in active[0]["model_name"].lower()


def test_T1_F7_04_switch_model_to_xgboost_updates_predict_live(
    fresh_backend_client: httpx.Client,
) -> None:
    admin_h = auth_headers_for(fresh_backend_client, ADMIN_CREDS)
    sw = fresh_backend_client.post(
        "/api/v1/ml/switch-model",
        json={"model_name": "xgboost"},
        headers=admin_h,
    )
    assert sw.status_code == 200, sw.text
    pred = fresh_backend_client.post("/api/v1/ml/predict-live", json={}, headers=admin_h)
    assert pred.status_code == 200, pred.text
    data = pred.json()
    assert "xgboost" in data["active_model"].lower()
    assert data["active_prediction"] == data["xgb_prediction"]


def test_T1_F7_05_switch_model_to_random_forest_updates_predict_live(
    fresh_backend_client: httpx.Client,
) -> None:
    admin_h = auth_headers_for(fresh_backend_client, ADMIN_CREDS)
    sw = fresh_backend_client.post(
        "/api/v1/ml/switch-model",
        json={"model_name": "random_forest"},
        headers=admin_h,
    )
    assert sw.status_code == 200, sw.text
    pred = fresh_backend_client.post("/api/v1/ml/predict-live", json={}, headers=admin_h)
    assert pred.status_code == 200, pred.text
    data = pred.json()
    assert "random forest" in data["active_model"].lower()
    assert data["active_prediction"] == data["rf_prediction"]


# ---------------------------------------------------------------------------
# F8: Student Achievement Badges Endpoint
# ---------------------------------------------------------------------------

def test_T1_F8_01_student_gets_five_achievement_badges(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/student-badges/{STUDENT_1_ID}",
        params={"session_id": SESSION_ID},
        headers=student_1_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["student_id"] == STUDENT_1_ID
    assert data["session_id"] == SESSION_ID
    assert data["total_students_in_class"] >= 2
    badges = data["badges"]
    assert len(badges) == 5
    titles = {b["title"] for b in badges}
    assert titles == {"Top Performer", "Attendance Champ", "Subject Ace", "All-Rounder", "Active Learner"}
    for b in badges:
        for key in ("id", "title", "description", "icon", "unlocked", "color"):
            assert key in b


def test_T1_F8_02_top_ranked_student_unlocks_primary_badges(
    api_client: httpx.Client, student_2_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/student-badges/{STUDENT_2_ID}",
        params={"session_id": SESSION_ID},
        headers=student_2_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["rank"] == 1
    by_title = {b["title"]: b["unlocked"] for b in data["badges"]}
    assert by_title["Top Performer"] is True
    assert by_title["Attendance Champ"] is True
    assert by_title["Subject Ace"] is True
    assert by_title["All-Rounder"] is True


def test_T1_F8_03_low_performing_student_badges_locked_with_active_learner(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/student-badges/{STUDENT_3_ID}",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    by_title = {b["title"]: b["unlocked"] for b in resp.json()["badges"]}
    assert by_title["Top Performer"] is False
    assert by_title["Attendance Champ"] is False
    assert by_title["Subject Ace"] is False
    assert by_title["Active Learner"] is True


def test_T1_F8_04_scoped_teacher_can_view_student_badges(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/student-badges/{STUDENT_1_ID}",
        params={"session_id": SESSION_ID},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["student_id"] == STUDENT_1_ID


def test_T1_F8_05_student_badges_response_contains_no_peer_pii(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/student-badges/{STUDENT_1_ID}",
        params={"session_id": SESSION_ID},
        headers=student_1_headers,
    )
    assert resp.status_code == 200, resp.text
    raw = resp.text
    for peer_pii in ("Priya Sharma", "STU1002", "David Miller", "STU1003", "Emma Watson", "STU1004"):
        assert peer_pii not in raw
