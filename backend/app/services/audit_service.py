from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.audit import AuditLog
from backend.app.core.logging import logger


def create_audit_entry(
    db: Session,
    user_id: Optional[int],
    action: str,
    entity_name: str,
    entity_id: Optional[int] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """
    Append-only audit record written in the same transaction as the change (R-014, D-013).
    """
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_name=entity_name,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        reason=reason,
        ip_address=ip_address
    )
    db.add(audit_entry)
    logger.info(f"Audit log appended: action={action}, entity={entity_name}, entity_id={entity_id}")
    return audit_entry


def get_audit_logs(
    db: Session,
    entity_name: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[AuditLog]:
    query = db.query(AuditLog)
    if entity_name:
        query = query.filter(AuditLog.entity_name == entity_name)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

