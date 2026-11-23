import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    check_student_scope,
    get_current_user,
    get_db,
    require_admin,
    require_teacher_or_admin,
)
from backend.app.models.ml import ModelRegistry
from backend.app.models.user import User
from backend.app.schemas.ml import (
    ClusterExplorationResponse,
    LivePredictInput,
    LivePredictOutput,
    ModelDriftResponse,
    ModelRegistryResponse,
    StudentEstimateResponse,
    SwitchModelRequest,
)
from backend.app.services.ml_service import (
    calculate_feature_drift,
    get_kmeans_clusters,
    get_student_prediction,
    predict_live_simulator,
    switch_active_model,
)

router = APIRouter(prefix="/ml", tags=["Machine Learning & Analytics"])


@router.get("/students/{student_id}/estimate", response_model=StudentEstimateResponse)
def api_get_student_estimate(
    student_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Contract API-003, R-009, R-010, R-015, D-012, C-02:
    Teacher or Admin reads performance estimate and risk level for a student.
    Guards against false reassurance: requires at least 2 completed exams,
    otherwise returns status 'not_enough_data' with no number.
    Teacher must have scope over student's class (C-02).
    """
    check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
    return get_student_prediction(db=db, student_id=student_id, session_id=session_id)


@router.get("/models", response_model=List[ModelRegistryResponse])
def api_get_registered_models(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    D-005, §8.6: Lists active and historical models in the registry with complete metadata.
    """
    return db.query(ModelRegistry).order_by(ModelRegistry.trained_at.desc()).all()


@router.get("/clusters", response_model=ClusterExplorationResponse)
def api_get_clusters(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    R-011: K-Means exploration of student groups based strictly on academic engagement.
    Presented as exploratory pattern analysis, not as categories of people.
    """
    return get_kmeans_clusters(db=db, session_id=session_id)


@router.get("/drift", response_model=ModelDriftResponse)
def api_get_feature_drift(
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Playbook §8.6, DoD-008: Model Feature Drift Monitoring.
    Stores and compares feature means per session against training registry metadata.
    """
    return calculate_feature_drift(db=db, session_id=session_id)


sim_limit = asyncio.Semaphore(2)


@router.post("/predict-live", response_model=LivePredictOutput)
async def api_predict_live(
    payload: LivePredictInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Real-time interactive What-If score simulator across Linear Regression,
    Random Forest, and XGBoost with concurrency capping to prevent memory spikes.
    """
    async with sim_limit:
        return await run_in_threadpool(predict_live_simulator, data=payload, db=db)


@router.post("/switch-model")
def api_switch_active_model(
    payload: SwitchModelRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Switches active regression algorithm (Linear, Random Forest, XGBoost) in Model Registry.
    """
    return switch_active_model(db=db, target_name=payload.model_name, user_id=admin.id)

