"""
SCHOLARIS ERP - Grade Validator
"""

from fastapi import HTTPException, status


def validate_grade_data(name: str, school_id: int) -> None:
    if not name or not name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade name cannot be empty")
    if school_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid school_id")
