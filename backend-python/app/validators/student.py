"""
SCHOLARIS ERP - Student Validator
"""

from datetime import date
from fastapi import HTTPException, status


def validate_student_data(first_name: str, last_name: str, admission_number: str, dob: date = None) -> None:
    if not first_name or not first_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="First name cannot be empty")
    if not last_name or not last_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Last name cannot be empty")
    if not admission_number or not admission_number.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admission number cannot be empty")
    if dob and dob > date.today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date of birth cannot be in the future")
