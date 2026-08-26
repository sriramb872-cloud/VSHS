# app/schemas/marks.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class StudentMarkInput(BaseModel):
    student_id: int = Field(..., description="Student ID")
    marks_obtained: float = Field(..., ge=0, description="Marks obtained by the student")

class MarksEntryCreate(BaseModel):
    exam_id: int = Field(..., description="Exam ID")
    marks: List[StudentMarkInput] = Field(..., description="List of student marks")

class MarksEntryUpdate(BaseModel):
    marks: List[StudentMarkInput] = Field(..., description="List of student marks to update")

class MarkResponse(BaseModel):
    id: int
    exam_id: int
    student_id: int
    marks_obtained: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MarksListResponse(BaseModel):
    total: int
    items: list[MarkResponse]
    """
SCHOLARIS ERP

Module:
Description:

TODO:
"""
