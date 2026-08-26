"""
SCHOLARIS ERP - Section Validator
"""

from fastapi import HTTPException, status


def validate_section_data(name: str, grade_id: int, school_id: int, capacity: int = None) -> None:
    if not name or not name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section name cannot be empty")
    if grade_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grade_id")
    if school_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid school_id")
    if capacity is not None and capacity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Capacity must be greater than 0")
