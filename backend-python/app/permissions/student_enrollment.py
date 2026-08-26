"""
SCHOLARIS ERP - Student Enrollment Permissions
"""

from fastapi import HTTPException, status
from app.models.role import UserRole
from app.models.user import User


def check_enrollment_read_permission(user: User, school_id: int, student_user_id: int = None) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access enrollments of another school"
        )
    if user.role == UserRole.STUDENT and student_user_id is not None and user.id != student_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Students can only view their own enrollment history"
        )


def check_enrollment_write_permission(user: User, school_id: int) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.role == UserRole.PRINCIPAL and user.school_id == school_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Only Principal or Super Admin can manage student enrollments"
    )
