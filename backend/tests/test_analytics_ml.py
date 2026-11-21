from datetime import date
import pytest
from backend.app.ml_engine.trainer import train_and_save_artifacts
from backend.app.models.academics import AttendanceRecord, Exam, Mark
from backend.app.models.ml import ModelRegistry
from backend.tests.conftest import make_token


def test_analytics_calculations(client, db, test_data):
    """
    T-010: Computed analytics values equal expected numbers for fixture.
    """
    # Create 4 attendance records: 3 present, 1 absent -> 75%
    for i, st in enumerate(["present", "present", "present", "absent"]):
        db.add(AttendanceRecord(
            session_id=test_data["session"].id,
            class_id=test_data["class_1"].id,
            subject_id=test_data["subj_math"].id,
            student_id=test_data["student_1"].id,
            date=date(2026, 11, 1 + i),
            status=st
        ))
    db.commit()

    token = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(
        f"/api/v1/analytics/attendance?session_id={test_data['session'].id}&student_id={test_data['student_1'].id}",
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_records"] == 4
    assert data["present_count"] == 3
    assert data["absent_count"] == 1
    assert data["overall_attendance_rate"] == 75.0


def test_ml_minimum_history_safeguard(client, db, test_data):
    """
    T-017 & §8.5: If student has fewer than 2 completed exams,
    endpoint returns 'not_enough_data' and NO number.
    """
    token = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    headers = {"Authorization": f"Bearer {token}"}

    # Only 1 exam entered
    exam1 = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_math"].id,
        name="Exam 1",
        date=date(2026, 10, 1),
        max_marks=100.0
    )
    db.add(exam1)
    db.flush()
    db.add(Mark(exam_id=exam1.id, student_id=test_data["student_1"].id, score=80.0))
    db.commit()

    resp = client.get(
        f"/api/v1/students/{test_data['student_1'].id}/estimate?session_id={test_data['session'].id}",
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    # Safeguard check: must return not_enough_data with no number
    assert data["status"] == "not_enough_data"
    assert data["value"] is None
    assert data["interval_lower"] is None
    assert "at least 2 completed exams required" in data["estimate_text"]


def test_ml_prediction_with_truth_wording_and_intervals(client, db, test_data):
    """
    T-012, T-017 & R-015: When >= 2 exams exist, returns estimate with uncertainty interval,
    model version, data source label, synthetic flag, and required truth wording.
    """
    # Ensure trained models are registered in this test DB session
    meta = train_and_save_artifacts()
    for task_name, task_data in meta.items():
        existing = db.query(ModelRegistry).filter(ModelRegistry.version == task_data["version"]).first()
        if not existing:
            db.add(ModelRegistry(
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
                trained_by="test"
            ))
    db.commit()

    # Add 2 completed exams for Student 1
    ex1 = Exam(session_id=test_data["session"].id, class_id=test_data["class_1"].id, subject_id=test_data["subj_math"].id, name="Test 1", date=date(2026, 9, 10), max_marks=50.0)
    ex2 = Exam(session_id=test_data["session"].id, class_id=test_data["class_1"].id, subject_id=test_data["subj_math"].id, name="Test 2", date=date(2026, 10, 10), max_marks=100.0)
    db.add_all([ex1, ex2])
    db.flush()
    db.add(Mark(exam_id=ex1.id, student_id=test_data["student_1"].id, score=40.0))
    db.add(Mark(exam_id=ex2.id, student_id=test_data["student_1"].id, score=85.0))
    db.commit()

    token = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(
        f"/api/v1/students/{test_data['student_1'].id}/estimate?session_id={test_data['session'].id}",
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["value"] is not None
    assert data["interval_lower"] is not None
    assert data["interval_upper"] is not None
    assert data["interval_lower"] <= data["value"] <= data["interval_upper"]
    assert data["is_synthetic"] is True
    assert "estimate from patterns in past data" in data["estimate_text"]
    assert "prompt for teacher review, not an automated verdict" in data["disclaimer"]


def test_recommendation_traceability_and_review(client, db, test_data):
    """
    T-014: Recommendations traceable to indicators and reviewed by teacher.
    """
    token = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    headers = {"Authorization": f"Bearer {token}"}

    # Add low attendance for Student 1 (1 present, 3 absent -> 25%)
    for i, st in enumerate(["present", "absent", "absent", "absent"]):
        db.add(AttendanceRecord(
            session_id=test_data["session"].id,
            class_id=test_data["class_1"].id,
            subject_id=test_data["subj_math"].id,
            student_id=test_data["student_1"].id,
            date=date(2026, 11, 20 + i),
            status=st
        ))
    db.commit()

    # Query student recommendations (triggers rule evaluation)
    resp = client.get(
        f"/api/v1/recommendations/student/{test_data['student_1'].id}?session_id={test_data['session'].id}",
        headers=headers
    )
    assert resp.status_code == 200
    recs = resp.json()
    assert len(recs) >= 1
    low_att_rec = next((r for r in recs if r["rule_code"] == "TEST_ATT_LOW"), None)
    assert low_att_rec is not None
    assert low_att_rec["trigger_value"] == 25.0
    rec_id = low_att_rec["id"]

    # Teacher reviews recommendation
    review_resp = client.put(f"/api/v1/recommendations/{rec_id}/review", json={
        "review_status": "action_taken",
        "review_notes": "Contacted parents regarding attendance drop."
    }, headers=headers)
    assert review_resp.status_code == 200
    assert review_resp.json()["review_status"] == "action_taken"
    assert review_resp.json()["review_notes"] == "Contacted parents regarding attendance drop."
