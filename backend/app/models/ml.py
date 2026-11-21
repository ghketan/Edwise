from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.core.database import Base


class ModelRegistry(Base):
    """
    Registry of trained offline models and their full metadata (D-005, §8.6).
    The API refuses to serve a model without metadata.
    """
    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False, unique=True)
    task = Column(String(50), nullable=False)  # regression, classification, clustering
    data_source = Column(String(150), nullable=False)  # e.g., "DS-001 UCI Student Performance" or "DS-003 Synthetic"
    is_synthetic = Column(Boolean, default=False, nullable=False)
    feature_list = Column(JSON, nullable=False)  # list of feature names used
    split_method = Column(String(150), nullable=False)  # e.g., "grouped_by_student_5_fold"
    metrics = Column(JSON, nullable=False)  # {mae, rmse, r2, precision, recall, f1, baselines}
    artifact_path = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    trained_by = Column(String(100), default="system", nullable=False)

    predictions = relationship("Prediction", back_populates="model")


class Prediction(Base):
    """
    Stored inference estimates per student and session with truth wording metadata (API-003, R-015).
    """
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(Integer, ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=False)
    task = Column(String(50), nullable=False)  # regression, classification
    predicted_value = Column(Float, nullable=True)  # expected final mark or risk probability
    interval_lower = Column(Float, nullable=True)  # lower bound of uncertainty interval
    interval_upper = Column(Float, nullable=True)  # upper bound of uncertainty interval
    confidence = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)  # low, medium, high
    reason_codes = Column(JSON, nullable=True)  # indicators triggering the prediction
    data_through_date = Column(Date, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student = relationship("Student", back_populates="predictions")
    session = relationship("AcademicSession")
    model = relationship("ModelRegistry", back_populates="predictions")

