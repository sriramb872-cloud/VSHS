# backend-python/app/routers/v1/audit_logs.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    school_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"])),
):
    query = db.query(AuditLog)
    if school_id is not None:
        query = query.filter(AuditLog.school_id == school_id)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if resource_type is not None:
        query = query.filter(AuditLog.resource_type == resource_type)
    return (
        query.order_by(AuditLog.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )