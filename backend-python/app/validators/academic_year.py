"""
SCHOLARIS ERP - Academic Year Validator
"""

from datetime import date
from fastapi import HTTPException, status


def validate_academic_year_dates(start_date: date, end_date: date) -> None:
    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Academic year start date must be strictly before end date"
        )
    if (end_date - start_date).days < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Academic year duration must be at least 30 days"
        )
