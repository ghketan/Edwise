import pytest
from backend.tests.conftest import make_token


def test_student_forbidden_from_admin_endpoints(client, test_data):
    """T-003: Student role denied access to admin endpoints."""
    token = make_token(test_data["user_student_1"], student_id=test_data["student_1"].id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/v1/institution/sessions", json={
        "name": "Hacked Session",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31"
    }, headers=headers)
    assert resp.status_code == 403


def test_student_forbidden_from_recording_attendance(client, test_data):
    """T-003: Student cannot record attendance."""
    token = make_token(test_data["user_student_1"], student_id=test_data["student_1"].id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/api/v1/attendance", json={
        "session_id": test_data["session"].id,
        "class_id": test_data["class_1"].id,
        "subject_id": test_data["subj_math"].id,
        "date": "2026-11-01",
        "entries": [{"student_id": test_data["student_1"].id, "status": "present"}]
    }, headers=headers)
    assert resp.status_code == 403


def test_student_forbidden_from_ml_predictions(client, test_data):
    """T-003 & D-012: Student cannot view predictions or risk flags."""
    token = make_token(test_data["user_student_1"], student_id=test_data["student_1"].id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(
        f"/api/v1/students/{test_data['student_1'].id}/estimate?session_id={test_data['session'].id}",
        headers=headers
    )
    assert resp.status_code == 403


def test_student_tampering_other_student_records(client, test_data):
    """
    T-004: Direct-URL tampering: Student 1 attempts to view Student 2's marks.
    Expect 404 (out of scope) to avoid confirming object existence.
    """
    token_s1 = make_token(test_data["user_student_1"], student_id=test_data["student_1"].id)
    headers = {"Authorization": f"Bearer {token_s1}"}

    # S1 tries to access S2's marks
    resp = client.get(f"/api/v1/marks/student/{test_data['student_2'].id}", headers=headers)
    assert resp.status_code == 404


def test_teacher_scope_unassigned_class_rejected(client, test_data):
    """
    T-004 & T-007: Teacher 2 is NOT assigned to Class 10 Math.
    Attempting to save attendance for Class 10 Math must return 404.
    """
    token_t2 = make_token(test_data["user_teacher_2"], teacher_id=test_data["teacher_2"].id)
    headers = {"Authorization": f"Bearer {token_t2}"}

    resp = client.put("/api/v1/attendance", json={
        "session_id": test_data["session"].id,
        "class_id": test_data["class_1"].id,
        "subject_id": test_data["subj_math"].id,
        "date": "2026-11-05",
        "entries": [{"student_id": test_data["student_1"].id, "status": "present"}]
    }, headers=headers)
    assert resp.status_code == 404


def test_assigned_teacher_allowed(client, test_data):
    """
    T-007: Teacher 1 is assigned to Class 10 Math and can save attendance.
    """
    token_t1 = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    headers = {"Authorization": f"Bearer {token_t1}"}

    resp = client.put("/api/v1/attendance", json={
        "session_id": test_data["session"].id,
        "class_id": test_data["class_1"].id,
        "subject_id": test_data["subj_math"].id,
        "date": "2026-11-05",
        "entries": [{"student_id": test_data["student_1"].id, "status": "present"}]
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["saved_count"] == 1


def test_unassigned_teacher_cannot_view_student_details(client, test_data):
    """
    C-02, D-004: Teacher 2 is not assigned to Class 10 where Student 1 belongs.
    Teacher 2 requesting GET /api/v1/students/{id} must return 404.
    """
    token_t2 = make_token(test_data["user_teacher_2"], teacher_id=test_data["teacher_2"].id)
    headers = {"Authorization": f"Bearer {token_t2}"}

    resp = client.get(f"/api/v1/students/{test_data['student_1'].id}", headers=headers)
    assert resp.status_code == 404


def test_assigned_teacher_can_view_student_details(client, test_data):
    """
    C-02, D-004: Teacher 1 is assigned to Class 10 Math where Student 1 belongs.
    Teacher 1 requesting GET /api/v1/students/{id} succeeds.
    """
    token_t1 = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    headers = {"Authorization": f"Bearer {token_t1}"}

    resp = client.get(f"/api/v1/students/{test_data['student_1'].id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["admission_number"] == test_data["student_1"].admission_number


def test_unassigned_teacher_cannot_access_student_reports_or_ml(client, test_data):
    """
    C-02: Teacher 2 cannot view reports or ML estimates for Student 1.
    Must return 404 to avoid object enumeration.
    """
    token_t2 = make_token(test_data["user_teacher_2"], teacher_id=test_data["teacher_2"].id)
    headers = {"Authorization": f"Bearer {token_t2}"}

    # 1. Report
    resp_report = client.get(
        f"/api/v1/reports/student/{test_data['student_1'].id}/pdf?session_id={test_data['session'].id}",
        headers=headers
    )
    assert resp_report.status_code == 404

    # 2. ML Estimate
    resp_ml = client.get(
        f"/api/v1/students/{test_data['student_1'].id}/estimate?session_id={test_data['session'].id}",
        headers=headers
    )
    assert resp_ml.status_code == 404


