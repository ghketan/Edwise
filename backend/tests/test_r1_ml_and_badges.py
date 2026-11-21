from datetime import date
import pytest
from backend.app.ml_engine.trainer import train_and_save_artifacts
from backend.app.models.academics import AttendanceRecord, Exam, Mark
from backend.app.models.audit import AuditLog
from backend.app.models.institution import Student
from backend.app.models.ml import ModelRegistry
from backend.tests.conftest import make_token


@pytest.fixture
def seeded_regression_models(db):
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
                trained_by="test_r1",
            ))
    db.commit()
    return meta


# ==============================================================================
# F7: ML Registry, Model Switcher & Live Predict Tests
# ==============================================================================
def test_ml_models_single_active_regression_and_rbac(client, test_data, seeded_regression_models):
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}
    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}

    assert client.get("/api/v1/ml/models", headers=t1_headers).status_code == 403
    assert client.get("/api/v1/ml/models", headers=s1_headers).status_code == 403

    resp = client.get("/api/v1/ml/models", headers=admin_headers)
    assert resp.status_code == 200
    reg_models = [m for m in resp.json() if m["task"] == "regression"]
    assert len(reg_models) == 3
    active_regs = [m for m in reg_models if m["is_active"]]
    assert len(active_regs) == 1
    assert active_regs[0]["version"] == "v1.0.0-reg"


def test_ml_switch_model_and_audit_log(client, db, test_data, seeded_regression_models):
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}
    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}

    # Non-Admin forbidden
    assert client.post("/api/v1/ml/switch-model", json={"model_name": "random_forest"}, headers=t1_headers).status_code == 403
    assert client.post("/api/v1/ml/switch-model", json={"model_name": "random_forest"}, headers=s1_headers).status_code == 403

    # Switch to random_forest -> xgboost -> linear_regression -> exact model_name
    r1 = client.post("/api/v1/ml/switch-model", json={"model_name": "random_forest"}, headers=admin_headers)
    assert r1.status_code == 200
    assert "Random Forest" in r1.json()["active_model"]
    active_after_rf = db.query(ModelRegistry).filter(ModelRegistry.task == "regression", ModelRegistry.is_active.is_(True)).all()
    assert len(active_after_rf) == 1 and active_after_rf[0].version == "v1.0.0-rf"

    audit = db.query(AuditLog).filter(
        AuditLog.action == "ml_model.switched",
        AuditLog.entity_name == "model_registry",
    ).first()
    assert audit is not None
    assert audit.user_id == test_data["admin"].id
    assert audit.new_values["version"] == "v1.0.0-rf"

    r2 = client.post("/api/v1/ml/switch-model", json={"model_name": "xgboost"}, headers=admin_headers)
    assert r2.status_code == 200
    assert "XGBoost" in r2.json()["active_model"]
    active_after_xgb = db.query(ModelRegistry).filter(ModelRegistry.task == "regression", ModelRegistry.is_active.is_(True)).all()
    assert len(active_after_xgb) == 1 and active_after_xgb[0].version == "v1.0.0-xgb"

    r3 = client.post("/api/v1/ml/switch-model", json={"model_name": "linear_regression"}, headers=admin_headers)
    assert r3.status_code == 200
    assert "Linear" in r3.json()["active_model"]

    r4 = client.post(
        "/api/v1/ml/switch-model",
        json={"model_name": "Random Forest Regressor (120 Trees)"},
        headers=admin_headers,
    )
    assert r4.status_code == 200
    assert r4.json()["version"] == "v1.0.0-rf"

    # Invalid / empty model names rejected with 422 without corrupting active flag
    assert client.post("/api/v1/ml/switch-model", json={"model_name": "   "}, headers=admin_headers).status_code == 422
    assert client.post("/api/v1/ml/switch-model", json={"model_name": "nonexistent_algo"}, headers=admin_headers).status_code == 422
    still_active = db.query(ModelRegistry).filter(ModelRegistry.task == "regression", ModelRegistry.is_active.is_(True)).all()
    assert len(still_active) == 1 and still_active[0].version == "v1.0.0-rf"


