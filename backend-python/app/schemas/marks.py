# app/schemas/marks.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StudentMarkInput(BaseModel):
    student_id: int = Field(..., description="Student ID")
    marks_obtained: float = Field(..., ge=0, description="Marks obtained by the student")
    remarks: Optional[str] = Field(default=None, description="Optional remarks")


class MarksSubmitPayload(BaseModel):
    exam_subject_id: int = Field(..., description="Exam Subject ID")
    marks: List[StudentMarkInput] = Field(..., description="List of student marks")


# Backward compatibility alias
MarksEntryCreate = MarksSubmitPayload


class StudentFormativeMarkInput(BaseModel):
    student_id: int = Field(..., description="Student ID")
    written_test: float = Field(default=0.0, ge=0, le=20, description="Written test marks (max 20)")
    project: float = Field(default=0.0, ge=0, le=5, description="Project marks (max 5)")
    read_reflection: float = Field(default=0.0, ge=0, le=5, description="Read reflection marks (max 5)")
    notebook: float = Field(default=0.0, ge=0, le=5, description="Notebook marks (max 5)")


class FormativeMarksSubmitPayload(BaseModel):
    exam_subject_id: int = Field(..., description="Exam Subject ID")
    marks: List[StudentFormativeMarkInput] = Field(..., description="List of student formative marks")


class MarkResponse(BaseModel):
    id: int
    exam_subject_id: int
    student_id: int
    student_name: Optional[str] = None
    roll_number: Optional[str] = None
    marks_obtained: float
    max_marks: float = 100.0
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MarksListResponse(BaseModel):
    total: int
    items: List[MarkResponse]


class StudentMarksViewItem(BaseModel):
    exam_id: int
    exam_name: str
    exam_type: str
    assessment_mode: str
    exam_subject_id: int
    subject_id: int
    subject_name: str
    marks_obtained: float
    max_marks: float
    passing_marks: float
    is_passed: bool
    components: Optional[Dict[str, float]] = None


class StudentMarksViewResponse(BaseModel):
    total: int
    items: List[StudentMarksViewItem]