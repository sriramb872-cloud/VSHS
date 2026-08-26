"""
SCHOLARIS ERP - Student Permissions
"""

from fastapi import HTTPException, status
from app.models.role import UserRole
from app.models.user import User


def check_student_read_permission(user: User, school_id: int, student_user_id: int = None) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot view students of another school"
        )
    if user.role == UserRole.STUDENT and student_user_id is not None and user.id != student_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Students can only access their own profile"
        )


def check_student_write_permission(user: User, school_id: int) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot create or update students for another school"
        )
    if user.role not in [UserRole.PRINCIPAL, UserRole.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only Principal or Teacher can manage student records"
        )
