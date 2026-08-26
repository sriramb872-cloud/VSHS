"""
SCHOLARIS ERP - Teacher Validator
"""

from fastapi import HTTPException, status


def validate_teacher_data(first_name: str, last_name: str, employee_id: str, school_id: int) -> None:
    if not first_name or not first_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Teacher first name cannot be empty")
    if not last_name or not last_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Teacher last name cannot be empty")
    if not employee_id or not employee_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee ID cannot be empty")
    if school_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid school_id")
