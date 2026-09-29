"""
SCHOLARIS ERP - Teacher Subject Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TeacherSubjectBase(BaseModel):
    teacher_id: int
    subject_id: int
    grade_id: int
    section_id: int
    school_id: int
    academic_year_id: Optional[int] = None


class TeacherSubjectCreate(TeacherSubjectBase):
    pass


class TeacherSubjectUpdate(BaseModel):
    teacher_id: Optional[int] = None
    subject_id: Optional[int] = None
    grade_id: Optional[int] = None
    section_id: Optional[int] = None
    academic_year_id: Optional[int] = None


class TeacherSubjectResponse(TeacherSubjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
