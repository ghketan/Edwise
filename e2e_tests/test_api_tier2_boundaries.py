from __future__ import annotations

from datetime import date, timedelta
from typing import Dict

import httpx
import pytest

from helpers.auth import auth_headers_for
from helpers.seed_helpers import (
    ADMIN_CREDS,
    CLASS_ID,
    DOUBT_2_ID,
    EXAM_1_ID,
    SECTION_A_ID,
    SESSION_ID,
    STUDENT_1_ID,
    STUDENT_2_ID,
    STUDENT_3_ID,
    SUBJECT_MATH_ID,
    SUBJECT_SCI_ID,
    TEACHER_ALAN_CREDS,
    TEACHER_SARAH_CREDS,
    create_announcement,
    create_doubt,
    create_exam,
    create_fresh_class_with_section,
    create_fresh_student,
    get_regression_models,
    record_attendance_days,
    save_student_marks,
    unique_tag,
)

pytestmark = [pytest.mark.tier2, pytest.mark.api]


# ---------------------------------------------------------------------------
# F1: Doubts API Boundaries & RBAC
# ---------------------------------------------------------------------------

def test_T2_F1_01_empty_and_whitespace_doubt_question_rejected(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    before = api_client.get(
        "/api/v1/doubts", params={"session_id": SESSION_ID}, headers=student_1_headers
    ).json()
    for bad_q in ("", "   \t\n  "):
        resp = api_client.post(
            "/api/v1/doubts",
            json={"session_id": SESSION_ID, "subject_id": SUBJECT_MATH_ID, "question": bad_q},
            headers=student_1_headers,
        )
        assert resp.status_code == 422, f"Expected 422 for {bad_q!r}, got {resp.status_code}: {resp.text}"
    after = api_client.get(
        "/api/v1/doubts", params={"session_id": SESSION_ID}, headers=student_1_headers
    ).json()
    assert len(after) == len(before)


def test_T2_F1_02_empty_and_whitespace_doubt_answer_rejected(
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
    teacher_sarah_headers: Dict[str, str],
) -> None:
    d = create_doubt(api_client, student_1_headers, question=f"Blank answer check [{unique_tag()}]")
    for bad_a in ("", "   "):
        resp = api_client.post(
            f"/api/v1/doubts/{d['id']}/answer",
            json={"answer": bad_a},
            headers=teacher_sarah_headers,
        )
        assert resp.status_code == 422, f"Expected 422 for {bad_a!r}, got {resp.status_code}"
    doubts = api_client.get(
        "/api/v1/doubts", params={"session_id": SESSION_ID}, headers=student_1_headers
    ).json()
    target = next(item for item in doubts if item["id"] == d["id"])
    assert target["is_resolved"] is False


def test_T2_F1_03_invalid_subject_or_session_fk_rejected_cleanly(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    r_sub = api_client.post(
        "/api/v1/doubts",
        json={"session_id": SESSION_ID, "subject_id": 99999, "question": "Valid question?"},
        headers=student_1_headers,
    )
    assert r_sub.status_code in (404, 422), r_sub.text

    r_ses = api_client.post(
        "/api/v1/doubts",
        json={"session_id": 99999, "subject_id": SUBJECT_MATH_ID, "question": "Valid question?"},
        headers=student_1_headers,
    )
    assert r_ses.status_code in (404, 422), r_ses.text


def test_T2_F1_04_doubts_rbac_and_unauthenticated(
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    student_1_headers: Dict[str, str],
) -> None:
    unauth = api_client.get("/api/v1/doubts", params={"session_id": SESSION_ID})
    assert unauth.status_code == 401

    teacher_post = api_client.post(
        "/api/v1/doubts",
        json={"session_id": SESSION_ID, "subject_id": SUBJECT_MATH_ID, "question": "Teacher asking?"},
        headers=teacher_sarah_headers,
    )
    assert teacher_post.status_code == 403

    student_ans = api_client.post(
        f"/api/v1/doubts/{DOUBT_2_ID}/answer",
        json={"answer": "Self answer"},
        headers=student_1_headers,
    )
    assert student_ans.status_code == 403


def test_T2_F1_05_cross_student_isolation_and_missing_doubt_404(
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
    student_2_headers: Dict[str, str],
    teacher_sarah_headers: Dict[str, str],
) -> None:
    secret_q = f"Private STU1001 question [{unique_tag()}]"
    create_doubt(api_client, student_1_headers, question=secret_q)

    stu2_doubts = api_client.get(
        "/api/v1/doubts", params={"session_id": SESSION_ID}, headers=student_2_headers
    )
    assert stu2_doubts.status_code == 200
    assert all(d["student_id"] != STUDENT_1_ID for d in stu2_doubts.json())
    assert all(secret_q not in d["question"] for d in stu2_doubts.json())

    missing = api_client.post(
        "/api/v1/doubts/99999/answer",
        json={"answer": "Valid answer"},
        headers=teacher_sarah_headers,
    )
    assert missing.status_code == 404


# ---------------------------------------------------------------------------
# F2: Announcements API Boundaries & RBAC
# ---------------------------------------------------------------------------

def test_T2_F2_01_whitespace_title_or_content_rejected(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    r1 = api_client.post(
        "/api/v1/announcements",
        json={"session_id": SESSION_ID, "class_id": CLASS_ID, "title": "   ", "content": "Valid", "priority": "Normal"},
        headers=teacher_sarah_headers,
    )
    assert r1.status_code == 422

    r2 = api_client.post(
        "/api/v1/announcements",
        json={"session_id": SESSION_ID, "class_id": CLASS_ID, "title": "Valid", "content": "   \n ", "priority": "Normal"},
        headers=teacher_sarah_headers,
    )
    assert r2.status_code == 422


def test_T2_F2_02_invalid_priority_or_unknown_class_rejected_without_500(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    r_prio = api_client.post(
        "/api/v1/announcements",
        json={"session_id": SESSION_ID, "class_id": CLASS_ID, "title": "Notice", "content": "Body", "priority": "Urgent"},
        headers=teacher_sarah_headers,
    )
    assert r_prio.status_code == 422

    r_cls = api_client.post(
        "/api/v1/announcements",
        json={"session_id": SESSION_ID, "class_id": 99999, "title": "Notice", "content": "Body", "priority": "Normal"},
        headers=teacher_sarah_headers,
    )
    assert r_cls.status_code in (404, 422)


def test_T2_F2_03_announcements_rbac_and_unauthenticated(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    assert api_client.get("/api/v1/announcements", params={"session_id": SESSION_ID}).status_code == 401

    r_post = api_client.post(
        "/api/v1/announcements",
        json={"session_id": SESSION_ID, "title": "Hack", "content": "Body", "priority": "Normal"},
        headers=student_1_headers,
    )
    assert r_post.status_code == 403

    r_del = api_client.delete("/api/v1/announcements/1", headers=student_1_headers)
    assert r_del.status_code == 403


def test_T2_F2_04_cross_teacher_delete_forbidden(
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    teacher_alan_headers: Dict[str, str],
) -> None:
    ann = create_announcement(api_client, teacher_sarah_headers, title=f"Sarah Own Notice {unique_tag()}")
    try:
        del_resp = api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=teacher_alan_headers)
        assert del_resp.status_code in (403, 422), del_resp.text

        items = api_client.get(
            "/api/v1/announcements", params={"session_id": SESSION_ID}, headers=teacher_sarah_headers
        ).json()
        assert any(a["id"] == ann["id"] for a in items)
    finally:
        api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=teacher_sarah_headers)


def test_T2_F2_05_student_class_filter_override_and_delete_missing_404(
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
    student_1_headers: Dict[str, str],
) -> None:
    other_cls = create_fresh_class_with_section(api_client, admin_headers, name=f"Other Class {unique_tag()}")
    other_ann = create_announcement(
        api_client,
        admin_headers,
        class_id=other_cls["class_id"],
        title=f"Other Class Notice {unique_tag()}",
    )
    try:
        resp = api_client.get(
            "/api/v1/announcements",
            params={"session_id": SESSION_ID, "class_id": other_cls["class_id"]},
            headers=student_1_headers,
        )
        assert resp.status_code == 200
        ids = {a["id"] for a in resp.json()}
        assert other_ann["id"] not in ids

        missing_del = api_client.delete("/api/v1/announcements/99999", headers=admin_headers)
        assert missing_del.status_code == 404
    finally:
        api_client.delete(f"/api/v1/announcements/{other_ann['id']}", headers=admin_headers)


# ---------------------------------------------------------------------------
# F3: Exam Datesheet Download & Scoping Boundaries
# ---------------------------------------------------------------------------

def test_T2_F3_01_download_missing_datesheet_returns_404(
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    student_1_headers: Dict[str, str],
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"No Datesheet {unique_tag()}")
    resp = api_client.get(f"/api/v1/exams/{exam['id']}/datesheet", headers=student_1_headers)
    assert resp.status_code == 404, resp.text


def test_T2_F3_02_cross_teacher_datesheet_upload_and_detail_out_of_scope(
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    teacher_alan_headers: Dict[str, str],
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"Sarah Scope Exam {unique_tag()}")
    up = api_client.post(
        f"/api/v1/exams/{exam['id']}/datesheet",
        files={"file": ("hack.pdf", b"%PDF-1.4 hack", "application/pdf")},
        headers=teacher_alan_headers,
    )
    assert up.status_code in (403, 404), up.text

    det = api_client.get(f"/api/v1/exams/{exam['id']}", headers=teacher_alan_headers)
    assert det.status_code in (403, 404), det.text

    sarah_det = api_client.get(f"/api/v1/exams/{exam['id']}", headers=teacher_sarah_headers).json()
    assert sarah_det["datesheet_filename"] is None


def test_T2_F3_03_datesheet_rbac_unauth_and_missing_exam(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    assert api_client.get(f"/api/v1/exams/{EXAM_1_ID}/datesheet").status_code == 401
    assert (
        api_client.post(
            f"/api/v1/exams/{EXAM_1_ID}/datesheet",
            files={"file": ("s.pdf", b"%PDF-1.4", "application/pdf")},
            headers=student_1_headers,
        ).status_code
        == 403
    )
    assert api_client.get("/api/v1/exams/99999/datesheet", headers=student_1_headers).status_code == 404


def test_T2_F3_04_exam_countdown_past_today_and_future(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    today = date.today()
    past_ex = create_exam(api_client, teacher_sarah_headers, name=f"Past {unique_tag()}", exam_date=today - timedelta(days=2))
    today_ex = create_exam(api_client, teacher_sarah_headers, name=f"Today {unique_tag()}", exam_date=today)
    fut_ex = create_exam(api_client, teacher_sarah_headers, name=f"Future {unique_tag()}", exam_date=today + timedelta(days=10))

    exams = api_client.get("/api/v1/exams", params={"session_id": SESSION_ID}, headers=teacher_sarah_headers).json()
    by_id = {e["id"]: e for e in exams}
    assert by_id[past_ex["id"]]["days_left"] == -2
    assert by_id[past_ex["id"]]["countdown_status"] == "Completed"
    assert by_id[today_ex["id"]]["days_left"] == 0
    assert by_id[today_ex["id"]]["countdown_status"] == "Today!"
    assert by_id[fut_ex["id"]]["days_left"] == 10
    assert by_id[fut_ex["id"]]["countdown_status"] == "10 Days Left"


def test_T2_F3_05_datesheet_path_traversal_and_empty_file_safe(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"Traversal Exam {unique_tag()}")
    trav = api_client.post(
        f"/api/v1/exams/{exam['id']}/datesheet",
        files={"file": ("../../evil.pdf", b"%PDF-1.4 safe", "application/pdf")},
        headers=teacher_sarah_headers,
    )
    assert trav.status_code in (200, 400, 422), trav.text
    if trav.status_code == 200:
        fname = trav.json()["datesheet_filename"]
        assert ".." not in fname and "/" not in fname and "\\" not in fname

    exam2 = create_exam(api_client, teacher_sarah_headers, name=f"Empty File Exam {unique_tag()}")
    empty = api_client.post(
        f"/api/v1/exams/{exam2['id']}/datesheet",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=teacher_sarah_headers,
    )
    assert empty.status_code in (200, 400, 422), empty.text


# ---------------------------------------------------------------------------
# F4: Attendance Goal Planner Boundaries
# ---------------------------------------------------------------------------

def test_T2_F4_01_target_pct_100_with_missed_classes_no_zerodivision(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/attendance/goal/{STUDENT_3_ID}",
        params={"session_id": SESSION_ID, "target_pct": 100.0},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["target_rate"] == 100.0
    assert data["is_warning"] is True
    assert data["safe_skips_available"] == 0
    assert isinstance(data["needed_consecutive_classes"], int) and data["needed_consecutive_classes"] >= 0
    assert data["status_message"].strip()


def test_T2_F4_02_zero_attendance_records_baseline_safe(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    stu = create_fresh_student(api_client, admin_headers, claim=False)
    resp = api_client.get(
        f"/api/v1/attendance/goal/{stu['id']}",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_conducted"] == 0
    assert data["current_attended"] == 0
    assert data["needed_consecutive_classes"] == 0
    assert data["safe_skips_available"] == 0
    assert data["is_warning"] is False


def test_T2_F4_03_exact_75_pct_vs_below_75_pct_ratio_boundary(
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
    teacher_sarah_headers: Dict[str, str],
) -> None:
    # Student with exact 3/4 = 75.0%
    stu_75 = create_fresh_student(api_client, admin_headers, claim=False)
    record_attendance_days(
        api_client, teacher_sarah_headers, student_id=stu_75["id"], present_count=3, absent_count=1, start_date=date(2026, 2, 1)
    )
    r_75 = api_client.get(
        f"/api/v1/attendance/goal/{stu_75['id']}",
        params={"session_id": SESSION_ID, "target_pct": 75.0},
        headers=admin_headers,
    )
    assert r_75.status_code == 200
    d_75 = r_75.json()
    assert d_75["is_warning"] is False
    assert d_75["needed_consecutive_classes"] == 0
    assert d_75["safe_skips_available"] == 0

    # Student with 14/19 = 73.68% (below 75%, rounds nicely, needs 1 consecutive class)
    stu_low = create_fresh_student(api_client, admin_headers, claim=False)
    record_attendance_days(
        api_client, teacher_sarah_headers, student_id=stu_low["id"], present_count=14, absent_count=5, start_date=date(2026, 3, 1)
    )
    r_low = api_client.get(
        f"/api/v1/attendance/goal/{stu_low['id']}",
        params={"session_id": SESSION_ID, "target_pct": 75.0},
        headers=admin_headers,
    )
    assert r_low.status_code == 200
    d_low = r_low.json()
    assert d_low["is_warning"] is True
    assert d_low["needed_consecutive_classes"] >= 1
    assert d_low["safe_skips_available"] == 0


def test_T2_F4_04_invalid_target_pct_bounds_rejected(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    assert (
        api_client.get(
            f"/api/v1/attendance/goal/{STUDENT_1_ID}",
            params={"session_id": SESSION_ID, "target_pct": 49.9},
            headers=admin_headers,
        ).status_code
        == 422
    )
    assert (
        api_client.get(
            f"/api/v1/attendance/goal/{STUDENT_1_ID}",
            params={"session_id": SESSION_ID, "target_pct": 100.1},
            headers=admin_headers,
        ).status_code
        == 422
    )
    assert (
        api_client.get(
            f"/api/v1/attendance/goal/{STUDENT_1_ID}",
            params={"session_id": SESSION_ID, "target_pct": 50.0},
            headers=admin_headers,
        ).status_code
        == 200
    )


def test_T2_F4_05_attendance_goal_cross_student_and_rbac(
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
    student_1_headers: Dict[str, str],
    teacher_sarah_headers: Dict[str, str],
) -> None:
    assert (
        api_client.get(
            f"/api/v1/attendance/goal/{STUDENT_1_ID}", params={"session_id": SESSION_ID}
        ).status_code
        == 401
    )
    assert (
        api_client.get(
            f"/api/v1/attendance/goal/{STUDENT_2_ID}",
            params={"session_id": SESSION_ID},
            headers=student_1_headers,
        ).status_code
        == 404
    )
    other_cls = create_fresh_class_with_section(api_client, admin_headers)
    other_stu = create_fresh_student(
        api_client, admin_headers, class_id=other_cls["class_id"], section_id=other_cls["section_id"], claim=False
    )
    assert (
        api_client.get(
            f"/api/v1/attendance/goal/{other_stu['id']}",
            params={"session_id": SESSION_ID},
            headers=teacher_sarah_headers,
        ).status_code
        == 404
    )


# ---------------------------------------------------------------------------
# F5: AI Lesson Plan Boundaries
# ---------------------------------------------------------------------------

def test_T2_F5_01_empty_class_zero_marks_fallback(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    empty_cls = create_fresh_class_with_section(api_client, admin_headers, name=f"Empty Marks Class {unique_tag()}")
    resp = api_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{empty_cls['class_id']}",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["focus_subject"] == "Mathematics"
    assert data["avg_score"] == 68.0
    assert len(data["weekly_schedule"]) == 3


def test_T2_F5_02_ai_lesson_plan_rbac_student_403_unauth_401(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    assert (
        api_client.get(
            f"/api/v1/analytics/ai-lesson-plan/{CLASS_ID}", params={"session_id": SESSION_ID}
        ).status_code
        == 401
    )
    assert (
        api_client.get(
            f"/api/v1/analytics/ai-lesson-plan/{CLASS_ID}",
            params={"session_id": SESSION_ID},
            headers=student_1_headers,
        ).status_code
        == 403
    )


def test_T2_F5_03_unassigned_class_scope_returns_404(
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
    teacher_sarah_headers: Dict[str, str],
) -> None:
    unassigned_cls = create_fresh_class_with_section(api_client, admin_headers)
    r_unassigned = api_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{unassigned_cls['class_id']}",
        params={"session_id": SESSION_ID},
        headers=teacher_sarah_headers,
    )
    assert r_unassigned.status_code == 404

    r_missing = api_client.get(
        "/api/v1/analytics/ai-lesson-plan/99999",
        params={"session_id": SESSION_ID},
        headers=teacher_sarah_headers,
    )
    assert r_missing.status_code == 404


def test_T2_F5_04_absent_only_marks_no_zerodivision(
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
) -> None:
    cls_info = create_fresh_class_with_section(api_client, admin_headers, name=f"Absent Class {unique_tag()}")
    stu = create_fresh_student(
        api_client, admin_headers, class_id=cls_info["class_id"], section_id=cls_info["section_id"], claim=False
    )
    api_client.post(
        "/api/v1/institution/assignments/teachers",
        json={
            "session_id": SESSION_ID,
            "class_id": cls_info["class_id"],
            "section_id": cls_info["section_id"],
            "subject_id": SUBJECT_MATH_ID,
            "teacher_id": 1,
        },
        headers=admin_headers,
    )
    ex = create_exam(
        api_client,
        admin_headers,
        class_id=cls_info["class_id"],
        section_id=cls_info["section_id"],
        subject_id=SUBJECT_MATH_ID,
    )
    save_student_marks(api_client, admin_headers, ex["id"], [{"student_id": stu["id"], "score": None, "is_absent": True}])

    resp = api_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{cls_info['class_id']}",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["weekly_schedule"]) == 3


def test_T2_F5_05_missing_session_id_returns_422(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/ai-lesson-plan/{CLASS_ID}",
        headers=teacher_sarah_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# F6: Bulk Marks CSV Upload Boundaries
# ---------------------------------------------------------------------------

def test_T2_F6_01_unknown_alphanumeric_admission_number_no_500(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"Unknown Adm {unique_tag()}", max_marks=50.0)
    csv_data = f"Admission Number,Exam ID,Score\nSTU9999,{exam['id']},40\n".encode("utf-8")
    resp = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID)},
        files={"file": ("unknown.csv", csv_data, "text/csv")},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code in (200, 422), resp.text
    if resp.status_code == 200:
        assert resp.json()["imported_count"] == 0


def test_T2_F6_02_empty_and_invalid_headers_csv_rejected(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    r_empty = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID)},
        files={"file": ("empty.csv", b"", "text/csv")},
        headers=teacher_sarah_headers,
    )
    assert r_empty.status_code in (400, 422), r_empty.text

    r_bad = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID)},
        files={"file": ("bad.csv", b"Foo,Bar,Baz\n1,2,3\n", "text/csv")},
        headers=teacher_sarah_headers,
    )
    assert r_bad.status_code in (400, 422), r_bad.text


def test_T2_F6_03_non_numeric_score_rejected_without_corrupting_marks(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"NonNumeric {unique_tag()}", max_marks=50.0)
    save_student_marks(api_client, teacher_sarah_headers, exam["id"], [{"student_id": STUDENT_1_ID, "score": 41.0}])

    csv_data = f"Admission Number,Exam ID,Score\nSTU1001,{exam['id']},not_a_number\n".encode("utf-8")
    resp = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID)},
        files={"file": ("badscore.csv", csv_data, "text/csv")},
        headers=teacher_sarah_headers,
    )
    assert resp.status_code in (400, 422), resp.text

    marks = api_client.get(f"/api/v1/marks/exam/{exam['id']}", headers=teacher_sarah_headers).json()
    assert any(m["student_id"] == STUDENT_1_ID and m["score"] == 41.0 for m in marks)


def test_T2_F6_04_out_of_bounds_scores_rejected_not_clamped(
    api_client: httpx.Client, teacher_sarah_headers: Dict[str, str]
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"Bounds {unique_tag()}", max_marks=50.0)
    save_student_marks(api_client, teacher_sarah_headers, exam["id"], [{"student_id": STUDENT_1_ID, "score": 33.0}])

    for bad_score in ("-5", "999"):
        csv_data = f"Admission Number,Exam ID,Score\nSTU1001,{exam['id']},{bad_score}\n".encode("utf-8")
        resp = api_client.post(
            "/api/v1/marks/upload-csv",
            data={"session_id": str(SESSION_ID)},
            files={"file": ("oob.csv", csv_data, "text/csv")},
            headers=teacher_sarah_headers,
        )
        assert resp.status_code in (400, 422), f"Expected rejection for score {bad_score}, got {resp.status_code}: {resp.text}"

    marks = api_client.get(f"/api/v1/marks/exam/{exam['id']}", headers=teacher_sarah_headers).json()
    assert any(m["student_id"] == STUDENT_1_ID and m["score"] == 33.0 for m in marks)


def test_T2_F6_05_csv_upload_cross_teacher_scope_and_student_rbac(
    api_client: httpx.Client,
    teacher_alan_headers: Dict[str, str],
    student_1_headers: Dict[str, str],
) -> None:
    csv_data = f"Admission Number,Exam ID,Score\nSTU1001,{EXAM_1_ID},40\n".encode("utf-8")
    r_alan = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID)},
        files={"file": ("alan.csv", csv_data, "text/csv")},
        headers=teacher_alan_headers,
    )
    assert r_alan.status_code in (403, 404), r_alan.text

    r_stu = api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID)},
        files={"file": ("stu.csv", csv_data, "text/csv")},
        headers=student_1_headers,
    )
    assert r_stu.status_code == 403


