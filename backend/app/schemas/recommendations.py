from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class RecommendationRuleBase(BaseModel):
    rule_code: str
    title: str
    indicator: str  # attendance_rate, score_drop, missing_assignments
    operator: str  # <, <=, >, >=
    threshold_value: float
    severity: str = "medium"
    template_message: str
    is_active: bool = True

    @field_validator("indicator")
    @classmethod
    def validate_indicator(cls, v: str) -> str:
        valid_indicators = {"attendance_rate", "score_drop", "missing_assignments"}
        if v not in valid_indicators:
            raise ValueError(f"Indicator must be one of {valid_indicators}")
        return v

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        valid_ops = {"<", "<=", ">", ">="}
        if v not in valid_ops:
            raise ValueError(f"Operator must be one of {valid_ops}")
        return v


class RecommendationRuleCreate(RecommendationRuleBase):
    pass


class RecommendationRuleResponse(RecommendationRuleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class StudentRecommendationResponse(BaseModel):
    id: int
    student_id: int
    student_name: str
    admission_number: str
    rule_code: str
    title: str
    trigger_value: float
    message: str
    severity: str
    review_status: str
    review_notes: Optional[str] = None
    reviewed_by: Optional[int] = None
    generated_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationReviewRequest(BaseModel):
    review_status: str  # "reviewed_no_action", "action_taken"
    review_notes: Optional[str] = None

    @field_validator("review_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = {"reviewed_no_action", "action_taken", "pending"}
        if v not in valid:
            raise ValueError(f"Status must be one of {valid}")
        return v
