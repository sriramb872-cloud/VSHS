"""
SCHOLARIS ERP - User Permissions
"""

from fastapi import HTTPException, status
from app.models.role import UserRole
from app.models.user import User


def check_user_manage_permission(current_user: User, target_school_id: int = None, target_role: UserRole = None) -> None:
    if current_user.role == UserRole.SUPER_ADMIN:
        return
    if current_user.role == UserRole.PRINCIPAL:
        if target_school_id and current_user.school_id != target_school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Principal cannot manage users of another school"
            )
        if target_role == UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Principal cannot create or manage Super Admin accounts"
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Insufficient permissions to manage users"
    )
