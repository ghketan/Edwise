from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelRegistryResponse(BaseModel):
    id: int
    model_name: str
    version: str
    task: str
    data_source: str
    is_synthetic: bool
    feature_list: List[str]
    split_method: str
    metrics: Dict[str, Any]
    is_active: bool
    trained_at: datetime
    trained_by: str

    model_config = ConfigDict(from_attributes=True)


class StudentEstimateResponse(BaseModel):
    """
    Contract API-003: Model inference estimate with strict truth wording
    and safeguards against false reassurance (R-009, R-010, R-015, D-005, D-012).
    """
    status: str  # "success", "not_enough_data", "model_unavailable"
    value: Optional[float] = None
    interval_lower: Optional[float] = None
    interval_upper: Optional[float] = None
    confidence: Optional[float] = None
    risk_level: Optional[str] = None  # "low", "medium", "high"
    model_version: Optional[str] = None
    data_source_label: Optional[str] = None
    is_synthetic: bool = False
    data_through: Optional[str] = None
    reason_codes: Optional[List[str]] = None
    estimate_text: str
    disclaimer: str = "This estimate is generated from historical statistical patterns and serves as a prompt for teacher review, not an automated verdict or academic decision."


class ClusterGroup(BaseModel):
    cluster_id: int
    cluster_label: str
    student_count: int
    feature_means: Dict[str, float]
    description: str


class ClusterExplorationResponse(BaseModel):
    """
    K-Means exploration of student groups (R-011):
    Presented as exploratory pattern analysis, not as categories of people.
    """
    model_version: str
    n_clusters: int
    is_synthetic: bool
    note: str = "Exploratory cluster analysis based strictly on academic engagement metrics (attendance rate, exam average, assignment submission rate). This does not categorize individuals."
    clusters: List[ClusterGroup]


class FeatureDriftDetail(BaseModel):
    baseline_mean: float
    session_mean: float
    delta: float
    percent_difference: float
    drift_flag: bool


class ModelDriftResponse(BaseModel):
    """
    Model Feature Drift Monitoring (Playbook §8.6, DoD-008):
    Tracks active academic session feature means against offline training baseline means.
    """
    model_version: str
    session_id: int
    feature_drift: Dict[str, FeatureDriftDetail]
    drift_detected: bool
    status: str  # "normal", "drift_warning", "no_data"
    threshold: float
    note: str


class LivePredictInput(BaseModel):
    unit_test_score: float = Field(75.0, ge=0.0, le=100.0)
    mid_term_score: float = Field(78.0, ge=0.0, le=100.0)
    assignment_score: float = Field(82.0, ge=0.0, le=100.0)
    practical_score: float = Field(80.0, ge=0.0, le=100.0)
    attendance_pct: float = Field(90.0, ge=0.0, le=100.0)
    previous_exam_score: float = Field(72.0, ge=0.0, le=100.0)
    subject_name: Optional[str] = "Mathematics"

    @field_validator(
        "unit_test_score",
        "mid_term_score",
        "assignment_score",
        "practical_score",
        "attendance_pct",
        "previous_exam_score",
    )
    @classmethod
    def validate_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Score/attendance input must be a finite number")
        return v


class LivePredictOutput(BaseModel):
    subject_name: str
    rf_prediction: float
    xgb_prediction: float
    linear_prediction: float
    active_model: str
    active_prediction: float
    improvement_pct: float
    risk_level: str
    recommended_study_hours: float
    extra_time_increase: float


class SwitchModelRequest(BaseModel):
    model_name: str  # "linear_regression", "random_forest", "xgboost"

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("model_name cannot be empty")
        return cleaned

