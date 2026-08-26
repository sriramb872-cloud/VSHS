# app/schemas/homework.py
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

class HomeworkBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Homework title")
    description: str = Field(..., description="Homework details and instructions")
    academic_year_id: Optional[int] = Field(None, description="Academic year ID")
    grade_id: int = Field(..., description="Grade ID")
    section_id: int = Field(..., description="Section ID")
    subject_id: int = Field(..., description="Subject ID")
    due_date: date = Field(..., description="Due date for the homework")

class HomeworkCreate(HomeworkBase):
    pass

class HomeworkUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    academic_year_id: Optional[int] = None
    grade_id: Optional[int] = None
    section_id: Optional[int] = None
    subject_id: Optional[int] = None
    due_date: Optional[date] = None

class HomeworkResponse(HomeworkBase):
    id: int
    teacher_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class HomeworkListResponse(BaseModel):
    total: int
    items: list[HomeworkResponse]