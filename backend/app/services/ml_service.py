import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.academics import Assignment, AttendanceRecord, Exam, Mark, Submission
from backend.app.models.institution import Enrollment, Student
from backend.app.models.ml import ModelRegistry, Prediction
from backend.app.schemas.ml import (
    ClusterExplorationResponse,
    ClusterGroup,
    FeatureDriftDetail,
    LivePredictInput,
    LivePredictOutput,
    ModelDriftResponse,
    ModelRegistryResponse,
    StudentEstimateResponse,
)
from backend.app.services.analytics_service import get_attendance_analytics
from backend.app.services.audit_service import create_audit_entry

_ARTIFACT_CACHE: Dict[str, Tuple[float, Any]] = {}


def _load_artifact_cached(path: str) -> Optional[Any]:
    if not path or not os.path.exists(path):
        return None
    abs_path = os.path.abspath(path)
    mtime = os.path.getmtime(abs_path)
    cached = _ARTIFACT_CACHE.get(abs_path)
    if cached and cached[0] == mtime:
        return cached[1]
    artifact = joblib.load(abs_path)
    _ARTIFACT_CACHE[abs_path] = (mtime, artifact)
    return artifact


def get_active_model(db: Session, task: str) -> Optional[ModelRegistry]:
    return db.query(ModelRegistry).filter(
        ModelRegistry.task == task,
        ModelRegistry.is_active.is_(True)
    ).order_by(ModelRegistry.trained_at.desc()).first()


def resolve_artifact_path(stored_path: str) -> str:
    """Resolve artifact path robustly across Windows and Docker Linux environments (H-08)."""
    if os.path.exists(stored_path):
        return stored_path
    base_name = os.path.basename(stored_path)
    fallback = os.path.join(settings.MODEL_ARTIFACTS_DIR, base_name)
    return fallback


def extract_student_features(
    db: Session,
    student_id: int,
    session_id: int
) -> dict:
    """
    Extracts strictly academic behaviour features per D-015, C-06:
    prior_exam_avg, attendance_rate, assignment_rate, exam_count.
    Properly scoped to the student's class and session.
    """
    # 1. Exam marks in session
    marks = db.query(Mark).join(Exam, Mark.exam_id == Exam.id).filter(
        Mark.student_id == student_id,
        Exam.session_id == session_id,
        Mark.score.isnot(None),
        Mark.is_absent.is_(False)
    ).all()

    exam_count = len(marks)
    if exam_count > 0:
        pcts = [(m.score / m.exam.max_marks) * 100 for m in marks if m.exam.max_marks > 0]
        prior_exam_avg = round(float(np.mean(pcts)), 2) if pcts else 0.0
    else:
        prior_exam_avg = 0.0

    # 2. Attendance rate in session
    att = get_attendance_analytics(db, session_id=session_id, student_id=student_id)
    has_attendance = att.total_records > 0
    attendance_rate = att.overall_attendance_rate if has_attendance else 85.0

    # 3. Assignment submission rate scoped to student's class (C-06)
    student = db.query(Student).filter(Student.id == student_id).first()
    enr = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.session_id == session_id
    ).first()
    class_id = enr.class_id if enr else (student.class_id if student else None)
    section_id = enr.section_id if enr else (student.section_id if student else None)

    assign_query = db.query(Assignment).filter(
        Assignment.session_id == session_id,
        Assignment.class_id == class_id
    )
    if section_id:
        assign_query = assign_query.filter(
            (Assignment.section_id == section_id) | (Assignment.section_id.is_(None))
        )
    class_assignments = assign_query.all()
    class_assign_ids = [a.id for a in class_assignments]

    if class_assign_ids:
        submitted_count = db.query(Submission).filter(
            Submission.student_id == student_id,
            Submission.assignment_id.in_(class_assign_ids)
        ).count()
        assignment_rate = round(float(np.clip((submitted_count / len(class_assign_ids)) * 100, 0, 100)), 2)
    else:
        assignment_rate = 100.0  # neutral if no assignments configured for class

    return {
        "exam_count": exam_count,
        "prior_exam_avg": prior_exam_avg,
        "attendance_rate": attendance_rate,
        "has_attendance": has_attendance,
        "assignment_rate": assignment_rate
    }


