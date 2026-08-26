"""
SCHOLARIS ERP - Audit Log Permissions
"""

from fastapi import HTTPException, status
from app.models.role import UserRole
from app.models.user import User


def check_audit_log_read_permission(user: User, school_id: int = None) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.role == UserRole.PRINCIPAL:
        if school_id and user.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot view audit logs of another school"
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Only Super Admin and Principal can view audit logs"
    )
