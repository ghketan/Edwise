import pytest
from datetime import datetime, timezone
from backend.app.models.academics import Assignment
from backend.tests.conftest import make_token


def test_user_verify_and_status_toggle(client, db, test_data):
    """
    Test admin user verification (POST /users/{id}/verify) and user updates.
    """
    admin_token = make_token(test_data["user_admin"])
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Verify student account
    verify_resp = client.post(f"/api/v1/users/{test_data['user_student_1'].id}/verify", headers=admin_headers)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["is_verified"] is True

    # Toggle active status
    update_resp = client.put(f"/api/v1/users/{test_data['user_student_1'].id}", json={
        "is_active": False
    }, headers=admin_headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["is_active"] is False


def test_ml_feature_drift_endpoint(client, db, test_data):
    """
    Test model drift monitoring endpoint (Playbook §8.6, DoD-008).
    """
    from backend.app.models.ml import ModelRegistry

    db.add(ModelRegistry(
        model_name="LinearRegression Baseline",
        version="v1.0.0-reg-test",
        task="regression",
        data_source="Test Synthetic",
        is_synthetic=True,
        feature_list=["attendance_rate", "prior_exam_avg", "assignment_rate"],
        split_method="5-fold",
        metrics={"mae": 4.5, "training_feature_means": {"attendance_rate": 80.0, "prior_exam_avg": 65.0, "assignment_rate": 85.0}},
        artifact_path="none",
        is_active=True
    ))
    db.commit()

    admin_token = make_token(test_data["user_admin"])
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get(f"/api/v1/ml/drift?session_id={test_data['session'].id}", headers=admin_headers)
    assert resp.status_code == 200
    drift_data = resp.json()
    assert "model_version" in drift_data
    assert "feature_drift" in drift_data
    assert "attendance_rate" in drift_data["feature_drift"]
    assert "status" in drift_data
    assert drift_data["threshold"] == 15.0


def test_assignment_attachment_submission(client, db, test_data):
    """
    Test assignment submission with solution link/attachment URL.
    """
    student_token = make_token(test_data["user_student_1"], student_id=test_data["student_1"].id)
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Create assignment
    asg = Assignment(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_math"].id,
        teacher_id=test_data["teacher_1"].id,
        title="Calculus Lab with GitHub Repo",
        max_points=100.0,
        due_date=datetime(2026, 12, 1, 23, 59, tzinfo=timezone.utc)
    )
    db.add(asg)
    db.commit()
    db.refresh(asg)

    # Student submits with attachment URL
    submit_resp = client.post(
        f"/api/v1/assignments/{asg.id}/submit",
        json={
            "assignment_id": asg.id,
            "content": "Repository contains solution notebooks.",
            "attachment_url": "https://github.com/institution/calculus-lab"
        },
        headers=student_headers
    )
    assert submit_resp.status_code == 200
    sub_data = submit_resp.json()
    assert sub_data["attachment_url"] == "https://github.com/institution/calculus-lab"
    assert sub_data["status"] == "submitted"
