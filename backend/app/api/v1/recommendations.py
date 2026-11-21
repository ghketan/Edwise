from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    check_student_scope,
    get_current_user,
    get_db,
    require_admin,
    require_teacher_or_admin,
)
from backend.app.core.exceptions import NotFoundError
from backend.app.models.recommendations import StudentRecommendation
from backend.app.models.user import User
from backend.app.schemas.recommendations import (
    RecommendationReviewRequest,
    RecommendationRuleCreate,
    RecommendationRuleResponse,
    StudentRecommendationResponse,
)
from backend.app.services.audit_service import create_audit_entry
from backend.app.services.recommendation_service import (
    create_recommendation_rule,
    evaluate_rules_for_student,
    get_recommendation_rules,
    get_recommendations_for_student,
    review_recommendation,
)

router = APIRouter(prefix="/recommendations", tags=["Rule-Based Recommendations"])


@router.get("/rules", response_model=List[RecommendationRuleResponse])
def api_get_rules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_recommendation_rules(db)


@router.post("/rules", response_model=RecommendationRuleResponse)
def api_create_rule(
    rule_in: RecommendationRuleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    rule = create_recommendation_rule(db, rule_in)
    create_audit_entry(
        db=db,
        user_id=admin.id,
        action="recommendation_rule.created",
        entity_name="recommendation_rule",
        entity_id=rule.id,
        new_values=rule_in.model_dump(mode="json"),
        reason="Admin added recommendation rule"
    )
    db.commit()
    return rule


@router.get("/student/{student_id}", response_model=List[StudentRecommendationResponse])
def api_get_student_recommendations(
    student_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    R-012, D-008, C-02: Rule-based recommendations traceable to exact indicator values.
    Teacher must have scope over student's class (C-02).
    """
    check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
    evaluate_rules_for_student(db, student_id=student_id, session_id=session_id)
    return get_recommendations_for_student(db, student_id=student_id, session_id=session_id)


@router.put("/{rec_id}/review", response_model=StudentRecommendationResponse)
def api_review_recommendation(
    rec_id: int,
    review_in: RecommendationReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Teacher reviews a recommendation card and logs 'reviewed_no_action' or 'action_taken' with notes.
    Enforces that teacher teaches the student's class (C-02).
    """
    rec_check = db.query(StudentRecommendation).filter(StudentRecommendation.id == rec_id).first()
    if not rec_check:
        raise NotFoundError("Recommendation not found")

    check_student_scope(db=db, user=current_user, student_id=rec_check.student_id, session_id=rec_check.session_id)

    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    rec = review_recommendation(
        db=db,
        rec_id=rec_id,
        review_in=review_in,
        teacher_id=teacher_id,
        user_id=current_user.id
    )
    return StudentRecommendationResponse(
        id=rec.id,
        student_id=rec.student_id,
        student_name=rec.student.full_name,
        admission_number=rec.student.admission_number,
        rule_code=rec.rule.rule_code,
        title=rec.rule.title,
        trigger_value=rec.trigger_value,
        message=rec.message,
        severity=rec.rule.severity,
        review_status=rec.review_status,
        review_notes=rec.review_notes,
        reviewed_by=rec.reviewed_by,
        generated_at=rec.generated_at,
        reviewed_at=rec.reviewed_at
    )
