from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.core.database import Base


class RecommendationRule(Base):
    """
    Configurable rules for generating traceable recommendations (D-008, R-012).
    """
    __tablename__ = "recommendation_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(150), nullable=False)
    indicator = Column(String(50), nullable=False)  # attendance_rate, score_drop, missing_assignments
    operator = Column(String(10), nullable=False)  # <, <=, >, >=
    threshold_value = Column(Float, nullable=False)
    severity = Column(String(20), default="medium", nullable=False)  # low, medium, high
    template_message = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    student_recommendations = relationship("StudentRecommendation", back_populates="rule", cascade="all, delete-orphan")


class StudentRecommendation(Base):
    """
    Specific recommendation generated for a student with triggering values and review status (UI-005, §6.3).
    """
    __tablename__ = "student_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(Integer, ForeignKey("recommendation_rules.id", ondelete="CASCADE"), nullable=False)
    trigger_value = Column(Float, nullable=False)  # exact triggering metric value
    message = Column(Text, nullable=False)
    review_status = Column(String(30), default="pending", nullable=False)  # pending, reviewed_no_action, action_taken
    reviewed_by = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    student = relationship("Student", back_populates="recommendations")
    session = relationship("AcademicSession")
    rule = relationship("RecommendationRule", back_populates="student_recommendations")
    reviewer = relationship("Teacher")

