from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple
import uuid

import httpx

from .auth import auth_headers_for

# Authoritative seeded credentials (backend/seed_data.py)
ADMIN_CREDS: Tuple[str, str] = ("admin", "Admin@123")
TEACHER_SARAH_CREDS: Tuple[str, str] = ("teacher_sarah", "Teacher@123")
TEACHER_ALAN_CREDS: Tuple[str, str] = ("teacher_alan", "Teacher@123")
STUDENT_1_CREDS: Tuple[str, str] = ("STU1001", "Student@123")
STUDENT_2_CREDS: Tuple[str, str] = ("STU1002", "Student@123")

# Seeded entity IDs in edwise.db
SESSION_ID = 1
CLASS_ID = 1
SECTION_A_ID = 1
SECTION_B_ID = 2
SUBJECT_MATH_ID = 1
SUBJECT_SCI_ID = 2
SUBJECT_ENG_ID = 3
SUBJECT_HIST_ID = 4
TEACHER_SARAH_ID = 1
TEACHER_ALAN_ID = 2
STUDENT_1_ID = 1  # STU1001 Alex Carter
STUDENT_2_ID = 2  # STU1002 Priya Sharma
STUDENT_3_ID = 3  # STU1003 David Miller (unclaimed)
STUDENT_4_ID = 4  # STU1004 Emma Watson (unclaimed)
STUDENT_5_ID = 5  # STU1005 Lucas Silva (unclaimed)
STUDENT_6_ID = 6  # STU1006 Aisha Khan (unclaimed)
EXAM_1_ID = 1     # Unit Test 1 - Algebra (Math, max_marks=50)
EXAM_2_ID = 2     # Midterm Examination - Mathematics (Math, max_marks=100)
DOUBT_1_ID = 1    # STU1001, Math, resolved
DOUBT_2_ID = 2    # STU1001, Science, pending


def unique_tag(prefix: str = "E2E") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_exam(
    client: httpx.Client,
    headers: Dict[str, str],
    *,
    session_id: int = SESSION_ID,
    class_id: int = CLASS_ID,
    section_id: Optional[int] = SECTION_A_ID,
    subject_id: int = SUBJECT_MATH_ID,
    name: Optional[str] = None,
    exam_type: str = "exam",
    exam_date: Optional[date] = None,
    time_slot: str = "09:00 AM - 12:00 PM",
    max_marks: float = 100.0,
    weightage: float = 1.0,
) -> dict:
    payload = {
        "session_id": session_id,
        "class_id": class_id,
        "section_id": section_id,
        "subject_id": subject_id,
        "name": name or f"Exam {unique_tag()}",
        "exam_type": exam_type,
        "date": (exam_date or (date.today() + timedelta(days=5))).isoformat(),
        "time_slot": time_slot,
        "max_marks": max_marks,
        "weightage": weightage,
    }
    resp = client.post("/api/v1/exams", json=payload, headers=headers)
    assert resp.status_code == 200, f"create_exam failed: {resp.status_code} {resp.text}"
    return resp.json()


def upload_exam_datesheet(
    client: httpx.Client,
    headers: Dict[str, str],
    exam_id: int,
    filename: str = "datesheet.pdf",
    content: bytes = b"%PDF-1.4 E2E Test Datesheet Content\n%%EOF",
    content_type: str = "application/pdf",
) -> dict:
    resp = client.post(
        f"/api/v1/exams/{exam_id}/datesheet",
        files={"file": (filename, content, content_type)},
        headers=headers,
    )
    assert resp.status_code == 200, f"upload_exam_datesheet failed: {resp.status_code} {resp.text}"
    return resp.json()


def create_announcement(
    client: httpx.Client,
    headers: Dict[str, str],
    *,
    session_id: int = SESSION_ID,
    class_id: Optional[int] = CLASS_ID,
    section_id: Optional[int] = None,
    title: Optional[str] = None,
    content: str = "E2E test announcement content.",
    priority: str = "Normal",
) -> dict:
    resp = client.post(
        "/api/v1/announcements",
        json={
            "session_id": session_id,
            "class_id": class_id,
            "section_id": section_id,
            "title": title or f"Notice {unique_tag()}",
            "content": content,
            "priority": priority,
        },
        headers=headers,
    )
    assert resp.status_code == 200, f"create_announcement failed: {resp.status_code} {resp.text}"
    return resp.json()


def create_doubt(
    client: httpx.Client,
    headers: Dict[str, str],
    *,
    session_id: int = SESSION_ID,
    subject_id: int = SUBJECT_MATH_ID,
    question: Optional[str] = None,
) -> dict:
    resp = client.post(
        "/api/v1/doubts",
        json={
            "session_id": session_id,
            "subject_id": subject_id,
            "question": question or f"Question {unique_tag()}?",
        },
        headers=headers,
    )
    assert resp.status_code == 200, f"create_doubt failed: {resp.status_code} {resp.text}"
    return resp.json()


