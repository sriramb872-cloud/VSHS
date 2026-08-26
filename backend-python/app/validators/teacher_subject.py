"""
SCHOLARIS ERP - Teacher Subject Assignment Validator
"""

from fastapi import HTTPException, status


def validate_teacher_subject_assignment(teacher_id: int, subject_id: int, grade_id: int, section_id: int, school_id: int) -> None:
    if teacher_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid teacher_id")
    if subject_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subject_id")
    if grade_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grade_id")
    if section_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid section_id")
    if school_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid school_id")
