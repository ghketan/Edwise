from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, require_admin
from backend.app.models.user import User
from backend.app.schemas.audit import AuditLogResponse
from backend.app.services.audit_service import get_audit_logs

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("/logs", response_model=List[AuditLogResponse])
def api_get_audit_logs(
    entity_name: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    R-014, D-013, M-10: Administrator reviews append-only audit trail for marks,
    attendance, enrollments, and verification actions with bounded pagination.
    """
    return get_audit_logs(
        db=db,
        entity_name=entity_name,
        action=action,
        user_id=user_id,
        skip=skip,
        limit=limit
    )
