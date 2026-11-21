import pytest
from backend.app.models.user import User, UserRole


def test_login_success(client, test_data):
    response = client.post("/api/v1/auth/login", json={
        "username": "test_admin",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "ADMINISTRATOR"
    assert data["username"] == "test_admin"


def test_login_invalid_password(client, test_data):
    response = client.post("/api/v1/auth/login", json={
        "username": "test_admin",
        "password": "wrong_password"
    })
    assert response.status_code == 401
    assert "detail" in response.json()


def test_login_inactive_user(client, db, test_data):
    user = test_data["user_student_1"]
    user.is_active = False
    db.commit()

    response = client.post("/api/v1/auth/login", json={
        "username": "STU001",
        "password": "password123"
    })
    assert response.status_code == 401


def test_student_registration_claim_roster_success(client, db, test_data):
    """
    T-006: Student registers with unclaimed admission number matching roster.
    """
    unclaimed = test_data["student_unclaimed"]
    req = {
        "admission_number": unclaimed.admission_number,
        "class_id": unclaimed.class_id,
        "password": "NewStudent@123",
        "contact_email": "new.student@school.internal"
    }

    response = client.post("/api/v1/auth/register-student", json=req)
    assert response.status_code == 202
    assert response.json()["status"] in ("verified", "pending_verification")

    # Now verify the student can log in with new password
    login_resp = client.post("/api/v1/auth/login", json={
        "username": unclaimed.admission_number,
        "password": "NewStudent@123"
    })
    assert login_resp.status_code == 200
    assert login_resp.json()["role"] == "STUDENT"


def test_student_registration_enumeration_defense(client, test_data):
    """
    T-006: Unknown admission number and wrong class yield uniform 202 responses
    so attacker cannot enumerate valid admission numbers.
    """
    # 1. Unknown admission number
    resp_unknown = client.post("/api/v1/auth/register-student", json={
        "admission_number": "STU_DOES_NOT_EXIST",
        "class_id": test_data["class_1"].id,
        "password": "password123"
    })
    assert resp_unknown.status_code == 202
    assert resp_unknown.json()["status"] == "pending_verification"

    # 2. Wrong class ID for existing student
    resp_wrong_class = client.post("/api/v1/auth/register-student", json={
        "admission_number": test_data["student_unclaimed"].admission_number,
        "class_id": test_data["class_2"].id,  # wrong class
        "password": "password123"
    })
    assert resp_wrong_class.status_code == 202
    assert resp_wrong_class.json()["status"] == "pending_verification"

    # 3. Already claimed student
    resp_claimed = client.post("/api/v1/auth/register-student", json={
        "admission_number": "STU001",
        "class_id": test_data["class_1"].id,
        "password": "password123"
    })
    assert resp_claimed.status_code == 202
    assert resp_claimed.json()["status"] == "pending_verification"


def test_password_exceeding_72_bytes_rejected(client, test_data):
    """
    H-05: Bcrypt truncates or crashes at >72 bytes.
    Pydantic schema must reject >72 character passwords with 422.
    """
    long_pwd = "A" * 75
    resp = client.post("/api/v1/auth/login", json={
        "username": "test_admin",
        "password": long_pwd
    })
    assert resp.status_code == 422


def test_unverified_user_cannot_login(client, db, test_data):
    """
    C-05: Unverified user cannot log in.
    """
    user = test_data["user_student_2"]
    user.is_verified = False
    db.commit()

    resp = client.post("/api/v1/auth/login", json={
        "username": "STU002",
        "password": "password123"
    })
    assert resp.status_code == 401



