"""
SCHOLARIS ERP - Attendance Validator
"""

from datetime import date
from typing import List
from fastapi import HTTPException, status
from app.models.attendance_record import AttendanceStatus


def validate_attendance_date(attendance_date: date) -> None:
    if attendance_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record attendance for a future date"
        )


def validate_attendance_status(status_val: str) -> None:
    valid_statuses = [s.value for s in AttendanceStatus]
    if status_val not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid attendance status. Must be one of: {', '.join(valid_statuses)}"
        )
