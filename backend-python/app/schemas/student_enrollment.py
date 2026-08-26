"""
SCHOLARIS ERP - Student Enrollment Schemas
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class StudentEnrollmentBase(BaseModel):
    student_id: int
    academic_year_id: int
    grade_id: int
    section_id: int
    school_id: int
    roll_number: Optional[str] = Field(None, max_length=20)
    enrollment_date: date
    is_active: bool = True


class StudentEnrollmentCreate(StudentEnrollmentBase):
    pass


class StudentEnrollmentUpdate(BaseModel):
    grade_id: Optional[int] = None
    section_id: Optional[int] = None
    roll_number: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class StudentEnrollmentResponse(StudentEnrollmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
