"""
SCHOLARIS ERP - Section Permissions
"""

from fastapi import HTTPException, status
from app.models.role import UserRole
from app.models.user import User


def check_section_read_permission(user: User, school_id: int) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access sections of another school"
        )


def check_section_write_permission(user: User, school_id: int) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.role == UserRole.PRINCIPAL and user.school_id == school_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Only Principal or Super Admin can manage sections"
    )
