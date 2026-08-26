"""
SCHOLARIS ERP - Attendance Record Validator
"""

from fastapi import HTTPException, status
from app.validators.attendance import validate_attendance_date, validate_attendance_status


def validate_attendance_record_payload(student_id: int, school_id: int, record_date, status_val: str) -> None:
    if student_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid student_id")
    if school_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid school_id")
    validate_attendance_date(record_date)
    validate_attendance_status(status_val)
