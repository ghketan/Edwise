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


def test_class_subjects_management_and_scoping(client, db, test_data):
    """
    Test independent class subjects configuration:
    - Admin creates/links subject to class
    - Listing returns class-specific subjects
    - Unlinking removes the association
    """
    admin_token = make_token(test_data["user_admin"])
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    class_id = test_data["class_1"].id
    sub_id = test_data["subj_math"].id

    # 1. Assign existing subject to class
    assign_resp = client.post(
        f"/api/v1/institution/classes/{class_id}/subjects",
        json={"subject_id": sub_id},
        headers=admin_headers
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["id"] == sub_id

    # 2. Get class subjects
    get_resp = client.get(
        f"/api/v1/institution/classes/{class_id}/subjects",
        headers=admin_headers
    )
    assert get_resp.status_code == 200
    sub_ids = [s["id"] for s in get_resp.json()]
    assert sub_id in sub_ids

    # 3. Create brand new subject directly for this class
    new_sub_resp = client.post(
        f"/api/v1/institution/classes/{class_id}/subjects",
        json={"name": "Applied Robotics", "code": "ROB101", "description": "Hands-on robotics"},
        headers=admin_headers
    )
    assert new_sub_resp.status_code == 200
    new_sub_id = new_sub_resp.json()["id"]
    assert new_sub_resp.json()["code"] == "ROB101"

    # 4. Remove subject from class
    del_resp = client.delete(
        f"/api/v1/institution/classes/{class_id}/subjects/{new_sub_id}",
        headers=admin_headers
    )
    assert del_resp.status_code == 200


def test_attendance_full_day_vs_single_subject(client, db, test_data):
    """
    Test teacher attendance marking:
    - Full-day attendance creates records across class subjects
    - Single-subject attendance updates only that subject
    - Verifies 'entries' payload format
    """
    from datetime import date
    teacher_token = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    class_id = test_data["class_1"].id
    student_id = test_data["student_1"].id
    session_id = test_data["session"].id
    today = str(date.today())

    # 1. Full-day attendance (all subjects)
    full_day_resp = client.put(
        "/api/v1/attendance",
        json={
            "session_id": session_id,
            "class_id": class_id,
            "subject_id": None,
            "is_full_day": True,
            "date": today,
            "entries": [
                {"student_id": student_id, "status": "present", "notes": "Full day present"}
            ]
        },
        headers=teacher_headers
    )
    assert full_day_resp.status_code == 200
    assert full_day_resp.json()["status"] == "success"

    # 2. Specific subject attendance (e.g. mark absent specifically in math)
    subject_resp = client.put(
        "/api/v1/attendance",
        json={
            "session_id": session_id,
            "class_id": class_id,
            "subject_id": test_data["subj_math"].id,
            "date": today,
            "entries": [
                {"student_id": student_id, "status": "absent", "notes": "Missed math period"}
            ]
        },
        headers=teacher_headers
    )
    assert subject_resp.status_code == 200

    # 3. Verify math attendance is now absent
    att_resp = client.get(
        f"/api/v1/attendance?session_id={session_id}&class_id={class_id}&subject_id={test_data['subj_math'].id}&date={today}",
        headers=teacher_headers
    )
    assert att_resp.status_code == 200
    math_recs = [r for r in att_resp.json() if r["student_id"] == student_id]
    assert len(math_recs) == 1
    assert math_recs[0]["status"] == "absent"


def test_student_assignment_file_upload_and_serving(client, db, test_data):
    """
    Test student handwritten assignment file upload and file retrieval:
    - Student uploads file (PDF / image)
    - Verifies attachment_url is generated
    - Verifies file content is retrievable via GET /assignments/files/{filename}
    """
    student_token = make_token(test_data["user_student_1"], student_id=test_data["student_1"].id)
    student_headers = {"Authorization": f"Bearer {student_token}"}

    asg = Assignment(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_math"].id,
        teacher_id=test_data["teacher_1"].id,
        title="Handwritten Calculus Homework",
        max_points=50.0,
        due_date=datetime(2026, 12, 10, 23, 59, tzinfo=timezone.utc)
    )
    db.add(asg)
    db.commit()
    db.refresh(asg)

    # Fake handwritten PDF file bytes
    file_bytes = b"%PDF-1.4 Mock handwritten student homework submission."
    files = {"file": ("homework_scan.pdf", file_bytes, "application/pdf")}
    data = {"content": "Uploaded handwritten steps for problems 1 to 5."}

    upload_resp = client.post(
        f"/api/v1/assignments/{asg.id}/submit-file",
        files=files,
        data=data,
        headers=student_headers
    )
    assert upload_resp.status_code == 200
    sub_data = upload_resp.json()
    assert sub_data["attachment_url"] is not None
    assert "/api/v1/assignments/files/" in sub_data["attachment_url"]
    assert sub_data["status"] == "submitted"

    # Retrieve uploaded file
    filename = sub_data["attachment_url"].split("/")[-1]
    get_file_resp = client.get(
        f"/api/v1/assignments/files/{filename}",
        headers=student_headers
    )
    assert get_file_resp.status_code == 200
    assert get_file_resp.content == file_bytes
