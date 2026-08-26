"""
SCHOLARIS ERP - Student Enrollment Validator
"""

from fastapi import HTTPException, status


def validate_enrollment_data(student_id: int, academic_year_id: int, grade_id: int, section_id: int, school_id: int) -> None:
    if student_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid student_id")
    if academic_year_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid academic_year_id")
    if grade_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grade_id")
    if section_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid section_id")
    if school_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid school_id")
