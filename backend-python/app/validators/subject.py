"""
SCHOLARIS ERP - Subject Validator
"""

from fastapi import HTTPException, status


def validate_subject_data(name: str, code: str, school_id: int) -> None:
    if not name or not name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject name cannot be empty")
    if not code or not code.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject code cannot be empty")
    if school_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid school_id")