def test_ml_predict_live_all_roles_and_active_model_reflection(client, test_data, seeded_regression_models):
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}

    payload = {
        "unit_test_score": 82.0,
        "mid_term_score": 80.0,
        "assignment_score": 85.0,
        "practical_score": 84.0,
        "attendance_pct": 92.0,
        "previous_exam_score": 76.0,
        "subject_name": "Mathematics",
    }

    resp = client.post("/api/v1/ml/predict-live", json=payload, headers=s1_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert 0.0 <= data["linear_prediction"] <= 100.0
    assert 0.0 <= data["rf_prediction"] <= 100.0
    assert 0.0 <= data["xgb_prediction"] <= 100.0
    assert "Linear" in data["active_model"]
    assert data["active_prediction"] == data["linear_prediction"]
    assert data["risk_level"] in {"Low Risk", "Medium Risk", "High Risk"}
    assert 0.5 <= data["recommended_study_hours"] <= 4.0

    # Switch to XGBoost and confirm predict-live tracks active model
    assert client.post("/api/v1/ml/switch-model", json={"model_name": "xgboost"}, headers=admin_headers).status_code == 200
    resp_xgb = client.post("/api/v1/ml/predict-live", json=payload, headers=s1_headers)
    assert resp_xgb.status_code == 200
    data_xgb = resp_xgb.json()
    assert "XGBoost" in data_xgb["active_model"]
    assert data_xgb["active_prediction"] == data_xgb["xgb_prediction"]

    # Out-of-range inputs rejected with 422
    assert client.post(
        "/api/v1/ml/predict-live",
        json={**payload, "unit_test_score": -5.0},
        headers=s1_headers,
    ).status_code == 422
    assert client.post(
        "/api/v1/ml/predict-live",
        json={**payload, "attendance_pct": 150.0},
        headers=s1_headers,
    ).status_code == 422


# ==============================================================================
# F8: Student Achievement Badges Tests
# ==============================================================================
def test_student_badges_all_five_badges_and_no_pii(client, db, test_data):
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    s2_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_2'], student_id=test_data['student_2'].id)}"}
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}

    ex_math = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_math"].id,
        name="Badges Math",
        date=date(2026, 10, 5),
        max_marks=100.0,
    )
    ex_sci = Exam(
        session_id=test_data["session"].id,
        class_id=test_data["class_1"].id,
        subject_id=test_data["subj_sci"].id,
        name="Badges Sci",
        date=date(2026, 10, 6),
        max_marks=100.0,
    )
    db.add_all([ex_math, ex_sci])
    db.flush()

    # student_2: 96% avg, 100% att -> Rank #1 + first 4 unlocked
    # student_1: 89% Math, 55% Sci (72% avg), 80% att -> Rank #2, only Subject Ace unlocked
    # student_unclaimed: 45% avg, 50% att -> Rank #3, only Active Learner unlocked
    db.add_all([
        Mark(exam_id=ex_math.id, student_id=test_data["student_2"].id, score=96.0),
        Mark(exam_id=ex_sci.id, student_id=test_data["student_2"].id, score=96.0),
        Mark(exam_id=ex_math.id, student_id=test_data["student_1"].id, score=89.0),
        Mark(exam_id=ex_sci.id, student_id=test_data["student_1"].id, score=55.0),
        Mark(exam_id=ex_math.id, student_id=test_data["student_unclaimed"].id, score=45.0),
        Mark(exam_id=ex_sci.id, student_id=test_data["student_unclaimed"].id, score=45.0),
    ])

    for i in range(4):
        db.add(AttendanceRecord(
            session_id=test_data["session"].id,
            class_id=test_data["class_1"].id,
            subject_id=test_data["subj_math"].id,
            student_id=test_data["student_2"].id,
            date=date(2026, 10, 1 + i),
            status="present",
        ))
    for i, st in enumerate(["present", "present", "present", "present", "absent"]):
        db.add(AttendanceRecord(
            session_id=test_data["session"].id,
            class_id=test_data["class_1"].id,
            subject_id=test_data["subj_math"].id,
            student_id=test_data["student_1"].id,
            date=date(2026, 10, 1 + i),
            status=st,
        ))
    for i, st in enumerate(["present", "absent"]):
        db.add(AttendanceRecord(
            session_id=test_data["session"].id,
            class_id=test_data["class_1"].id,
            subject_id=test_data["subj_math"].id,
            student_id=test_data["student_unclaimed"].id,
            date=date(2026, 10, 1 + i),
            status=st,
        ))
    db.commit()

    # Check Student 2
    r2 = client.get(
        f"/api/v1/analytics/student-badges/{test_data['student_2'].id}?session_id={test_data['session'].id}",
        headers=s2_headers,
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert set(d2.keys()) == {"student_id", "session_id", "rank", "total_students_in_class", "badges"}
    assert d2["rank"] == 1
    assert d2["total_students_in_class"] >= 3
    assert len(d2["badges"]) == 5
    b2 = {b["id"]: b["unlocked"] for b in d2["badges"]}
    assert b2 == {
        "top_performer": True,
        "attendance_champ": True,
        "subject_ace": True,
        "all_rounder": True,
        "active_learner": False,
    }

    # Check Student 1
    r1 = client.get(
        f"/api/v1/analytics/student-badges/{test_data['student_1'].id}?session_id={test_data['session'].id}",
        headers=s1_headers,
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["rank"] == 2
    b1 = {b["id"]: b["unlocked"] for b in d1["badges"]}
    assert b1 == {
        "top_performer": False,
        "attendance_champ": False,
        "subject_ace": True,
        "all_rounder": False,
        "active_learner": False,
    }

    # Check Student Unclaimed (Active Learner fallback)
    r3 = client.get(
        f"/api/v1/analytics/student-badges/{test_data['student_unclaimed'].id}?session_id={test_data['session'].id}",
        headers=admin_headers,
    )
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["rank"] == 3
    b3 = {b["id"]: b["unlocked"] for b in d3["badges"]}
    assert b3 == {
        "top_performer": False,
        "attendance_champ": False,
        "subject_ace": False,
        "all_rounder": False,
        "active_learner": True,
    }


def test_student_badges_zero_marks_edge_case(client, db, test_data):
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}
    solo_student = Student(
        admission_number="STU_SOLO_C2",
        full_name="Solo Student",
        class_id=test_data["class_2"].id,
        is_roster_claimed=False,
    )
    db.add(solo_student)
    db.commit()

    resp = client.get(
        f"/api/v1/analytics/student-badges/{solo_student.id}?session_id={test_data['session'].id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rank"] is None
    assert data["total_students_in_class"] == 1
    badges_map = {b["id"]: b["unlocked"] for b in data["badges"]}
    assert badges_map == {
        "top_performer": False,
        "attendance_champ": False,
        "subject_ace": False,
        "all_rounder": False,
        "active_learner": True,
    }


def test_student_badges_rbac_and_not_found(client, test_data):
    s1_headers = {"Authorization": f"Bearer {make_token(test_data['user_student_1'], student_id=test_data['student_1'].id)}"}
    t1_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_1'], teacher_id=test_data['teacher_1'].id)}"}
    t2_headers = {"Authorization": f"Bearer {make_token(test_data['user_teacher_2'], teacher_id=test_data['teacher_2'].id)}"}
    admin_headers = {"Authorization": f"Bearer {make_token(test_data['user_admin'])}"}

    assert client.get(
        f"/api/v1/analytics/student-badges/{test_data['student_2'].id}?session_id={test_data['session'].id}",
        headers=s1_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/analytics/student-badges/{test_data['student_1'].id}?session_id={test_data['session'].id}",
        headers=t2_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/analytics/student-badges/{test_data['student_1'].id}?session_id={test_data['session'].id}",
        headers=t1_headers,
    ).status_code == 200
    assert client.get(
        f"/api/v1/analytics/student-badges/{test_data['student_1'].id}?session_id={test_data['session'].id}",
        headers=admin_headers,
    ).status_code == 200
    assert client.get(
        f"/api/v1/analytics/student-badges/99999?session_id={test_data['session'].id}",
        headers=admin_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/analytics/student-badges/{test_data['student_1'].id}?session_id=99999",
        headers=admin_headers,
    ).status_code == 404
