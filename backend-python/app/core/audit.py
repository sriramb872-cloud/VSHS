# app/core/audit.py
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.crud.audit_log import crud_audit_log
from app.schemas.audit_log import AuditLogCreate


def write_audit_log(
    db: Session,
    *,
    user_id: Optional[int],
    school_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[Any] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        crud_audit_log.create(
            db,
            AuditLogCreate(
                user_id=user_id,
                school_id=school_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id is not None else None,
                details=details or {},
            ),
        )
    except Exception:
        # Logging must never break the primary request.
        db.rollback()