# ---------------------------------------------------------------------------
# F7: ML Live Predict & Model Switcher Boundaries
# ---------------------------------------------------------------------------

def test_T2_F7_01_invalid_model_name_rejected_without_silent_fallback(
    fresh_backend_client: httpx.Client,
) -> None:
    admin_h = auth_headers_for(fresh_backend_client, ADMIN_CREDS)
    before_active = [m["model_name"] for m in get_regression_models(fresh_backend_client, admin_h) if m["is_active"]]

    for bad_name in ("neural_net", "   "):
        resp = fresh_backend_client.post(
            "/api/v1/ml/switch-model",
            json={"model_name": bad_name},
            headers=admin_h,
        )
        assert resp.status_code in (404, 422), f"Expected rejection for {bad_name!r}, got {resp.status_code}: {resp.text}"

    after_active = [m["model_name"] for m in get_regression_models(fresh_backend_client, admin_h) if m["is_active"]]
    assert after_active == before_active


def test_T2_F7_02_predict_live_extreme_zero_and_hundred_clamping(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    zero_resp = api_client.post(
        "/api/v1/ml/predict-live",
        json={
            "unit_test_score": 0.0,
            "mid_term_score": 0.0,
            "assignment_score": 0.0,
            "practical_score": 0.0,
            "attendance_pct": 0.0,
            "previous_exam_score": 0.0,
        },
        headers=student_1_headers,
    )
    assert zero_resp.status_code == 200, zero_resp.text
    z = zero_resp.json()
    for k in ("rf_prediction", "xgb_prediction", "linear_prediction", "active_prediction"):
        assert 0.0 <= z[k] <= 100.0
    assert 0.5 <= z["recommended_study_hours"] <= 4.0
    assert z["risk_level"] == "High Risk"

    full_resp = api_client.post(
        "/api/v1/ml/predict-live",
        json={
            "unit_test_score": 100.0,
            "mid_term_score": 100.0,
            "assignment_score": 100.0,
            "practical_score": 100.0,
            "attendance_pct": 100.0,
            "previous_exam_score": 100.0,
        },
        headers=student_1_headers,
    )
    assert full_resp.status_code == 200, full_resp.text
    f = full_resp.json()
    for k in ("rf_prediction", "xgb_prediction", "linear_prediction", "active_prediction"):
        assert 0.0 <= f[k] <= 100.0
    assert 0.5 <= f["recommended_study_hours"] <= 4.0
    assert f["risk_level"] == "Low Risk"


def test_T2_F7_03_predict_live_invalid_types_rejected(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    resp = api_client.post(
        "/api/v1/ml/predict-live",
        json={"unit_test_score": "bad", "attendance_pct": 90},
        headers=student_1_headers,
    )
    assert resp.status_code == 422


def test_T2_F7_04_ml_endpoints_rbac_and_unauthenticated(
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
    teacher_sarah_headers: Dict[str, str],
) -> None:
    assert api_client.post("/api/v1/ml/predict-live", json={}).status_code == 401
    for headers in (student_1_headers, teacher_sarah_headers):
        assert api_client.get("/api/v1/ml/models", headers=headers).status_code == 403
        assert (
            api_client.post(
                "/api/v1/ml/switch-model",
                json={"model_name": "xgboost"},
                headers=headers,
            ).status_code
            == 403
        )


def test_T2_F7_05_repeated_model_switches_keep_strictly_one_active_regression(
    fresh_backend_client: httpx.Client,
) -> None:
    admin_h = auth_headers_for(fresh_backend_client, ADMIN_CREDS)
    for model_key in ("linear_regression", "xgboost", "random_forest"):
        sw = fresh_backend_client.post(
            "/api/v1/ml/switch-model", json={"model_name": model_key}, headers=admin_h
        )
        assert sw.status_code == 200, sw.text
        reg_models = get_regression_models(fresh_backend_client, admin_h)
        assert sum(1 for m in reg_models if m["is_active"]) == 1

    all_models = fresh_backend_client.get("/api/v1/ml/models", headers=admin_h).json()
    non_reg_active = [m for m in all_models if "regression" not in m["task"].lower() and m["is_active"]]
    assert len(non_reg_active) >= 2


# ---------------------------------------------------------------------------
# F8: Student Achievement Badges Boundaries
# ---------------------------------------------------------------------------

def test_T2_F8_01_zero_history_student_does_not_falsely_unlock_performance_badges(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    stu = create_fresh_student(api_client, admin_headers, claim=False)
    resp = api_client.get(
        f"/api/v1/analytics/student-badges/{stu['id']}",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    by_title = {b["title"]: b["unlocked"] for b in resp.json()["badges"]}
    assert by_title["Top Performer"] is False
    assert by_title["Attendance Champ"] is False
    assert by_title["Subject Ace"] is False
    assert by_title["All-Rounder"] is False


def test_T2_F8_02_cross_student_badges_scope_returns_404(
    api_client: httpx.Client, student_1_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        f"/api/v1/analytics/student-badges/{STUDENT_2_ID}",
        params={"session_id": SESSION_ID},
        headers=student_1_headers,
    )
    assert resp.status_code == 404


def test_T2_F8_03_unknown_student_badges_returns_404(
    api_client: httpx.Client, admin_headers: Dict[str, str]
) -> None:
    resp = api_client.get(
        "/api/v1/analytics/student-badges/99999",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_T2_F8_04_unauth_and_out_of_scope_teacher_badges(
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
    teacher_sarah_headers: Dict[str, str],
) -> None:
    assert (
        api_client.get(
            f"/api/v1/analytics/student-badges/{STUDENT_1_ID}",
            params={"session_id": SESSION_ID},
        ).status_code
        == 401
    )
    other_cls = create_fresh_class_with_section(api_client, admin_headers)
    other_stu = create_fresh_student(
        api_client, admin_headers, class_id=other_cls["class_id"], section_id=other_cls["section_id"], claim=False
    )
    assert (
        api_client.get(
            f"/api/v1/analytics/student-badges/{other_stu['id']}",
            params={"session_id": SESSION_ID},
            headers=teacher_sarah_headers,
        ).status_code
        == 404
    )


def test_T2_F8_05_attendance_champ_exact_95_pct_threshold(
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
    teacher_sarah_headers: Dict[str, str],
) -> None:
    # 18/19 = 94.7% (<95%) -> locked; then +1 present = 19/20 = 95.0% -> unlocked
    stu = create_fresh_student(api_client, admin_headers, claim=False)
    record_attendance_days(
        api_client, teacher_sarah_headers, student_id=stu["id"], present_count=18, absent_count=1, start_date=date(2026, 4, 1)
    )
    r_below = api_client.get(
        f"/api/v1/analytics/student-badges/{stu['id']}",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert r_below.status_code == 200
    below_map = {b["title"]: b["unlocked"] for b in r_below.json()["badges"]}
    assert below_map["Attendance Champ"] is False

    record_attendance_days(
        api_client, teacher_sarah_headers, student_id=stu["id"], present_count=1, absent_count=0, start_date=date(2026, 5, 1)
    )
    r_at = api_client.get(
        f"/api/v1/analytics/student-badges/{stu['id']}",
        params={"session_id": SESSION_ID},
        headers=admin_headers,
    )
    assert r_at.status_code == 200
    at_map = {b["title"]: b["unlocked"] for b in r_at.json()["badges"]}
    assert at_map["Attendance Champ"] is True
