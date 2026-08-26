# app/schemas/exam.py
from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, Field

class ExamBase(BaseModel):
    name: str = Field(..., max_length=255, description="Exam Name")
    exam_type: str = Field(..., max_length=100, description="Exam Type (Unit Test, Monthly Test, Quarterly, etc.)")
    academic_year_id: int = Field(..., description="Academic Year ID")
    grade_id: int = Field(..., description="Grade ID")
    section_id: int = Field(..., description="Section ID")
    subject_id: int = Field(..., description="Subject ID")
    exam_date: date = Field(..., description="Date of the examination")
    start_time: time = Field(..., description="Start time of the examination")
    end_time: time = Field(..., description="End time of the examination")
    maximum_marks: float = Field(..., gt=0, description="Maximum marks attainable")
    passing_marks: float = Field(..., ge=0, description="Passing marks required")
    instructions: Optional[str] = Field(default=None, description="Optional exam instructions")

class ExamCreate(ExamBase):
    pass

class ExamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    exam_type: Optional[str] = Field(default=None, max_length=100)
    academic_year_id: Optional[int] = None
    grade_id: Optional[int] = None
    section_id: Optional[int] = None
    subject_id: Optional[int] = None
    exam_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    maximum_marks: Optional[float] = Field(default=None, gt=0)
    passing_marks: Optional[float] = Field(default=None, ge=0)
    instructions: Optional[str] = None

class ExamResponse(ExamBase):
    id: int
    teacher_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ExamListResponse(BaseModel):
    total: int
    items: list[ExamResponse]