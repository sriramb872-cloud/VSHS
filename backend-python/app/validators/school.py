"""
SCHOLARIS ERP - School Validator
"""

import re
from fastapi import HTTPException, status


def validate_school_code(code: str) -> None:
    if not code or not code.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School code cannot be empty")
    if not re.match(r"^[A-Za-z0-9_-]+$", code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School code must contain only alphanumeric characters, underscores, or hyphens"
        )
