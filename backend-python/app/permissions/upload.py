"""
SCHOLARIS ERP - Upload Permissions
"""

from fastapi import HTTPException, status
from app.models.role import UserRole
from app.models.user import User


def check_upload_access(user: User, upload_school_id: int = None, uploaded_by_id: int = None) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        return
    if upload_school_id and user.school_id != upload_school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access files from another school"
        )
    if uploaded_by_id and user.role == UserRole.STUDENT and user.id != uploaded_by_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Students can only access their own uploads"
        )
