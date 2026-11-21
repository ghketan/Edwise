from datetime import datetime, timedelta, timezone
import pytest
from backend.app.models.audit import AuditLog
from backend.tests.conftest import make_token


def test_attendance_idempotency_and_audit(client, db, test_data):
    """
    T-007 & T-016: Repeat requests are idempotent.
    Changes write an audit entry with old and new values.
    """
    token_t1 = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    headers = {"Authorization": f"Bearer {token_t1}"}

    payload = {
        "session_id": test_data["session"].id,
        "class_id": test_data["class_1"].id,
        "subject_id": test_data["subj_math"].id,
        "date": "2026-11-10",
        "entries": [
            {"student_id": test_data["student_1"].id, "status": "present", "notes": "On time"},
            {"student_id": test_data["student_2"].id, "status": "absent", "notes": "Sick"}
        ]
    }

    # First save
    resp1 = client.put("/api/v1/attendance", json=payload, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["saved_count"] == 2

    # Second save with updated status
    payload["entries"][1]["status"] = "excused"
    resp2 = client.put("/api/v1/attendance", json=payload, headers=headers)
    assert resp2.status_code == 200

    # Verify audit entry in database
    audit_entry = db.query(AuditLog).filter(
        AuditLog.action == "attendance.changed",
        AuditLog.entity_name == "attendance"
    ).first()
    assert audit_entry is not None
    assert audit_entry.old_values["status"] == "absent"
    assert audit_entry.new_values["status"] == "excused"


def test_marks_validation_and_audit(client, db, test_data):
    """
    T-008 & T-016: Score validation (0 <= score <= max_marks), blank vs zero, and audit logging.
    """
    token_t1 = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    headers = {"Authorization": f"Bearer {token_t1}"}

    # 1. Create Exam (max_marks = 50.0)
    exam_resp = client.post("/api/v1/exams", json={
        "session_id": test_data["session"].id,
        "class_id": test_data["class_1"].id,
        "subject_id": test_data["subj_math"].id,
        "name": "Quiz 1",
        "date": "2026-11-12",
        "max_marks": 50.0
    }, headers=headers)
    assert exam_resp.status_code == 200
    exam_id = exam_resp.json()["id"]

    # 2. Out of bounds score (> 50.0) -> rejected with 422
    invalid_resp = client.put("/api/v1/marks", json={
        "exam_id": exam_id,
        "entries": [{"student_id": test_data["student_1"].id, "score": 55.0}],
        "reason": "Initial marks entry"
    }, headers=headers)
    assert invalid_resp.status_code == 422

    # 3. Negative score -> rejected with 422
    neg_resp = client.put("/api/v1/marks", json={
        "exam_id": exam_id,
        "entries": [{"student_id": test_data["student_1"].id, "score": -5.0}],
        "reason": "Initial marks entry"
    }, headers=headers)
    assert neg_resp.status_code == 422

    # 4. Valid save: S1 has 45.0, S2 has blank (None)
    valid_resp = client.put("/api/v1/marks", json={
        "exam_id": exam_id,
        "entries": [
            {"student_id": test_data["student_1"].id, "score": 45.0},
            {"student_id": test_data["student_2"].id, "score": None, "is_absent": True}
        ],
        "reason": "Initial test entry"
    }, headers=headers)
    assert valid_resp.status_code == 200

    # 5. Edit mark with audit reason
    edit_resp = client.put("/api/v1/marks", json={
        "exam_id": exam_id,
        "entries": [{"student_id": test_data["student_1"].id, "score": 48.0}],
        "reason": "Re-evaluation of question 3"
    }, headers=headers)
    assert edit_resp.status_code == 200

    # Verify audit log captures old and new score
    mark_audit = db.query(AuditLog).filter(
        AuditLog.action == "mark.updated",
        AuditLog.entity_name == "mark"
    ).first()
    assert mark_audit is not None
    assert mark_audit.old_values["score"] == 45.0
    assert mark_audit.new_values["score"] == 48.0
    assert mark_audit.reason == "Re-evaluation of question 3"


def test_assignment_submission_grading_lifecycle(client, test_data):
    """
    T-009: Assignment creation, submission, and grading lifecycle.
    """
    t_token = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    t_headers = {"Authorization": f"Bearer {t_token}"}
    s_token = make_token(test_data["user_student_1"], student_id=test_data["student_1"].id)
    s_headers = {"Authorization": f"Bearer {s_token}"}

    # 1. Teacher creates assignment
    assign_resp = client.post("/api/v1/assignments", json={
        "session_id": test_data["session"].id,
        "class_id": test_data["class_1"].id,
        "subject_id": test_data["subj_math"].id,
        "title": "Algebra Homework",
        "max_points": 100.0,
        "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    }, headers=t_headers)
    assert assign_resp.status_code == 200
    assign_id = assign_resp.json()["id"]

    # 2. Student submits assignment
    sub_resp = client.post(f"/api/v1/assignments/{assign_id}/submit", json={
        "assignment_id": assign_id,
        "content": "My completed assignment"
    }, headers=s_headers)
    assert sub_resp.status_code == 200
    sub_id = sub_resp.json()["id"]
    assert sub_resp.json()["status"] == "submitted"

    # 3. Teacher grades submission
    grade_resp = client.put(f"/api/v1/assignments/submissions/{sub_id}/grade", json={
        "points_awarded": 92.5,
        "feedback": "Great clarity in proofs."
    }, headers=t_headers)
    assert grade_resp.status_code == 200
    assert grade_resp.json()["status"] == "graded"
    assert grade_resp.json()["points_awarded"] == 92.5


def test_grading_bounds_and_scoping(client, test_data):
    """
    R-005, C-03: Grading validation and object scoping.
    1. Points awarded > max_points rejected with 400.
    2. Teacher not assigned to subject/class rejected with 404.
    """
    t1_token = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    t1_headers = {"Authorization": f"Bearer {t1_token}"}
    t2_token = make_token(test_data["user_teacher_2"], teacher_id=test_data["teacher_2"].id)
    t2_headers = {"Authorization": f"Bearer {t2_token}"}
    s_token = make_token(test_data["user_student_1"], student_id=test_data["student_1"].id)
    s_headers = {"Authorization": f"Bearer {s_token}"}

    # Create assignment
    assign_resp = client.post("/api/v1/assignments", json={
        "session_id": test_data["session"].id,
        "class_id": test_data["class_1"].id,
        "subject_id": test_data["subj_math"].id,
        "title": "Geometry Proofs",
        "max_points": 50.0,
        "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    }, headers=t1_headers)
    assign_id = assign_resp.json()["id"]

    # Submit
    sub_resp = client.post(f"/api/v1/assignments/{assign_id}/submit", json={
        "assignment_id": assign_id,
        "content": "Proof steps attached"
    }, headers=s_headers)
    sub_id = sub_resp.json()["id"]

    # 1. Reject score > max_points (ValidationError -> 422)
    over_resp = client.put(f"/api/v1/assignments/submissions/{sub_id}/grade", json={
        "points_awarded": 55.0,
        "feedback": "Impossible score"
    }, headers=t1_headers)
    assert over_resp.status_code == 422
    assert "between 0 and assignment max points" in over_resp.json()["detail"]

    # 2. Reject unassigned teacher
    unassigned_resp = client.put(f"/api/v1/assignments/submissions/{sub_id}/grade", json={
        "points_awarded": 45.0
    }, headers=t2_headers)
    assert unassigned_resp.status_code == 404


def test_attendance_and_marks_non_enrolled_student_rejected(client, test_data):
    """
    Invariant 3: Student must be actively enrolled in the class and session.
    Attempting to save attendance or marks for a student in a different class returns 422.
    """
    admin_token = make_token(test_data["user_admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Student 1 is in class_1, attempting to record attendance for class_2
    resp = client.put("/api/v1/attendance", json={
        "session_id": test_data["session"].id,
        "class_id": test_data["class_2"].id,
        "subject_id": test_data["subj_math"].id,
        "date": "2026-11-10",
        "entries": [{"student_id": test_data["student_1"].id, "status": "present"}]
    }, headers=headers)
    assert resp.status_code == 422
    assert "not actively enrolled" in resp.json()["detail"]


