"""
SCHOLARIS ERP - School Permissions
"""

from fastapi import HTTPException, status
from app.models.role import UserRole
from app.models.user import User


def check_school_super_admin_permission(user: User) -> None:
    if user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only Super Admin can perform platform-level school operations"
        )


def check_school_access_permission(user: User, school_id: int) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access data for another school"
        )