def claim_student_account(
    client: httpx.Client,
    admission_number: str,
    class_id: int = CLASS_ID,
    password: str = "Student@123",
) -> dict:
    resp = client.post(
        "/api/v1/auth/register-student",
        json={
            "admission_number": admission_number,
            "class_id": class_id,
            "password": password,
            "contact_email": f"{admission_number.lower()}@student.edwise.internal",
        },
    )
    assert resp.status_code == 202, f"claim_student_account failed: {resp.status_code} {resp.text}"
    return resp.json()


def create_fresh_student(
    client: httpx.Client,
    admin_headers: Dict[str, str],
    *,
    class_id: int = CLASS_ID,
    section_id: int = SECTION_A_ID,
    session_id: int = SESSION_ID,
    password: str = "Student@123",
    claim: bool = True,
) -> Dict[str, Any]:
    adm_no = f"STU_{uuid.uuid4().hex[:6].upper()}"
    full_name = f"Test Student {adm_no}"
    imp_resp = client.post(
        "/api/v1/institution/roster/import",
        json={
            "students": [
                {
                    "admission_number": adm_no,
                    "full_name": full_name,
                    "class_id": class_id,
                    "section_id": section_id,
                    "contact_email": f"{adm_no.lower()}@student.edwise.internal",
                }
            ]
        },
        headers=admin_headers,
    )
    assert imp_resp.status_code == 200, f"roster/import failed: {imp_resp.status_code} {imp_resp.text}"

    # Look up the newly created student ID
    st_resp = client.get(
        "/api/v1/institution/students",
        params={"class_id": class_id},
        headers=admin_headers,
    )
    assert st_resp.status_code == 200
    student_obj = next((s for s in st_resp.json() if s["admission_number"] == adm_no), None)
    assert student_obj is not None, f"Created student {adm_no} not found in roster"

    enr_resp = client.post(
        "/api/v1/institution/enrollments",
        json={
            "student_id": student_obj["id"],
            "session_id": session_id,
            "class_id": class_id,
            "section_id": section_id,
            "roll_number": f"R-{adm_no[-4:]}",
        },
        headers=admin_headers,
    )
    assert enr_resp.status_code == 200, f"enrollments failed: {enr_resp.status_code} {enr_resp.text}"

    if claim:
        claim_student_account(client, adm_no, class_id=class_id, password=password)

    return {
        "student": student_obj,
        "id": student_obj["id"],
        "admission_number": adm_no,
        "password": password,
        "full_name": full_name,
        "class_id": class_id,
        "section_id": section_id,
    }


def create_fresh_class_with_section(
    client: httpx.Client,
    admin_headers: Dict[str, str],
    *,
    session_id: int = SESSION_ID,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    cls_resp = client.post(
        "/api/v1/institution/classes",
        json={"name": name or f"Grade {unique_tag()}", "session_id": session_id},
        headers=admin_headers,
    )
    assert cls_resp.status_code == 200, f"create_class failed: {cls_resp.status_code} {cls_resp.text}"
    cls_obj = cls_resp.json()

    sec_resp = client.post(
        "/api/v1/institution/sections",
        json={"name": "A", "class_id": cls_obj["id"]},
        headers=admin_headers,
    )
    assert sec_resp.status_code == 200, f"create_section failed: {sec_resp.status_code} {sec_resp.text}"
    sec_obj = sec_resp.json()
    return {"class": cls_obj, "class_id": cls_obj["id"], "section": sec_obj, "section_id": sec_obj["id"]}


def record_attendance_days(
    client: httpx.Client,
    headers: Dict[str, str],
    *,
    student_id: int,
    present_count: int,
    absent_count: int,
    class_id: int = CLASS_ID,
    section_id: int = SECTION_A_ID,
    subject_id: int = SUBJECT_MATH_ID,
    session_id: int = SESSION_ID,
    start_date: Optional[date] = None,
) -> None:
    base = start_date or date(2026, 1, 1)
    idx = 0
    for status, total in (("present", present_count), ("absent", absent_count)):
        for _ in range(total):
            rec_date = base + timedelta(days=idx)
            idx += 1
            resp = client.put(
                "/api/v1/attendance",
                json={
                    "session_id": session_id,
                    "class_id": class_id,
                    "section_id": section_id,
                    "subject_id": subject_id,
                    "date": rec_date.isoformat(),
                    "entries": [{"student_id": student_id, "status": status}],
                },
                headers=headers,
            )
            assert resp.status_code == 200, f"save_attendance failed: {resp.status_code} {resp.text}"


def save_student_marks(
    client: httpx.Client,
    headers: Dict[str, str],
    exam_id: int,
    entries: List[Dict[str, Any]],
    reason: str = "E2E test setup",
) -> dict:
    resp = client.put(
        "/api/v1/marks",
        json={"exam_id": exam_id, "entries": entries, "reason": reason},
        headers=headers,
    )
    assert resp.status_code == 200, f"save_marks failed: {resp.status_code} {resp.text}"
    return resp.json()


def get_regression_models(client: httpx.Client, admin_headers: Dict[str, str]) -> List[dict]:
    resp = client.get("/api/v1/ml/models", headers=admin_headers)
    assert resp.status_code == 200, f"get_models failed: {resp.status_code} {resp.text}"
    return [m for m in resp.json() if "regression" in str(m.get("task", "")).lower()]