def get_student_prediction(
    db: Session,
    student_id: int,
    session_id: int
) -> StudentEstimateResponse:
    """
    Contract API-003, R-009, R-010, R-015, D-005, D-012, H-08:
    Inference endpoint with minimum-history guard (>=2 exams required) and strict truth wording.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    today_utc = datetime.now(timezone.utc).date()
    features = extract_student_features(db, student_id=student_id, session_id=session_id)

    # Minimum history safeguard (§8.5, UI-005, T-017)
    if features["exam_count"] < 2:
        return StudentEstimateResponse(
            status="not_enough_data",
            value=None,
            interval_lower=None,
            interval_upper=None,
            confidence=None,
            risk_level=None,
            model_version=None,
            data_source_label=None,
            is_synthetic=False,
            data_through=str(today_utc),
            reason_codes=[f"Completed exams: {features['exam_count']} (minimum 2 required)"],
            estimate_text="Not enough data: at least 2 completed exams required before generating estimate."
        )

    # Fetch active regression model
    reg_registry = get_active_model(db, task="regression")
    clf_registry = get_active_model(db, task="classification")

    if not reg_registry:
        return StudentEstimateResponse(
            status="model_unavailable",
            estimate_text="Prediction unavailable: active model or artifact missing."
        )

    reg_path = resolve_artifact_path(reg_registry.artifact_path)
    if not os.path.exists(reg_path):
        return StudentEstimateResponse(
            status="model_unavailable",
            estimate_text="Prediction unavailable: active model or artifact missing."
        )

    # Load artifacts
    reg_artifact = _load_artifact_cached(reg_path)
    reg_model = reg_artifact["model"]
    residual_std = reg_artifact.get("residual_std", 6.0)

    # Feature DataFrame conforming to training feature names
    X = pd.DataFrame([{
        "prior_exam_avg": features["prior_exam_avg"],
        "attendance_rate": features["attendance_rate"],
        "assignment_rate": features["assignment_rate"]
    }])

    pred_score = float(np.clip(reg_model.predict(X)[0], 0, 100))
    pred_score = round(pred_score, 2)

    # Uncertainty interval (95% CI approximately 1.96 * residual_std)
    interval_lower = round(float(np.clip(pred_score - 1.96 * residual_std, 0, 100)), 2)
    interval_upper = round(float(np.clip(pred_score + 1.96 * residual_std, 0, 100)), 2)

    # Risk level from classification if available
    risk_level = "low"
    if clf_registry:
        clf_path = resolve_artifact_path(clf_registry.artifact_path)
        clf_artifact = _load_artifact_cached(clf_path)
        if clf_artifact is not None:
            clf_model = clf_artifact["model"]
            probs = clf_model.predict_proba(X)[0]
            risk_prob = float(probs[1]) if len(probs) > 1 else 0.0
            if risk_prob >= 0.5:
                risk_level = "high"
            elif risk_prob >= 0.25:
                risk_level = "medium"
            else:
                risk_level = "low"

    reason_codes = [
        f"Prior exam avg: {features['prior_exam_avg']}%",
        f"Attendance rate: {features['attendance_rate']}%" if features["has_attendance"] else "Attendance: baseline assumed (no records logged)",
        f"Assignment completion: {features['assignment_rate']}%"
    ]

    calibrated_confidence = round(float(np.clip(1.0 - (residual_std / 30.0), 0.1, 0.99)), 2)

    # Store prediction record
    prediction_record = Prediction(
        student_id=student.id,
        session_id=session_id,
        model_id=reg_registry.id,
        task="regression",
        predicted_value=pred_score,
        interval_lower=interval_lower,
        interval_upper=interval_upper,
        confidence=calibrated_confidence,
        risk_level=risk_level,
        reason_codes=reason_codes,
        data_through_date=today_utc,
        is_synthetic=reg_registry.is_synthetic
    )
    db.add(prediction_record)
    db.commit()

    return StudentEstimateResponse(
        status="success",
        value=pred_score,
        interval_lower=interval_lower,
        interval_upper=interval_upper,
        confidence=calibrated_confidence,
        risk_level=risk_level,
        model_version=reg_registry.version,
        data_source_label=reg_registry.data_source,
        is_synthetic=reg_registry.is_synthetic,
        data_through=str(today_utc),
        reason_codes=reason_codes,
        estimate_text=f"an estimate from patterns in past data, version {reg_registry.version}, trained on {reg_registry.data_source}"
    )


def get_kmeans_clusters(
    db: Session,
    session_id: int
) -> ClusterExplorationResponse:
    """
    K-Means student pattern exploration (R-011).
    Exploratory pattern analysis strictly based on academic engagement metrics.
    """
    clust_registry = get_active_model(db, task="clustering")
    if not clust_registry:
        return ClusterExplorationResponse(
            model_version="v1.0.0-clust",
            n_clusters=0,
            is_synthetic=True,
            clusters=[]
        )

    clust_path = resolve_artifact_path(clust_registry.artifact_path)
    clust_artifact = _load_artifact_cached(clust_path)
    if clust_artifact is None:
        return ClusterExplorationResponse(
            model_version=clust_registry.version,
            n_clusters=0,
            is_synthetic=clust_registry.is_synthetic,
            clusters=[]
        )

    centers_data = clust_artifact.get("cluster_centers", [])

    clusters = [
        ClusterGroup(
            cluster_id=c["cluster_id"],
            cluster_label=c["label"],
            student_count=c["student_count"],
            feature_means=c["feature_means"],
            description=c["description"]
        )
        for c in centers_data
    ]

    return ClusterExplorationResponse(
        model_version=clust_registry.version,
        n_clusters=len(clusters),
        is_synthetic=clust_registry.is_synthetic,
        clusters=clusters
    )


def calculate_feature_drift(
    db: Session,
    session_id: int
) -> ModelDriftResponse:
    """
    Model feature drift monitoring (Playbook §8.6, DoD-008):
    Compares current academic session feature means against training registry baselines.
    """
    reg_registry = get_active_model(db, task="regression")
    if not reg_registry:
        return ModelDriftResponse(
            model_version="offline-v1.0",
            session_id=session_id,
            feature_drift={},
            drift_detected=False,
            status="no_model",
            threshold=15.0,
            note="No active regression model registered in the system."
        )

    baseline_means = {
        "attendance_rate": 81.5,
        "prior_exam_avg": 66.8,
        "assignment_rate": 83.2,
    }
    if reg_registry.metrics and isinstance(reg_registry.metrics, dict):
        if "training_feature_means" in reg_registry.metrics:
            baseline_means.update(reg_registry.metrics["training_feature_means"])

    students = db.query(Student).all()
    if not students:
        return ModelDriftResponse(
            model_version=reg_registry.version,
            session_id=session_id,
            feature_drift={},
            drift_detected=False,
            status="no_data",
            threshold=15.0,
            note="No student records present in session to compute feature drift."
        )

    att_vals = []
    exam_vals = []
    asg_vals = []

    for s in students:
        feats = extract_student_features(db, student_id=s.id, session_id=session_id)
        att_vals.append(feats["attendance_rate"])
        if feats["exam_count"] > 0:
            exam_vals.append(feats["prior_exam_avg"])
        asg_vals.append(feats["assignment_rate"])

    curr_att = float(np.mean(att_vals)) if att_vals else baseline_means["attendance_rate"]
    curr_exam = float(np.mean(exam_vals)) if exam_vals else baseline_means["prior_exam_avg"]
    curr_asg = float(np.mean(asg_vals)) if asg_vals else baseline_means["assignment_rate"]

    current_means = {
        "attendance_rate": round(curr_att, 1),
        "prior_exam_avg": round(curr_exam, 1),
        "assignment_rate": round(curr_asg, 1),
    }

    threshold_pct = 15.0
    drift_detected = False
    drift_details = {}

    for feature, base_val in baseline_means.items():
        curr_val = current_means.get(feature, base_val)
        delta = round(curr_val - base_val, 1)
        pct_diff = round(abs(delta) / base_val * 100.0, 1) if base_val > 0 else 0.0
        drift_flag = pct_diff > threshold_pct
        if drift_flag:
            drift_detected = True

        drift_details[feature] = FeatureDriftDetail(
            baseline_mean=base_val,
            session_mean=curr_val,
            delta=delta,
            percent_difference=pct_diff,
            drift_flag=drift_flag,
        )

    return ModelDriftResponse(
        model_version=reg_registry.version,
        session_id=session_id,
        feature_drift=drift_details,
        drift_detected=drift_detected,
        status="drift_warning" if drift_detected else "normal",
        threshold=threshold_pct,
        note="Comparison of current session feature means against training registry baselines (Playbook §8.6). If drift exceeds threshold, model retraining is prompted."
    )


def predict_live_simulator(data: LivePredictInput, db: Session) -> LivePredictOutput:
    """
    Live real-time 'What-If' performance score simulation across
    Linear Regression, Random Forest, and XGBoost models.
    """
    prior_exam_avg = float(np.mean([data.unit_test_score, data.mid_term_score, data.previous_exam_score]))
    attendance_rate = float(data.attendance_pct)
    assignment_rate = float(np.mean([data.assignment_score, data.practical_score]))

    X = pd.DataFrame([{
        "prior_exam_avg": prior_exam_avg,
        "attendance_rate": attendance_rate,
        "assignment_rate": assignment_rate
    }])

    # 1. Linear Regression
    lin_pred = 74.0
    lin_path = resolve_artifact_path(os.path.join(settings.MODEL_ARTIFACTS_DIR, "regression_v1.joblib"))
    try:
        lin_art = _load_artifact_cached(lin_path)
        if lin_art is not None:
            lin_pred = float(np.clip(lin_art["model"].predict(X)[0], 0, 100))
    except Exception:
        pass

    # 2. Random Forest
    rf_pred = 77.0
    rf_path = resolve_artifact_path(os.path.join(settings.MODEL_ARTIFACTS_DIR, "random_forest_v1.joblib"))
    try:
        rf_art = _load_artifact_cached(rf_path)
        if rf_art is not None:
            rf_pred = float(np.clip(rf_art["model"].predict(X)[0], 0, 100))
    except Exception:
        pass

    # 3. XGBoost
    xgb_pred = 79.0
    xgb_path = resolve_artifact_path(os.path.join(settings.MODEL_ARTIFACTS_DIR, "xgboost_v1.joblib"))
    try:
        xgb_art = _load_artifact_cached(xgb_path)
        if xgb_art is not None:
            xgb_pred = float(np.clip(xgb_art["model"].predict(X)[0], 0, 100))
    except Exception:
        pass

    active_reg = get_active_model(db, task="regression")
    active_name = active_reg.model_name if active_reg else "Linear Regression"
    active_name_lower = active_name.lower()
    if "random forest" in active_name_lower:
        active_pred = rf_pred
    elif "xgboost" in active_name_lower:
        active_pred = xgb_pred
    else:
        active_pred = lin_pred

    active_pred = round(active_pred, 1)
    rf_pred = round(rf_pred, 1)
    xgb_pred = round(xgb_pred, 1)
    lin_pred = round(lin_pred, 1)

    prev = max(1.0, data.previous_exam_score)
    imp_pct = round(((active_pred - prev) / prev) * 100.0, 1)

    if attendance_rate < 70.0 or active_pred < 55.0:
        risk_level = "High Risk"
    elif attendance_rate < 80.0 or active_pred < 68.0:
        risk_level = "Medium Risk"
    else:
        risk_level = "Low Risk"

    deficit = max(0.0, 85.0 - active_pred)
    study_hours = round(max(0.5, min(4.0, 0.5 + (deficit / 15.0))), 1)
    extra_time = round(max(0.0, min(2.0, (75.0 - active_pred) / 20.0)), 1) if active_pred < 75.0 else 0.0

    return LivePredictOutput(
        subject_name=data.subject_name or "Mathematics",
        rf_prediction=rf_pred,
        xgb_prediction=xgb_pred,
        linear_prediction=lin_pred,
        active_model=active_name,
        active_prediction=active_pred,
        improvement_pct=imp_pct,
        risk_level=risk_level,
        recommended_study_hours=study_hours,
        extra_time_increase=extra_time
    )


def switch_active_model(db: Session, target_name: str, user_id: Optional[int] = None) -> dict:
    """
    Switch which regression model in ModelRegistry is active for production predictions.
    """
    key = (target_name or "").strip().lower()
    if not key:
        raise ValidationError("model_name must not be empty")

    reg_models = db.query(ModelRegistry).filter(ModelRegistry.task == "regression").order_by(ModelRegistry.id.asc()).all()
    if not reg_models:
        raise NotFoundError("No regression models registered")

    alias_matchers = {
        "linear_regression": lambda m: "linear" in m.model_name.lower(),
        "linear regression": lambda m: "linear" in m.model_name.lower(),
        "linear": lambda m: "linear" in m.model_name.lower(),
        "random_forest": lambda m: "random forest" in m.model_name.lower(),
        "random forest": lambda m: "random forest" in m.model_name.lower(),
        "rf": lambda m: "random forest" in m.model_name.lower(),
        "xgboost": lambda m: "xgboost" in m.model_name.lower(),
        "xgb": lambda m: "xgboost" in m.model_name.lower(),
    }

    matched = None
    if key in alias_matchers:
        matcher = alias_matchers[key]
        matched = next((m for m in reg_models if matcher(m)), None)
        if not matched:
            raise NotFoundError(f"Regression model '{target_name}' is not registered")
    else:
        matched = next(
            (m for m in reg_models if m.model_name.lower() == key or m.version.lower() == key),
            None,
        )
        if not matched:
            raise ValidationError(
                f"Invalid regression model '{target_name}'. Allowed: linear_regression, random_forest, xgboost"
            )

    prev_active = [m for m in reg_models if m.is_active]
    old_values = (
        {"active_model": prev_active[0].model_name, "version": prev_active[0].version}
        if len(prev_active) == 1
        else {"active_models": [m.model_name for m in prev_active]}
        if prev_active
        else None
    )

    for m in reg_models:
        m.is_active = (m.id == matched.id)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=user_id,
        action="ml_model.switched",
        entity_name="model_registry",
        entity_id=matched.id,
        old_values=old_values,
        new_values={"active_model": matched.model_name, "version": matched.version},
        reason="Admin switched active regression model",
    )
    db.commit()

    return {
        "status": "success",
        "active_model": matched.model_name,
        "version": matched.version
    }

