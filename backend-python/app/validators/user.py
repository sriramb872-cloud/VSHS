"""
SCHOLARIS ERP - User Validator
"""

import re
from fastapi import HTTPException, status
from app.models.role import UserRole


def validate_email_format(email: str) -> None:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(pattern, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")


def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )


def validate_user_role(role_val: str) -> None:
    valid_roles = [r.value for r in UserRole]
    if role_val not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
