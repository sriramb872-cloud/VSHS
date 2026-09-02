# app/schemas/exam.py
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ExamSubjectResponse(BaseModel):
    id: int
    exam_id: int
    subject_id: int
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    teacher_id: Optional[int] = None
    teacher_name: Optional[str] = None
    maximum_marks: float
    passing_marks: float
    is_marks_submitted: bool
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExamBase(BaseModel):
    name: str = Field(..., max_length=255, description="Exam Name (e.g. FA1, SA1)")
    exam_type: str = Field(..., max_length=100, description="Exam Type (Formative Assessment, Summative Assessment, etc.)")
    assessment_mode: str = Field(default="FORMATIVE", description="FORMATIVE or SUMMATIVE")
    academic_year_id: int = Field(..., description="Academic Year ID")
    grade_id: int = Field(..., description="Grade ID")
    section_id: int = Field(..., description="Section ID")
    start_date: date = Field(..., description="Start date of the examination window")
    end_date: date = Field(..., description="End date of the examination window")


class ExamCreate(ExamBase):
    maximum_marks: Optional[float] = Field(default=None, gt=0, description="Default max marks for subjects")
    passing_marks: Optional[float] = Field(default=None, ge=0, description="Default passing marks for subjects")


class ExamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    exam_type: Optional[str] = Field(default=None, max_length=100)
    assessment_mode: Optional[str] = None
    academic_year_id: Optional[int] = None
    grade_id: Optional[int] = None
    section_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None


class ExamResponse(ExamBase):
    id: int
    school_id: int
    status: str
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    grade_name: Optional[str] = None
    section_name: Optional[str] = None
    exam_subjects: Optional[List[ExamSubjectResponse]] = []

    class Config:
        from_attributes = True


class ExamListResponse(BaseModel):
    total: int
    items: List[ExamResponse]


class MarksStatusItem(BaseModel):
    exam_subject_id: int
    subject_id: int
    subject_name: str
    teacher_id: Optional[int] = None
    teacher_name: Optional[str] = None
    maximum_marks: float
    passing_marks: float
    is_marks_submitted: bool
    submitted_at: Optional[datetime] = None


class MarksStatusResponse(BaseModel):
    exam_id: int
    exam_name: str
    status: str
    assessment_mode: str
    total_subjects: int
    submitted_subjects: int
    is_all_submitted: bool
    items: List[MarksStatusItem]


class ExamPublishResponse(BaseModel):
    message: str
    exam_id: int
    status: str
    students_notified: int
    missing_marks_zeroed: int