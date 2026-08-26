# app/schemas/report_card.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class AssessmentComponentScore(BaseModel):
    component_name: str
    raw_marks_obtained: float
    raw_maximum_marks: float
    report_maximum_marks: float
    converted_marks: float

class SubjectAssessmentResult(BaseModel):
    assessment_name: str
    components: List[AssessmentComponentScore]
    total_obtained: float
    total_maximum: float

class SubjectReportCardDetail(BaseModel):
    subject_id: int
    subject_name: str
    assessments: List[SubjectAssessmentResult]
    subject_total_obtained: float
    subject_total_maximum: float
    percentage: float
    grade: str

class ReportCardResponse(BaseModel):
    student_id: int
    student_name: str
    grade_id: int
    section_id: int
    academic_year_id: int
    subjects: List[SubjectReportCardDetail]
    grand_total_obtained: float
    grand_total_maximum: float
    overall_percentage: float
    overall_grade: str
    overall_result: str  # Pass / Fail
    teacher_remarks: Optional[str] = None

    class Config:
        from_attributes = True

class ReportCardRemarksUpdate(BaseModel):
    teacher_remarks: str = Field(..., description="Teacher remarks for the report card")

class ReportCardListResponse(BaseModel):
    total: int
    items: List[ReportCardResponse]
    """
SCHOLARIS ERP

Module:
Description:

TODO:
"""
